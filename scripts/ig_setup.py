#!/usr/bin/env python3
"""ig_setup — self-test, connect account, show profile.

  python scripts/ig_setup.py --selftest        # verify ffmpeg/deps/config
  python scripts/ig_setup.py --login           # session mode login (saves session)
  python scripts/ig_setup.py --login --code 123456   # after IG challenge
  python scripts/ig_setup.py --token TOKEN     # graph mode
  python scripts/ig_setup.py --profile         # who am I connected as
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def selftest() -> int:
    print("=== Glm-Flash-ig-skill self-test ===")
    ok = True
    try:
        from igskill.config import load_config
        cfg = load_config()
        print(f"[ok] config loaded — mode={cfg.resolved_mode} tz={cfg.timezone} "
              f"cap={cfg.max_posts_per_day}/day")
    except SystemExit as e:
        print(f"[warn] config: {e}")
    import importlib
    for mod in ("dotenv", "PIL", "httpx", "fastapi", "uvicorn", "requests"):
        try:
            importlib.import_module(mod)
            print(f"[ok] python dep: {mod}")
        except ImportError:
            print(f"[MISS] python dep: {mod}  -> pip install {mod}")
            ok = False
    try:
        import shutil
        if shutil.which("ffmpeg"):
            print("[ok] ffmpeg found")
        else:
            print("[MISS] ffmpeg — install it (see README)")
            ok = False
    except Exception:
        pass
    try:
        from igskill.media import thumbnail
        from PIL import Image
        tmp = Path("/tmp/igskill_selftest")
        tmp.mkdir(exist_ok=True)
        img = tmp / "t.jpg"
        Image.new("RGB", (600, 600), (20, 20, 40)).save(img)
        out = thumbnail(img, tmp / "cover.jpg", at=0)
        print(f"[ok] ffmpeg pipeline ran -> {out.name}")
    except Exception as e:
        print(f"[MISS] media pipeline: {e}")
        ok = False
    try:
        from igskill.scheduler import best_slots
        from igskill.config import Config
        slots = best_slots(Config(), "reel", days=1)
        print(f"[ok] scheduler slots: {len(slots)} next slots computed")
    except Exception as e:
        print(f"[MISS] scheduler: {e}")
        ok = False
    print("=== " + ("ALL GOOD — you're ready to go viral 🚀" if ok else "fix the MISS items above") + " ===")
    return 0 if ok else 1


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--login", action="store_true")
    p.add_argument("--code", help="2FA/challenge verification code")
    p.add_argument("--token", help="Graph API access token (stores in .env)")
    p.add_argument("--profile", action="store_true")
    a = p.parse_args()

    if a.selftest:
        sys.exit(selftest())

    if a.token:
        env = Path(__file__).resolve().parent.parent / ".env"
        lines = env.read_text().splitlines() if env.exists() else []
        lines = [l for l in lines if not l.startswith("IG_ACCESS_TOKEN=")]
        lines.append(f"IG_ACCESS_TOKEN={a.token}")
        env.write_text("\n".join(lines) + "\n")
        print("[ok] token saved to .env — graph mode active")

    from igskill.config import load_config
    from igskill.ig_client import get_client

    if a.login:
        cfg = load_config()
        client = get_client(cfg)
        res = client.login(code=a.code)
        print(f"[ok] logged in (restored: {res['restored']})")

    if a.profile or (a.login and not a.selftest):
        cfg = load_config()
        import json
        print(json.dumps(get_client(cfg).profile(), indent=2, ensure_ascii=False))

    if not any([a.selftest, a.login, a.token, a.profile]):
        p.print_help()


if __name__ == "__main__":
    main()
