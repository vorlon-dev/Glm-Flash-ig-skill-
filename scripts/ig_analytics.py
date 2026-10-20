#!/usr/bin/env python3
"""ig_analytics — engagement snapshots + 'what worked' report.

  python scripts/ig_analytics.py snapshot   # pull fresh metrics (needs connection)
  python scripts/ig_analytics.py report     # read the strategy report
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from igskill.config import load_config  # noqa: E402


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["snapshot", "report"])
    p.add_argument("--limit", type=int, default=12)
    a = p.parse_args()

    cfg = load_config()
    if a.cmd == "snapshot":
        from igskill.analytics import snapshot
        saved = snapshot(cfg, limit=a.limit)
        print(f"[snapshot] stored metrics for {len(saved)} posts")
        for s in saved:
            print(f"  post {s['ig_media_id']}: likes={s['likes']} comments={s['comments']}")
    else:
        from igskill.analytics import report
        print(report(cfg))


if __name__ == "__main__":
    main()
