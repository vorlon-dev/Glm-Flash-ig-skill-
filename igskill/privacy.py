"""Privacy guardrails — the enforcement layer for SKILL.md's Constitution.

Rule: touching DMs / notifications / story viewers / sending any reply
requires EXPLICIT user consent, recorded in .consent.json.

An agent (or user) must call `grant_consent(scope, note)` only after the user
explicitly asked for it in chat. Consent is scoped and revocable:

    scopes: "read_dms" | "reply_dms" | "read_comments" | "reply_comments"
            | "story_viewers" | "full_autopilot"
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

VALID_SCOPES = {
    "read_dms", "reply_dms", "read_comments", "reply_comments",
    "story_viewers", "full_autopilot",
}

# What each scope allows
SCOPE_DESCRIPTIONS = {
    "read_dms": "open and read direct messages",
    "reply_dms": "send direct message replies (draft shown to user first)",
    "read_comments": "read comments on posts",
    "reply_comments": "post comment replies (draft shown to user first)",
    "story_viewers": "see who viewed stories",
    "full_autopilot": "publish scheduled posts without showing each one first",
}


class ConsentRequired(PermissionError):
    """Raised when an action needs explicit user permission that isn't on file."""

    def __init__(self, scope: str, why: str = ""):
        self.scope = scope
        msg = (
            f"CONSENT REQUIRED for '{scope}' ({SCOPE_DESCRIPTIONS.get(scope, scope)}).\n"
            "Per this skill's Constitution, private/conversational actions need the "
            "user's explicit permission.\n"
            "Ask the user, then record it with:\n"
            f"  python -m igskill.privacy --grant {scope} --note \"user approved in chat\"\n"
            f"{why}".strip()
        )
        super().__init__(msg)


def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"grants": {}}
    return {"grants": {}}


def has_consent(scope: str, cfg) -> bool:
    """Check whether a consent scope is currently granted."""
    if scope not in VALID_SCOPES:
        raise ValueError(f"unknown consent scope: {scope}")
    data = _load(cfg.consent_path)
    grant = data.get("grants", {}).get(scope)
    return bool(grant and grant.get("active", False))


def require_consent(scope: str, cfg, why: str = "") -> None:
    """Raise ConsentRequired unless the user granted this scope."""
    if not has_consent(scope, cfg):
        raise ConsentRequired(scope, why)


def grant_consent(scope: str, note: str, cfg) -> dict:
    """Record a user-granted consent. Only call this after the user explicitly approved."""
    if scope not in VALID_SCOPES:
        raise ValueError(f"unknown consent scope: {scope}")
    data = _load(cfg.consent_path)
    data.setdefault("grants", {})[scope] = {
        "active": True,
        "note": note or "user approved in chat",
        "granted_at": datetime.now(timezone.utc).isoformat(),
    }
    cfg.consent_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data["grants"][scope]


def revoke_consent(scope: str, cfg) -> None:
    data = _load(cfg.consent_path)
    if scope in data.get("grants", {}):
        data["grants"][scope]["active"] = False
        data["grants"][scope]["revoked_at"] = datetime.now(timezone.utc).isoformat()
        cfg.consent_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def consent_report(cfg) -> str:
    data = _load(cfg.consent_path)
    lines = ["Consent status (.consent.json):"]
    for scope in sorted(VALID_SCOPES):
        g = data.get("grants", {}).get(scope)
        state = "GRANTED" if (g and g.get("active")) else "not granted"
        lines.append(f"  {scope:<16} {state}")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    from .config import SKILL_ROOT, Config

    p = argparse.ArgumentParser(description="Privacy consent management")
    p.add_argument("--grant", choices=sorted(VALID_SCOPES))
    p.add_argument("--revoke", choices=sorted(VALID_SCOPES))
    p.add_argument("--note", default="")
    p.add_argument("--status", action="store_true")
    a = p.parse_args()

    cfg = Config()
    if a.grant:
        grant_consent(a.grant, a.note, cfg)
        print(f"granted: {a.grant}")
    elif a.revoke:
        revoke_consent(a.revoke, cfg)
        print(f"revoked: {a.revoke}")
    print(consent_report(cfg))
