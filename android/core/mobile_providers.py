"""MITSU Mobile — API, TTS, and Speech Recognition for Android."""
import os
import json
import time
import random
from pathlib import Path

# ── Provider Config ──────────────────────────────────────────────────────
PROVIDERS = {
    "gemini": {
        "name": "Gemini (Google)",
        "model": "gemini-2.5-flash",
    },
    "ollama": {
        "name": "Ollama (Local)",
        "model": "gemma3:1b",
        "base_url": "http://localhost:11434",
    },
    "openrouter": {
        "name": "OpenRouter",
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "base_url": "https://openrouter.ai/api/v1",
    },
}


def _get_provider():
    """Detect which provider to use."""
    # Check provider.json first
    try:
        cfg_file = Path.home() / ".mitsu" / "provider.json"
        if cfg_file.exists():
            cfg = json.loads(cfg_file.read_text())
            p = cfg.get("provider", "").lower()
            if p in PROVIDERS:
                return p
    except Exception:
        pass

    # Check env
    env = os.environ.get("MITSU_PROVIDER", "").lower()
    if env in PROVIDERS:
        return env

    # Check available keys
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"

    return "gemini"  # default


def call_ai(user_message: str, mood: str = "chill") -> str:
    """Call the AI provider and get a response."""
    provider = _get_provider()

    # Build mood-aware system prompt
    mood_prefix = _get_mood_prefix(mood)
    system = (
        "You are Mitsu — a friendly, witty AI assistant. "
        "Be casual and conversational. Keep responses concise but helpful. "
        f"Current mood vibe: {mood}. {mood_prefix}"
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]

    try:
        if provider == "gemini":
            return _call_gemini(messages)
        elif provider == "ollama":
            return _call_ollama(messages)
        elif provider == "openrouter":
            return _call_openrouter(messages)
    except Exception as e:
        return f"API Error: {str(e)}"

    return "I'm not sure how to respond. Try again?"


def _call_gemini(messages):
    """Call Google Gemini API."""
    import urllib.request

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return "Gemini API key not set. Please configure it in settings."

    model = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    # Convert messages to Gemini format
    contents = []
    for msg in messages:
        role = "user" if msg["role"] in ("user", "system") else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })

    payload = json.dumps({"contents": contents}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_ollama(messages):
    """Call local Ollama API."""
    import urllib.request

    base_url = PROVIDERS["ollama"]["base_url"]
    model = PROVIDERS["ollama"]["model"]

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        return data["message"]["content"]


def _call_openrouter(messages):
    """Call OpenRouter API."""
    import urllib.request

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return "OpenRouter API key not set. Please configure it in settings."

    base_url = PROVIDERS["openrouter"]["base_url"]
    model = PROVIDERS["openrouter"]["model"]

    payload = json.dumps({
        "model": model,
        "messages": messages,
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]


def _get_mood_prefix(mood):
    """Get a mood-appropriate prefix for the system prompt."""
    prefixes = {
        "chill": "Keep it relaxed and casual.",
        "excited": "Match the user's energy! Be hyped!",
        "focused": "Be precise and task-oriented.",
        "playful": "Be fun and teasing.",
        "worried": "Be reassuring and helpful.",
        "proud": "Be warm and celebratory.",
        "sleepy": "Be cozy and gentle.",
    }
    return prefixes.get(mood, "")


def speak_mobile(text: str, voice_params: dict = None):
    """Speak text on mobile using TTS."""
    try:
        if platform == "android":
            # Use Android TTS via plyer
            from plyer import tts
            tts.speech(text=text, lang="en")
        else:
            # Fallback to edge-tts on desktop
            _speak_edge(text, voice_params)
    except Exception:
        pass


def _speak_edge(text, voice_params=None):
    """Edge-TTS fallback for desktop testing."""
    try:
        import subprocess, tempfile

        voice = "en-US-AriaNeural"
        pitch = voice_params.get("pitch", "+0Hz") if voice_params else "+0Hz"
        rate = voice_params.get("rate", "+0%") if voice_params else "+0%"

        tmp = tempfile.mktemp(suffix=".mp3")
        cmd = ["edge-tts", "--voice", voice, "--text", text, "--write-media", tmp]

        if pitch and pitch != "+0Hz":
            cmd.extend(["--pitch", pitch])
        if rate and rate != "+0%":
            cmd.extend(["--rate", rate])

        subprocess.run(cmd, capture_output=True, timeout=30)
        subprocess.run(["mpv", "--no-video", tmp], capture_output=True, timeout=60)

        try:
            os.unlink(tmp)
        except Exception:
            pass
    except Exception:
        pass


def recognize_speech() -> str | None:
    """Recognize speech from microphone."""
    try:
        if platform == "android":
            # Use Android speech recognition via plyer
            from plyer import speech
            result = speechpeech_to_text(timeout=10)
            return result
        else:
            # Fallback to speech_recognition library
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                audio = recognizer.listen(source, timeout=5)
            return recognizer.recognize_google(audio)
    except Exception:
        return None
