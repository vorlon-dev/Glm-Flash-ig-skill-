"""Viral content generation — captions, hooks, hashtags, week plans.

Two modes:
  agent mode (default): the calling AI agent already wrote a content JSON —
      this module validates/normalizes it and enriches hashtags offline.
  api mode: calls the Z.ai GLM API (OpenAI-compatible) when ZAI_API_KEY is set.

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
    """Normalize agent/API output into a ContentPlan; return (plan, warnings)."""
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


# ---------------------------------------------------------------- API mode --

VIRAL_SYSTEM_PROMPT = """You are a viral Instagram influencer and growth strategist.
Write scroll-stopping content in the requested niche and language.
Rules:
- Caption structure: hook line (<=90 chars) + tension + payoff + one CTA/question.
- No emojis spam: max 3 emojis total. Line breaks between sections.
- Hashtags: 8-15, mixed sizes (3 big, 5 mid, 7 niche), no banned tags.
- Return STRICT JSON only, no markdown fences.
JSON schema:
{"caption": str, "hashtags": [str], "alt_text": str, "comment_pin": str}
For idea lists use schema:
{"ideas": [{"title": str, "format": "reel|carousel|photo", "hook": str, "beats": [str]}]}"""


def _zai_chat(cfg, messages: list[dict], max_tokens: int = 900) -> str:
    import httpx

    resp = httpx.post(
        f"{cfg.zai_base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {cfg.zai_api_key}"},
        json={
            "model": cfg.zai_model,
            "messages": messages,
            "temperature": 0.9,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start = min((i for i in (text.find("{"), text.find("[")) if i >= 0), default=-1)
    if start < 0:
        raise ValueError(f"no JSON in model output:\n{text[:300]}")
    return json.loads(text[start:])  # may raise — caller handles


def generate_content(cfg, niche: str, idea: str, post_type: str = "reel") -> dict:
    """API mode: generate one caption/hashtag set via Z.ai GLM."""
    if not cfg.zai_api_key:
        raise SystemExit("ZAI_API_KEY not set — either write content JSON yourself "
                         "(agent mode) or add the key to .env")
    raw = _zai_chat(cfg, [
        {"role": "system", "content": VIRAL_SYSTEM_PROMPT},
        {"role": "user", "content":
            f"niche: {niche}\nformat: {post_type}\npost idea: {idea}\n"
            f"language: {cfg.language}\ntimezone market: {cfg.timezone}"},
    ])
    return _extract_json(raw)


def generate_week_plan(cfg, niche: str, count: int = 7) -> list[dict]:
    """API mode: generate a week of post ideas."""
    if not cfg.zai_api_key:
        raise SystemExit("ZAI_API_KEY not set — use agent mode (write ideas JSON) "
                         "or add the key to .env")
    raw = _zai_chat(cfg, [
        {"role": "system", "content": VIRAL_SYSTEM_PROMPT},
        {"role": "user", "content":
            f"Give me {count} Instagram post ideas for a {niche} account targeting "
            f"{cfg.timezone} audience. Mix formats (reels 60%, carousels 20%, photos 20%). "
            f"Each idea: title, format, hook, 3-4 beat-by-beat content points."},
    ], max_tokens=1600)
    data = _extract_json(raw)
    return data.get("ideas", data if isinstance(data, list) else [])


def offline_ideas(niche: str, count: int = 7) -> list[dict]:
    """Zero-API fallback ideas from templates (agent should still improve them)."""
    t = load_templates().get("niches", {}).get(niche, {}) or load_templates().get("niches", {}).get("general", {})
    hooks = t.get("hooks") or [
        "POV: you just started {niche} and everyone gives you this advice...",
        "Nobody tells beginners in {niche} this:",
        "3 mistakes killing your {niche} progress (I made all 3)",
        "Do this for 7 days and thank me later {niche} edition:",
    ]
    ideas = []
    for i in range(count):
        hook = hooks[i % len(hooks)].format(niche=niche)
        ideas.append({
            "title": f"{niche.title()} post #{i + 1}",
            "format": "reel" if i % 5 != 4 else "carousel",
            "hook": hook,
            "beats": ["pattern-interrupt first frame", "deliver value fast",
                      "loop the ending", "CTA in caption"],
        })
    random.shuffle(ideas)
    return ideas
