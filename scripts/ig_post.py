#!/usr/bin/env python3
"""ig_post — edit + post one piece of content (the daily workhorse).

  python scripts/ig_post.py reel  --media clip.mp4 --content content.json
  python scripts/ig_post.py photo --media img.jpg --caption "hook..." --tags "#a,#b"
  python scripts/ig_post.py reel  --media clip.mp4 --content content.json \
      --subs subs.srt --music bgm.mp3 --watermark "@me" --beat 2.0

Edit pipeline runs before posting (reels: 9:16 -> subs -> music -> wm -> compress).
Posts respect the daily cap + human-like delay.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from igskill.config import load_config          # noqa: E402
from igskill.content_gen import validate_content  # noqa: E402
from igskill.ig_client import get_client, guard_daily_cap  # noqa: E402
from igskill.media import full_reel_pipeline, fit_post, is_video  # noqa: E402


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="edit + post to Instagram")
    p.add_argument("kind", choices=["photo", "reel", "story", "video"])
    p.add_argument("--media", required=True, help="photo/video file")
    p.add_argument("--content", help="content JSON file (agent-written)")
    p.add_argument("--caption", help="caption text (overrides content file)")
    p.add_argument("--tags", help="comma separated hashtags")
    p.add_argument("--subs", help=".srt subtitles file to burn")
    p.add_argument("--music", help="background music file")
    p.add_argument("--watermark", help="@handle text watermark")
    p.add_argument("--beat", type=float, help="beat-cut every N seconds")
    p.add_argument("--ratio", default="1:1", choices=["1:1", "4:5"],
                   help="photo post ratio")
    p.add_argument("--no-edit", action="store_true", help="upload as-is")
    p.add_argument("--queue", help="schedule at 'YYYY-MM-DD HH:MM' instead of now")
    a = p.parse_args()

    cfg = load_config()
    media = Path(a.media)
    if not media.exists():
        raise SystemExit(f"media not found: {media}")

    # ---- content plan
    raw: dict = {}
    if a.content:
        raw = json.loads(Path(a.content).read_text(encoding="utf-8"))
    if a.caption:
        raw["caption"] = a.caption
    if a.tags:
        raw["hashtags"] = [t.strip() for t in a.tags.split(",") if t.strip()]
    raw.setdefault("post_type", a.kind)
    plan, warnings = validate_content(raw)
    for w in warnings:
        print(f"[content] {w}")

    # ---- edit pipeline
    if not a.no_edit and a.kind in ("photo",):
        media = fit_post(media, cfg.workdir / f"{media.stem}_post.jpg", ratio=a.ratio)
    elif not a.no_edit and a.kind in ("reel", "video"):
        media = full_reel_pipeline(
            media, cfg.workdir, srt=a.subs, music=a.music,
            watermark_text=a.watermark or cfg.watermark, beat_every=a.beat)

    # ---- post or queue
    if a.queue:
        from igskill.scheduler import add_to_queue
        qid = add_to_queue(cfg, str(media), raw, a.kind, a.queue)
        print(f"[queued] #{qid} for {a.queue} -> {media}")
        return

    guard_daily_cap(cfg)
    client = get_client(cfg)
    caption = plan.full_caption()
    if a.kind == "story":
        ig_id = client.publish_story(str(media))
    elif a.kind == "reel":
        ig_id = client.publish_reel(str(media), caption)
    elif a.kind == "video":
        ig_id = client.publish_video(str(media), caption)
    else:
        ig_id = client.publish_photo(str(media), caption)
    print(f"[posted] {a.kind} -> {ig_id}\ncaption used:\n{caption[:300]}")


if __name__ == "__main__":
    main()
