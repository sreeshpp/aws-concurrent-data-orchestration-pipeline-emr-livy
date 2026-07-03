"""Local agent paths and optional config file loading."""

import os
from pathlib import Path


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def _xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


AGENT_NAME = "job-monitor"
CONFIG_DIR = _xdg_config_home() / AGENT_NAME
DATA_DIR = _xdg_data_home() / AGENT_NAME
CONFIG_FILE = CONFIG_DIR / "config.env"
STATE_FILE = DATA_DIR / "seen_jobs.json"
PID_FILE = DATA_DIR / "agent.pid"
LOG_FILE = DATA_DIR / "agent.log"
ALERTS_LOG = DATA_DIR / "alerts.log"


def ensure_data_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_local_config() -> None:
    """Load KEY=VALUE pairs from the local config file into os.environ."""
    if not CONFIG_FILE.exists():
        return
    with CONFIG_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
