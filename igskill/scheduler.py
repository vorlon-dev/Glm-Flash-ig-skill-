"""Scheduler — SQLite queue, best-time slots, daily caps.

Tables:
  queue(id, media_path, content_json, post_type, scheduled_at, status, ig_media_id, created_at)
  posts(id, ig_media_id, post_type, caption_snip, posted_at)   -> rate-limit source of truth
  metrics(id, post_id, likes, comments, captured_at)           -> analytics snapshots
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .config import Config

SCHEMA = """
CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_path TEXT NOT NULL,
    content_json TEXT NOT NULL DEFAULT '{}',
    post_type TEXT NOT NULL DEFAULT 'reel',
    scheduled_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',   -- queued|posted|failed|cancelled
    ig_media_id TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ig_media_id TEXT,
    post_type TEXT,
    caption_snip TEXT,
    posted_at TEXT
);
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    captured_at TEXT NOT NULL
);
"""


def _db(cfg: Config) -> sqlite3.Connection:
    conn = sqlite3.connect(cfg.db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


# ------------------------------------------------------------- best slots --

# Research-backed engagement windows (local time, by format).
# Reels peak twice: lunch scroll + prime time. Carousels: evenings + weekend.
BASE_SLOTS = {
    "reel":     ["07:30", "12:15", "19:30"],
    "carousel": ["11:00", "20:00"],
    "photo":    ["09:00", "18:30"],
    "story":    ["10:00", "16:00", "21:00"],
}
WEEKEND_BONUS = {"19:00", "19:30", "20:00", "20:30", "11:00", "12:15"}


def best_slots(cfg: Config, post_type: str = "reel", days: int = 7) -> list[dict]:
    """Next `days` days of recommended slot times for the timezone's local clock."""
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(cfg.timezone)
    now = datetime.now(tz)
    slots = []
    for d in range(days):
        day = (now + timedelta(days=d))
        for t in BASE_SLOTS.get(post_type, BASE_SLOTS["reel"]):
            hh, mm = map(int, t.split(":"))
            dt = day.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if dt <= now:
                continue
            tag = ""
            if day.weekday() >= 5 and t in WEEKEND_BONUS:
                tag = "weekend-boost"
            if 19 <= hh <= 21:
                tag = (tag + " prime-time").strip()
            slots.append({"at": dt.strftime("%Y-%m-%d %H:%M"), "type": post_type, "tag": tag})
    return slots[:days * len(BASE_SLOTS.get(post_type, []))]


def next_slot(cfg: Config, post_type: str = "reel") -> str:
    slots = best_slots(cfg, post_type, days=8)
    return slots[0]["at"] if slots else (datetime.now() + timedelta(hours=2)) \
        .strftime("%Y-%m-%d %H:%M")


# ------------------------------------------------------------------ queue --

def add_to_queue(cfg: Config, media_path: str, content: dict,
                 post_type: str, scheduled_at: str | None = None) -> int:
    if not Path(media_path).exists():
        raise FileNotFoundError(media_path)
    at = scheduled_at or next_slot(cfg, post_type)
    conn = _db(cfg)
    cur = conn.execute(
        "INSERT INTO queue (media_path, content_json, post_type, scheduled_at, status, created_at) "
        "VALUES (?,?,?,?, 'queued', ?)",
        (str(media_path), json.dumps(content, ensure_ascii=False),
         post_type, at, datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    qid = cur.lastrowid
    conn.close()
    return qid


def list_queue(cfg: Config, status: str | None = None) -> list[dict]:
    conn = _db(cfg)
    if status:
        rows = conn.execute("SELECT * FROM queue WHERE status=? ORDER BY scheduled_at",
                            (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM queue ORDER BY scheduled_at").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cancel_queued(cfg: Config, queue_id: int) -> bool:
    conn = _db(cfg)
    cur = conn.execute("UPDATE queue SET status='cancelled' WHERE id=? AND status='queued'",
                       (queue_id,))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def due_items(cfg: Config, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    conn = _db(cfg)
    rows = conn.execute(
        "SELECT * FROM queue WHERE status='queued' AND scheduled_at<=?",
        (now.strftime("%Y-%m-%d %H:%M"),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_posts_today(cfg: Config) -> int:
    conn = _db(cfg)
    today = datetime.now().strftime("%Y-%m-%d")
    n = conn.execute(
        "SELECT COUNT(*) c FROM posts WHERE substr(posted_at,1,10)=?", (today,)
    ).fetchone()["c"]
    conn.close()
    return n


# --------------------------------------------------------------- posting --

def publish_queue_item(cfg: Config, item: dict, client) -> str:
    """Post one queue item through the given client. Enforces the daily cap."""
    from .ig_client import guard_daily_cap, IGError
    guard_daily_cap(cfg)

    content = json.loads(item["content_json"] or "{}")
    from .content_gen import ContentPlan
    plan = ContentPlan.from_dict(content)
    caption = plan.full_caption()
    ptype = item["post_type"]
    media = item["media_path"]

    try:
        if ptype == "story":
            ig_id = client.publish_story(media)
        elif ptype in ("reel", "video"):
            ig_id = client.publish_reel(media, caption)
        elif ptype == "carousel":
            raise IGError("carousel needs multi-file support — post as reel/photo "
                          "or split into single files")
        else:
            ig_id = client.publish_photo(media, caption)
    except Exception as e:
        conn = _db(cfg)
        conn.execute("UPDATE queue SET status='failed' WHERE id=?", (item["id"],))
        conn.commit(); conn.close()
        raise

    conn = _db(cfg)
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("UPDATE queue SET status='posted', ig_media_id=? WHERE id=?",
                 (str(ig_id), item["id"]))
    conn.execute("INSERT INTO posts (ig_media_id, post_type, caption_snip, posted_at) "
                 "VALUES (?,?,?,?)",
                 (str(ig_id), ptype, caption[:100], now))
    conn.commit(); conn.close()
    return str(ig_id)


def run_due(cfg: Config, client=None) -> list[dict]:
    """Publish everything due. Returns results list."""
    from .ig_client import get_client
    client = client or get_client(cfg)
    results = []
    for item in due_items(cfg):
        try:
            ig_id = publish_queue_item(cfg, item, client)
            results.append({"queue_id": item["id"], "ok": True, "ig_media_id": ig_id})
            print(f"[queue] #{item['id']} posted -> {ig_id}")
        except Exception as e:
            results.append({"queue_id": item["id"], "ok": False, "error": str(e)})
            print(f"[queue] #{item['id']} FAILED: {e}")
    return results
