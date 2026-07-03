"""Filter job postings by title and location criteria."""

import re
from typing import Iterable, List

from job_monitor.config import SearchProfile
from job_monitor.linkedin_client import JobPosting


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def title_matches(title: str, patterns: Iterable[str]) -> bool:
    """Return True if the job title matches any of the allowed patterns."""
    normalized_title = _normalize(title)
    for pattern in patterns:
        if _normalize(pattern) in normalized_title:
            return True
    return False


def location_matches_kochi(location: str) -> bool:
    normalized = _normalize(location)
    return "kochi" in normalized or "cochin" in normalized


def location_matches_trivandrum(location: str) -> bool:
    normalized = _normalize(location)
    return (
        "trivandrum" in normalized
        or "thiruvananthapuram" in normalized
        or "tvm" in normalized
    )


def is_remote(location: str) -> bool:
    normalized = _normalize(location)
    return "remote" in normalized or normalized == "india"


def filter_jobs(
    jobs: List[JobPosting], profile: SearchProfile
) -> List[JobPosting]:
    """Apply profile-specific filters to job postings."""
    filtered: List[JobPosting] = []

    for job in jobs:
        if not title_matches(job.title, profile.title_patterns):
            continue

        if profile.name == "remote_india":
            if not is_remote(job.location):
                continue
        elif profile.name == "kochi":
            if not location_matches_kochi(job.location):
                continue
        elif profile.name == "trivandrum":
            if not location_matches_trivandrum(job.location):
                continue

        filtered.append(job)

    return filtered
