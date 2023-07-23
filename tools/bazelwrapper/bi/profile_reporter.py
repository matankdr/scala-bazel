from bazelwrapper.bi import frog
from bazelwrapper.bi.profile import Profile
from bazelwrapper.bi.schema import ProfileEventBatch, bi_events_of, ProfileEvent, StatsEvent, micros_to_millis
from bazelwrapper.context import Context
from bazelwrapper.utils.env_vars import non_empty_env_var_value
from bazelwrapper.utils.feature_flags import Flag

_use_gzip_flag = Flag(
    full_cli_flag="--wix_use_gzip_for_frog_api"
)

_no_batch_api = Flag(
    full_cli_flag="--wix_disable_batch_frog_api",
    env_var_name="WIX_DEVEX_DISABLE_FROG_BATCHES"
)

# IMPORTANT:
# The size of a batch is critical for real-time dashboard data delivery. A batch that exceeds 64k on the BI system
# backend (after their enrichment!) will not pass through to grafana, because the BI system uses UDP to dispatch events
# and batches to the relevant sub-systems and that poses a technical limitation on the message size.
#
# Testing with Bazel trace events, 50 seems to work nicely most of the time and 100 is sometimes edgy. The size of a
# batch depends on the size of the data of course, so keep that in mind before changing and experiment with your
# specific data.
_DEVEX_FROG_BATCH_SIZE_ENV_VAR_NAME = "WIX_DEVEX_FROG_BATCH_SIZE"
_FROG_DEFAULT_BATCH_SIZE = "50"


def process(profile: Profile, ctx: Context):
    use_gzip = _use_gzip_flag.on(ctx)
    ctx.logger.debug("Gzip compression for Frog? {}".format(use_gzip))
    no_batch = _no_batch_api.on(ctx)
    ctx.logger.debug("Frog batch API disabled? {}".format(no_batch))
    batch_size = _frog_batch_size(ctx)
    ctx.logger.debug("Frog batch size is set to? {}".format(batch_size))
    ctx.logger.info("Processing profile for build_id='{}'".format(profile.build_id()))

    success_count = 0
    total_count = 0
    with frog.client() as frog_client:
        stats = StatsEventHandler(frog_client=frog_client, use_gzip=use_gzip)
        raw_handler = raw_event_handler(
            frog_client=frog_client, use_batch=not no_batch, use_gzip=use_gzip, batch_size=batch_size)

        for profile_event in bi_events_of(profile):
            if _should_report(profile_event):
                total_count += 1
                success_count += raw_handler.process(profile_event, ctx)

                stats.process(profile_event, ctx)

                if total_count % (4 * batch_size) == 0:
                    ctx.logger.debug("{count} events processed...".format(count=total_count))

        success_count += raw_handler.flush(ctx)
        stats.flush(ctx)

    ctx.logger.debug(
        "Successfully sent {success_count} events out of {total_count} events sent.".format(
            success_count=success_count, total_count=total_count
        )
    )
    ctx.logger.info(
        "Finished processing profile '{file_path}'.".format(file_path=profile.file_path)
    )


class ProfileEventMatcher:
    def __init__(self, category, name, phase):
        self.category = category
        self.name = name
        self.phase = phase

    def matches(self, event: ProfileEvent) -> bool:
        return event.category() == self.category and \
               event.name() == self.name and \
               event.phase() == self.phase


def raw_event_handler(frog_client, use_batch, use_gzip, batch_size):
    if use_batch:
        raw_handler = RawBatchEventHandler(
            frog_client=frog_client, use_gzip=use_gzip, batch_size=batch_size)
    else:
        raw_handler = RawEventHandler(frog_client=frog_client, use_gzip=use_gzip)

    return raw_handler


class RawEventHandler:

    def __init__(self, frog_client, use_gzip):
        self.frog_client = frog_client
        self.use_gzip = use_gzip
        self.ordinal = 0

    def process(self, event: ProfileEvent, ctx: Context):
        event.set_ordinal(self._next_ordinal())
        sent = self.frog_client.post_form(event=event, use_gzip=self.use_gzip)

        return 1 if sent else 0

    def flush(self, ctx: Context):
        return 0

    def _next_ordinal(self):
        self.ordinal += 1
        return self.ordinal


