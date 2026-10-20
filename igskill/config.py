"""Configuration — zero-config by design.

There is NO .env requirement. This repo is universal: a fresh chat pastes the
repo link, the agent clones it, and everything is configured at RUNTIME:

  - credentials are passed per-command by the agent (--user/--pass/--token)
    and used once; the Instagram password is NEVER written to disk
  - the instagrapi session cookie is cached in .state/session.json so later
    commands don't need the password again
  - profile facts (niche, watermark, timezone, goal) live in
    .state/profile.json, written by ig_setup.py / ig_audit.py
  - consent lives in .state/consent.json (see igskill/privacy.py)

Everything in .state/ is machine-local and git-ignored.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = SKILL_ROOT / ".state"

# Hard safety caps (ban prevention). Do NOT raise these.
HARD_MAX_POSTS_PER_DAY = 5


def detect_timezone() -> str:
    """Best-effort local timezone detection (sandbox/VM friendly)."""
    import os
    tz = os.environ.get("TZ", "").strip()
    if tz:
        return tz
    try:
        return Path("/etc/timezone").read_text(encoding="utf-8").strip() or "Asia/Calcutta"
    except OSError:
        return "Asia/Calcutta"


def _read_json(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def load_profile() -> dict:
    return _read_json(STATE_DIR / "profile.json", {})


def save_profile(update: dict) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    p = STATE_DIR / "profile.json"
    data = {**load_profile(), **update}
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


@dataclass
class Config:
    # --- runtime credentials (passed by the agent per-command; never persisted).
    # The password exists only in process memory during a login call.
    ig_username: str = field(default_factory=lambda: load_profile().get("username", ""))
    ig_password: str = ""          # intentionally NOT loaded from anywhere
    ig_access_token: str = field(default_factory=lambda: load_profile().get("graph_token", ""))
    ig_business_id: str = field(default_factory=lambda: load_profile().get("business_id", ""))

    # --- network (optional). Residential/mobile proxy for datacenter IPs that
    # Instagram blocks. Lives in .state/profile.json — machine-local,
    # git-ignored, never committed. Format: http://user:pass@host:port
    proxy: str = field(default_factory=lambda: load_profile().get("proxy", ""))

    # --- profile facts (auto-filled by ig_audit.py, overridable via ig_setup.py)
    niche: str = field(default_factory=lambda: load_profile().get("niche", "general"))
    watermark: str = field(default_factory=lambda: load_profile().get("watermark", ""))
    goal: str = field(default_factory=lambda: load_profile().get("goal", ""))
    language: str = field(default_factory=lambda: load_profile().get("language", "english"))
    timezone: str = field(default_factory=lambda: load_profile().get("timezone") or detect_timezone())

    # --- safety (defaults are the policy; hard cap enforced below)
    max_posts_per_day: int = min(int(load_profile().get("max_posts_per_day", 3)),
                                 HARD_MAX_POSTS_PER_DAY)
    min_delay_seconds: int = 30
    max_delay_seconds: int = 120

    # --- dashboard
    host: str = "127.0.0.1"
    port: int = 8790

    # ------------------------------------------------------------ paths --
    @property
    def session_file(self) -> Path:
        return STATE_DIR / "session.json"

    @property
    def db_path(self) -> Path:
        return SKILL_ROOT / "ig_data.db"

    @property
    def consent_path(self) -> Path:
        return STATE_DIR / "consent.json"

    @property
    def workdir(self) -> Path:
        d = SKILL_ROOT / "workspace"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ----------------------------------------------------------- status --
    @property
    def resolved_mode(self) -> str:
        return "graph" if self.ig_access_token else "session"

    @property
    def has_session(self) -> bool:
        return self.session_file.exists()

    def connected_hint(self) -> str:
        if self.resolved_mode == "graph":
            base = "graph token loaded from .state/profile.json"
        elif self.has_session:
            base = "session file found — passwordless re-login available"
        else:
            base = ("not connected yet — run: python scripts/ig_setup.py "
                    "--login --user <u> --pass <p>")
        if self.proxy:
            base += " · proxy: ON"
        return base

    def require_credentials(self) -> None:
        """Raise a clear, agent-actionable error when an action needs login."""
        if self.resolved_mode == "graph" and self.ig_access_token:
            return
        if self.resolved_mode == "session" and (self.has_session or self.ig_username):
            return
        raise SystemExit(
            "Instagram not connected yet.\n"
            "Ask the user for their username + password (in chat), then run:\n"
            "  python scripts/ig_setup.py --login --user '<username>' --pass '<password>'\n"
            "(The password is used once for login and never stored on disk.)"
        )

    def safety_delay(self) -> float:
        """Randomized human-like delay between actions (ban prevention)."""
        lo = max(10, self.min_delay_seconds)
        hi = max(lo + 5, self.max_delay_seconds)
        return random.uniform(lo, hi)


def load_config() -> Config:
    """Always returns a usable Config — this skill is zero-config by design."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return Config()
