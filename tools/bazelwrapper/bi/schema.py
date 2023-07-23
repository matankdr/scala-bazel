import time
from typing import List, Optional, Generator

from bazelwrapper.bi.frog import EventMeta, BiEvent, Batch, BatchEvent
from bazelwrapper.bi.profile import Profile
from bazelwrapper.context import Context
from bazelwrapper.env.info import build_info_snapshot

LOCAL_DEVEX_PROJECT_NAME = "local-devex"
DEVEX_SOURCE_ID = 119

BUILD_COMMAND_FIELD_NAME = "build_command"
BUILD_COMMAND_TARGETS_FIELD_NAME = "build_command_targets"
EXIT_CODE_FIELD_NAME = "exit_code"
CORRELATION_ID_FIELD_NAME = "correlation_id"
ENV_TYPE_FIELD_NAME = 'env_type'
BUILD_TYPE_FIELD_NAME = 'build_type' # used by CI to distinguish between branch/crossrepo/pr/master/etc, in local builds it would be empty
ENV_ID_FIELD_NAME = 'env_id'
OS_FAMILY_FIELD_NAME = 'os_family'
OS_VERSION_FIELD_NAME = 'os_version'
TOTAL_RAM_FIELD_NAME = 'total_ram'
PROCESSOR_FIELD_NAME = 'proccessor_architecture'
CPUS_FIELD_NAME = 'cpus'
BUILD_ID_FIELD_NAME = "build_id"
BUILD_TIMESTAMP_FIELD_NAME = "build_timestamp"
ORDINAL_FIELD_NAME = "ordinal"
TOOLS_VERSION_FIELD_NAME = "tools_version"
WIXTALLER_VERSION_FIELD_NAME = "wixtaller_version"
PYTHON_VERSION_FIELD_NAME = "python_version"
REPOSITORY_FIELD_NAME = "repository"
PROFILE_EVENT_FIELD_PREFIX = "te_"
VMR_REPO_RULE_TYPE_NAME = "vmr_repo_rule_type"
VMR_BUILD_POST_INVALIDATION_NAME = "vmr_build_post_invalidation"
VMR_VECTOR_MODE_NAME = "vmr_vector_mode"
REMOTE_CACHE_PROVIDER = "remote_cache_provider"

_TIMESTAMP_FIELD_NAME = "{prefix}ts".format(prefix=PROFILE_EVENT_FIELD_PREFIX)
_TIMESTAMP_MS_FIELD_NAME = 'ts_ms'

BAZEL_PROFILE_EVENT_META = EventMeta(
    project=LOCAL_DEVEX_PROJECT_NAME,
    source_id=DEVEX_SOURCE_ID,
    event_id=2,
)

BAZEL_STATS_EVENT_META = EventMeta(
    project=LOCAL_DEVEX_PROJECT_NAME,
    source_id=DEVEX_SOURCE_ID,
    event_id=3,
)


class StatsEvent(BiEvent):
    def __init__(self, raw_data: dict, headers: dict):
        super().__init__(raw_data, headers, BAZEL_STATS_EVENT_META)
        self.headers = headers


class ProfileEvent(BiEvent):
    def __init__(self, raw_data: dict, headers: dict):
        super().__init__(raw_data, headers, BAZEL_PROFILE_EVENT_META)
        self._ordinal = -1

    def name(self):
        return self.data.get("name", None)

    def category(self):
        return self.data.get("cat", None)

    def phase(self):
        return self.data.get("ph", None)

    def timestamp_micro(self):
        return self.data.get("ts", None)

    def duration_micro(self):
        return self.data.get("dur", None)

    def timestamp_milli(self):
        micros = self.timestamp_micro()
        return micros_to_millis(micros) if micros is not None else None

    def duration_millis(self):
        micros = self.duration_micro()
        return micros_to_millis(micros) if micros is not None else None

    def build_id(self):
        return self.headers.get(BUILD_ID_FIELD_NAME, None)

    def set_ordinal(self, ordinal: int):
        self._ordinal = ordinal

    def to_bi_schema(self, include_headers=True):
        # The ordinal filed must be set before sending the event and reflect the order of processed events, excluding
        # filtered events. The sequence of ordinal values must not have holes in it - this is how we know we got
        # everything on the backend.
        assert self._ordinal != -1, "Ordinal is expected to be set at this point."

        bi_event = {
            ORDINAL_FIELD_NAME: self._ordinal,
            **_enrich(_prefix_raw_event_fields(self.data)),
        }

        if include_headers:
            bi_event = {**self.headers, **bi_event}

        return bi_event


def bi_events_of(profile: Profile) -> Generator[ProfileEvent, None, None]:
    header_fields = _prepare_header_fields(profile)

    ordinal = 0
    for event in profile.trace_events():
        ordinal += 1
        yield ProfileEvent(raw_data=event, headers=header_fields)


def build_event_info_with(bazel_exit_code: int, ctx: Context):
    return {
        EXIT_CODE_FIELD_NAME: bazel_exit_code,
        **build_info_snapshot(ctx)
    }


