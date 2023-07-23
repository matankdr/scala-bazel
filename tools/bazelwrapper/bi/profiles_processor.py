import os
from os import path

from bazelwrapper.bi.profile import Profile, list_all_by_mtime
from bazelwrapper.bi.profile_reporter import process
from bazelwrapper.context import Context


def _delete(profile: Profile, ctx: Context):
    def last_command_profile_info_path_for(file_name):
        # last command profiles info is kept out of the profiles directory for convenience and to avoid clashes
        return os.path.join(ctx.config_dir, file_name)

    if path.exists(profile.file_path):
        ctx.logger.debug("Deleting profile: {path}".format(path=profile.file_path))

        last_profile_path = last_command_profile_info_path_for("last.command.prof.gz")
        os.replace(src=profile.file_path, dst=last_profile_path)

    if path.exists(profile.info_file_path):
        ctx.logger.debug("Deleting profile info file: {path}".format(path=profile.info_file_path))

        last_profile_info_path = last_command_profile_info_path_for("last.command.prof.gz.info")
        os.replace(src=profile.info_file_path, dst=last_profile_info_path)


def _process(profile: Profile, ctx: Context):
    try:
        process(profile, ctx)

    except Exception as e:
        ctx.logger.exception(e)
        ctx.logger.error("Failed to process profile '{file_path}'. {err}".format(file_path=profile.file_path, err=e))

    finally:
        # We delete every processed profile even if we failed because we don't want to process the same event twice and
        # we can't afford a sophisticated tracking mechanism on dev workstations.
        if not ctx.profile_path_override:
            _delete(profile, ctx)


def process_profiles(ctx: Context, process_fn=_process, delete_fn=_delete):
    def process_current_profiles():
        processed_profiles = 0
        if ctx.profile_path_override:
            profiles = [Profile(ctx.profile_path_override)]
        else:
            profiles = list_all_by_mtime(ctx)
        
        for profile in profiles:

            if profile.is_stale():
                ctx.logger.info("Going to delete stale profile: {path}".format(path=profile.file_path))
                delete_fn(profile, ctx)

            elif profile.is_ready():
                ctx.logger.info("Going to process profile: {path}".format(path=profile.file_path))
                processed_profiles += 1
                process_fn(profile, ctx)

            else:
                ctx.logger.info("Not ready yet. Skipping {path}...".format(path=profile.file_path))

        return processed_profiles

    # since directory listing is momentary, we want to run again as long as there are more profiles in order to process
    # profiles that might have been created while we processed the previous batch.
    if ctx.profile_path_override: # incase we are overriding, there will be only one profile
        process_current_profiles()
    else:
        while process_current_profiles() > 0:
            pass
