# INSTALL.md — for the AI agent performing the install

> A user just pasted this repo link in a fresh chat. Follow exactly these
> steps, then continue with SKILL.md §1.

## 1. Clone & bootstrap

```bash
git clone <REPO_URL> glm-ig-skill
cd glm-ig-skill
pip install -r requirements.txt
cp .env.example .env
```

If `ffmpeg` is missing (`ffmpeg -version` fails), install it first:
- Ubuntu/Debian: `sudo apt install -y ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: `winget install Gyan.FFmpeg`

## 2. Verify

```bash
python scripts/ig_setup.py --selftest
```
All lines should be `[ok]`. Fix any `[MISS]` before continuing.

## 3. Collect from the user (one friendly message)

- Instagram **username + password** (session mode) — or a **Graph API
  token** if they run a Business account (official, safest)
- Their **niche** (fitness / food / travel / fashion / tech / music / comedy / other)
- Their **goal** (followers, sales, brand) and country/timezone
- Optional: a folder of raw media to work with

## 4. Connect

```bash
python scripts/ig_setup.py --login          # session mode
python scripts/ig_setup.py --token <TOKEN>  # graph mode
python scripts/ig_setup.py --profile        # verify who is connected
```
If Instagram sends a login challenge: ask the user for the 6-digit code and
re-run with `--code 123456`. Never try to bypass challenges.

## 5. Configure

Write `.env` with: NICHE, TIMEZONE, WATERMARK (their @handle), MAX_POSTS_PER_DAY
(default 3, hard cap 5). Leave ZAI_API_KEY empty — in agent mode the agent
writes captions itself; no API key is needed.

## 6. Deliver

Produce the **First Viral Report** (SKILL.md §6) in chat, then generate the
week-1 autopilot plan (`python scripts/ig_autopilot.py plan --niche <niche>`)
and show it for approval. Do not post anything before approval.

## Privacy briefing (tell the user, verbatim or in your words)

- The skill never opens DMs or notifications unless you explicitly allow it
- Any reply to DMs/comments is drafted and shown to you before sending
- Consent is stored in `.consent.json` and revocable any time
- Credentials/session files stay on this machine and are git-ignored
