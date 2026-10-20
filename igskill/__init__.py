"""
Glm-Flash-ig-skill — AI Instagram Viral Manager toolkit.

Modules:
    config      — runtime state + safety caps (zero-config, no .env)
    privacy     — consent guardrails (DM access requires permission)
    content_gen — viral captions/hashtags/ideas (the agent writes them — no API keys)
    media       — ffmpeg editing pipeline (reels, subtitles, music, watermark)
    ig_client   — Instagram adapter: Graph API (official) + session (instagrapi)
    scheduler   — SQLite queue + best-time slots
    analytics   — engagement snapshots + "what worked" report
    autopilot   — one prompt -> a week of scheduled posts
    server      — FastAPI dashboard
"""
__version__ = "1.0.0"
__skill_name__ = "instagram-viral-manager"
