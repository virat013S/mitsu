# Mitsu

Mitsu is a desktop assistant that stays out of the way until you talk to it. It
runs a small local server, opens a window (or a browser tab), and keeps a mic
open for normal speech. You can also type. Replies can be spoken aloud.

The voice stack runs on your machine. The model is your choice: a local Ollama
model by default, or a hosted provider if you add a key. Nothing requires an
account to get started.

It is closer to a desktop sidekick than a chat page: it can remember small
things, look at your screen when you ask, run tasks, and work in a project
folder. The JARVIS comparison is fair, but this is a normal app you install and
run, not a character.

## What it does

- Listens continuously after startup. There is no wake word by default. The mic
  pauses while Mitsu is speaking so it does not answer itself.
- Speaks with a local Piper voice. Speech recognition uses faster-whisper.
- Uses the Ollama model you pick. Auto mode falls back to an installed chat
  model when nothing is selected. No local model is required or bundled.
- Streams local replies token by token instead of making you wait for the whole
  answer.
- Talks to OpenAI, OpenRouter, Gemini, Anthropic, OpenCode Zen/Go, Pollinations,
  and any OpenAI-compatible endpoint. Keys live in the OS keychain.
- Can look at the screen when you ask a visual question. The request is the
  permission; frames are not kept.
- Has short-term and long-term memory, tasks, research, file tools, and a small
  project builder.
- Has a separate superuser console for commands that need it. It is locked
  until you set a pass phrase, every run is logged, and a destructive-command
  blocklist applies.

## Requirements

- Python 3.11 or newer
- A microphone and speakers for voice (typing works without them)
- Linux is the main target. Windows and macOS work from source; see below.
- Ollama is optional. Without it, Mitsu falls back to keyless Pollinations.

## Install

```bash
git clone https://github.com/virat013S/mitsu
cd mitsu
./install
mitsu
```

The installer works from any shell. It creates a user-level virtual environment,
installs the Python package, and downloads the voice models into the Mitsu data
directory. It may ask for sudo once to install system packages such as ffmpeg;
it does not run sudo silently and does not store your password.

Windows:

```bat
git clone https://github.com/virat013S/mitsu
cd mitsu
install.bat
mitsu
```

macOS:

```bash
git clone https://github.com/virat013S/mitsu
cd mitsu
./install
brew install sox ffmpeg
mitsu
```

The first launch opens a short setup screen. The voice models download once.
After that, listening and speaking work offline.

## Packaged builds

Tagged releases include portable builds made by GitHub Actions:

- Linux x64: unpack the `.tar.gz`, then run `mitsu/mitsu`.
- Windows x64: unpack the `.zip`, then run `mitsu/mitsu.exe`.
- macOS arm64: unzip `Mitsu.app`, then open it. The first launch may need
  right-click -> Open because the build is not notarized.

The packaged builds carry Python and the runtime dependencies, so they do not
need a separate Python install. They use the same `~/.local/share/mitsu` data
directory and the same first-run setup as a source install. Voice models are
still downloaded on first use, not baked into the archive.

To build one locally:

```bash
python3 -m pip install -e ".[voice,native,tray]"
python3 -m pip install "pyinstaller>=6.10,<7"
python3 packaging/build.py
```

The output lands in `dist/`. The script starts the packaged server and checks
`/api/health` and the UI before it writes the archive. The workflow is in
`.github/workflows/build.yml`.

## Local models

Mitsu uses Ollama at `http://127.0.0.1:11434` by default. If Ollama is installed
but stopped, Mitsu starts `ollama serve` as your user; it never asks for sudo or
an API key for local models.

Mitsu does not assume a model name. Open Settings, then Model, and pick any
model that is already installed. Auto mode uses the first installed chat model
when you have not picked one. The model list only shows what is on disk.

If you have no models yet, pull one you want:

```bash
ollama pull <model>
```

The selected model is loaded when the server starts and kept warm for 30
minutes. Pulling a model from the app's model library is optional.

Useful environment variables:

```bash
OLLAMA_HOST=http://127.0.0.1:11434
MITSU_OLLAMA_MODEL=<installed-model>  # optional auto override
MITSU_OLLAMA_NUM_CTX=8192          # context window
MITSU_OLLAMA_NUM_PREDICT=512       # reply token cap
MITSU_OLLAMA_KEEP_ALIVE=30m
MITSU_OLLAMA_THINK=1               # allow thinking on models that support it
MITSU_OLLAMA_WARM=0                # skip startup warm-up
```

## Hosted providers

Open Settings, choose a provider, and paste a key. Mitsu probes the provider
with a small request before adding it to the picker. A provider that cannot
answer is hidden instead of failing every turn.

Auto mode stays local when Ollama is available. Picking a provider explicitly
pins it. Switching back to auto is always one click.

## Commands

```bash
mitsu                 # open the app
mitsu serve           # browser UI only
mitsu doctor          # paths, voice, mic, providers
mitsu say "hello"     # speak through the server voice
mitsu listen          # one mic turn in the terminal
mitsu chat            # one terminal chat turn
mitsu autostart       # install a login entry
mitsu su status       # superuser state
```

Inside the app, `/` opens the command list. `Enter` sends, `Shift+Enter` adds a
new line, and `Esc` stops speech or closes a panel.

## Files and privacy

- Profile, memory, logs, and downloaded voices live in `~/.local/share/mitsu`.
  Set `MITSU_DATA_DIR` to move them.
- API keys go to the OS keychain. The fallback file is readable only by your
  user.
- Screen captures happen only for an explicit visual question and are not saved.
- Superuser commands require an unlocked session and are written to `su.log`.
  There is no silent sudo path.
- The server binds to `127.0.0.1` by default.

## Development

```bash
python3 -m pytest -q
python3 -m mitsu --no-tray serve
```

The UI is plain HTML/CSS/JS in `ui/`. The backend is FastAPI in
`mitsu/server/api.py`. Providers are behind `mitsu/providers/base.py`; the local
Ollama path is in `mitsu/providers/builtin.py` and
`mitsu/providers/registry.py`.

Known errors and their fixes are in [docs/ERRORS.md](docs/ERRORS.md).

## License

MIT. See [LICENSE](LICENSE).
