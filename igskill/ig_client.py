"""Instagram client adapter — one interface, two engines.

  graph   — official Instagram Graph API (Business accounts, safest)
  session — instagrapi username/password (full features, unofficial)

No .env, no API keys: credentials are passed at runtime by the agent, the
password is used once and never stored, and the session cookie enables
passwordless resume. An optional residential proxy (cfg.proxy) routes ALL
traffic — login and session calls — for datacenter IPs that Instagram blocks
(login errors are auto-classified: rate-limit / challenge / bad password).
Publishing is rate-limited by igskill.scheduler (hard cap 5/day) and always
preceded by a randomized human-like delay.

instagrapi is imported lazily so the toolkit works without it (graph mode,
dashboard, editing, scheduling all still run).
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

import requests

from .config import Config


class IGError(RuntimeError):
    pass


# --------------------------------------------------------- login diagnostics --

RATE_LIMIT_MARKERS = ("429", "rate limit", "ratelimit", "please wait",
                      "throttl", "too many requests", "try again later",
                      "use a quality proxy")


def looks_like_rate_limit(msg: str) -> bool:
    """Detect Instagram IP rate-limiting (datacenter IPs get this a lot)."""
    low = str(msg).lower()
    return any(m in low for m in RATE_LIMIT_MARKERS)


def friendly_login_error(e: Exception) -> IGError:
    """Translate raw login exceptions into agent-actionable guidance."""
    msg = str(e)
    low = msg.lower()
    name = type(e).__name__.lower()
    if looks_like_rate_limit(msg) or "ratelimit" in name or "throttled" in name:
        return IGError(
            "Instagram is rejecting logins from this server's IP — cloud/"
            "datacenter IPs are commonly blocked. This is NOT a credentials "
            "problem.\n"
            "Do NOT retry again immediately: repeated attempts can flag the "
            "account (2 tries max, then stop).\n"
            "Pick ONE:\n"
            "  A. wait 30-60 min, then retry ONCE with the same command\n"
            "  B. ask the user for a residential/mobile proxy and re-run "
            "login with: --proxy 'http://user:pass@host:port'  (fastest fix)\n"
            "  C. switch to the official Graph API (Business account, zero "
            "ban risk): python scripts/ig_setup.py --token <TOKEN>"
        )
    if ("challenge" in low or "challenge" in name
            or "2fa" in low or ("two" in low and "factor" in low)):
        return IGError(
            "Instagram sent a login challenge (2FA/verification code).\n"
            "Ask the user for the 6-digit code they received, then run:\n"
            "  python scripts/ig_setup.py --login --user '<u>' --pass '<p>'"
            " --code <CODE>"
        )
    if ("badpassword" in name or "badcredentials" in name
            or ("password" in low and any(w in low for w in
                ("incorrect", "wrong", "invalid", "bad")))):
        return IGError(
            "Wrong username or password. Confirm both with the user in chat "
            "— never guess, never brute-force."
        )
    return IGError(f"login failed: {msg}")


class GraphAPIClient:
    """Official Instagram Graph API. Needs IG_ACCESS_TOKEN (+ IG_BUSINESS_ID)."""

    BASE = "https://graph.facebook.com/v21.0"

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.proxies = ({"http": cfg.proxy, "https": cfg.proxy}
                        if cfg.proxy else None)
        if not cfg.ig_access_token:
            raise IGError(
                "graph mode needs a token. Get it from the user (Business "
                "account) and run: python scripts/ig_setup.py --token <TOKEN>")
        self.token = cfg.ig_access_token
        self.user_id = cfg.ig_business_id or self._me()

    def _me(self) -> str:
        r = requests.get(f"{self.BASE}/me", params={
            "fields": "id,username", "access_token": self.token},
            timeout=30, proxies=self.proxies)
        return self._ok(r)["id"]

    @staticmethod
    def _ok(r: requests.Response) -> dict:
        data = r.json()
        if r.status_code != 200 or "error" in data:
            err = data.get("error", {}).get("message", r.text[:200])
            raise IGError(f"Graph API error: {err}")
        return data

    def profile(self) -> dict:
        return self._ok(requests.get(f"{self.BASE}/{self.user_id}", params={
            "fields": "username,followers_count,media_count,profile_picture_url",
            "access_token": self.token}, timeout=30, proxies=self.proxies))

    def _container(self, params: dict) -> str:
        params["access_token"] = self.token
        data = self._ok(requests.post(
            f"{self.BASE}/{self.user_id}/media", data=params, timeout=60,
            proxies=self.proxies))
        return data["id"]

    def _wait_container(self, container_id: str, tries: int = 30) -> None:
        for _ in range(tries):
            st = self._ok(requests.get(f"{self.BASE}/{container_id}", params={
                "fields": "status_code", "access_token": self.token},
                timeout=30, proxies=self.proxies))
            code = st.get("status_code")
            if code == "FINISHED":
                return
            if code == "ERROR":
                raise IGError("container processing failed (check media URL/codec)")
            time.sleep(3)
        raise IGError("container timeout — try again")

    def _publish(self, creation_id: str) -> str:
        data = self._ok(requests.post(f"{self.BASE}/{self.user_id}/media_publish",
                                      data={"creation_id": creation_id,
                                            "access_token": self.token},
                                      timeout=60, proxies=self.proxies))
        return data.get("id", "published")

    def _human_delay(self) -> None:
        time.sleep(random.uniform(max(10, self.cfg.min_delay_seconds),
                                  max(15, self.cfg.max_delay_seconds)))

    def publish_photo(self, image_url: str, caption: str) -> str:
        self._human_delay()
        cid = self._container({"image_url": image_url, "caption": caption})
        self._wait_container(cid)
        return self._publish(cid)

    def publish_video(self, video_url: str, caption: str, as_reel: bool = False) -> str:
        self._human_delay()
        params = {"media_type": "REELS" if as_reel else "VIDEO",
                  "video_url": video_url, "caption": caption}
        cid = self._container(params)
        self._wait_container(cid, tries=60)
        return self._publish(cid)

    def publish_reel(self, video_url: str, caption: str) -> str:
        return self.publish_video(video_url, caption, as_reel=True)

    def publish_story(self, image_url: str) -> str:
        self._human_delay()
        cid = self._container({"image_url": image_url, "media_type": "STORIES"})
        self._wait_container(cid)
        return self._publish(cid)

    def recent_media(self, limit: int = 12) -> list[dict]:
        edge = self._ok(requests.get(f"{self.BASE}/{self.user_id}/media", params={
            "fields": "id,like_count,comments_count,timestamp,media_type,permalink",
            "limit": limit, "access_token": self.token},
            timeout=30, proxies=self.proxies))
        return edge.get("data", [])


class SessionClient:
    """instagrapi engine — credentials used ONCE at login, then cookie session.

    The password is never written to disk. Resume is passwordless: the cached
    session in .state/session.json is probed with the home-feed endpoint
    (documented session test) purely to check validity — its content is
    discarded and never read for data.
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        try:
            from instagrapi import Client  # lazy: heavy import
        except ImportError as e:
            raise IGError(
                "instagrapi is not installed (needed for session mode).\n"
                "  pip install instagrapi"
            ) from e
        self.Client = Client
        self.cl = Client()
        if cfg.proxy:
            try:
                self.cl.set_proxy(cfg.proxy)
            except Exception as e:
                raise IGError(
                    f"bad proxy URL ({e}). Format: http://user:pass@host:port"
                ) from e
        self.cl.delay_range = [max(2, cfg.min_delay_seconds // 3),
                               max(4, cfg.max_delay_seconds // 3)]
        self.session_file = Path(cfg.session_file)
        self._loaded = False
        self.last_resume_error = ""

    # ------------------------------------------------------------- session --
    def _try_resume(self) -> bool:
        """Passwordless resume from cached cookies. Probe = home-feed endpoint
        (validity check only — feed content is discarded, never stored/shown)."""
        self.last_resume_error = ""
        if not self.session_file.exists():
            return False
        try:
            self.cl.load_settings(self.session_file)
            self.cl.get_timeline_feed()  # validity probe only
            self._loaded = True
            return True
        except Exception as e:
            self.last_resume_error = str(e)
            return False

    def login(self, code: str | None = None) -> dict:
        if not code and self._try_resume():
            return {"ok": True, "restored": "valid session file — no password needed"}
        # If even the session probe is rate-limited, the IP is blocked — a
        # password login now would ALSO fail and further flag the account.
        if looks_like_rate_limit(self.last_resume_error):
            raise friendly_login_error(Exception(self.last_resume_error))
        if not (self.cfg.ig_username and self.cfg.ig_password):
            raise IGError(
                "no valid session and no credentials provided.\n"
                "Ask the user in chat, then run:\n"
                "  python scripts/ig_setup.py --login --user '<u>' --pass '<p>'"
                " [--code 123456]"
            )
        try:
            self.cl.login(self.cfg.ig_username, self.cfg.ig_password,
                          verification_code=code)
        except Exception as e:
            raise friendly_login_error(e) from e
        self.cl.dump_settings(self.session_file)
        self._loaded = True
        return {"ok": True, "restored": "fresh login (password discarded)"}

    def _ensure(self) -> None:
        if not self._loaded:
            if self._try_resume():
                return
            raise IGError(
                "Instagram session missing or expired.\n"
                "Tell the user, and ask them to confirm re-login in chat, then:\n"
                "  python scripts/ig_setup.py --login --user '<u>' --pass '<p>'"
            )

    def profile(self) -> dict:
        self._ensure()
        u = self.cl.account_info()
        return {"username": u.username, "followers_count": u.follower_count,
                "media_count": u.media_count, "full_name": u.full_name or ""}

    # ----------------------------------------------------------- publishing --
    def publish_photo(self, image_path: str, caption: str) -> str:
        self._ensure()
        time.sleep(random.uniform(max(10, self.cfg.min_delay_seconds),
                                  max(15, self.cfg.max_delay_seconds)))
        media = self.cl.photo_upload(str(image_path), caption)
        return str(media.pk)

    def publish_video(self, video_path: str, caption: str, as_reel: bool = False) -> str:
        self._ensure()
        time.sleep(random.uniform(max(10, self.cfg.min_delay_seconds),
                                  max(15, self.cfg.max_delay_seconds)))
        if as_reel:
            media = self.cl.clip_upload(str(video_path), caption)
        else:
            media = self.cl.video_upload(str(video_path), caption)
        return str(media.pk)

    def publish_reel(self, video_path: str, caption: str) -> str:
        return self.publish_video(video_path, caption, as_reel=True)

    def publish_story(self, media_path: str) -> str:
        self._ensure()
        time.sleep(random.uniform(8, 20))
        p = Path(media_path)
        if p.suffix.lower() in {".mp4", ".mov", ".m4v"}:
            media = self.cl.video_upload_to_story(str(p))
        else:
            media = self.cl.photo_upload_to_story(str(p))
        return str(media.pk)

    def recent_media(self, limit: int = 12) -> list[dict]:
        self._ensure()
        medias = self.cl.user_medias(self.cl.user_id, amount=limit)
        out = []
        for m in medias:
            out.append({
                "id": str(m.pk), "like_count": m.like_count,
                "comments_count": m.comment_count,
                "timestamp": m.taken_at.isoformat() if m.taken_at else "",
                "media_type": str(m.media_type), "permalink": "",
                "caption": (m.caption_text or "")[:80],
            })
        return out


def get_client(cfg: Config):
    """Factory honoring IG_MODE (auto -> graph if token else session)."""
    mode = cfg.resolved_mode
    if mode == "graph":
        return GraphAPIClient(cfg)
    return SessionClient(cfg)


# --------------------------------------------------------- daily rate limit --

def posts_today(cfg: Config) -> int:
    """Read today's published count from the scheduler DB (single source of truth)."""
    from .scheduler import count_posts_today
    try:
        return count_posts_today(cfg)
    except Exception:
        return 0


def guard_daily_cap(cfg: Config) -> None:
    n = posts_today(cfg)
    if n >= cfg.max_posts_per_day:
        raise IGError(
            f"daily cap reached ({n}/{cfg.max_posts_per_day} posts today).\n"
            "This hard limit protects the account from bans. Post tomorrow or "
            "queue for the scheduler — do NOT bypass."
        )


if __name__ == "__main__":
    from .config import load_config
    c = get_client(load_config())
    print(json.dumps(c.profile(), indent=2, ensure_ascii=False))
