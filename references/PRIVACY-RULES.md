# Privacy Rules — the full policy text

This is the human-readable policy behind the code in `igskill/privacy.py`.
Show this file to users whenever they ask "what can this skill see / touch?"

## The deal

This skill runs a real Instagram account on the user's behalf. That power
comes with a hard boundary: **the AI manages content and growth — it never
snoops.**

## What the AI does freely (no extra permission needed)

- Write captions, hooks, hashtags, and post ideas
- Edit the user's own media files (crop, subtitles, music, watermark)
- Publish posts/reels/stories that were **shown to or planned with the user**
- Read **public post metrics** (likes, comments, view counts) for analytics
- Suggest posting times and strategy

## What ALWAYS requires explicit permission first

| Action | Consent scope |
|---|---|
| Open or read DMs / private chats | `read_dms` |
| Send or reply to DMs | `reply_dms` |
| Read comments beyond metric counts | `read_comments` |
| Write comment replies | `reply_comments` |
| See story viewers | `story_viewers` |
| Post scheduled items without showing each one | `full_autopilot` |

Permission must come from the user in the current conversation. The AI asks,
shows exactly what it wants to do, and only then records consent (stored
locally in `.consent.json`). Consent can be revoked any time:

```bash
python -m igskill.privacy --revoke read_dms
python -m igskill.privacy --status
```

## Hard refusals (even if the user asks)

- Never read DMs "just to check" without being asked
- Never send a message the user hasn't approved (drafts first, always)
- Never mass-follow/unfollow/like — ban risk, refused by design
- Never bypass login challenges, rate limits, or the daily cap
- Never upload the user's credentials anywhere except their own local machine

## Data storage

- Password: **never stored anywhere** — used once in the login command's
  process memory, then discarded
- Session cookies: `.state/session.json` (local only, git-ignored)
- Profile facts (niche, watermark, timezone): `.state/profile.json`
- Consent: `.state/consent.json` (local only, git-ignored)
- Metrics/queue: `ig_data.db` (local SQLite)

Nothing is sent to any server other than Instagram's own APIs. There are no
API keys in this skill and no third-party LLM calls — the agent in the chat
is the content engine.
