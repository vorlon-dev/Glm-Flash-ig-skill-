# Make Your Own Skill — build a z.ai GLM skill like this one

This repo doubles as a **template** for anyone who wants to create an
agent-operated skill (Instagram manager, YouTube manager, Twitter/X manager,
WhatsApp assistant... anything). Follow these steps.

## What is a "skill"?

A skill is a folder an AI agent (GLM / z.ai chat) can load to become instantly
good at one job. The agent reads `SKILL.md`, then uses the bundled scripts and
references as its tools. Users don't read code — they paste your repo link in
a fresh chat and say "install this".

## Anatomy (copy this shape)

```
my-skill/
├── SKILL.md              ← REQUIRED. frontmatter + agent operating manual
├── README.md             ← human-facing overview (English)
├── HINGLISH-README.md    ← optional regional readme
├── INSTALL.md            ← the agent's install-from-link steps
├── requirements.txt
├── .env.example          ← every secret the user must fill
├── .gitignore            ← MUST ignore .env, sessions, databases
├── LICENSE
├── scripts/              ← thin CLI entrypoints (argparse + one import each)
├── igskill/              (or yourpackage/) ← the real logic
├── references/           ← deep docs the agent reads only when needed
└── templates/            ← offline JSON/templates so zero-config still works
```

## Step 1 — SKILL.md frontmatter

```yaml
---
name: my-skill-name
description: >
  Pushy, third-person, trigger-rich description. List the phrases users will
  type ("manage my X", "post this", "grow my Y") and say when to use it.
compatibility: python version, system deps (ffmpeg etc.)
---
```
The description is the ONLY thing always in the agent's context — make it
specific enough that the right conversations trigger it.

## Step 2 — the body (agent operating manual)

Cover, in this order:
1. **Constitution** — non-negotiable privacy/safety rules with reasons
2. **Install flow** — exact commands for a fresh-chat install from your link
3. **Persona** — who the agent becomes when running the skill
4. **Workflows** — copy-paste CLI invocations for every common job
5. **Content/output format** — the JSON/structures the agent must produce
6. **Troubleshooting table**
7. **Resource map** — what's in references/ and when to read it

Keep under ~500 lines. Push depth into `references/`.

## Step 3 — scripts pattern

Thin argparse wrappers that import the package and call one function:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mypackage.things import do_thing

p = argparse.ArgumentParser()
...
```
Rules that keep skills safe: hard caps in config (not CLIs), randomized
delays between external actions, consent checks for anything private,
lazy imports for heavy dependencies.

## Step 4 — safety checklist before you publish

- [ ] `.gitignore` covers `.env`, sessions, consent, database files
- [ ] Secrets never appear in code, logs, or examples
- [ ] Privacy actions require recorded consent (`privacy.py` pattern)
- [ ] Rate limits + delays are enforced centrally
- [ ] Works with zero API keys (offline/agent mode) — API mode optional
- [ ] `--selftest` command exists so agents can verify the install

## Step 5 — publish & let others install

```bash
git init && git add . && git commit -m "v1.0"
git remote add origin https://github.com/<you>/<skill-repo>.git
git branch -M main && git push -u origin main
```

Now anyone opens a fresh chat with their AI agent, pastes:
> https://github.com/<you>/<skill-repo> — install this and set it up

and the agent follows your INSTALL.md/SKILL.md automatically.

## Examples of what you can build with this template

- **YouTube manager** — upload, thumbnails, chapters, SEO titles
- **Twitter/X manager** — thread writer, scheduler, reply drafts
- **WhatsApp business bot** — catalog updates, auto-replies with consent
- **LinkedIn ghostwriter** — posts + engagement analytics
- **Pinterest scheduler** — pins from a blog RSS

Same skeleton, different `ig_client.py` + playbook.
