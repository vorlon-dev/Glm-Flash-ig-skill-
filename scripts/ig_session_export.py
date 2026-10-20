#!/usr/bin/env python3
"""ig_session_export — run this on YOUR OWN computer (NOT the sandbox).

Purpose: create an Instagram session file from your home IP, so the AI agent
can manage your account WITHOUT ever seeing your password and WITHOUT hitting
the datacenter-IP blocks (HTTP 429) that password logins from cloud servers
trigger.

How to use (on your local machine):

  pip install instagrapi
  python scripts/ig_session_export.py --user <your_username>
  # → writes ig_session.json next to you

Then send ig_session.json to your agent in chat. On the sandbox the agent
imports it:

  python scripts/ig_setup.py --import-session ig_session.json
  python scripts/ig_audit.py          # auto profile + niche analysis

Privacy notes:
  - the password is prompted hidden (getpass), used once in memory, NEVER
    written to disk and NEVER seen by the agent
  - ig_session.json = full account access: keep it private, send it only in
    the trusted chat, and delete your local copy once imported if you like
  - sessions expire after weeks/months or if you log out — just re-export
"""
import argparse
import getpass
import sys


def main() -> None:
    p = argparse.ArgumentParser(
        description="Export an Instagram session file on your own computer")
    p.add_argument("--user", required=True, help="your Instagram username")
    p.add_argument("--out", default="ig_session.json",
                   help="output file (default: ig_session.json)")
    a = p.parse_args()

    try:
        from instagrapi import Client
    except ImportError:
        sys.exit("instagrapi is missing. Install it first:\n"
                 "  pip install instagrapi")

    pw = getpass.getpass(f"Instagram password for '{a.user}' (hidden): ")
    if not pw:
        sys.exit("empty password — aborted (nothing was sent anywhere)")

    cl = Client()
    cl.delay_range = [2, 5]

    try:
        cl.login(a.user, pw)
    except Exception as e:
        msg = str(e).lower()
        if "challenge" in msg or "code" in msg or "2fa" in msg:
            code = input("Instagram sent you a 6-digit code. Enter it: ").strip()
            try:
                cl.login(a.user, pw, verification_code=code)
            except Exception as e2:
                sys.exit(f"login with code failed: {e2}")
        else:
            sys.exit(f"login failed: {e}\n"
                     "(wrong password? rate-limited? wait a bit and retry — "
                     "you are on a home IP, so retries here are safe)")

    cl.dump_settings(a.out)
    print(f"\n[ok] session exported -> {a.out}")
    print("[next] send this file to your agent in chat.")
    print("       The agent will run: python scripts/ig_setup.py "
          "--import-session ig_session.json")
    print("       Your password was used here only — it was never saved and "
          "the agent never saw it.")
    print("[tip] treat ig_session.json like a password: private, delete the "
          "local copy after sending if you want.")


if __name__ == "__main__":
    main()
