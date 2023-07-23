import os
import socket
import logging

from bazelwrapper.bi.profiles_processor import process_profiles
from bazelwrapper.context import create_cli_context, config_dir, create_logger
from bazelwrapper.utils.logging import daily_log_file_handler
from bazelwrapper.utils.pidlock import Lock

LOCK_FAILURE_EXIT_CODE = 3

# Setting global socket timeouts as a best effort
_DEFAULT_SOCKET_TIMEOUT = 3.0
socket.setdefaulttimeout(_DEFAULT_SOCKET_TIMEOUT)


def _create_file_logger(name: str):
    logs_dir = os.path.join(config_dir(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, name)
    log_level = os.environ.get("WIX_DEVEX_BI_REPORTER_LOG_LEVEL") or "DEBUG"

    return create_logger(level=logging.getLevelName(log_level), handler=daily_log_file_handler(log_path=log_path))


def _on_process_lock_failed(locker_pid):
    lock_file_path = os.path.join(config_dir(), ".reporter_lock.log.lock")
    with Lock(file_path=lock_file_path, on_failure=_on_process_lock_failed):
        # Using a separate logger in order to avoid corrupting the main log, which is used by the locking process.
        logger = _create_file_logger("reporter_lock.log")
        logger.warning("Failed to acquire process lock. "
                       "The lock is currently held by pid={pid}. "
                       "Exiting...".format(pid=locker_pid))

    exit(LOCK_FAILURE_EXIT_CODE)


def main():
    # The reason we're creating the main logger here, is to make sure it is initialized for any code that might be using
    # utils.logging.get_default_logger(), like the LockMaintainer thread..
    main_logger = _create_file_logger("reporter.log")

    # Writing to global system resources such as files outside of the lock block may result is file errors, corruptions
    # duplicate reports and other oddities.
    lock_file_path = os.path.join(config_dir(), ".reporter.lock")
    with Lock(file_path=lock_file_path, on_failure=_on_process_lock_failed, auto_refresh=True):
        ctx = create_cli_context(logger=main_logger)

        ctx.logger.info("Reporter starting...")

        try:
            process_profiles(ctx)
        except Exception as ex:
            ctx.logger.exception(ex)
        finally:
            ctx.logger.info("Reporter finished.")

