# Errors and fixes

This is the list I keep while building Mitsu. It covers messages the app can
show, what causes them, and what to do. If a new error shows up, it gets added
here with the fix.

## Voice and microphone

| Symptom | Cause | Fix |
|---|---|---|
| `mic: (heard nothing - mic may be muted or missing)` | The selected input is muted, disconnected, or is a silent virtual device | Run `mitsu doctor`, check the input in `pavucontrol`, then try Mic again |
| MIC DOCTOR shows `peak<400` on every source | The input is muted or no live mic is connected | Unmute the input, plug in a mic, and run MIC DOCTOR again. No restart is needed |
| MIC DOCTOR shows `peak=32768` but Whisper hears nothing | High hardware gain is clipping the input; a large peak is not speech | Lower Capture and Mic Boost in `alsamixer` or `pavucontrol`. Mitsu also detects clipping and lowers capture gain automatically |
| Mic works, then is deaf after a reboot | ALSA restores a high capture gain and the input saturates on its own noise floor | Mitsu detects this and lowers only the capture gain at startup. Set `MITSU_MIC_AUTOFIX=0` to opt out |
| Mic works, then stays deaf after a reboot | The default Pulse source is a Bluetooth headset in A2DP mode and carries no input | Mitsu probes inputs and picks one with signal. Override with `MITSU_MIC_SOURCE=<source>` |
| `browser voice: NO (native window)` | The native webview has no browser speech API | Server voice (Piper) still works. Pick a voice in Settings |
| `no server TTS engine (Piper voice missing and no espeak)` | The Piper engine was not downloaded, only the voice file | Rerun `./install`, or `python3 scripts/install.py`. TTS picks the engine up without a restart |
| `voice: PIPER MISSING` in doctor | Voice files are missing | Rerun the installer; it downloads Piper and the safe voices into the data directory |
| Piper exits with `rc=-6` or `Phonemes must be one codepoint` | The bundled 2023 Piper build cannot read newer voice models | Use Lessac, LJSpeech, Arctic, Kristin, or Dante. The incompatible voices were removed from the catalog |
| `no mic recorder (...)` on macOS | macOS has no `parecord` or `arecord` | `brew install sox ffmpeg`; Mitsu falls back to `sox rec`, then `ffmpeg` |
| TTS engine missing on macOS | There is no prebuilt Piper binary for Darwin | The installer installs `piper-tts` through pip and writes a small `piper` shim |
| Mitsu answers its own greeting or reply | The always-on mic hears the speakers | Capture is cancelled when TTS starts and re-arms 900 ms after speech ends. Transcripts that overlap the last reply are discarded |
| Mitsu answers a random phrase like "I know what I'm going to do" | A noise spike was treated as speech and Whisper hallucinated on silence | The VAD now requires 0.5 s of sustained speech, records the full 30 s window, and drops known hallucinations |
| Whisper model download fails | HTTPS to Hugging Face is blocked | Set `HF_ENDPOINT=https://hf-mirror.com`, or place the model in the data directory manually |

## Local models and Ollama

| Symptom | Cause | Fix |
|---|---|---|
| Ollama is installed, but the picker asks for an API key | Ollama was stopped, and the old default was cached with an uninstalled model | Local models never open the key dialog. The picker offers "start local Ollama", which runs `ollama serve` as your user. The default re-resolves every 15 s |
| Ollama is selected and every reply says `model not found` | Ollama is running but has no models | Pull any chat model you want (`ollama pull <model>`), then pick it in Settings. Auto stays on keyless cloud until a model is installed |
| The model picker lists models that are not downloaded | The old picker merged a catalog with the live Ollama list | The Ollama picker now shows only installed models. Use the model library to pull new ones |
| Setup asks for one exact model even though other models are installed | Setup checked for a hardcoded tag instead of checking what is on disk | Setup now marks any installed chat model as present and leaves the choice to you |
| Auto switches models for code or research | The old deep route changed models when it saw code words | Auto now uses the installed model you selected, or the first installed chat model. It does not swap per prompt |
| Qwen returns nothing, or spends the whole reply budget thinking | Qwen3 can put its answer after a hidden reasoning block | If you pick Qwen manually, thinking is disabled by default and the reply budget is bounded. Set `MITSU_OLLAMA_THINK=1` to allow it |
| The first local reply takes 5-20 seconds | The model is cold and has to load from disk | Mitsu warms the fast model at server startup and keeps it loaded for 30 minutes. `MITSU_OLLAMA_WARM=0` disables this |
| Local replies appear all at once after a long pause | The old chat path waited for the full completion | Local replies now stream token by token over the WebSocket |
| `auto` answers with `ollama/openai-fast` and a 404 | Auto changed the provider but kept a model name from another provider | Auto pairs the resolved provider with its own installed model. An explicitly chosen model is still honored |
| Always-listening answers come from Pollinations although Ollama is installed | The profile was pinned to the keyless fallback | The default is `auto (local first)` and is saved as `provider_mode=auto`. An explicit pick is saved as manual |
| A local model returns an empty reply | Small model with a long context | Mitsu retries with a shorter context; pick a larger model if it keeps happening |
| Research, build, or screen vision fails with `provider auto` | Those paths passed `auto/auto` straight to a provider | They now resolve auto to a real installed provider and model before the request |

