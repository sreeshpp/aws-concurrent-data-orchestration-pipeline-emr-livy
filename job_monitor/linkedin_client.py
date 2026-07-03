"""Fetch and parse LinkedIn job listings via the public guest API."""

import html
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional

from job_monitor.config import (
    LINKEDIN_JOBS_API,
    MAX_PAGES,
    PAGE_SIZE,
    USER_AGENT,
    SearchProfile,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobPosting:
    """A parsed LinkedIn job posting."""

    job_id: str
    title: str
    company: str
    location: str
    url: str
    profile: str


def _build_search_url(profile: SearchProfile, start: int) -> str:
    params: Dict[str, str] = {
        "keywords": profile.keywords,
        "location": profile.location,
        "start": str(start),
    }
    if profile.remote_only:
        params["f_WT"] = "2"
    return f"{LINKEDIN_JOBS_API}?{urllib.parse.urlencode(params)}"


def _fetch_page(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_job_cards(page_html: str, profile_name: str) -> List[JobPosting]:
    postings: List[JobPosting] = []
    cards = re.split(r"<li>", page_html)

    for card in cards:
        urn_match = re.search(r'data-entity-urn="urn:li:jobPosting:(\d+)"', card)
        if not urn_match:
            continue

        title_match = re.search(
            r"base-search-card__title[^>]*>\s*([^<]+)", card
        )
        location_match = re.search(
            r"job-search-card__location[^>]*>\s*([^<]+)", card
        )
        link_match = re.search(
            r'href="(https://[^"]+/jobs/view/[^"]+)"', card
        )
        company_match = re.search(
            r"base-search-card__subtitle[^>]*>.*?hidden-nested-link[^>]*>([^<]+)",
            card,
            re.S,
        )

        if not title_match or not link_match:
            continue

        job_url = html.unescape(link_match.group(1).split("?")[0])
        postings.append(
            JobPosting(
                job_id=urn_match.group(1),
                title=title_match.group(1).strip(),
                company=(company_match.group(1).strip() if company_match else "Unknown"),
                location=(location_match.group(1).strip() if location_match else ""),
                url=job_url,
                profile=profile_name,
            )
        )

    return postings


def fetch_jobs_for_profile(profile: SearchProfile) -> List[JobPosting]:
    """Fetch all job postings for a search profile, paginating through results."""
    seen_ids: set = set()
    all_postings: List[JobPosting] = []

    for page in range(MAX_PAGES):
        start = page * PAGE_SIZE
        url = _build_search_url(profile, start)
        try:
            page_html = _fetch_page(url)
        except urllib.error.URLError as exc:
            logger.error("Failed to fetch %s (start=%s): %s", profile.name, start, exc)
            break

        postings = _parse_job_cards(page_html, profile.name)
        if not postings:
            break

        new_on_page = 0
        for posting in postings:
            if posting.job_id not in seen_ids:
                seen_ids.add(posting.job_id)
                all_postings.append(posting)
                new_on_page += 1

        if new_on_page == 0:
            break

    logger.info("Fetched %d jobs for profile %s", len(all_postings), profile.name)
    return all_postings
