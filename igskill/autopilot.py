"""Autopilot — one prompt -> a full week of planned, edited, scheduled posts.

Flow:
  1. IDEAS   — agent-written JSON file or offline templates (the agent IS the
               content engine; no API keys exist in this skill)
  2. MEDIA   — use user's raw folder (round-robin), else build text-card reels
  3. EDIT    — full reel pipeline (9:16, subs-ready, watermark, compress)
  4. COPY    — captions/hashtags written by the agent
  5. SCHEDULE— best slots per timezone, daily cap respected

Consent ladder (Constitution rule):
  - the first plan always waits for user approval before run --execute
  - "full autopilot" requires the full_autopilot consent scope
"""
from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path

from .config import Config
from .content_gen import ContentPlan, offline_ideas
from .privacy import has_consent, require_consent

PLAN_FILE = "autopilot_plan.json"


# ------------------------------------------------------------ text cards --

def make_text_card(title: str, subtitle: str, out: Path, seed: int | None = None) -> Path:
    """Render a bold hook-card 1080x1920 PNG (offline content when no media exists)."""
    from PIL import Image, ImageDraw, ImageFont

    rng = random.Random(seed)
    palettes = [(12, 12, 24), (20, 8, 28), (6, 20, 26), (24, 14, 6)]
    base = palettes[rng.randrange(len(palettes))]
    img = Image.new("RGB", (1080, 1920), base)
    d = ImageDraw.Draw(img)
    # gradient glow blobs
    for _ in range(6):
        cx, cy, r = rng.randint(0, 1080), rng.randint(0, 1920), rng.randint(220, 520)
        col = tuple(min(255, c + rng.randint(18, 45)) for c in base)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    img = img.filter(__import__("PIL.ImageFilter", fromlist=["GaussianBlur"])
                     .GaussianBlur(120))

    d = ImageDraw.Draw(img)
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    font = big = small = None
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, 72)
            big = ImageFont.truetype(fp, 110)
            small = ImageFont.truetype(fp, 44)
            break
        except OSError:
            continue
    font = font or ImageFont.load_default()
    big = big or font
    small = small or font

    def wrap(text: str, fnt, max_w: int = 900) -> list[str]:
        words, lines, cur = text.split(), [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if d.textlength(test, font=fnt) <= max_w:
                cur = test
            else:
                lines.append(cur); cur = w
        if cur:
            lines.append(cur)
        return lines

    y = 480
    for line in wrap(title, big):
        d.text(((1080 - d.textlength(line, font=big)) / 2, y), line,
               font=big, fill=(255, 255, 255))
        y += 130
    y += 40
    for line in wrap(subtitle, font):
        d.text(((1080 - d.textlength(line, font=font)) / 2, y), line,
               font=font, fill=(230, 230, 240))
        y += 95
    d.text((540 - d.textlength(subtitle[:40], font=small) / 2, 1700),
           "", font=small, fill=(160, 160, 180))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


# ------------------------------------------------------------------ plan --

def build_plan(cfg: Config, niche: str, count: int = 7, *,
               ideas_file: str | None = None,
               media_dir: str | None = None) -> Path:
    """Create autopilot_plan.json — the week strategy. Does NOT post anything.

    ideas_file: the AGENT writes ideas JSON itself (it's the content engine):
        [{"title": str, "format": "reel|carousel|photo", "hook": str,
          "beats": [str]}]
    Without ideas_file, offline templates provide starter ideas the agent
    should rewrite before showing the plan to the user.
    """
    if ideas_file:
        ideas = json.loads(Path(ideas_file).read_text(encoding="utf-8"))
        ideas = ideas.get("ideas", ideas) if isinstance(ideas, dict) else ideas
    else:
        ideas = offline_ideas(niche, count)
    ideas = ideas[:count]

    raw_media: list[Path] = []
    if media_dir and Path(media_dir).exists():
        raw_media = [p for p in Path(media_dir).iterdir()
                     if p.suffix.lower() in
                     {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".webm"}]
        raw_media.sort()

    plan_items = []
    work = cfg.workdir
    for i, idea in enumerate(ideas):
        title = idea.get("hook") or idea.get("title") or f"Post {i + 1}"
        fmt = (idea.get("format") or "reel").lower()
        beats = idea.get("beats") or []
        item: dict = {"index": i, "title": title, "format": fmt, "beats": beats}

        if raw_media:
            src = raw_media[i % len(raw_media)]
            item["source_media"] = str(src)
        else:
            card = make_text_card(
                title, " • ".join(beats[:2]) if beats else niche,
                work / f"card_{i:02d}.png", seed=i)
            item["source_media"] = str(card)

        content = {"caption": f"{title}\n\n{' '.join(beats[:2])}"
                              f"\n\nWhich one hits? Comment 👇",
                   "hashtags": [], "post_type": "reel" if fmt == "reel" else "photo"}
        item["content"] = content
        plan_items.append(item)

    plan = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "niche": niche, "count": len(plan_items),
        "status": "awaiting_user_approval",   # Constitution: first plan needs a yes
        "_note": "agent: rewrite captions/hashtags in items[].content before approval",
        "items": plan_items,
    }
    out = cfg.workdir / PLAN_FILE
    out.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[autopilot] plan saved -> {out}\n"
          f"Show it to the user. After they approve:\n"
          f"  python scripts/ig_autopilot.py approve\n"
          f"  python scripts/ig_autopilot.py run")
    return out


def execute_plan(cfg: Config, client=None) -> list[dict]:
    """Edit media + queue every approved plan item into best slots."""
    plan_path = cfg.workdir / PLAN_FILE
    if not plan_path.exists():
        raise SystemExit("no plan found — run `plan` first")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("status") != "approved":
        raise SystemExit(
            "plan is NOT approved yet (Constitution rule).\n"
            "After the user approves, run:\n"
            "  python -c \"import json,pathlib; p=pathlib.Path("
            f"'{plan_path}'); d=json.loads(p.read_text()); "
            "d['status']='approved'; p.write_text(json.dumps(d, indent=2))\"\n"
            f"or with consent: full_autopilot scope granted "
            f"({'yes' if has_consent('full_autopilot', cfg) else 'no'}).")
    require_consent("full_autopilot", cfg,
                    why="executing a full week plan posts multiple times without "
                        "showing each item.")

    from .media import full_reel_pipeline, fit_post
    from . import scheduler

    results = []
    slots = scheduler.best_slots(cfg, "reel", days=14)
    slot_i = 0
    for item in plan["items"]:
        src = item["source_media"]
        out_dir = cfg.workdir / f"post_{item['index']:02d}"
        if item["format"] in ("reel", "video"):
            final = full_reel_pipeline(src, out_dir,
                                       watermark_text=cfg.watermark)
            ptype = "reel"
        else:
            final = fit_post(src, out_dir / "final.jpg")
            ptype = "photo"
        at = slots[slot_i]["at"] if slot_i < len(slots) else None
        slot_i += 2  # spread across days
        qid = scheduler.add_to_queue(cfg, str(final), item["content"], ptype, at)
        results.append({"queue_id": qid, "scheduled_at": at,
                        "media": str(final), "title": item["title"][:40]})
        print(f"[autopilot] queued #{qid} '{item['title'][:40]}' @ {at}")

    plan["status"] = "queued"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    return results
