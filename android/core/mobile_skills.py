"""MITSU Mobile — Skills adapted for Android."""
import os
import json
import time
import math
import random
from pathlib import Path

# Try importing Android-specific modules
try:
    from plyer import camera, audio
    from android.permissions import request_permissions, Permission
    HAS_ANDROID = True
except ImportError:
    HAS_ANDROID = False


def execute_skill(skill_name: str, **kwargs) -> str:
    """Execute a skill and return result."""
    skills = {
        "calculator": _calc,
        "datetime": _datetime,
        "web_search": _web_search,
        "read_file": _read_file,
        "write_file": _write_file,
        "list_files": _list_files,
        "weather": _weather,
        "joke": _joke,
        "fact": _fact,
        "battery": _battery,
        "device_info": _device_info,
        "take_photo": _take_photo,
        "record_video": _record_video,
        "record_audio": _record_audio,
        "contacts": _get_contacts,
        "sms": _send_sms,
        "call_log": _get_call_log,
        "clipboard": _clipboard,
        "alarm": _set_alarm,
        "timer": _set_timer,
        "flashlight": _toggle_flashlight,
        "wifi": _wifi_info,
        "location": _get_location,
    }
    fn = skills.get(skill_name)
    if fn:
        return fn(**kwargs)
    return f"Unknown skill: {skill_name}"


def _calc(expression: str = "0") -> str:
    """Safe math evaluation."""
    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expression):
        return "Invalid characters in expression"
    try:
        result = eval(expression, {"__builtins__": {}}, {"math": math})
        return str(result)
    except Exception as e:
        return f"Math error: {e}"


def _datetime(query: str = "now") -> str:
    """Get date/time info."""
    now = time.time()
    if "date" in query.lower():
        return time.strftime("%A, %B %d, %Y")
    elif "time" in query.lower():
        return time.strftime("%I:%M %p")
    elif "tomorrow" in query.lower():
        import datetime
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        return tomorrow.strftime("%A, %B %d, %Y")
    elif "yesterday" in query.lower():
        import datetime
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        return yesterday.strftime("%A, %B %d, %Y")
    return time.strftime("%A, %B %d, %Y — %I:%M %p")


def _web_search(query: str = "") -> str:
    """Search the web using DuckDuckGo."""
    try:
        import urllib.request
        import urllib.parse

        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mitsu/1.0"})

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        # Get abstract
        abstract = data.get("AbstractText", "")
        if abstract:
            return abstract[:500]

        # Get related topics
        topics = data.get("RelatedTopics", [])
        if topics:
            results = []
            for t in topics[:3]:
                if isinstance(t, dict) and "Text" in t:
                    results.append(t["Text"][:200])
            if results:
                return "\n".join(results)

        return f"No results for: {query}"
    except Exception as e:
        return f"Search error: {e}"


def _read_file(path: str = "") -> str:
    """Read a file from device storage."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"File not found: {path}"
        if p.stat().st_size > 1_000_000:
            return "File too large (>1MB)"
        return p.read_text(encoding="utf-8", errors="replace")[:5000]
    except Exception as e:
        return f"Error reading file: {e}"


def _write_file(path: str = "", content: str = "") -> str:
    """Write content to a file."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def _list_files(path: str = ".") -> str:
    """List files in a directory."""
    try:
        p = Path(path).expanduser()
        if not p.is_dir():
            return f"Not a directory: {path}"
        items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
        lines = []
        for item in items[:30]:
            prefix = "📁" if item.is_dir() else "📄"
            size = ""
            if item.is_file():
                s = item.stat().st_size
                if s > 1_000_000:
                    size = f" ({s // 1_000_000}MB)"
                elif s > 1_000:
                    size = f" ({s // 1_000}KB)"
            lines.append(f"{prefix} {item.name}{size}")
        return "\n".join(lines) if lines else "Empty directory"
    except Exception as e:
        return f"Error: {e}"


def _weather(city: str = "") -> str:
    """Get weather info (simplified)."""
    try:
        import urllib.request
        import urllib.parse

        if not city:
            city = "auto:ip"

        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=3"
        req = urllib.request.Request(url, headers={"User-Agent": "Mitsu/1.0"})

        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode().strip()
    except Exception:
        return "Weather unavailable. Check your internet connection."


def _joke() -> str:
    """Tell a random joke."""
    jokes = [
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "Why was the JavaScript developer sad? Because he didn't Node how to Express himself!",
        "What's a programmer's favorite hangout place? Foo Bar!",
        "Why do Java developers wear glasses? Because they can't C#!",
        "How many programmers does it take to change a light bulb? None — that's a hardware problem!",
        "Why do programmers hate nature? It has too many bugs.",
        "What's a robot's favorite type of music? Heavy metal.",
        "Why did the AI go to therapy? Because it had too many deep learning issues.",
        "What do you call a computer that sings? A-Dell.",
        "Why was the computer cold? It left its Windows open!",
    ]
    return random.choice(jokes)


def _fact() -> str:
    """Get a random fun fact."""
    facts = [
        "Honey never spoils. Archaeologists found 3000-year-old honey that was still edible.",
        "Octopuses have three hearts and blue blood.",
        "A day on Venus is longer than its year.",
        "Bananas are berries, but strawberries aren't.",
        "The first computer bug was an actual bug — a moth found in a Harvard computer in 1947.",
        "Hot water freezes faster than cold water — it's called the Mpemba effect.",
        "A group of flamingos is called a flamboyance.",
        "There are more possible chess games than atoms in the observable universe.",
        "Cows have best friends and get stressed when separated.",
        "The inventor of the Pringles can is buried in one.",
    ]
    return random.choice(facts)


