#!/usr/bin/env python3
"""ig_setup — zero-config connection: self-test, login, profile, settings.

Everything is runtime-args based. No .env. Universal repo.

  python scripts/ig_setup.py --selftest
  python scripts/ig_setup.py --login --user '<u>' --pass '<p>' [--code 123456]
  python scripts/ig_setup.py --token <GRAPH_TOKEN>        # Business accounts
  python scripts/ig_setup.py --profile
  python scripts/ig_setup.py --set-niche "street food" --set-goal followers

After a successful --login, the profile is auto-analyzed (niche, engagement,
best formats) and .state/profile.json is updated. The password is used ONCE
for login and is never written to disk.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def selftest() -> int:
    print("=== Glm-Flash-ig-skill self-test ===")
    ok = True
    import importlib
    for mod in ("PIL", "fastapi", "uvicorn", "requests", "pydantic"):
        try:
            importlib.import_module(mod)
            print(f"[ok] python dep: {mod}")
        except ImportError:
            print(f"[MISS] python dep: {mod}  -> pip install {mod}")
            ok = False
    import shutil
    if shutil.which("ffmpeg"):
        print("[ok] ffmpeg found")
    else:
        print("[MISS] ffmpeg — install it (see README)")
        ok = False
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
        from igskill.config import load_config
        slots = best_slots(load_config(), "reel", days=1)
        print(f"[ok] scheduler slots: {len(slots)} next slots "
              f"({load_config().timezone})")
    except Exception as e:
        print(f"[MISS] scheduler: {e}")
        ok = False
    from igskill.config import load_config
    cfg = load_config()
    print(f"[ok] state dir ready — {cfg.connected_hint()}")
    print("=== " + ("ALL GOOD — ready to go viral 🚀" if ok else "fix the MISS items above") + " ===")
    return 0 if ok else 1


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="zero-config Instagram connection")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--login", action="store_true",
                   help="session-mode login (username/password, used once)")
    p.add_argument("--user", help="Instagram username (runtime, not stored)")
    p.add_argument("--pass", dest="password", help="Instagram password "
                   "(runtime, used once, NEVER saved to disk)")
    p.add_argument("--code", help="2FA/challenge verification code")
    p.add_argument("--token", help="Graph API token (Business accounts)")
    p.add_argument("--profile", action="store_true")
    p.add_argument("--set-niche", dest="set_niche")
    p.add_argument("--set-goal", dest="set_goal")
    p.add_argument("--set-handle", dest="set_handle",
                   help="watermark handle, e.g. @myhandle")
    a = p.parse_args()

    if a.selftest:
        sys.exit(selftest())

    from igskill.config import load_config, save_profile

    if a.token:
        save_profile({"graph_token": a.token, "mode": "graph"})
        print("[ok] Graph token saved to .state/profile.json (local only) "
              "— graph mode active")

    if a.set_niche:
        save_profile({"niche": a.set_niche})
        print(f"[ok] niche -> {a.set_niche}")
    if a.set_goal:
        save_profile({"goal": a.set_goal})
        print(f"[ok] goal -> {a.set_goal}")
    if a.set_handle:
        save_profile({"watermark": a.set_handle})
        print(f"[ok] watermark -> {a.set_handle}")

    if a.login:
        cfg = load_config()
        if not (a.user and a.password):
            raise SystemExit("login needs --user and --pass "
                             "(ask the user in chat; never store them)")
        from igskill.ig_client import SessionClient
        cfg.ig_username = a.user
        cfg.ig_password = a.password
        client = SessionClient(cfg)
        res = client.login(code=a.code)
        save_profile({"username": a.user,
                      "watermark": f"@{a.user}" if not cfg.watermark else cfg.watermark,
                      "mode": "session"})
        print(f"[ok] logged in (restored: {res['restored']}) — session cached, "
              "password discarded")
        print("[next] auto-analyzing profile...")
        try:
            import subprocess
            r = subprocess.run([sys.executable, str(Path(__file__).parent / "ig_audit.py")],
                               capture_output=True, text=True, timeout=180)
            print(r.stdout)
            if r.returncode != 0:
                print(r.stderr[-300:])
        except Exception as e:
            print(f"[warn] auto-audit skipped: {e}")

    if a.profile:
        cfg = load_config()
        import igskill.ig_client as igc
        try:
            print(json.dumps(igc.get_client(cfg).profile(), indent=2,
                             ensure_ascii=False))
        except SystemExit as e:
            print(e)

    if not any([a.selftest, a.login, a.token, a.profile, a.set_niche,
                a.set_goal, a.set_handle]):
        p.print_help()


if __name__ == "__main__":
    main()
