# Mitsu v2

A JARVIS-style **autonomous desktop AI companion** that lives on your computer:
always-on offline voice, many provider brains, desktop awareness and control,
a pet, a HUD, and full super-user access — loud and logged, never silent.

```
Type `mitsu` → window opens → ears open 👂 (says so) → talk or type.
```

## Features (all from v1, rebuilt cleaner)
- **Voice, fully offline**: faster-whisper STT + Piper TTS (local), auto
  arms on boot ("Ears open 👂 — talk anytime."), opt out via 👂 / Alt+A /
  `/always` / ⚙ Settings.
- **Every provider, honestly**: OpenRouter (live free list), OpenAI, Gemini,
  Anthropic, **OpenCode Zen + Go** (Responses API), Ollama (first-class),
  keyless Pollinations, custom endpoints.
  - The picker only lists brains that **actually answer** — each is pinged
    with one tiny real request on load (`/api/providers?probe=1`); locked /
    keyless / dead ones hide behind `➕ other providers (add key)`.
  - Free models tagged `FREE`; Zen/Go free models tagged `OpenCode-app-only`.
  - Throttled free model auto-fails-over to the next free model.
  - Any dead/locked brain hands the turn to a working one:
    `_zen didn't answer — this came from ollama/gemma3:1b`.
  - Fresh installs start on `auto`: Ollama if present, else keyless cloud.
    Zero keys needed for the first answer.
- **Descriptors that see**: `what is this?` / `/what` → screenshots, asks the
  best available vision model, answers from your screen. The question is the
  approval; nothing is stored.
- **Desktop control, permissions-first**: workspaces focus, screenshots, app
  launching — with a sudo plan/consent flow (`/api/sudo/plan`). Sudo is never
  asked from chat, never stored.
- **Super user access (new in v2)**: arm once with a pass-phase
  (`/su setup <words>`), unlock per-session (`/su unlock`) → local admin-grade
  shell commands (`/api/su/exec`) with a destructive-pattern blocklist and a
  full `su.log`. Nothing runs quietly.
- **Agents, tasks, automations, skills, research, browser agent, workspace
  scaffolding, memory (short/project/long), pet window, HUD, tray.**
- **`mitsu doctor`**: paths, profile, voice stack, mic, wake word, providers —
  one honest report.

## Layers (§)
| Layer | Where | Note |
|---|---|---|
| core | `mitsu/core/` | paths, atomic store, event bus, profile |
| providers | `mitsu/providers/` | brains + probe/failover + keychain |
| brain | `mitsu/brain/` | chat orchestration, routing, memory, personality |
| voice | `mitsu/voice/` | STT/TTS servers, wake, enroll |
| desktop | `mitsu/desktop/` | seeing + control |
| security | `mitsu/security/` | super user console |
| modules | `agents skills tasks automation workspace tools permissions browser research pet setup tray server` | |
| ui | `ui/` | static HUD (same window, pywebview if available) |

## Run
```bash
pip install -e .           # core
python -m pip install -e ".[voice,native,tray,dev]"   # everything
bash scripts/install.sh    # system deps + voices + INSTALL EVERYTHING
mitsu doctor               # verify
mitsu                      # dance
```

## Disclaimers (read once, keep forever)
- **Vision/screen features**: your message asking about the screen is the
  consent. Model providers receive the captured frame only when you ask.
- **Super user**: you arm it, you unlock it, every action is logged to
  `su.log`. If you never run `/su setup`, none of it exists.
- **Keys**: stored in your OS keychain (service `mitsu`). Never in chat, never
  in files with world-read permissions.
- **Sudo/UAC**: Mitsu never types your password anywhere and never keeps it;
  the plan/consent modal is the only path for privileged actions.
- **Voice training data stays local** (whisper + Piper run on-device).

See `docs/ERRORS.md` for every error that can appear and its fix.
