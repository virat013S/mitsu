"""MITSU Mobile — Skills adapted for Android."""
import os
import json
import time
import math
from pathlib import Path


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
