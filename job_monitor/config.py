"""Configuration for the LinkedIn job monitor."""

import os
from dataclasses import dataclass, field
from typing import List

from job_monitor.paths import STATE_FILE as LOCAL_STATE_FILE, load_local_config

load_local_config()


@dataclass
class SearchProfile:
    """A LinkedIn job search profile."""

    name: str
    keywords: str
    location: str
    remote_only: bool = False
    title_patterns: List[str] = field(default_factory=list)


DEFAULT_TITLE_PATTERNS = [
    "senior data engineer",
    "sr data engineer",
    "sr. data engineer",
    "lead data engineer",
    "principal data engineer",
    "staff data engineer",
    "data engineer ii",
    "data engineer 2",
]

SEARCH_PROFILES = [
    SearchProfile(
        name="remote_india",
        keywords="senior data engineer",
        location="India",
        remote_only=True,
        title_patterns=DEFAULT_TITLE_PATTERNS,
    ),
    SearchProfile(
        name="kochi",
        keywords="data engineer",
        location="Kochi, Kerala, India",
        remote_only=False,
        title_patterns=DEFAULT_TITLE_PATTERNS,
    ),
    SearchProfile(
        name="trivandrum",
        keywords="data engineer",
        location="Thiruvananthapuram, Kerala, India",
        remote_only=False,
        title_patterns=DEFAULT_TITLE_PATTERNS,
    ),
]

LINKEDIN_JOBS_API = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
PAGE_SIZE = 25
MAX_PAGES = 4

STATE_FILE = os.environ.get("JOB_MONITOR_STATE_FILE", str(LOCAL_STATE_FILE))
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
ALERT_EMAIL_TO = os.environ.get("ALERT_EMAIL_TO", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)
