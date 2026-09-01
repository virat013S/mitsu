# Mitsu

**A JARVIS alternative, better than JARVIS** — a custom AI desktop assistant with voice interaction, local AI support, full system control, and a sleek black & white aesthetic.

> Inspired by [JARVIS-OS](https://github.com/MAL19INDUSTRIES/JARVIS-OS-V.2), built and extended by [virat013S](https://github.com/virat013S).

---

## What is Mitsu?

Mitsu is a locally-run AI assistant that can:

- **Voice Chat** — real-time voice with Gemini Live, or text-based with local Gemma 3 1B
- **Desktop Control** — open apps, volume, brightness, screenshots, window management
- **Browser Automation** — search, click, fill forms, navigate, take screenshots
- **Messaging** — iMessage, WhatsApp, Instagram, Discord integration
- **File Management** — create, read, write, delete, organize, find files
- **Deep Research** — multi-source web research with background or visible mode
- **Presentations** — create and edit PowerPoint decks
- **Email** — Gmail integration with approval-gated sending
- **Permission System** — sudo commands require user approval
- **Black & White Noir Theme** — pure black canvas, white energy

### Multi-Provider AI

| Mode | Description | Cost |
|------|-------------|------|
| **Local (Gemma 3 1B)** | Runs offline via Ollama, no API key needed | Free |
| **Cloud (Gemini)** | Best voice quality, requires Google API key | Free tier available |
| **OpenRouter** | Free tier models, needs internet | Free |

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

The installer will:
1. Check Python 3.11+ is installed
2. Create a virtual environment
3. Install all dependencies
4. Set up configuration
5. Check if Ollama is available (for local mode)
6. Install the `mitsu` CLI command

---

## Configuration

On first launch, Mitsu will ask you:
1. **What to call you** — your nickname
2. **Which mode to use** — Cloud / Local / OpenRouter

You can also configure manually by editing `.env`:

```env
# Provider: gemini | ollama | openrouter
MITSU_PROVIDER="ollama"

# Gemini (for cloud mode)
GEMINI_API_KEY="your-key-here"

# Ollama (for local mode)
OLLAMA_MODEL="gemma3:1b"

# OpenRouter (for free tier)
OPENROUTER_API_KEY="your-key-here"
```

---

## Local Mode Setup (Gemma 3 1B)

Local mode runs entirely on your hardware — no API key, no internet needed.

### Requirements
- **RAM:** 2GB+ free
- **CPU:** Any modern processor
- **GPU:** Not required (runs on CPU)

### Setup

1. Install Ollama:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. Pull the model:
   ```bash
   ollama pull gemma3:1b
   ```

3. Run Mitsu:
   ```bash
   mitsu
   ```
   Select "Local Mode" when prompted.

---

## Cloud Mode Setup (Gemini)

1. Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey)
2. Run `mitsu` and select "Cloud Mode"
3. Paste your API key when prompted

---

## OpenRouter Setup

1. Get a free API key at [OpenRouter](https://openrouter.ai/keys)
2. Run `mitsu` and select "OpenRouter"
3. Paste your API key when prompted

---

## Features

### Voice Interaction
- Real-time voice with Gemini Live
- **2-clap startup gate** — clap twice to activate (configurable)
- Configurable voice names: puck, charon, kore, fenrir, aoede, leda, orus, schedar, zubenelgenubi

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

### Permission System
- Sudo commands require explicit user approval
- All system actions are logged
- UI approval dialogs for sensitive operations

---

## Mitsu Personality

Mitsu isn't a cold machine — she's more like a sharp best friend who knows everything:

- **Friendly & witty** — makes occasional clever jokes
- **Calls you by name** — remembers your nickname
- **Adapts to context** — casual for chat, professional for work
- **Protective** — warns about issues, protects your privacy
- **Proactive** — suggests improvements, celebrates wins

On startup, Mitsu greets you:
> "Welcome back, Virat! What are we getting into today?"

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
│   ├── mitsu_client.py  # Client protocol
│   ├── providers.py     # Multi-provider backend (Gemini/Ollama/OpenRouter)
│   ├── permissions.py   # Sudo permission system
│   └── prompt.txt       # Mitsu personality definition
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

## Commands

Mitsu responds to natural language. Examples:

- "Open Spotify"
- "What's the weather in Tokyo?"
- "Send a message to John on WhatsApp"
- "Research the latest AI trends"
- "Create a presentation about climate change"
- "What files are on my desktop?"
- "Set a reminder for tomorrow at 3pm"
- "Take a screenshot"

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
