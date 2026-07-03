"""Local background agent that checks LinkedIn jobs every hour."""

import logging
import os
import signal
import sys
import time
from logging.handlers import RotatingFileHandler

from job_monitor.monitor import run_monitor
from job_monitor.paths import LOG_FILE, PID_FILE, ensure_data_dirs, load_local_config

CHECK_INTERVAL_SECONDS = int(os.environ.get("JOB_MONITOR_INTERVAL_SECONDS", "3600"))
_shutdown_requested = False


def _handle_signal(signum, _frame) -> None:
    global _shutdown_requested
    logging.getLogger(__name__).info("Received signal %s, shutting down...", signum)
    _shutdown_requested = True


def _setup_logging(to_file: bool = True) -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    if to_file:
        ensure_data_dirs()
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def _write_pid() -> None:
    ensure_data_dirs()
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def _remove_pid() -> None:
    if PID_FILE.exists():
        PID_FILE.unlink(missing_ok=True)


def run_agent_loop() -> None:
    """Run the monitor in a loop until a shutdown signal is received."""
    global _shutdown_requested

    load_local_config()
    _setup_logging(to_file=True)
    logger = logging.getLogger(__name__)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    _write_pid()
    logger.info(
        "Local job monitor agent started (pid=%s, interval=%ss)",
        os.getpid(),
        CHECK_INTERVAL_SECONDS,
    )

    try:
        while not _shutdown_requested:
            try:
                count = run_monitor()
                logger.info("Check complete — %d new job(s)", count)
            except Exception:
                logger.exception("Monitor check failed")

            slept = 0
            while slept < CHECK_INTERVAL_SECONDS and not _shutdown_requested:
                time.sleep(min(30, CHECK_INTERVAL_SECONDS - slept))
                slept += 30
    finally:
        _remove_pid()
        logger.info("Local job monitor agent stopped")


def is_agent_running() -> tuple[bool, int | None]:
    """Return whether the agent is running and its PID if so."""
    if not PID_FILE.exists():
        return False, None
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except ValueError:
        return False, None
    try:
        os.kill(pid, 0)
        return True, pid
    except OSError:
        PID_FILE.unlink(missing_ok=True)
        return False, None


if __name__ == "__main__":
    run_agent_loop()