class RawBatchEventHandler(RawEventHandler):

    def __init__(self, frog_client, use_gzip, batch_size):
        super().__init__(frog_client, use_gzip)
        self.ordinal = 0
        self._batch_events = []
        self._batch_size = batch_size

    def process(self, event: ProfileEvent, ctx: Context):
        event.set_ordinal(self._next_ordinal())
        self._batch_events.append(event)
        return self._send_batch(force=False, ctx=ctx)

    def flush(self, ctx: Context):
        return self._send_batch(force=True, ctx=ctx)

    def _send_batch(self, force, ctx):
        current_batch_size = len(self._batch_events)

        if current_batch_size > 0 and (force or current_batch_size == self._batch_size):
            batch = ProfileEventBatch.create(events=self._batch_events)
            self._batch_events = []
            if self.frog_client.post_batch(
                    batch=batch,
                    use_gzip=self.use_gzip
            ):
                ctx.logger.debug("Batch sent successfully (size={})".format(current_batch_size))
                return current_batch_size

        return 0


class StatsEventHandler:
    _finish_event_matcher = ProfileEventMatcher(category="general information", name="Finishing", phase="i")
    _run_analysis_event_matcher = \
        ProfileEventMatcher(category="general information", name="runAnalysisPhase", phase="X")
    _remote_cache_check_event_matcher = \
        ProfileEventMatcher(category="remote action cache check", name="check cache hit", phase="X")
    _remote_cache_download_event_matcher = \
        ProfileEventMatcher(category="remote output download", name="download outputs", phase="X")
    _remote_cache_download_minimal_event_matcher = \
        ProfileEventMatcher(category="remote output download", name="download outputs minimal", phase="X")
    _remote_cache_upload_event_matcher = \
        ProfileEventMatcher(category="Remote execution upload time", name="upload outputs", phase="X")

    def __init__(self, frog_client, use_gzip):
        self.frog_client = frog_client
        self.use_gzip = use_gzip
        self._analysis_duration = None
        self._total_duration = None
        self._remote_cache_checks = 0
        self._remote_downloads = 0
        self._remote_uploads = 0
        self._remote_cache_total_check_duration = 0
        self._remote_output_total_download_duration = 0
        self._remote_output_total_upload_duration = 0

    def process(self, event: ProfileEvent, ctx: Context) -> int:
        if self._finish_event_matcher.matches(event):
            ctx.logger.debug("Finish event found. Total build time recorded.")
            # The timestamp of the finish event is the build duration.
            # Timestamps in bazel profiles are relative to the the start time of the build.
            self._total_duration = event.timestamp_milli()

            if self._send(event.headers, self.use_gzip, ctx):
                ctx.logger.info("Stats event send successfully.")
                return 1
        else:
            self._observe(event, ctx)

        return 0

    def flush(self, ctx: Context):
        return 0

    def _observe(self, event: ProfileEvent, ctx: Context):
        if self._run_analysis_event_matcher.matches(event):
            ctx.logger.debug("Analysis phase duration recorded.")
            self._analysis_duration = event.duration_millis()

        elif self._remote_cache_check_event_matcher.matches(event):
            self._remote_cache_checks += 1
            self._remote_cache_total_check_duration += event.duration_micro()

        elif self._remote_cache_download_event_matcher.matches(event) or \
                self._remote_cache_download_minimal_event_matcher.matches(event):
            self._remote_downloads += 1
            self._remote_output_total_download_duration += event.duration_micro()

        elif self._remote_cache_upload_event_matcher.matches(event):
            self._remote_uploads += 1
            self._remote_output_total_upload_duration += event.duration_micro()

    def _send(self, headers, use_gzip, ctx):
        ctx.logger.info("Sending build stats event...")

        # IMPORTANT: remote_downloads + remote_uploads != remote_cache_checks
        #   => cache hit rate cannot be calculated based on these numbers.
        data = {
            "total_duration": self._total_duration,
            "remote_cache_checks": self._remote_cache_checks,
            "remote_downloads": self._remote_downloads,
            "remote_uploads": self._remote_uploads,
            "remote_cache_total_check_duration": micros_to_millis(self._remote_cache_total_check_duration),
            "remote_output_total_download_duration": micros_to_millis(self._remote_output_total_download_duration),
            "remote_output_total_upload_duration": micros_to_millis(self._remote_output_total_upload_duration),
        }

        if self._analysis_duration is not None:
            data["analysis_duration"] = self._analysis_duration

        stats_event = StatsEvent(
            raw_data=data,
            headers=headers
        )

        return self.frog_client.post_form(event=stats_event, use_gzip=use_gzip)


def _should_report(event: ProfileEvent):
    # counter events are not interesting to us at this point and by removing them we can speed up the
    # reporting process significantly and in a simple way
    return event.phase() != "C"


def _frog_batch_size(ctx: Context):
    return int(
        non_empty_env_var_value(
            name=_DEVEX_FROG_BATCH_SIZE_ENV_VAR_NAME,
            default_fn=lambda x: _FROG_DEFAULT_BATCH_SIZE,
            ctx=ctx
        )
    )
