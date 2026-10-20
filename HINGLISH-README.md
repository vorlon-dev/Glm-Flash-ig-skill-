# ⚡ Glm-Flash-ig-skill (Hinglish Guide)

**AI ka bheja hua Instagram manager.** Naya chat kholo, ye repo ka link paste
karo, aur AI tumhara personal viral influencer ban jayega — profile + niche
auto-analysis se leke video editing, captions, hashtags, posting, scheduling,
analytics — sab kuch AI khud karega. **Koi API key nahi, koi .env file nahi** —
repo universal hai. Aur haan: **DMs aur personal chats ko AI kabhi nahi kholta**
bina tumhari explicit permission ke. Promise. 🔒

## Kaise kaam karta hai (seedhi baat)

```
Tum (naya chat): "ye link install karo → github.com/vorlon-dev/Glm-Flash-ig-skill-"
        ↓
AI repo clone karta hai, self-test chalata hai
        ↓
AI puchega: IG ka username + password (bas itna hi — niche khud detect karega)
        ↓
Tum: "@mera_handle / merapassword"
        ↓
AI login karta hai (password sirf ek baar use hota hai, kahin save nahi hota)
        ↓
AUTO profile + niche analysis (engagement, kaunsa format chal raha hai)
        ↓
First Viral Report: audit → week-1 plan → video ko reel banata hai (9:16,
    subtitles, music, watermark) → hook-first caption + hashtags likhta hai →
    best time pe post ya schedule karta hai → "kya chala" report deta hai
```

**GLM key, OpenAI key, .env — kuch nahi chahiye.** Content AI khud likhta hai.

## Features ek nazar mein

- 🎬 **Pro editing** — koi bhi video → 9:16 reel (blur-fill), photo → 1:1/4:5
  post, auto-subtitles, background music (voice ducking ke saath), beat-cut
  jump cuts, watermark, IG limits ke hisaab se compression, photos → slideshow reel
- ✍️ **Viral copy** — hook-first captions, rotating hashtag sets (3 size mix),
  pinned comment ideas
- 🗓 **Smart timing** — niche + timezone ke hisaab se best slots (IST default),
  SQLite queue, din mein max 5 post (hard cap)
- 🤖 **Autopilot** — ek prompt → poore hafte ka plan (approval ke baad hi chalega)
- 📈 **Analytics** — engagement snapshots, "kya chala" report: top posts, best
  format, best hour
- 🖥 **Dashboard** — `python scripts/ig_server.py` → neon UI pe sab kuch
- 🛡 **Privacy** — DM/comment/story-viewers sirf tumhare written consent pe,
  reply se pehle draft dikhta hai, credentials sirf tumhari machine pe

## Setup (step by step)

```bash
git clone https://github.com/vorlon-dev/Glm-Flash-ig-skill-.git
cd Glm-Flash-ig-skill
python -m pip install -r requirements.txt   # bare `pip` mat use karna — galat Python mein chala jaata hai
python scripts/ig_setup.py --selftest  # sab [ok] aana chahiye

# connect — password sirf EK baar use hota hai, kahin save nahi hota
python scripts/ig_setup.py --login --user '<tumhara_handle>' --pass '<password>'
# → login ke turant baad AUTO profile + niche analysis chal jaata hai
#
# cloud server pe login 429 de raha hai? Instagram datacenter IPs block karta hai.
# Fix: residential proxy laga do — ek baar save hoga, har command mein apne aap use hoga:
# python scripts/ig_setup.py --login --user '<tumhara_handle>' --pass '<password>' \
#        --proxy 'http://user:pass@host:port'
```

2FA/challenge code aaye to: same command mein `--code 123456` add kar do

**Password na dena ho (sabse safe tarika):** apne computer pe session banao —
`pip install instagrapi` phir `python scripts/ig_session_export.py --user '<handle>'`
→ `ig_session.json` file chat mein bhej do. Agent usse `--import-session` se
import kar lega. Password tumhare computer se bahar jaata hi nahi. 🔒

## Roz ka kaam

```bash
# reel post (auto 9:16 + subs + music + watermark + compress)
python scripts/ig_post.py reel --media clip.mp4 \
  --caption "POV: tumhari 12-second recipe ne group chat tod diya 👀" \
  --tags "#streetfood,#foodreels"

# hafte ka autopilot (ideas bhi AI khud likhta hai)
python scripts/ig_autopilot.py plan --niche "street food" --ideas ideas.json
python scripts/ig_autopilot.py approve     # plan padh ke approve karo
python scripts/ig_autopilot.py run

# schedule dekho / due posts chalao
python scripts/ig_schedule.py slots
python scripts/ig_schedule.py run-due

# analytics
python scripts/ig_analytics.py snapshot
python scripts/ig_analytics.py report

# dashboard
python scripts/ig_server.py                # http://127.0.0.1:8790
```

## Important baatein (dhyan se padhna)

- **Session mode** (username/password) unofficial API use karta hai — chhota
  risk hai. Business account hai to **graph mode** best hai (`--token <TOKEN>`).
- **Password sirf login wale ek command mein use hota hai, disk pe kabhi
  nahi jaata.** Sirf session cookie cache hoti hai (`.state/` mein, local).
- Din mein 3 post default, max 5 — ye tumhare account ko ban se bachata hai.
- DM/comment access sirf tumhare written consent pe (`.state/consent.json`),
  reply se pehle draft dikhta hai, aur consent kabhi bhi revoke ho sakti hai.
- Follow-bots / mass-follow nahi hai — organic growth hi sustainable hai.

## Apna khud ka skill banao

Ye repo ek **template** hai — Instagram ki jagah YouTube, Twitter/X, WhatsApp,
LinkedIn manager bana sakte ho. Full guide:
[references/MAKE-YOUR-OWN-SKILL.md](references/MAKE-YOUR-OWN-SKILL.md)

English README ke liye: [README.md](README.md)

## Disclaimer

Ye project Instagram/Meta se affiliated nahi hai. Session mode unofficial API
hai, platform ToS ke against ja sakta hai — apne risk pe use karo. MIT License.
