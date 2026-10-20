"""Configuration loading and safety caps.

All settings come from environment variables / .env in the skill root.
Safety caps are enforced here so no other module can accidentally bypass them.
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_a, **_k):  # type: ignore
        return False

SKILL_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = SKILL_ROOT / ".env"
load_dotenv(ENV_PATH)

# Hard safety caps (ban prevention). Do NOT raise these.
HARD_MAX_POSTS_PER_DAY = 5
HARD_MAX_ACTIONS_PER_HOUR = 30


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


@dataclass
class Config:
    # --- Instagram connection ---
    ig_mode: str = field(default_factory=lambda: _env("IG_MODE", "auto"))   # auto|session|graph
    ig_username: str = field(default_factory=lambda: _env("IG_USERNAME"))
    ig_password: str = field(default_factory=lambda: _env("IG_PASSWORD"))
    ig_access_token: str = field(default_factory=lambda: _env("IG_ACCESS_TOKEN"))
    ig_business_id: str = field(default_factory=lambda: _env("IG_BUSINESS_ID"))
    ig_session_file: str = field(default_factory=lambda: _env(
        "IG_SESSION_FILE", str(SKILL_ROOT / ".ig_session.json")))

    # --- Content engine ---
    zai_api_key: str = field(default_factory=lambda: _env("ZAI_API_KEY"))
    zai_base_url: str = field(default_factory=lambda: _env(
        "ZAI_BASE_URL", "https://api.z.ai/api/paas/v4"))
    zai_model: str = field(default_factory=lambda: _env("ZAI_MODEL", "glm-4.6"))

    # --- Persona / strategy ---
    niche: str = field(default_factory=lambda: _env("NICHE", "general"))
    timezone: str = field(default_factory=lambda: _env("TIMEZONE", "Asia/Calcutta"))
    watermark: str = field(default_factory=lambda: _env("WATERMARK", ""))
    language: str = field(default_factory=lambda: _env("LANGUAGE", "english"))

    # --- Safety (effective values can only be lower than hard caps) ---
    max_posts_per_day: int = min(
        int(_env("MAX_POSTS_PER_DAY", "3") or 3), HARD_MAX_POSTS_PER_DAY)
    min_delay_seconds: int = int(_env("MIN_DELAY_SECONDS", "30") or 30)
    max_delay_seconds: int = int(_env("MAX_DELAY_SECONDS", "120") or 120)

    # --- Server ---
    host: str = field(default_factory=lambda: _env("HOST", "127.0.0.1"))
    port: int = int(_env("PORT", "8790") or 8790)

    @property
    def resolved_mode(self) -> str:
        """auto -> graph if token present else session."""
        if self.ig_mode == "auto":
            return "graph" if self.ig_access_token else "session"
        return self.ig_mode

    @property
    def db_path(self) -> Path:
        return SKILL_ROOT / "ig_data.db"

    @property
    def consent_path(self) -> Path:
        return SKILL_ROOT / ".consent.json"

    @property
    def workdir(self) -> Path:
        d = SKILL_ROOT / "workspace"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def validate(self) -> list[str]:
        problems = []
        mode = self.resolved_mode
        if mode == "session" and not (self.ig_username and self.ig_password):
            problems.append("session mode needs IG_USERNAME and IG_PASSWORD in .env")
        if mode == "graph" and not self.ig_access_token:
            problems.append("graph mode needs IG_ACCESS_TOKEN in .env")
        if self.max_posts_per_day > HARD_MAX_POSTS_PER_DAY:
            problems.append(f"MAX_POSTS_PER_DAY cannot exceed {HARD_MAX_POSTS_PER_DAY}")
        return problems

    def safety_delay(self) -> float:
        """Randomized human-like delay between actions (ban prevention)."""
        lo = max(10, self.min_delay_seconds)
        hi = max(lo + 5, self.max_delay_seconds)
        return random.uniform(lo, hi)


def load_config() -> Config:
    cfg = Config()
    problems = cfg.validate()
    if problems:
        raise SystemExit(
            "[config] .env problems:\n  - " + "\n  - ".join(problems)
            + "\nCopy .env.example to .env and fill it in (see README)."
        )
    return cfg
