#!/usr/bin/env python3
"""ig_audit — automatic profile & niche analysis (runs right after login).

Pulls the connected profile + recent post metrics and prints a JSON briefing
the AI agent reads to deliver the First Viral Report:

  python scripts/ig_audit.py            # full audit
  python scripts/ig_audit.py --limit 18 # more posts in the sample

The agent interprets this and confirms the niche with the user (or asks for
it if the profile is ambiguous). No API keys, no .env — the agent itself is
the analyst.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def analyze(profile: dict, medias: list[dict]) -> dict:
    """Pure function: profile + recent media -> structured briefing."""
    eng = []
    by_type = {}
    timestamps = []
    for m in medias:
        likes = int(m.get("like_count") or 0)
        comments = int(m.get("comments_count") or 0)
        eng.append({"likes": likes, "comments": comments, "total": likes + comments})
        t = str(m.get("media_type", "unknown"))
        by_type.setdefault(t, {"count": 0, "eng": 0})
        by_type[t]["count"] += 1
        by_type[t]["eng"] += likes + comments
        ts = m.get("timestamp") or ""
        if ts:
            timestamps.append(ts[:10])

    total_eng = sum(e["total"] for e in eng)
    n = len(eng) or 1
    followers = int(profile.get("followers_count") or 0)
    avg = total_eng / n
    best = max(eng, key=lambda e: e["total"]) if eng else {"total": 0}
    er = (avg / followers * 100) if followers else 0.0

    # posting frequency (posts represented in sample over their day-span)
    freq_hint = ""
    if len(timestamps) >= 2:
        try:
            from datetime import date
            days = sorted({date.fromisoformat(t) for t in timestamps})
            span = max((d - days[0]).days for d in days) or 1
            freq_hint = f"~{len(days) / span:.1f} posts/day in recent sample"
        except ValueError:
            pass

    formats = sorted(by_type.items(), key=lambda kv: kv[1]["eng"], reverse=True)
    return {
        "profile": profile,
        "sample_size": len(eng),
        "avg_engagement": round(avg, 1),
        "engagement_rate_pct": round(er, 2),
        "top_post_engagement": best.get("total", 0),
        "formats_ranked": [
            {"type": t, "posts": v["count"],
             "avg_eng": round(v["eng"] / v["count"], 1)} for t, v in formats
        ],
        "posting_frequency": freq_hint,
        "recent_medias": [
            {"id": m.get("id"), "likes": m.get("like_count"),
             "comments": m.get("comments_count"), "caption": m.get("caption", "")[:60]}
            for m in medias
        ],
    }


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="auto profile & niche analysis")
    p.add_argument("--limit", type=int, default=12)
    a = p.parse_args()

    from igskill.config import load_config, save_profile
    from igskill.ig_client import get_client

    cfg = load_config()
    cfg.require_credentials()
    client = get_client(cfg)

    print(f"[audit] connecting ({cfg.resolved_mode})...", file=sys.stderr)
    profile = client.profile()
    medias = client.recent_media(limit=a.limit)

    briefing = analyze(profile, medias)
    save_profile({
        "username": profile.get("username", cfg.ig_username),
        "followers": profile.get("followers_count"),
        "last_audit": briefing.get("avg_engagement"),
        "watermark": cfg.watermark or f"@{profile.get('username', '')}",
    })

    print(json.dumps(briefing, indent=2, ensure_ascii=False))
    print("\n[agent] read the JSON above, then:", file=sys.stderr)
    print("  1. infer the niche (bio, captions, content mix) — or ask the user",
          file=sys.stderr)
    print("  2. confirm niche: python scripts/ig_setup.py --set-niche '...'",
          file=sys.stderr)
    print("  3. deliver the First Viral Report (SKILL.md section 6)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
