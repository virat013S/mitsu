# MITSU

**A JARVIS alternative, better than JARVIS** — a custom AI desktop assistant with voice interaction, local AI support, full system control, emotions, and a sleek black & white aesthetic.

> Inspired by [JARVIS-OS](https://github.com/MAL19INDUSTRIES/JARVIS-OS-V.2), built and extended by [virat013S](https://github.com/virat013S).

---

## What is Mitsu?

Mitsu is a locally-run AI assistant that can:

- **Voice Chat** — real-time voice with Gemini Live, or text-based with local Gemma 3 1B
- **Emotions & Expressions** — moods that change tone and voice (excited, chill, focused, playful, worried, proud, sleepy)
- **Desktop Control** — open apps, volume, brightness, screenshots, window management
- **Browser Automation** — search, click, fill forms, navigate, take screenshots
- **Messaging** — iMessage, WhatsApp, Instagram, Discord integration
- **File Management** — create, read, write, delete, organize, find files
- **Deep Research** — multi-source web research with background or visible mode
- **Presentations** — create and edit PowerPoint decks
- **Email** — Gmail integration with approval-gated sending
- **Voice/Image/Video Recognition** — identify speakers, analyze images, OCR, video analysis
- **Permission System** — sudo commands require user approval
- **Black & White Noir Theme** — pure black canvas, white energy

---

## Requirements

| Requirement | Details |
|-------------|---------|
| **Python** | 3.11 or higher |
| **OS** | Linux, macOS, or Windows (WSL recommended) |
| **RAM** | 4GB minimum, 8GB+ recommended |
| **Disk** | ~2GB for dependencies + models |
| **Internet** | Required for setup, Gemini, and OpenRouter modes |

### Provider-Specific Requirements

| Mode | Extra Requirements |
|------|-------------------|
| **Gemini (Cloud)** | Free API key from [Google AI Studio](https://aistudio.google.com/apikey) |
| **Ollama (Local)** | [Ollama](https://ollama.com) installed + `gemma3:1b` model pulled |
| **OpenRouter** | Free API key from [OpenRouter](https://openrouter.ai/keys) |

> **IMPORTANT:** A Gemini API key is **always required** during setup, even if you plan to use Ollama or OpenRouter mode. The UI validates it on every startup. You can get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — it takes 30 seconds.

---

## Quick Start

### Linux / macOS / WSL

```bash
git clone https://github.com/virat013S/mitsu.git
cd mitsu
./install
mitsu
```

### Windows

```
git clone https://github.com/virat013S/mitsu.git
cd mitsu
install.bat
mitsu
```

### What the installer does:
1. Checks Python 3.11+ is installed
2. Creates a virtual environment (`.venv/`)
3. Installs all dependencies (PyQt6, edge-tts, opencv, etc.)
4. Sets up configuration files
5. Installs the `mitsu` CLI command to `~/.local/bin/`

---

## Configuration

On first launch, Mitsu will ask you:
1. **Your name** — what Mitsu calls you
2. **Provider mode** — Cloud (Gemini) / Local (Ollama) / OpenRouter
3. **API keys** — based on your provider selection

### Manual Configuration (`.env`)

```env
# Provider: gemini | ollama | openrouter
MITSU_PROVIDER="ollama"

# Gemini API key (always required for setup)
GEMINI_API_KEY="your-gemini-key-here"

# OpenRouter (free tier)
OPENROUTER_API_KEY="your-openrouter-key-here"

# OpenRouter model (default: nvidia/nemotron-3-ultra-550b-a55b:free)
OPENROUTER_MODEL="nvidia/nemotron-3-ultra-550b-a55b:free"
```

### Provider Details

| Mode | Model | Cost | Voice |
|------|-------|------|-------|
| **Gemini** | gemini-2.5-flash | Free tier available | Gemini Live (best quality) |
| **Ollama** | gemma3:1b | Free, offline | edge-tts fallback |
| **OpenRouter** | nvidia/nemotron-3-ultra-550b-a55b:free | Free | edge-tts fallback |

---

## Emotions & Expressions

Mitsu has moods that affect how he speaks and responds:

| Mood | Voice Change | When It Triggers |
|------|-------------|------------------|
| **Chill** | Normal speed | Default state |
| **Excited** | Faster, higher pitch | User is excited, "!", "let's go" |
| **Focused** | Normal speed | Task-oriented messages |
| **Playful** | Slightly faster | Jokes, memes, fun talk |
| **Worried** | Slower, lower | Errors, problems, stress |
| **Proud** | Warm tone | Achievements, completions |
| **Sleepy** | Slow, low | Late night (11pm-5am) |

The emotions system detects your tone and adjusts Mitsu's text personality and voice parameters (pitch/speed) automatically.

---

## Features

### Voice Interaction
- Real-time voice with Gemini Live
- **2-clap startup gate** — clap twice to activate (configurable)
- Configurable voice names: puck, charon, kore, fenrir, aoede, leda, orus, schedar, zubenelgenubi
- Edge-TTS fallback for Ollama/OpenRouter modes

### Desktop Control
- Open/close applications
- Volume, brightness, WiFi control
- Window management, screenshots
- Keyboard shortcuts, typing automation

### Browser Automation
- Open websites, search the web
- Click elements, fill forms
- Screenshot pages, navigate
- Multiple browser support (Chrome, Firefox, Edge, etc.)

### File Management
- Create, read, write, delete files
- Organize desktop, find files by name/extension
- Disk usage statistics

### Deep Research
- Multi-source web research
- Background or visible browser mode
- Save reports to files or read aloud

### Presentations
- Create PowerPoint decks from scratch
- Edit, redesign, extend existing decks
- PDF export support

### Email (Gmail)
- Read, search, compose emails
- Approval-gated sending (never sends without your OK)
- OAuth2 authentication

### Recognition
- **Voice:** Identify who is talking, save voice profiles
- **Image:** Analyze images, detect faces, OCR text extraction
- **Video:** Watch videos, describe scenes, extract key frames

### Permission System
- Sudo commands require explicit user approval
- All system actions are logged
- UI approval dialogs for sensitive operations

---

## Mitsu Personality

Mitsu isn't a cold machine — he's like a sharp best friend who knows everything:

- **Friendly & witty** — makes occasional clever jokes
- **Calls you by name** — remembers your nickname
- **Adapts to context** — casual for chat, professional for work
- **Emotionally aware** — matches your energy, calms you down, hypes you up
- **Protective** — warns about issues, protects your privacy
- **Proactive** — suggests improvements, celebrates wins

---

## Project Structure

```
mitsu/
├── main.py              # Entry point, live engine, startup menu
├── ui.py                # PyQt6 interface (9000+ lines)
├── install              # One-command installer (Linux/macOS)
├── install.bat          # Windows installer
├── .env.example         # Configuration template
├── core/
│   ├── emotions.py      # Mood detection & voice expression
│   ├── providers.py     # Multi-provider backend (Gemini/Ollama/OpenRouter)
│   ├── permissions.py   # Sudo permission system
│   ├── recognition.py   # Voice/Image/Video analysis
│   ├── skills.py        # Built-in skills (calculator, web, code, etc.)
│   ├── prompt.txt       # Mitsu personality definition
│   └── llm.py           # LLM abstraction layer
├── actions/             # 27 action modules (browser, files, email, etc.)
├── agent/               # Task planner & executor
├── api/                 # FastAPI web backend
├── web/                 # Next.js web client
├── config/              # Configuration files
├── memory/              # Long-term memory
├── scripts/             # Setup & CLI scripts
└── assets/              # Fonts, images
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Space` | Push-to-talk |
| `Escape` | Cancel current action |
| `Ctrl+Q` | Quit Mitsu |

---

## Example Commands

- "Open Spotify"
- "What's the weather in Tokyo?"
- "Send a message to John on WhatsApp"
- "Research the latest AI trends"
- "Create a presentation about climate change"
- "What files are on my desktop?"
- "Set a reminder for tomorrow at 3pm"
- "Take a screenshot"
- "Read this image" (with image attached)
- "Who is talking?" (with audio attached)

---

## Troubleshooting

### "Gemini API key error" on startup
- A Gemini API key is **always required** during setup validation
- Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- The key is validated on every startup, even for Ollama/OpenRouter modes

### Voice not working
- Install edge-tts: `pip install edge-tts`
- Install mpv: `sudo pacman -S mpv` (Arch) / `brew install mpv` (macOS)
- Check edge-tts is in PATH: `which edge-tts`

### Ollama not connecting
- Make sure Ollama is running: `ollama serve`
- Pull the model: `ollama pull gemma3:1b`
- Check status: `ollama list`

### UI lagging
- Close other heavy applications
- Try Ollama mode (lighter on resources)
- Check RAM usage: `free -h`

---

## Credits

- **Inspired by:** [JARVIS-OS](https://github.com/MAL19INDUSTRIES/JARVIS-OS-V.2)
- **Built by:** [virat013S](https://github.com/virat013S)
- **License:** MIT

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Support

- Open an [issue](https://github.com/virat013S/mitsu/issues) on GitHub
- Star the repo if you like it!
