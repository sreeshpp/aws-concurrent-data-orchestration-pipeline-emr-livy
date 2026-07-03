"""Local desktop and file-based alerts for the job monitor agent."""

import logging
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from typing import List

from job_monitor.linkedin_client import JobPosting
from job_monitor.paths import ALERTS_LOG, ensure_data_dirs

logger = logging.getLogger(__name__)

PROFILE_LABELS = {
    "remote_india": "Remote India",
    "kochi": "Kochi",
    "trivandrum": "Trivandrum",
}


def _summary_text(jobs: List[JobPosting]) -> str:
    if len(jobs) == 1:
        job = jobs[0]
        return f"{job.title} at {job.company} ({PROFILE_LABELS.get(job.profile, job.profile)})"
    return f"{len(jobs)} new Senior Data Engineer jobs on LinkedIn"


def _detail_text(jobs: List[JobPosting]) -> str:
    lines = []
    for job in jobs[:5]:
        lines.append(f"{job.title} @ {job.company} — {job.location}")
    if len(jobs) > 5:
        lines.append(f"...and {len(jobs) - 5} more (see alerts log)")
    return "\n".join(lines)


def send_desktop_notification(jobs: List[JobPosting]) -> bool:
    """Show a native desktop notification when new jobs are found."""
    title = "LinkedIn Job Alert"
    body = _summary_text(jobs)
    system = platform.system()

    try:
        if system == "Linux" and shutil.which("notify-send"):
            subprocess.run(
                ["notify-send", "-a", "job-monitor", title, body],
                check=False,
                timeout=10,
            )
            logger.info("Desktop notification sent (notify-send)")
            return True

        if system == "Darwin":
            script = (
                f'display notification "{body}" with title "{title}" sound name "Glass"'
            )
            subprocess.run(["osascript", "-e", script], check=False, timeout=10)
            logger.info("Desktop notification sent (macOS)")
            return True
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Desktop notification failed: %s", exc)

    return False


def append_alerts_log(jobs: List[JobPosting]) -> None:
    """Persist alert details to a local log file the user can open anytime."""
    ensure_data_dirs()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    with ALERTS_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"\n=== {timestamp} — {len(jobs)} new job(s) ===\n")
        for job in jobs:
            label = PROFILE_LABELS.get(job.profile, job.profile)
            handle.write(
                f"[{label}] {job.title} at {job.company}\n"
                f"  Location: {job.location}\n"
                f"  {job.url}\n"
            )

    logger.info("Wrote alert details to %s", ALERTS_LOG)


def send_local_alerts(jobs: List[JobPosting]) -> bool:
    """Send local alerts via desktop notification and alerts log."""
    if not jobs:
        return False
    append_alerts_log(jobs)
    return send_desktop_notification(jobs)
