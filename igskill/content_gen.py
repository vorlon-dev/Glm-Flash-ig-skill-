"""Viral content generation — captions, hooks, hashtags, ideas.

THE AGENT IS THE CONTENT ENGINE. No API keys exist in this skill: in agent
mode the calling AI writes captions/hooks/hashtags/ideas itself (it's an
influencer, after all) and hands them to the scripts as content JSON. The
offline templates below are the fallback when the agent wants raw material.

Content JSON shape:
{
  "caption": "hook + tension + payoff + CTA",
  "hashtags": ["#a", "#b"],
  "post_type": "reel|photo|carousel|story",
  "alt_text": "...",
  "comment_pin": "..."
}
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

TEMPLATES_PATH = Path(__file__).resolve().parent.parent / "templates" / "caption_templates.json"


@dataclass
class ContentPlan:
    caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    post_type: str = "reel"
    alt_text: str = ""
    comment_pin: str = ""
    ideas: list[dict] = field(default_factory=list)

    def hashtag_string(self) -> str:
        tags = []
        for h in self.hashtags:
            h = h.strip()
            if h and not h.startswith("#"):
                h = "#" + h
            tags.append(h)
        return " ".join(dict.fromkeys(tags))  # dedupe, keep order

    def full_caption(self) -> str:
        text = self.caption.strip()
        tags = self.hashtag_string()
        if tags:
            text = f"{text}\n\n.\n.\n{tags}" if len(text) > 80 else f"{text}\n\n{tags}"
        return text[:2200]  # IG hard limit

    @classmethod
    def from_dict(cls, d: dict) -> "ContentPlan":
        known = {k: d[k] for k in ("caption", "post_type", "alt_text", "comment_pin", "ideas") if k in d}
        tags = d.get("hashtags", [])
        if isinstance(tags, str):
            tags = [t for t in re.split(r"[,\s]+", tags) if t]
        return cls(hashtags=list(tags), **known)


def load_templates() -> dict:
    if TEMPLATES_PATH.exists():
        return json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
    return {}


def rotate_hashtags(base_tags: list[str], niche: str, set_index: int = 0) -> list[str]:
    """Rotate hashtag sets so consecutive posts never reuse the same block."""
    t = load_templates().get("niches", {}).get(niche, {})
    sets = t.get("hashtag_sets") or load_templates().get("niches", {}).get("general", {}).get("hashtag_sets", [])
    if sets:
        chosen = sets[set_index % len(sets)]
        return list(dict.fromkeys(base_tags + chosen))[:15]
    return base_tags[:15]


def validate_content(d: dict) -> tuple[ContentPlan, list[str]]:
    """Normalize agent-written content into a ContentPlan; return (plan, warnings)."""
    warnings = []
    plan = ContentPlan.from_dict(d)
    if not plan.caption:
        warnings.append("caption missing — add a hook-first caption")
    first_line = plan.caption.splitlines()[0] if plan.caption else ""
    if len(first_line) > 125:
        warnings.append("first caption line >125 chars — hooks should be short")
    if "?" not in plan.caption and not any(
        w in plan.caption.lower() for w in ("comment", "save", "share", "follow", "tag")
    ):
        warnings.append("no CTA/question — add one to farm engagement")
    if len(plan.hashtags) > 15:
        plan.hashtags = plan.hashtags[:15]
        warnings.append("trimmed hashtags to 15")
    if plan.post_type not in ("reel", "photo", "carousel", "story", "video"):
        plan.post_type = "reel"
    return plan, warnings


def offline_ideas(niche: str, count: int = 7) -> list[dict]:
    """Starter ideas from templates — the agent should rewrite and improve them."""
    t = load_templates().get("niches", {}).get(niche, {}) or load_templates().get("niches", {}).get("general", {})
    hooks = t.get("hooks") or [
        "POV: you just started {niche} and everyone gives you this advice...",
        "Nobody tells beginners in {niche} this:",
        "3 mistakes killing your {niche} progress (I made all 3)",
        "Do this for 7 days and thank me later {niche} edition:",
    ]
    ctas = t.get("ctas") or ["Which one hits? 👇", "Save this before it's gone"]
    ideas = []
    for i in range(count):
        hook = hooks[i % len(hooks)].format(niche=niche)
        ideas.append({
            "title": f"{niche.title()} post #{i + 1}",
            "format": "reel" if i % 5 != 4 else "carousel",
            "hook": hook,
            "beats": ["pattern-interrupt first frame", "deliver value fast",
                      "loop the ending", ctas[i % len(ctas)]],
        })
    random.shuffle(ideas)
    return ideas
