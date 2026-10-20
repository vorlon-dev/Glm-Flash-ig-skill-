#!/usr/bin/env python3
"""ig_server — the mission-control dashboard.

  python scripts/ig_server.py            # http://127.0.0.1:8790
  HOST=0.0.0.0 PORT=9000 python scripts/ig_server.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    import argparse

    import uvicorn

    p = argparse.ArgumentParser(description="IG Viral Manager dashboard server")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    a = p.parse_args()

    from igskill.config import load_config
    cfg = load_config()
    host = a.host or cfg.host
    port = a.port or cfg.port
    print(f"⚡ IG Viral Manager dashboard -> http://{host}:{port}")
    print("   API docs  -> /docs   (queue, autopilot, analytics, consent)")
    uvicorn.run("igskill.server:app", host=host, port=port,
                reload=False, log_level="info")


if __name__ == "__main__":
    main()
