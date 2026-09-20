"""Configuration for the resume analysis agent."""

import os
from dataclasses import dataclass

from resume_agent.paths import CONFIG_FILE, ensure_config_dir


def _load_env_file(path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_local_config() -> None:
    """Load optional config from ~/.config/resume-agent/config.env."""
    ensure_config_dir()
    _load_env_file(CONFIG_FILE)


@dataclass(frozen=True)
class AgentConfig:
    provider: str
    model: str
    api_key: str
    base_url: str | None
    aws_region: str
    temperature: float
    max_tokens: int

    @classmethod
    def from_env(cls) -> "AgentConfig":
        load_local_config()
        provider = os.environ.get("RESUME_AGENT_PROVIDER", "anthropic").strip().lower()
        default_models = {
            "anthropic": "claude-sonnet-4-20250514",
            "bedrock": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        }
        return cls(
            provider=provider,
            model=os.environ.get(
                "RESUME_AGENT_MODEL",
                default_models.get(provider, "claude-sonnet-4-20250514"),
            ),
            api_key=os.environ.get(
                "ANTHROPIC_API_KEY", os.environ.get("RESUME_AGENT_API_KEY", "")
            ),
            base_url=os.environ.get("ANTHROPIC_BASE_URL") or None,
            aws_region=os.environ.get("AWS_REGION", "us-east-1"),
            temperature=float(os.environ.get("RESUME_AGENT_TEMPERATURE", "0.4")),
            max_tokens=int(os.environ.get("RESUME_AGENT_MAX_TOKENS", "2048")),
        )

    def validate(self) -> None:
        if self.provider == "anthropic" and not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required for the Anthropic provider. "
                "Set it in your environment or ~/.config/resume-agent/config.env"
            )
        if self.provider == "bedrock":
            return
        if self.provider not in {"anthropic", "bedrock"}:
            raise ValueError(f"Unsupported provider: {self.provider}")
