"""Filesystem paths for the resume analysis agent."""

from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "resume-agent"
CONFIG_FILE = CONFIG_DIR / "config.env"
SAMPLE_RESUME = Path(__file__).resolve().parent.parent / "data" / "sample_resume.pdf"


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
