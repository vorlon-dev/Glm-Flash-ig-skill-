#!/usr/bin/env python3
"""ig_schedule — best-time slots + queue management.

  python scripts/ig_schedule.py slots --type reel --days 7
  python scripts/ig_schedule.py add --media reel.mp4 --content content.json \
      --type reel --at "2026-10-21 19:30"
  python scripts/ig_schedule.py list
  python scripts/ig_schedule.py run-due
  python scripts/ig_schedule.py cancel 4
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from igskill.config import load_config  # noqa: E402
from igskill.scheduler import (add_to_queue, best_slots, cancel_queued,  # noqa: E402
                               list_queue, run_due)


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="posting scheduler")
    p.add_argument("cmd", choices=["slots", "add", "list", "run-due", "cancel"])
    p.add_argument("--media")
    p.add_argument("--content")
    p.add_argument("--caption")
    p.add_argument("--type", default="reel",
                   choices=["reel", "photo", "carousel", "story"])
    p.add_argument("--at", help="'YYYY-MM-DD HH:MM' (local timezone)")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("qid", nargs="?", type=int, help="queue id for cancel")
    a = p.parse_args()

    cfg = load_config()
    if a.cmd == "slots":
        for s in best_slots(cfg, a.type, a.days):
            tag = f"  ({s['tag']})" if s["tag"] else ""
            print(f"{s['at']}  {s['type']}{tag}")
    elif a.cmd == "add":
        content = {}
        if a.content:
            content = json.loads(Path(a.content).read_text(encoding="utf-8"))
        if a.caption:
            content["caption"] = a.caption
        qid = add_to_queue(cfg, a.media, content, a.type, a.at)
        print(f"[queued] #{qid} {a.type} @ {a.at or 'next best slot'}")
    elif a.cmd == "list":
        for i in list_queue(cfg):
            cap = (json.loads(i["content_json"]).get("caption") or "")[:42]
            print(f"#{i['id']:<4} {i['scheduled_at']}  {i['post_type']:<8} "
                  f"{i['status']:<9} {cap!r}")
    elif a.cmd == "run-due":
        results = run_due(cfg)
        print(f"[run-due] {sum(1 for r in results if r['ok'])}/"
              f"{len(results)} posted")
    elif a.cmd == "cancel":
        if a.qid is None:
            raise SystemExit("cancel needs a queue id: ... cancel 4")
        print("cancelled" if cancel_queued(cfg, a.qid) else "not cancelable")


if __name__ == "__main__":
    main()
