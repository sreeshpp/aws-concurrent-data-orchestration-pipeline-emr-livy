"""Main orchestration for the LinkedIn job monitor."""

import logging
import sys

from job_monitor.alerts import send_alerts
from job_monitor.config import SEARCH_PROFILES, STATE_FILE
from job_monitor.linkedin_client import JobPosting, fetch_jobs_for_profile
from job_monitor.matcher import filter_jobs
from job_monitor.state import JobStateStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def run_monitor() -> int:
    """
    Check LinkedIn for new matching jobs and send alerts.

    Returns the number of new jobs found.
    """
    store = JobStateStore(STATE_FILE)
    new_jobs: list[JobPosting] = []

    for profile in SEARCH_PROFILES:
        logger.info("Searching profile: %s", profile.name)
        raw_jobs = fetch_jobs_for_profile(profile)
        matched_jobs = filter_jobs(raw_jobs, profile)

        job_ids = {job.job_id for job in matched_jobs}
        unseen_ids = store.find_new_jobs(profile.name, job_ids)
        profile_new = [job for job in matched_jobs if job.job_id in unseen_ids]

        if profile_new:
            logger.info(
                "Found %d new job(s) for profile %s", len(profile_new), profile.name
            )
            new_jobs.extend(profile_new)

        store.mark_seen(profile.name, job_ids)

    if new_jobs:
        send_alerts(new_jobs)
    else:
        logger.info("No new matching jobs found this run")

    return len(new_jobs)


if __name__ == "__main__":
    count = run_monitor()
    sys.exit(0)
