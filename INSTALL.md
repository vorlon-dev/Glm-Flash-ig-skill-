# INSTALL.md — for the AI agent performing the install

> A user just pasted this repo link in a fresh chat. Follow exactly these
> steps, then continue with SKILL.md §1. No .env, no API keys — this repo is
> universal and zero-config.

## 1. Clone & bootstrap

```bash
git clone <REPO_URL> glm-ig-skill
cd glm-ig-skill
python -m pip install -r requirements.txt
```

⚠️ Use `python -m pip`, never bare `pip` — many sandboxes run a venv whose
Python differs from the one `pip` points to; bare pip silently installs into
the wrong environment and imports still fail afterward.

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

- Instagram **username + password** — that's the required part.
- Optional: their goal (followers / sales / brand) and country — otherwise
  you will auto-detect the niche and timezone right after login.

## 4. Connect (credentials are runtime-only, never stored)

```bash
python scripts/ig_setup.py --login --user '<username>' --pass '<password>'
```
- If Instagram sends a challenge: ask the user for the 6-digit code and re-run
  with `--code 123456`. Never bypass challenges.
- The password is used **once** by this command and never saved anywhere.
- The session is cached in `.state/session.json` for passwordless reuse.

### If login is blocked with HTTP 429 / "please wait a few minutes"

The server IP (a cloud datacenter IP) is blocked by Instagram — **this is not
a credentials problem**, and retrying repeatedly will flag the account. Try at
most TWICE, then pick one:

- **Residential/mobile proxy (fastest):** ask the user for a proxy URL, then
  ```bash
  python scripts/ig_setup.py --login --user '<u>' --pass '<p>' \
         --proxy 'http://user:pass@host:port'
  ```
  It is saved in `.state/` (local, git-ignored) and used for every later
  command automatically.
- **Official Graph API (safest, Business accounts):**
  `python scripts/ig_setup.py --token <TOKEN>`
- **Wait 30–60 min** and retry once.

Business accounts (optional, safest): `python scripts/ig_setup.py --token <TOKEN>`

Connection summary anytime: `python scripts/ig_setup.py --status`

## 5. Auto-analyze (happens automatically after login)

`ig_setup.py --login` chains `ig_audit.py`, which prints a JSON briefing:
profile stats, engagement rate, format mix, posting frequency. As the agent:

1. Read the briefing and **infer the niche** from bio/captions/content mix.
2. Confirm with the user in one line, or ask if ambiguous:
   `python scripts/ig_setup.py --set-niche "street food" --set-goal followers`
3. Deliver the **First Viral Report** (SKILL.md §6) in chat.

## 6. Then run their account

Generate the week-1 autopilot plan (you write the ideas — you're the content
engine), show it for approval, and never post before approval:

```bash
python scripts/ig_autopilot.py plan --niche "<niche>" --ideas my_ideas.json
# user approves in chat ->
python scripts/ig_autopilot.py approve && python scripts/ig_autopilot.py run
```

## Privacy briefing (tell the user, verbatim or in your words)

- The skill never opens DMs or notifications unless you explicitly allow it
- Any reply to DMs/comments is drafted and shown to you before sending
- Consent is recorded in `.state/consent.json` and revocable any time
- Your password is used once at login and never stored on disk — only the
  session cookie is cached (local, git-ignored)
- If you provide a proxy, it is also stored locally only (and displayed
  masked as `***@host:port` in status output)
