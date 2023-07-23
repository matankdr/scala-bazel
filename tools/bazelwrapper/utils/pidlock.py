import os
import signal
import threading
import time
from pathlib import Path
from typing import Callable

from bazelwrapper.utils.logging import get_default_logger

DEFAULT_LOCK_TIMEOUT_SEC = 60


class Lock:
    def __init__(self,
                 file_path,
                 on_failure: Callable[[int], any],
                 timeout_sec=DEFAULT_LOCK_TIMEOUT_SEC,
                 auto_refresh=False):
        self._pid = os.getpid()
        self._lock_file_path = file_path
        self._lock_timeout_sec = timeout_sec
        self._on_lock_failure = on_failure
        self._auto_refresh = auto_refresh
        self._auto_refresh = auto_refresh

    def __enter__(self):
        self.try_acquire()

        # If more than one process tries to lock at the same time only the last one will actually acquire.
        acquired, pid = self._acquired_status()
        if not acquired:
            self._on_lock_failure(pid)

        elif self._auto_refresh:
            self._maintainer_thread = LockMaintainer(
                lock=self,
                # Using a third of the timeout value to allow two refresh attempts before the lock becomes stale.
                interval=self._lock_timeout_sec / 3
            ).start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

        if exc_val is not None:
            raise exc_val

    def try_acquire(self):
        if not os.path.exists(self._lock_file_path):
            self._do_acquire()
        else:
            acquired, pid = self._acquired_status()
            if not acquired and self._is_lock_stale():
                # Another process' lock has timed-out!
                _kill_safe(pid)
                self._do_acquire()

    def release(self):
        if self.is_acquired():
            os.remove(self._lock_file_path)
            return True

        return False

    def refresh(self):
        p = Path(self._lock_file_path)
        if p.exists() and self.is_acquired():
            p.touch(exist_ok=True)

            return True

        return False

    def is_acquired(self):
        rtn, _ = self._acquired_status()
        return rtn

    def _do_acquire(self):
        with open(self._lock_file_path, "w") as lock_file:
            lock_file.write(str(self._pid))

    def _is_lock_stale(self):
        try:
            return os.path.getmtime(self._lock_file_path) < time.time() - self._lock_timeout_sec
        except FileNotFoundError:
            # Protecting against race condition with another process.
            return False

    def _acquired_status(self):
        pid = 0

        try:
            if os.path.exists(self._lock_file_path):
                with open(self._lock_file_path) as lock_file:
                    pid = int(lock_file.read())

        except Exception:
            return False, pid

        return pid == self._pid, pid


class LockMaintainer:
    def __init__(self, lock: Lock, interval: float):
        self._lock = lock
        self._interval = interval
        self._logger = get_default_logger()
        self._register_exit_signal_handlers()

    def _register_exit_signal_handlers(self):
        """
        We register signal handlers for SIG_TERM and SIG_INT as a best effort mechanism for clean exit.
        The primary use of this is to release the lock so that other processes will be able to acquire immediately.
        Otherwise they will have to wait for the lock to become stale.
        """
        try:
            signal.signal(signal.SIGTERM, self._on_exit_signal)
            signal.signal(signal.SIGINT, self._on_exit_signal)
        except Exception as ex:
            self._logger.warn("Failed to register signal handlers")
            self._logger.exception(ex)

    # noinspection PyUnusedLocal
    def _on_exit_signal(self, signum, frame):
        try:
            self._logger.error("Received stop signal {}".format(signum))
            self._logger.info("Releasing lock and exiting...".format(signum))
            self._lock.release()
        finally:
            exit(128 + signum)  # following a common exit code convention

    def refresh_lock_until_released(self):
        logger = self._logger

        logger.info("Lock auto-refresh thread has started...")
        logger.debug("Refresh interval is {}s".format(self._interval))

        time.sleep(self._interval)

        while self._lock.is_acquired():
            logger.debug("Going to refresh lock...")

            if self._lock.refresh():
                logger.debug("Lock refreshed successfully. will refresh again in {interval}s...".format(
                    interval=self._interval))
            else:
                logger.warning("Failed to refresh lock. Will try again on the next interval.")

            time.sleep(self._interval)

        logger.info("Lock auto-refresh thread is exiting...")

    def start(self) -> threading.Thread:
        lock_maintainer_thread = threading.Thread(target=self.refresh_lock_until_released)
        lock_maintainer_thread.setDaemon(True)
        lock_maintainer_thread.start()

        return lock_maintainer_thread


def _kill_safe(pid):
    if pid > 0:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
