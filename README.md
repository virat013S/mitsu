# MITSU

**A JARVIS alternative, better than JARVIS** — your own AI desktop assistant that actually feels like a friend. Voice chat, desktop control, browser automation, deep research, emotions, and a slick black & white theme.

> Inspired by [JARVIS-OS](https://github.com/MAL19INDUSTRIES/JARVIS-OS-V.2), built and extended by [virat013S](https://github.com/virat013S).

---

## What Even Is Mitsu?

Mitsu is a custom AI assistant that runs on YOUR machine. Not some cloud-only thing — it lives on your desktop, controls your apps, browses the web, reads your files, and actually talks back to you with personality.

**Here's what it can do:**

- **Talk to it** — real-time voice chat via Gemini Live, or text chat with local AI
- **Has emotions** — gets excited when you're excited, chills when it's late, hypes you up when you accomplish something
- **Controls your desktop** — opens apps, adjusts volume/brightness, takes screenshots, manages windows
- **Browses the web** — searches, clicks, fills forms, navigates pages, takes screenshots
- **Manages files** — create, read, write, delete, organize, find anything on your system
- **Deep research** — multi-source web research that actually digs deep
- **Makes presentations** — creates and edits PowerPoint decks
- **Handles email** — Gmail integration, never sends without your approval
- **Recognizes stuff** — identifies voices, analyzes images, reads text from screenshots, watches videos
- **Protects you** — sudo commands need your approval first, everything is logged
- **Looks fire** — pure black canvas, white energy, noir aesthetic

---

## Requirements

**That's it. It's lightweight.**

| What You Need | Details |
|---------------|---------|
| **Python** | 3.11 or newer |
| **RAM** | 2GB free (seriously, it's that light) |
| **Disk** | ~2GB for dependencies and models |
| **Internet** | Needed for setup, Gemini, and OpenRouter modes |

### What Each Mode Needs

| Mode | What It Uses | Cost |
|------|-------------|------|
| **Gemini (Cloud)** | Google's Gemini API — best voice quality | Free tier available |
| **Ollama (Local)** | Gemma 3 1B running on your hardware | Free, offline, private |
| **OpenRouter** | NVIDIA Nemotron 3 Ultra 550B — free tier | Free, needs internet |

> **Heads up:** You need a Gemini API key for setup, even if you're using Ollama or OpenRouter. Takes 30 seconds to get — [grab one here](https://aistudio.google.com/apikey). It's free.

---

## Installation

### Linux (Ubuntu/Debian/Arch/Fedora)

```bash
# Install Python if you don't have it
sudo apt install python3 python3-venv pip    # Ubuntu/Debian
sudo pacman -S python python-pip             # Arch
sudo dnf install python3 python3-pip         # Fedora

# Clone and install
git clone https://github.com/virat013S/mitsu.git
cd mitsu
chmod +x install
./install

# Run it
mitsu
```

### macOS

```bash
# Install Python if you don't have it
brew install python@3.12

# Clone and install
git clone https://github.com/virat013S/mitsu.git
cd mitsu
chmod +x install
./install

# Run it
mitsu
```

### Windows

```powershell
# Make sure Python 3.11+ is installed from python.org
# Check "Add Python to PATH" during installation

# Clone and install
git clone https://github.com/virat013S/mitsu.git
cd mitsu
install.bat

# Run it
mitsu
```

### What the Installer Does

1. Checks that Python 3.11+ is installed
2. Creates a virtual environment (`.venv/`) — keeps things clean
3. Installs all dependencies (PyQt6, edge-tts, opencv-python, etc.)
4. Sets up your config files
5. Installs the `mitsu` CLI command to `~/.local/bin/` (Linux/macOS) or your PATH (Windows)
6. Checks if Ollama is available for local mode

**Total install time:** ~2-5 minutes depending on your internet.

---

## First Time Setup

When you run `mitsu` for the first time:

```
  What should I call you? virat
  Nice to meet you, virat! Let's set things up.

  How would you like Mitsu to run?

    [1] Cloud Mode (Gemini API Key)       — best voice quality
    [2] Local Mode (Gemma 3 1B via Ollama) — free, offline, private
    [3] OpenRouter (Free Tier Models)      — free, needs internet

  Choose mode [1/2/3]:
```

Pick your mode, paste your API key (if needed), and you're good to go.

**After first setup**, Mitsu remembers your provider. Next time you just run `mitsu` and it starts right up.

---

## Provider Details

### Gemini (Cloud Mode)
- **Model:** gemini-2.5-flash-native-audio
- **Voice:** Gemini Live — real-time voice conversation, the best quality
- **Key:** Get free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- **Pros:** Best voice quality, real-time conversation, smart responses
- **Cons:** Needs internet, uses Google API

### Ollama (Local Mode)
- **Model:** Gemma 3 1B
- **Voice:** Edge-TTS fallback (free Microsoft voices)
- **Setup:** Install [Ollama](https://ollama.com), then `ollama pull gemma3:1b`
- **Pros:** Free, offline, private, no data leaves your machine
- **Cons:** Slower on older hardware, simpler voice

### OpenRouter (Free Tier)
- **Model:** NVIDIA Nemotron 3 Ultra 550B (550 billion parameters!)
- **Voice:** Edge-TTS fallback
- **Key:** Get free at [openrouter.ai/keys](https://openrouter.ai/keys)
- **Pros:** Huge model for free, no hardware requirements
- **Cons:** Needs internet, API rate limits

---

## Emotions & Expressions

Mitsu isn't a robot — he has moods. They change how he talks and how his voice sounds:

| Mood | What Happens | When |
|------|-------------|------|
| **Chill** | Relaxed tone, normal voice | Default state |
| **Excited** | Faster voice, higher pitch, hype energy | You say "!", "let's go", "omg" |
| **Focused** | Precise, task-mode, no fluff | Work tasks, coding, commands |
| **Playful** | Teasing, funny, slightly faster | Jokes, memes, fun conversations |
| **Worried** | Cautious, slower, lower pitch | Errors, problems, stress |
| **Proud** | Warm, celebrating, normal speed | You finish something, achievements |
| **Sleepy** | Slow, drowsy, low pitch | Late night (11pm-5am) |

The system detects your tone from what you type and adjusts automatically. Type "LET'S GO" and Mitsu matches your energy. Mention something's broken and he gets focused and helpful.

---

## Keyboard Shortcuts

| Shortcut | What It Does |
|----------|-------------|
| `Ctrl+Space` | Push-to-talk (hold to speak) |
| `Escape` | Cancel current action |
| `Ctrl+Q` | Quit Mitsu |

---

## What Can You Ask Mitsu?

Literally anything, but here are some examples:

**Daily Stuff:**
- "Open Spotify"
- "What's the weather in Tokyo?"
- "Set a reminder for tomorrow at 3pm"
- "What time is it?"

**Desktop Control:**
- "Take a screenshot"
- "Turn up the volume"
- "Open Firefox"
- "Show me what's on my desktop"

**Files & Code:**
- "What files are on my desktop?"
- "Create a new Python file called bot.py"
- "Read the file README.md"
- "Run this code and tell me the output"

**Research & Info:**
- "Research the latest AI trends"
- "What's happening in the news?"
- "Find me information about quantum computing"

**Creative:**
- "Create a presentation about climate change"
- "Make me a PowerPoint about space exploration"

**Communication:**
- "Send a message to John on WhatsApp"
- "Check my emails"
- "Compose an email to the team"

**Recognition:**
- "Who is talking?" (with audio)
- "What's in this image?" (with image)
- "Watch this video and tell me what happens" (with video)

---

## Project Structure

```
mitsu/
├── main.py              # Entry point, live engine, startup menu
├── ui.py                # PyQt6 interface (9000+ lines of goodness)
├── install              # One-command installer (Linux/macOS)
├── install.bat          # Windows installer
├── .env.example         # Configuration template
├── core/
│   ├── emotions.py      # Mood detection & voice expression
│   ├── providers.py     # Multi-provider backend (Gemini/Ollama/OpenRouter)
│   ├── permissions.py   # Sudo permission system
│   ├── recognition.py   # Voice/Image/Video analysis
│   ├── skills.py        # Built-in skills (calculator, web, code, etc.)
│   ├── prompt.txt       # Mitsu's personality definition
│   └── llm.py           # LLM abstraction layer
├── actions/             # 27 action modules
│   ├── browser_control.py    # Web browsing
│   ├── computer_control.py   # Desktop control
│   ├── file_controller.py    # File management
│   ├── deep_research.py      # Research engine
│   ├── presentation_maker.py # PowerPoint creation
│   ├── email_control.py      # Gmail integration
│   └── ...                   # And more
├── agent/               # Task planner & executor
├── api/                 # FastAPI web backend
├── web/                 # Next.js web client
├── config/              # Configuration files
├── memory/              # Long-term memory system
├── scripts/             # Setup & CLI scripts
├── tests/               # Test suite
└── assets/              # Fonts, images
```

---

## The Permission System

Mitsu asks before doing dangerous stuff. When a command needs `sudo`:

1. **You get a popup** — shows the exact command
2. **You approve or deny** — one click
3. **It gets logged** — everything is recorded for audit

You're always in control. Mitsu never runs `sudo` without your permission.

---

## Troubleshooting

### "Gemini API key error" on startup
**This is normal.** The setup validates your Gemini key even for Ollama/OpenRouter modes.
- Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- Paste it when asked during setup

### Voice not working
```bash
# Install edge-tts (free TTS)
.venv/bin/pip install edge-tts

# Install mpv (audio player)
sudo pacman -S mpv          # Arch
sudo apt install mpv        # Ubuntu
brew install mpv             # macOS

# Check edge-tts is available
which edge-tts
```

### Ollama not connecting
```bash
# Make sure Ollama is running
ollama serve

# Pull the model
ollama pull gemma3:1b

# Check everything is working
ollama list
```

### "mitsu" command not found
```bash
# Add ~/.local/bin to your PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Or just run directly
cd ~/mitsu && .venv/bin/python main.py
```

### UI is lagging
- Close other heavy apps
- Try Ollama mode (lighter on resources)
- Check RAM: `free -h`
- Check CPU: `htop`

### Install fails on pip dependencies
```bash
# Make sure you're using the venv
cd ~/mitsu
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Tips & Tricks

- **Clap to start:** On first boot, clap twice to activate voice mode (you can change this)
- **Use push-to-talk:** Hold `Ctrl+Space` to talk instead of voice detection
- **Switch providers:** Delete `~/.mitsu/provider.json` and restart to reconfigure
- **Custom voice:** Edit the voice name in settings — try different voices like "kore" or "charon"
- **Late night mode:** Mitsu gets sleepy and speaks softer after 11pm

---

## Credits

- **Inspired by:** [JARVIS-OS](https://github.com/MAL19INDUSTRIES/JARVIS-OS-V.2) — the OG JARVIS project
- **Built by:** [virat013S](https://github.com/virat013S) — a 13-year-old who wanted a better AI assistant
- **License:** MIT — do whatever you want with it

---

## Contributing

Want to make Mitsu better? Here's how:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/cool-stuff`)
3. Commit your changes (`git commit -m 'Add cool stuff'`)
4. Push to your branch (`git push origin feature/cool-stuff`)
5. Open a Pull Request

**Ideas for contributions:**
- New action modules
- Better emotion detection
- More voice options
- Better themes
- Bug fixes

---

## Support

- **Issues:** [Open an issue](https://github.com/virat013S/mitsu/issues) on GitHub
- **Star the repo** if you like it — it helps a lot!

---

## One Last Thing

Mitsu is built by a 13-year-old who just wanted something cool. If you like it, star the repo. If you don't, open an issue and tell me what to fix.

**Now go talk to your AI.** 🤖