## Providers and keys

| Symptom | Cause | Fix |
|---|---|---|
| A provider is missing from the picker | The startup probe found it locked, keyless, or dead | Choose "other providers (add key)", paste a working key, and it returns after the probe passes |
| `zen ... didn't answer - this came from ...` | The Zen key has no balance or plan; Mitsu handed the turn to a working provider | Add balance or a Go subscription at opencode.ai/zen. The fallback note names the provider that answered |
| `zen: free-tier keys only work inside OpenCode itself` | Zen free keys are locked to OpenCode's own client | Use a funded Zen key, or use another provider |
| `openrouter: rate-limited (free models throttle)` | Free OpenRouter models have per-minute limits | Mitsu fails over to the next free model; the route line names it |
| A hosted provider works in another app but not here | The key is scoped to a different API or the account has no credit | Check the provider dashboard, then paste a key with access to the chat API |
| `(no audio player found)` | No `paplay`, `ffplay`, or similar player is available for server TTS | Install `pipewire-audio` or `ffmpeg` |

## Desktop, security, and tasks

| Symptom | Cause | Fix |
|---|---|---|
| `super user locked - unlock first (/su unlock)` | The unlock window expired | `/su unlock <pass phrase>`. The window is 1-30 minutes |
| `blocked: destructive pattern (see su.log)` | The command matched the blocklist (`rm -rf /`, `mkfs`, pipe-to-shell, and similar) | Run it yourself in a terminal. Mitsu will not automate it |
| `/api/desktop/shot` returns 500 | A permission error escaped the endpoint in an early build | It now returns 403 with the approval message. Pull the current code |
| The screen request says the model cannot read images | The current model is text-only | Pull a vision-capable model (`ollama pull <vision-model>`), or switch to a provider with image support |
| A task stays in `running` after the app restarts | The old process owned the task | Restart the task from the Activity panel. Task state is not resumed across process restarts |

## Install, updates, and packaging

| Symptom | Cause | Fix |
|---|---|---|
| `mitsu` command not found | The package was not installed into the active environment | `./install`, or `python3 -m pip install -e .`, then restart the shell |
| `install.sh` fails in zsh or fish | An old installer was bash-only | Run `./install` or `python3 scripts/install.py`. Both are shell-independent |
| Window does not open, terminal prints a URL | pywebview or WebView2 is missing | `python3 -m pip install pywebview`; on Linux you may also need `python3-gobject`. The browser UI still works |
| Window fails after an upgrade with `No module named ...` | The old process or an old editable install is still active | `python3 -m pip install -e ".[tray,native,voice,dev]"`, then restart `mitsu` |
| `GLib-GIO-CRITICAL ... g_application_run() cannot acquire the default main context` | Two GLib loops in one process; the tray thread took the main context | Fixed: the window runs alone on Linux and the tray is only used in browser-fallback mode |
| `PyInstaller WinError 5` while rebuilding Windows | A stale `mitsu.exe` is still running under Wine | `wineserver -k`, wait five seconds, rebuild, then `git checkout -- packaging/mitsu.spec` |
| Packaged app prints `invalid choice: from multiprocessing.resource_tracker...` | PyInstaller makes `sys.executable` the app, so Python's resource tracker re-enters the CLI with `-c` | Fixed in `mitsu/__main__.py`: frozen builds handle the tracker command and call `freeze_support()` |
| Linux CI fails with `Cannot uninstall pip ... no RECORD file` | The Linux runtime step exported `/usr/lib/python3/dist-packages` globally, so setup-python imported Debian's pip | Scope `PYTHONPATH` to the PyInstaller build step; `pip` then uses the setup-python environment |
| `The configuration 'macos-14-arm64-us-default' is not supported` | GitHub retired macOS 14 runners on November 2, 2026 | Build on `macos-15` (arm64) |
| Packaged macOS app opens a blank window | PyInstaller stores data under `Contents/Resources`, not beside the executable | Fixed: the UI lookup also checks `Contents/Resources/ui` |
| A packaged build asks to `pip install` a missing Python package | Frozen builds do not have pip; the dependency was not included in the build | Rebuild with the dependency installed. The source install still uses the setup screen |
| Old answers after an update | The running server keeps the code from process start | Restart `mitsu` |
| The UI still looks like the previous build | The browser cached `app.js` or `styles.css` | Assets are served with `Cache-Control: no-store` and versioned URLs. Hard-refresh one ancient tab if needed |

## Tests

If you change provider routing or voice behavior, run:

```bash
python3 -m pytest -q
```

The suite covers the local model selection, request limits, streamed reply
events, microphone selection, clipping repair, VAD, TTS pause, and the provider
fallback paths.
