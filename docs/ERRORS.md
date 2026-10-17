# ERRORS — every error Mitsu can surface, what it means, the fix

| Message / symptom | Cause | Fix |
|---|---|---|
| `zen ... didn't answer — this came from …` | Zen key has no balance / plan, Mitsu gave the turn to a working brain | Add the $20 Zen balance or a Go subscription (opencode.ai/zen); the fallback note is truthful by design |
| `zen: free-tier keys only work *inside OpenCode itself*` | Zen free-tier keys are client-locked to OpenCode's own app | Use a funded key for Zen from Mitsu; free tier stays honest-error |
| `openrouter: rate-limited (free models throttle)` then `(failover → …)` | Free slugs throttle per minute | Nothing to do — next free model answered; the route line names it |
| Provider missing from the picker | Probe found it locked/keyless/dead on load | `➕ other providers (add key)` → paste a funded key; it returns after a passing probe |
| `super user locked — unlock first (/su unlock)` | `/su exec` while the unlock window expired | `/su unlock <pass-phase>` (window 1–30 min) |
| `blocked: destructive pattern (see su.log)` | Command matched the blocklist (`rm -rf /`, `mkfs`, pipe-to-shell…) | Do it yourself in a terminal — by design it is not automatable |
| `mic: (heard nothing — mic may be muted or missing)` | Wrong default sink or muted mic | `mitsu doctor` shows recorder sources; check `pavucontrol` |
| `browser voice: NO (native window)` | pywebview window has no JS speech API | Server voice (Piper) still speaks; switch voices in ⚙ → voice |
| `(no audio player found)` | No player binary for server TTS output | Install `pipewire-audio`/`paplay` (Linux) or let ffplay exist (Windows) |
| `PyInstaller WinError 5` during rebuild | Stale exe still running in wine | `wineserver -k`, wait 5 s, rebuild; `git checkout -- mitsu.spec` after |
| Empty reply from local model | Small model + long context | Mitsu auto-retries with slim context; otherwise pick a larger model |
| `voice: PIPER MISSING` in doctor | Voices never installed | `bash scripts/install.sh` (downloads Piper voices into data dir) |
| Whisper model download fails | HTTPS blocked | Set `HF_ENDPOINT=https://hf-mirror.com` or pre-place models in data dir |
| window doesn't open, terminal shows a URL | pywebview/WebView2 missing | `pip install pywebview` (Linux needs `python3-gobject`); Windows bundles ship WebView2Loader |
| `mitsu` command not found | Editable install not done | `pip install -e .` then restart shell |
| Old answers after an update | Running the pre-update process | Restart `mitsu` — the server keeps code from process start |
| `install.sh` fails on my shell (zsh/fish/…) | Old installer was bash-only | Shell-independent now: `sh scripts/install.sh` (wrapper) or `python3 scripts/install.py` — real installer is python |
| Window won't open after an upgrade (`No module named …`) | Old process / stale install with renamed modules | `pip install -e ".[tray,native,voice,dev]"` then restart `mitsu` |
| `GLib-GIO-CRITICAL … g_application_run() cannot acquire the default main context` | Two GLib loops in one process: the tray thread stole the main context before the GTK window | Fixed — window runs alone on Linux; tray only in browser-fallback mode. `git pull` and rerun |
| `no server TTS engine (Piper voice missing and no espeak)` in chat | Installer fetched the voice .onnx but the engine binary step was missing in early v2 | Fixed in `./install` — it now downloads the piper engine into `voices/piper/`. Rerun `./install` (or just `python3 scripts/install.py`); no restart needed, TTS picks it up live |
