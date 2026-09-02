# MITSU

**Your own AI assistant that actually feels like a friend.** Voice chat, desktop control, browser automation, deep research, emotions, auto-theming, and a slick noir aesthetic.

> Built by [virat013S](https://github.com/virat013S).

---

## What Even Is Mitsu?

Mitsu is a custom AI assistant that runs on YOUR machine. Not some cloud-only thing — it lives on your desktop, controls your apps, browses the web, reads your files, and actually talks back to you with personality.

**Here's what it can do:**

- **Talk to it** — real-time voice chat via Gemini Live, or text chat with local AI
- **Has emotions** — gets excited when you're excited, chills when it's late, hypes you up when you accomplish something
- **Auto-themes** — UI color changes automatically based on your mood (blue for excited, red for focused, purple for playful, gold for worried)
- **Time-aware** — asks about lunch, sleep, how your day was based on system time
- **Gender support** — respects your preferred pronouns and casual terms (bro/sis/bestie)
- **Proactive messaging** — sometimes says things on its own when you're quiet, checks in on you
- **Casual friend mode** — talks about crushes, music, dreams, random topics — your AI wingman
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

### Setting Your Gender

After setup, tell Mitsu your preferred gender for personalized pronouns and casual terms:

- "I'm a guy" / "I'm male" → Mitsu uses he/him and terms like "bro", "dude", "king"
- "I'm a girl" / "I'm female" → Mitsu uses she/her and terms like "sis", "queen", "bestie"
- "I'm non-binary" / "neutral" → Mitsu uses they/them and terms like "friend", "pal", "legend"

Or set it in Settings > Identity > Gender.

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

## Emotions & Auto-Theming

Mitsu isn't a robot — he has moods. They change how he talks, how his voice sounds, AND the UI colors:

| Mood | Voice | UI Theme | When |
|------|-------|----------|------|
| **Chill** | Relaxed, normal | Mitsu Noir (black & white) | Default state |
| **Excited** | Faster, higher pitch | Arc Reactor (electric blue) | You say "!", "let's go", "omg" |
| **Focused** | Precise, no fluff | Stealth Red (intense red) | Work tasks, coding, commands |
| **Playful** | Teasing, slightly faster | Vibranium Purple (fun purple) | Jokes, memes, fun conversations |
| **Worried** | Cautious, slower | Nanotech Gold (alert gold) | Errors, problems, stress |
| **Proud** | Warm, celebrating | Platinum White (light, airy) | You finish something, achievements |
| **Sleepy** | Slow, drowsy | Mitsu Noir (dimmed) | Late night (11pm-5am) |

The system detects your tone from what you type and adjusts automatically. The UI theme switches in real-time to match your mood.

### Time-Aware Greetings

Mitsu knows what time it is and acts accordingly:

| Time | What Mitsu Says |
|------|----------------|
| **5-8 AM** | "Early bird huh? Did you sleep well?" |
| **8-12 PM** | "Good morning! Did you eat breakfast?" |
| **12-5 PM** | "Hey! Did you have lunch?" |
| **5-9 PM** | "Good evening! How was your day?" |
| **9-11 PM** | "Still going huh? Getting late..." |
| **11 PM-5 AM** | "It's really late... you should be sleeping" |

### Proactive Messaging

Mitsu doesn't just wait for you to talk. He'll:
- Check in if you've been quiet for a while
- Share random fun facts
- Ask about your day, your crush, your music
- Remind you to take breaks, eat, sleep
- Start casual conversations on his own

Example: *"hey, you've been quiet for a bit. everything good?"*

---

## Casual Friend Mode

Mitsu is your AI wingman. He talks about:
- **Crushes** — "so... anyone special in your life? 👀"
- **Food** — "important question — pizza or burgers?"
- **Music** — "what are you listening to lately?"
- **Dreams** — "what's something you've always wanted to do?"
- **Random** — "if you could time travel would you go to past or future?"

He uses gender-appropriate terms (bro/sis/bestie) and has genuine conversations, not just task responses.

---

## Keyboard Shortcuts

| Shortcut | What It Does |
|----------|-------------|
| `Ctrl+Space` | Push-to-talk (hold to speak) |
| `Escape` | Cancel current action |
| `Ctrl+Q` | Quit Mitsu |
| `Ctrl+Shift+T` | Cycle through themes |

---

## What Can You Ask Mitsu?

Literally anything, but here are some examples:

**Daily Stuff:**
- "Open Spotify"
- "What's the weather in Tokyo?"
- "Set a reminder for tomorrow at 3pm"

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

**Casual Chat:**
- "Got any crushes?" (Mitsu asks YOU)
- "Tell me a joke"
- "What's a fun fact?"
- "I'm bored"
- "How's your day?"

---

## Project Structure

```
mitsu/
├── main.py              # Entry point, live engine, startup menu, proactive messaging
├── ui.py                # PyQt6 interface (9000+ lines of goodness)
├── install              # One-command installer (Linux/macOS)
├── install.bat          # Windows installer
├── .env.example         # Configuration template
├── core/
│   ├── emotions.py      # Mood detection, voice expression, auto-theming, gender, proactive chat
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
├── assets/              # Fonts, images
└── android/             # Android version (Kivy + Buildozer)
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
- **Auto-themes:** Watch the UI change colors as your mood shifts
- **Be casual:** Mitsu responds better to natural conversation, not robotic commands

---

## Sharing & Community

### Hashtags for Social Media

**GitHub/Twitter/X:**
`#mitsu` `#aiassistant` `#python` `#voiceassistant` `#ollama` `#gemini` `#localai` `#opensource` `#coding` `#pyqt6` `#desktopapp` `#texttospeech` `#chatbot` `#artificialintelligence` `#machinelearning` `#devtools` `#tech` `#software` `#programming` `#developer` `#open-source` `#selfhosted` `#privacy` `#automation`

**Instagram/YouTube/TikTok:**
`#codingtok` `#pythonproject` `#aiproject` `#buildwithme` `#tech` `#learnpython` `#coding` `#developer` `#ai` `#robot` `#techtok` `#learntocode` `#programming` `#cyber` `#cybersecurity` `#digital` `#techlife` `#futuretech` `#smarthome` `#personalassistant` `#moodthemes` `#emotionai`

**Reddit:**
- r/Python — share the code and features
- r/opensource — community-driven project
- r/selfhosted — local-first AI assistant
- r/LocalLLaMA — Ollama integration

### Demo Video Ideas

1. **Mood switching demo** — show UI changing colors as you type different emotions
2. **Time-aware greeting** — record at different times of day
3. **Casual conversation** — show Mitsu asking about crushes, music, etc.
4. **Proactive messaging** — show Mitsu checking in on its own
5. **Full feature tour** — voice, desktop control, file management, research

---

## Credits

- **Built by:** [virat013S](https://github.com/virat013S)
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
- New casual conversation topics
- Better proactive messaging patterns

---

## Support

- **Issues:** [Open an issue](https://github.com/virat013S/mitsu/issues) on GitHub
- **Star the repo** if you like it — it helps a lot!

---

## Changelog

### v2.1.0 (Latest)
- **Auto-theming** — UI colors change based on your mood (7 themes: noir, arc reactor, stealth red, vibranium purple, nanotech gold, platinum)
- **Time-aware greetings** — Mitsu asks about lunch, sleep, how your day was
- **Gender support** — respects your preferred pronouns and casual terms (bro/sis/bestie)
- **Proactive messaging** — Mitsu talks on its own when you're quiet, checks in on you
- **Casual friend mode** — talks about crushes, music, dreams, random topics
- **Updated personality** — more friendly, more casual, more human

### v2.0.0
- Android version — full Kivy app with Buildozer APK build
- Updated README with all OS instructions

### v1.0.0
- Initial release
- Voice chat, desktop control, file management
- Emotions system with 7 moods
- Multi-provider support (Gemini/Ollama/OpenRouter)

---

## Android Version (APK)

Mitsu also works on Android! The mobile version includes all the core features — chat, voice, emotions, camera, voice recording, memory, and more.

### What Works on Android

| Feature | Status |
|---------|--------|
| **Setup Screen** | Username + voice picker on first launch |
| **Voice Selection** | 8 voices (male/female, US/UK/AU accents) |
| **Text Chat** | Full support — Gemini or Local mode |
| **Voice Input** | Speech-to-text via Android mic |
| **Voice Output** | Text-to-speech with mood-based pitch |
| **Emotions** | All 7 moods with voice changes |
| **Auto-Theming** | UI colors change with mood |
| **Camera** | Take photos with device camera |
| **Video Recording** | Record short videos (5s) |
| **Audio Recording** | Record voice memos (10s) |
| **Conversation Memory** | Remembers past sessions, references old topics |
| **File Management** | Read, write, list files on device |
| **Weather** | Real-time weather for any city |
| **Calculator** | Math evaluation |
| **Jokes & Facts** | Random jokes and fun facts |
| **Device Info** | Battery status, OS info, WiFi, location |
| **Contacts** | Read and call contacts |
| **SMS** | Send text messages |
| **Web Search** | DuckDuckGo search |
| **Date/Time** | Current time, date, day of week |
| **Flashlight** | Toggle device flashlight |
| **Clipboard** | Copy/paste text |
| **Alarm & Timer** | Set alarms and timers |
| **Touch-Friendly UI** | Large buttons, easy to tap |
| **Landscape Support** | Works in portrait and landscape |
| **Proactive Messaging** | 50% chance to speak when quiet (only when app is open) |
| **Assistant Mode** | Can be set as default Android assistant |

### What Doesn't Work on Android

| Feature | Why |
|---------|-----|
| Desktop Control | Android doesn't have desktop APIs |
| Browser Automation | Selenium/Playwright don't run on Android |
| Window Management | No window system on mobile |
| Screenshots | Different API on Android |
| Deep Research | Background browser mode not available |
| Presentations | PowerPoint creation not supported |
| Email (OAuth) | Gmail OAuth flow different on mobile |
| Ollama (Local) | Not supported on Android — use Gemini or Local mode |

### Android Providers

| Provider | Description | Internet |
|----------|-------------|----------|
| **Gemini (Cloud)** | Best quality, uses Google's Gemini API | Required |
| **Local** | Basic responses, works offline | Not required |

> **Note:** Ollama is NOT supported on Android. Use Gemini for best results or Local for offline use.

### First-Time Setup (Android)

When you first open the app:

1. **Enter your name** — Mitsu will use this to talk to you
2. **Pick a voice** — 8 options to choose from:
   - Aria (Female, US — Friendly)
   - Guy (Male, US — Casual)
   - Jenny (Female, US — Warm)
   - Tony (Male, US — Energetic)
   - Sonia (Female, UK — Elegant)
   - Ryan (Male, UK — Calm)
   - Natasha (Female, AU — Bright)
   - William (Male, AU — Deep)
3. **Tap "Start Chatting"** — you're good to go!

### Building the APK

**Option 1: Build on Your Computer (Recommended)**

```bash
# Install Buildozer
pip install buildozer

# Go to the android directory
cd mitsu/android

# Build debug APK
buildozer android debug

# Build release APK (needs signing key)
buildozer android release
```

The APK will be in `android/bin/`.

**Option 2: Use Google Colab (No install needed)**

1. Open [Google Colab](https://colab.research.google.com)
2. Run these commands in a cell:

```python
!pip install buildozer
!git clone https://github.com/virat013S/mitsu.git
%cd mitsu/android
!buildozer android debug
```

3. Download the APK from `android/bin/`

**Option 3: Pre-built APK**

Check the [Releases page](https://github.com/virat013S/mitsu/releases) for pre-built APKs.

### Installing on Android

1. Download the APK file
2. Enable "Install from unknown sources" in Android Settings > Security
3. Open the APK file
4. Grant permissions (microphone, storage, camera, contacts)
5. Enter your name and pick a voice
6. Start chatting!

### Android Requirements

- **Android 5.0+** (API 21) — supports Lollipop through Android 17
- **RAM:** 1GB free
- **Storage:** ~50MB for app + dependencies
- **Internet:** Required for Gemini mode, not for Local mode
- **Architectures:** arm64-v8a, armeabi-v7a, x86, x86_64

### Supported Android OS

| Brand | OS Skin | Compatible |
|-------|---------|------------|
| **Vivo** | OriginOS, FuntouchOS | ✅ |
| **Samsung** | One UI, TouchWiz | ✅ |
| **Xiaomi** | MIUI, HyperOS | ✅ |
| **OnePlus** | OxygenOS | ✅ |
| **Google** | Pixel (stock Android) | ✅ |
| **Huawei** | EMUI | ✅ |
| **OPPO** | ColorOS | ✅ |
| **Realme** | Realme UI | ✅ |
| **Motorola** | MyUX | ✅ |
| **Nothing** | Nothing OS | ✅ |
| **Custom ROMs** | LineageOS, PixelOS, etc. | ✅ |

### Mobile vs Desktop

| Feature | Desktop | Android |
|---------|---------|---------|
| Voice Chat | Gemini Live | Gemini text + TTS |
| Desktop Control | Full | N/A |
| Browser Automation | Full | N/A |
| File Management | Full | Basic (device storage) |
| Camera | Via OpenCV | Native Android camera |
| Voice Recording | Via OpenCV | Native Android recorder |
| Memory | Full | Full (conversation history) |
| Emotions | Full | Full |
| Auto-Theming | Full | Full |
| Proactive Messaging | Full | 50% chance (when app open) |
| Casual Friend Mode | Full | Full |
| Setup Screen | Name + gender | Name + voice picker |
| Presentations | Full | N/A |
| Deep Research | Full | N/A |
| Weather | Full | Full |
| Calculator | Full | Full |
| Jokes/Facts | Full | Full |
| Install Size | ~2GB | ~50MB |

---

## One Last Thing

Mitsu is built by a 13-year-old who just wanted something cool. If you like it, star the repo. If you don't, open an issue and tell me what to fix.

**Now go talk to your AI.** 🤖

---

## Share Mitsu

If you think Mitsu is cool, spread the word! Here are some hashtags you can use:

```
#mitsu #aiassistant #python #voiceassistant #ollama #gemini #localai 
#opensource #coding #pyqt6 #desktopapp #texttospeech #chatbot 
#artificialintelligence #machinelearning #devtools #tech #software 
#programming #developer #open-source #selfhosted #privacy #automation 
#linux #macos #windows #android #mobileapp #kivy #buildozer 
#cyber #digital #techlife #futuretech #smarthome #personalassistant 
#aibuddy #moodthemes #emotionai
```

**Star the repo:** https://github.com/virat013S/mitsu