def validate_info_schema(profile: Profile):
    """
    This function validates the schema structure of the environment info dictionary against the basic BI schema
    definition. Value types are not validated.
    """
    info = profile.info()

    assert len(info) == 21
    assert "timestamp" in info and isinstance(info["timestamp"], float)
    assert BUILD_COMMAND_FIELD_NAME in info and isinstance(info[BUILD_COMMAND_FIELD_NAME], str)
    assert BUILD_COMMAND_TARGETS_FIELD_NAME in info and isinstance(info[BUILD_COMMAND_TARGETS_FIELD_NAME], str)
    assert EXIT_CODE_FIELD_NAME in info and isinstance(info[EXIT_CODE_FIELD_NAME], int)
    assert CORRELATION_ID_FIELD_NAME in info and isinstance(info[CORRELATION_ID_FIELD_NAME], str)
    assert ENV_ID_FIELD_NAME in info and isinstance(info[ENV_ID_FIELD_NAME], str)
    assert ENV_TYPE_FIELD_NAME in info and isinstance(info[ENV_TYPE_FIELD_NAME], str)
    assert BUILD_TYPE_FIELD_NAME in info and isinstance(info[BUILD_TYPE_FIELD_NAME], str)
    assert TOOLS_VERSION_FIELD_NAME in info and isinstance(info[TOOLS_VERSION_FIELD_NAME], str)
    assert WIXTALLER_VERSION_FIELD_NAME in info and isinstance(info[WIXTALLER_VERSION_FIELD_NAME], str)
    assert OS_FAMILY_FIELD_NAME in info and isinstance(info[OS_FAMILY_FIELD_NAME], str)
    assert OS_VERSION_FIELD_NAME in info and isinstance(info[OS_VERSION_FIELD_NAME], str)
    assert CPUS_FIELD_NAME in info and isinstance(info[CPUS_FIELD_NAME], int)
    assert TOTAL_RAM_FIELD_NAME in info and isinstance(info[TOTAL_RAM_FIELD_NAME], int)
    assert PROCESSOR_FIELD_NAME in info and isinstance(info[PROCESSOR_FIELD_NAME], str)
    assert PYTHON_VERSION_FIELD_NAME in info and isinstance(info[PYTHON_VERSION_FIELD_NAME], str)
    assert REPOSITORY_FIELD_NAME in info and isinstance(info[REPOSITORY_FIELD_NAME], str)
    assert VMR_REPO_RULE_TYPE_NAME in info and isinstance(info[VMR_REPO_RULE_TYPE_NAME], str)
    assert VMR_BUILD_POST_INVALIDATION_NAME in info and isinstance(info[VMR_BUILD_POST_INVALIDATION_NAME], bool)
    assert VMR_VECTOR_MODE_NAME in info and isinstance(info[VMR_VECTOR_MODE_NAME], str)
    assert REMOTE_CACHE_PROVIDER in info and isinstance(info[REMOTE_CACHE_PROVIDER], str)


class ProfileEventBatch:
    """
    This is a helper specific to ProfileEvent batch creation. The reason it is not generic is that these events are not
    created by us and in order to properly reproduce their correct timestamp, we need to decode the relative timestamp
    field reported by Bazel. This behavior is very specific to this implementation and will not allow mixing other types
    of events that don't share the same logic.
    """

    @staticmethod
    def create(events: List[ProfileEvent]) -> Optional[Batch]:
        """
        Retroactively creates a frog compatible BatchPayload object from Bazel profile events.
        """

        if len(events) == 0:
            return None

        headers = events[0].headers
        meta = events[0].meta

        batch_time_offset = ProfileEventBatch._calculate_batch_offset(headers)

        return Batch(
            dt=batch_time_offset,
            g=headers,
            e=ProfileEventBatch._create_events_list(events),
            meta=meta,
        )

    @staticmethod
    def _create_events_list(events: List[ProfileEvent]) -> List[BatchEvent]:
        batch_events = []

        min_timestamp = ProfileEventBatch._find_min_timestamp(events)

        def event_time_offset():
            return ProfileEventBatch._ts_ms_of(event) - min_timestamp

        for event in events:
            offset = event_time_offset()

            batch_events.append(
                BatchEvent(dt=offset, f=event)
            )

        return batch_events

    @staticmethod
    def _find_min_timestamp(events: List[ProfileEvent]):
        min_ts_ms = ProfileEventBatch._ts_ms_of(events[0])
        for event in events:
            ts_ms = ProfileEventBatch._ts_ms_of(event)
            min_ts_ms = min(ts_ms, min_ts_ms)

        return min_ts_ms

    @staticmethod
    def _ts_ms_of(event: ProfileEvent):
        timestamp = event.timestamp_milli()
        return timestamp if timestamp is not None and timestamp >= 0 else 0

    @staticmethod
    def _calculate_batch_offset(header):
        build_timestamp_ms = header[BUILD_TIMESTAMP_FIELD_NAME]
        now_ms = int(time.time() * 1000)
        return now_ms - build_timestamp_ms


def _prefix_raw_event_fields(d: dict):
    return {
        "{prefix}{name}".format(prefix=PROFILE_EVENT_FIELD_PREFIX, name=k): v for k, v in d.items()
    }


def _prepare_header_fields(profile: Profile):
    header_fields = profile.info().copy()

    header_fields[BUILD_TIMESTAMP_FIELD_NAME] = int(header_fields.pop('timestamp') * 1000)
    header_fields[BUILD_ID_FIELD_NAME] = profile.build_id()

    return header_fields


def _enrich(prefixed_event_data: dict):
    if _TIMESTAMP_FIELD_NAME in prefixed_event_data:
        return {
            # We add a millis version of 'ts' to get better SQL support on the BI platform
            _TIMESTAMP_MS_FIELD_NAME: micros_to_millis(prefixed_event_data[_TIMESTAMP_FIELD_NAME]),
            **prefixed_event_data,
        }
    else:
        return prefixed_event_data


def micros_to_millis(micros):
    return round(micros / 1000)
