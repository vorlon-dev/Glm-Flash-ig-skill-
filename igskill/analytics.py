"""Analytics — engagement snapshots and the 'what worked' report."""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import datetime

from .config import Config
from .scheduler import SCHEMA, _db


def snapshot(cfg: Config, client=None, limit: int = 12) -> list[dict]:
    """Pull fresh metrics for recent posts and store a snapshot."""
    from .ig_client import get_client
    client = client or get_client(cfg)
    media = client.recent_media(limit=limit)
    conn = _db(cfg)
    saved = []
    for m in media:
        cur = conn.execute(
            "SELECT id FROM posts WHERE ig_media_id=?", (str(m["id"]),)).fetchone()
        post_id = cur["id"] if cur else None
        if post_id is None:
            cur = conn.execute(
                "INSERT INTO posts (ig_media_id, post_type, caption_snip, posted_at) "
                "VALUES (?,?,?,?)",
                (str(m["id"]), m.get("media_type", "unknown"),
                 (m.get("caption") or "")[:100], m.get("timestamp", "")[:19]))
            post_id = cur.lastrowid
        conn.execute(
            "INSERT INTO metrics (post_id, likes, comments, captured_at) VALUES (?,?,?,?)",
            (post_id, int(m.get("like_count") or 0), int(m.get("comments_count") or 0),
             datetime.now().isoformat(timespec="seconds")))
        saved.append({"post_id": post_id, "ig_media_id": str(m["id"]),
                      "likes": m.get("like_count"), "comments": m.get("comments_count")})
    conn.commit(); conn.close()
    return saved


def report(cfg: Config) -> str:
    """'What worked' — engagement rate, top posts, best hour, format split."""
    conn: sqlite3.Connection = sqlite3.connect(cfg.db_path)
    conn.row_factory = sqlite3.Row

    posts = conn.execute("SELECT * FROM posts ORDER BY id DESC LIMIT 60").fetchall()
    if not posts:
        conn.close()
        return ("No posts tracked yet. Run:\n"
                "  python scripts/ig_analytics.py snapshot\n"
                "after your first post (or connect the account and snapshot imports "
                "your recent posts).")

    latest = {}
    for p in posts:
        row = conn.execute(
            "SELECT likes, comments, captured_at FROM metrics WHERE post_id=? "
            "ORDER BY captured_at DESC LIMIT 1", (p["id"],)).fetchone()
        if row:
            latest[p["id"]] = {**dict(p), "likes": row["likes"], "comments": row["comments"]}

    lines = ["", "================ WHAT WORKED ================"]
    total_eng = total_posts = 0
    by_type = defaultdict(lambda: [0, 0, 0])  # type -> [posts, eng_sum, likes_sum]
    by_hour = defaultdict(lambda: [0, 0])

    for p in latest.values():
        eng = (p["likes"] or 0) + (p["comments"] or 0)
        total_eng += eng
        total_posts += 1
        t = p.get("post_type") or "unknown"
        by_type[t][0] += 1; by_type[t][1] += eng; by_type[t][2] += p["likes"] or 0
        try:
            hour = int(p["posted_at"][11:13])
            by_hour[hour][0] += 1; by_hour[hour][1] += eng
        except (ValueError, IndexError):
            pass

    if total_posts:
        avg = total_eng / total_posts
        lines.append(f"posts analyzed : {total_posts}")
        lines.append(f"avg engagement : {avg:.1f} (likes+comments per post)")

        top = sorted(latest.values(),
                     key=lambda p: (p['likes'] or 0) + (p['comments'] or 0),
                     reverse=True)[:3]
        lines.append("\nTOP POSTS:")
        for t in top:
            eng = (t["likes"] or 0) + (t["comments"] or 0)
            over = (eng / avg * 100 - 100) if avg else 0
            lines.append(f"  [{t['post_type']}] {t['caption_snip'][:48]!r} "
                         f"eng={eng} ({over:+.0f}% vs avg)")

        lines.append("\nBY FORMAT:")
        for t, (n, eng, _) in sorted(by_type.items(), key=lambda kv: -kv[1][1] / max(kv[1][0], 1)):
            lines.append(f"  {t:<10} {n} posts, avg eng {eng / max(n, 1):.1f}")

        if by_hour:
            best_hour = max(by_hour.items(), key=lambda kv: kv[1][1] / max(kv[1][0], 1))
            lines.append(f"\nbest hour so far: {best_hour[0]:02d}:00 "
                         f"(avg eng {best_hour[1][1] / max(best_hour[1][0], 1):.1f})")
        lines.append("\nNOTE: insights refresh each snapshot — run it after 24-48h")
        lines.append("for fresh numbers on recent posts.")
    conn.close()
    return "\n".join(lines)


if __name__ == "__main__":
    from .config import load_config
    print(report(load_config()))
