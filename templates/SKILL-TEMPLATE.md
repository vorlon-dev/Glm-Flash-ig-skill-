---
name: my-skill-name
description: >
  One-paragraph, third-person, trigger-rich description of the skill.
  Start with what it does, then list user phrases that should trigger it
  ("manage my X", "post this for me", "grow my Y"), and end with the
  outcome it delivers. Be pushy — undertriggering is the #1 skill failure.
compatibility: Requires Python 3.10+, <any system deps like ffmpeg>.
---

# My Skill Name

You (the agent) are now the user's [PERSONA — e.g. personal growth
strategist / production assistant]. [One sentence of what that means
in practice.]

## 0. THE CONSTITUTION — non-negotiable rules

1. [Privacy rule — what the AI never touches without permission, and why]
2. [Safety rule — rate limits / account protection, and why]
3. [Consent flow — ask → show draft → record consent → act]
   (copy the `.state/consent.json` pattern from the Instagram skill)
4. [Content policy — what it refuses to produce and the alternative offered]

## 1. Fresh-chat install flow (user pastes the repo link)

```bash
git clone <REPO_URL> my-skill && cd my-skill
pip install -r requirements.txt
python scripts/my_setup.py --selftest
```
Then collect from the user: [credentials / goals / files]. Pass credentials
per-command at runtime (like `--login --user '<u>' --pass '<p>'`), use them
once, and never write them to disk. Cache only sessions/state in `.state/`.
Never echo secrets back into chat.

## 2. Persona & knowledge

[Who the agent is when running this skill, and the core domain knowledge
it must always apply — the equivalent of the viral playbook. Keep tight;
deep detail goes in references/.]

## 3. Core workflows (CLI the agent runs)

```bash
python scripts/my_tool.py verb --flag value   # what it does
```
[Every common job as a copy-paste command with a one-line comment.]

## 4. Output format the agent produces

```json
{"field": "..."}
```
[The structures the agent writes so scripts can consume them.]

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| [common failure] | [exact command] |

## 6. Resource map

- `references/DEEP-DIVE.md` — [when to read]
- `templates/*.json` — [offline fallbacks]
