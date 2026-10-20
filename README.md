# ⚡ Glm-Flash-ig-skill

**An AI-operated Instagram growth manager for z.ai GLM.** The user links their
Instagram in a fresh chat, and the agent becomes their viral influencer:
strategy, editing, captions, hashtags, posting, scheduling, analytics — all
handled by AI. Privacy-first by design: DMs and chats are **never** touched
without explicit permission.

[हिंदी-English version → HINGLISH-README.md](HINGLISH-README.md)

## How it works (the 10-second pitch)

```
User (fresh chat): "https://github.com/vorlon-dev/Glm-Flash-ig-skill- install this"
        ↓
Agent clones the repo, self-tests, asks for IG id + pass + niche
        ↓
User: "@myhandle / street food / India"
        ↓
Agent: audit → week-1 viral plan → edits media (ffmpeg) → writes hooks,
captions, hashtags → posts/schedules at best times → tracks what worked
```

No GLM key needed for the user: in agent mode **the AI writes the content
itself**. (Optional `ZAI_API_KEY` only unlocks `--use-api` generation.)

## Features

| | |
|---|---|
| 🎬 **Pro editing** | any video → 9:16 reels (blur-fill), 1:1/4:5 posts, auto-subtitles, music w/ voice-ducking, beat-cut jump cuts, watermark, compress under IG limits, photo→reel slideshows |
| ✍️ **Viral copy** | hook-first captions (H-T-P-C), rotating hashtag sets (big/mid/niche), pinned-comment ideas |
| 🗓 **Smart scheduling** | researched slot times per format & timezone (IST default), SQLite queue, daily cap 5 |
| 🤖 **Autopilot** | one prompt → full week: ideas → media pipeline → captions → schedule (approval-gated) |
| 📈 **Analytics** | engagement snapshots, "what worked" report: top posts, best format, best hour |
| 🖥 **Dashboard** | FastAPI + neon UI: status, queue, one-click autopilot, consent toggles |
| 🛡 **Privacy constitution** | DMs/notifications/story-viewers locked behind recorded consent; drafts before any reply; credentials stay local |

## Two connection modes

| | **session** (default) | **graph** (official) |
|---|---|---|
| Needs | username + password | Meta app token + Business account |
| Setup | seconds | ~15 min on Meta portal |
| Risk | small (unofficial API) | none |
| Feature scope | everything | publish + insights |

## Quickstart (human-run)

```bash
git clone https://github.com/vorlon-dev/Glm-Flash-ig-skill-.git
cd Glm-Flash-ig-skill
pip install -r requirements.txt        # + system ffmpeg
cp .env.example .env                   # fill IG creds + NICHE + TIMEZONE
python scripts/ig_setup.py --selftest
python scripts/ig_setup.py --login

# post a reel: auto 9:16 + subs + music + watermark + compress + post
python scripts/ig_post.py reel --media clip.mp4 \
  --caption "POV: your 12-second recipe broke the group chat 👀" \
  --tags "#streetfood,#foodreels" --subs subs.srt --music bgm.mp3

# week on autopilot (plan → approve → run)
python scripts/ig_autopilot.py plan --niche "street food"
python scripts/ig_autopilot.py approve && python scripts/ig_autopilot.py run

# dashboard
python scripts/ig_server.py            # http://127.0.0.1:8790
```

## CLI map

| Script | Purpose |
|---|---|
| `ig_setup.py` | `--selftest` · `--login [--code N]` · `--token T` · `--profile` |
| `ig_post.py` | edit + post `photo/reel/story/video` (or `--queue "YYYY-MM-DD HH:MM"`) |
| `ig_edit.py` | `reel-ify` `post-ify` `subtitles` `music` `beat-cut` `slideshow` `thumbnail` `pipeline` |
| `ig_schedule.py` | `slots` `add` `list` `run-due` `cancel` |
| `ig_analytics.py` | `snapshot` `report` |
| `ig_autopilot.py` | `plan` `approve` `run` `due` `status` |
| `ig_server.py` | dashboard + REST API (`/docs`) |

## Safety rails (built-in, not optional)

- hard cap **5 posts/day** (default 3) + randomized 30–120 s action delays
- login challenges surface to the user — never bypassed
- consent file `.consent.json` gates DMs/comments/replies/full-autopilot
- no follow-bots, no mass actions, no credential exfiltration
- everything local: `.env`, session, consent, SQLite are git-ignored

## Build your own skill

This repo is a **template** for agent-operated skills — see
[references/MAKE-YOUR-OWN-SKILL.md](references/MAKE-YOUR-OWN-SKILL.md) and
[templates/SKILL-TEMPLATE.md](templates/SKILL-TEMPLATE.md).

## Docs

- [INSTALL.md](INSTALL.md) — the agent's install-from-link procedure
- [references/VIRAL-PLAYBOOK.md](references/VIRAL-PLAYBOOK.md) — algorithm, hooks, niche cheatsheets
- [references/PRIVACY-RULES.md](references/PRIVACY-RULES.md) — the full privacy policy

## Disclaimer

This project is not affiliated with Instagram or Meta. Session mode uses an
unofficial API and may violate platform ToS — use at your own risk, prefer
graph mode for business accounts. MIT License.