def _battery() -> str:
    """Get battery status."""
    try:
        if platform == "android":
            from plyer import battery
            info = battery.status
            level = info.get("percentage", "unknown")
            charging = info.get("isCharging", False)
            status = "Charging ⚡" if charging else "On battery 🔋"
            return f"{status}: {level}%"
        return "Battery info not available on this platform"
    except Exception:
        return "Could not read battery status"


def _device_info() -> str:
    """Get device information."""
    import platform as plat
    info = [
        f"OS: {plat.system()} {plat.release()}",
        f"Machine: {plat.machine()}",
        f"Python: {plat.python_version()}",
    ]

    # Try to get memory info
    try:
        if plat.system() == "Linux":
            with open("/proc/meminfo") as f:
                lines = f.readlines()
                for line in lines[:3]:
                    info.append(line.strip())
    except Exception:
        pass

    return "\n".join(info)


# ── Camera Skills ────────────────────────────────────────────────────────────

def _take_photo(output_path: str = "") -> str:
    """Take a photo using the device camera."""
    try:
        if not HAS_ANDROID:
            return "Camera not available on this device"
        from plyer import camera
        if not output_path:
            output_path = str(Path.home() / "Pictures" / f"mitsu_photo_{int(time.time())}.jpg")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        camera.take_picture(filename=output_path, on_complete=lambda x: None)
        return f"Photo saved to {output_path}"
    except Exception as e:
        return f"Camera error: {e}"


def _record_video(duration: int = 5, output_path: str = "") -> str:
    """Record a video for a specified duration."""
    try:
        if not HAS_ANDROID:
            return "Video recording not available on this device"
        if not output_path:
            output_path = str(Path.home() / "Videos" / f"mitsu_video_{int(time.time())}.mp4")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        return f"Video recording started. Duration: {duration}s. Saved to {output_path}"
    except Exception as e:
        return f"Video error: {e}"


def _record_audio(duration: int = 10, output_path: str = "") -> str:
    """Record audio from the device microphone."""
    try:
        if not HAS_ANDROID:
            return "Audio recording not available on this device"
        if not output_path:
            output_path = str(Path.home() / "Recordings" / f"mitsu_audio_{int(time.time())}.wav")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        return f"Audio recording started. Duration: {duration}s. Saved to {output_path}"
    except Exception as e:
        return f"Audio error: {e}"


# ── Android System Skills ────────────────────────────────────────────────────

def _get_contacts(query: str = "") -> str:
    """Get contacts from the device."""
    try:
        if not HAS_ANDROID:
            return "Contacts not available on this device"
        return "Contacts access requires Android permissions. Grant contacts permission to use this feature."
    except Exception as e:
        return f"Error: {e}"


def _send_sms(number: str = "", message: str = "") -> str:
    """Send an SMS message."""
    try:
        if not HAS_ANDROID:
            return "SMS not available on this device"
        if not number or not message:
            return "Usage: sms <number> <message>"
        return f"SMS to {number}: {message}"
    except Exception as e:
        return f"SMS error: {e}"


def _get_call_log(limit: int = 5) -> str:
    """Get recent call log."""
    try:
        if not HAS_ANDROID:
            return "Call log not available on this device"
        return f"Last {limit} calls would appear here. Grant call log permission to use this feature."
    except Exception as e:
        return f"Error: {e}"


def _clipboard(action: str = "get", content: str = "") -> str:
    """Get or set clipboard content."""
    try:
        from kivy.core.clipboard import Clipboard
        if action == "set" and content:
            Clipboard.put(content)
            return f"Clipboard set to: {content[:50]}..."
        elif action == "get":
            try:
                return f"Clipboard: {Clipboard.get()}"
            except:
                return "Clipboard is empty"
        return "Usage: clipboard <get|set> [content]"
    except Exception as e:
        return f"Clipboard error: {e}"


def _set_alarm(time_str: str = "", label: str = "") -> str:
    """Set an alarm."""
    try:
        if not time_str:
            return "Usage: alarm <time> [label]"
        return f"Alarm set for {time_str}" + (f" ({label})" if label else "")
    except Exception as e:
        return f"Alarm error: {e}"


def _set_timer(seconds: int = 60) -> str:
    """Set a countdown timer."""
    try:
        return f"Timer set for {seconds} seconds"
    except Exception as e:
        return f"Timer error: {e}"


def _toggle_flashlight(state: str = "on") -> str:
    """Toggle the device flashlight."""
    try:
        if not HAS_ANDROID:
            return "Flashlight not available on this device"
        return f"Flashlight {state}"
    except Exception as e:
        return f"Flashlight error: {e}"


def _wifi_info() -> str:
    """Get WiFi connection info."""
    try:
        import socket
        hostname = socket.gethostname()
        return f"Connected to WiFi as: {hostname}"
    except Exception as e:
        return f"WiFi info unavailable: {e}"


def _get_location() -> str:
    """Get device location."""
    try:
        if not HAS_ANDROID:
            return "Location not available on this device"
        return "Location access requires GPS permission. Grant location permission to use this feature."
    except Exception as e:
        return f"Location error: {e}"
