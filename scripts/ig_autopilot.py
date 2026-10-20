#!/usr/bin/env python3
"""ig_autopilot — one prompt -> a week of viral content.

  # 1. make the plan (agent can pass its own ideas JSON)
  python scripts/ig_autopilot.py plan --niche "street food" --count 7
  python scripts/ig_autopilot.py plan --niche fitness --ideas ideas.json
  python scripts/ig_autopilot.py plan --niche fashion --use-api --media-dir ./raw

  # 2. USER REVIEWS THE PLAN (Constitution rule) then:
  python scripts/ig_autopilot.py approve     # records user approval
  python scripts/ig_autopilot.py run         # edit + queue everything

  # 3. post what's due (cron this for full autopilot)
  python scripts/ig_autopilot.py due
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from igskill.config import load_config  # noqa: E402


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="weekly viral autopilot")
    p.add_argument("cmd", choices=["plan", "approve", "run", "due", "status"])
    p.add_argument("--niche", default=None)
    p.add_argument("--count", type=int, default=7)
    p.add_argument("--ideas", help="agent-written ideas JSON file")
    p.add_argument("--use-api", action="store_true", help="generate via Z.ai GLM")
    p.add_argument("--media-dir", help="folder with your raw photos/videos")
    a = p.parse_args()

    cfg = load_config()

    if a.cmd == "plan":
        from igskill.autopilot import build_plan
        niche = a.niche or cfg.niche
        if niche == "general" and not a.niche:
            raise SystemExit("give a niche: --niche 'street food' (or set NICHE in .env)")
        build_plan(cfg, niche, a.count, ideas_file=a.ideas,
                   use_api=a.use_api, media_dir=a.media_dir)
    elif a.cmd == "approve":
        plan_path = cfg.workdir / "autopilot_plan.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["status"] = "approved"
        plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False),
                             encoding="utf-8")
        print("[approved] plan unlocked — `run` will now edit + schedule")
    elif a.cmd == "run":
        from igskill.autopilot import execute_plan
        execute_plan(cfg)
    elif a.cmd == "due":
        from igskill.scheduler import run_due
        run_due(cfg)
    elif a.cmd == "status":
        plan_path = cfg.workdir / "autopilot_plan.json"
        if plan_path.exists():
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            print(f"plan: {plan['created']} niche={plan['niche']} "
                  f"items={plan['count']} status={plan['status']}")
        else:
            print("no plan yet — run `plan` first")


if __name__ == "__main__":
    main()
