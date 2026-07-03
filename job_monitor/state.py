"""Persist seen job IDs to avoid duplicate alerts."""

import json
import logging
import os
from typing import Dict, Set

logger = logging.getLogger(__name__)


class JobStateStore:
    """JSON-backed store of previously seen job IDs per profile."""

    def __init__(self, state_file: str):
        self.state_file = os.path.abspath(state_file)
        self._state: Dict[str, list] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.state_file):
            self._state = {}
            return
        try:
            with open(self.state_file, "r", encoding="utf-8") as handle:
                self._state = json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load state file %s: %s", self.state_file, exc)
            self._state = {}

    def _save(self) -> None:
        directory = os.path.dirname(self.state_file)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as handle:
            json.dump(self._state, handle, indent=2)

    def get_seen_ids(self, profile: str) -> Set[str]:
        return set(self._state.get(profile, []))

    def mark_seen(self, profile: str, job_ids: Set[str]) -> None:
        existing = self.get_seen_ids(profile)
        existing.update(job_ids)
        self._state[profile] = sorted(existing)
        self._save()

    def find_new_jobs(self, profile: str, job_ids: Set[str]) -> Set[str]:
        seen = self.get_seen_ids(profile)
        return job_ids - seen
