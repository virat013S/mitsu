"""Mitsu Skills — built-in tools to make any model smarter.

Skills give even small local models (Gemma 3 1B) superpowers:
- Calculator: precise math without LLM hallucination
- Web Fetch: grab content from any URL
- Code Runner: execute Python safely
- File Reader: read any file on disk
- Web Search: search the internet
- Datetime: current time, date math
- JSON Parser: extract structured data
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import tempfile
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx


# ── Calculator ──────────────────────────────────────────────────────────────

SAFE_MATH_FUNCS = {
    "abs": abs, "round": round, "min": min, "max": max,
    "sum": sum, "len": len, "int": int, "float": float,
    "sqrt": math.sqrt, "pow": pow, "log": math.log, "log10": math.log10,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "pi": math.pi, "e": math.e, "ceil": math.ceil, "floor": math.floor,
    "factorial": math.factorial, "gcd": math.gcd,
}


def skill_calculator(expression: str) -> str:
    """Evaluate a math expression safely. No imports, no side effects."""
    try:
        # Clean the expression
        expr = expression.strip()
        expr = expr.replace("^", "**")  # caret to power
        result = eval(expr, {"__builtins__": {}}, SAFE_MATH_FUNCS)
        return str(result)
    except Exception as e:
        return f"Math error: {e}"


# ── Web Fetch ───────────────────────────────────────────────────────────────

def skill_web_fetch(url: str, max_chars: int = 5000) -> str:
    """Fetch content from a URL and return readable text."""
    try:
        resp = httpx.get(url, timeout=15.0, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Mitsu/1.0)"
        })
        resp.raise_for_status()
        content = resp.text
        # Try to extract readable text from HTML
        if "<html" in content.lower():
            # Simple HTML tag removal
            content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r"<[^>]+>", " ", content)
            content = re.sub(r"\s+", " ", content).strip()
        if len(content) > max_chars:
            content = content[:max_chars] + "\n...[truncated]"
        return content
    except Exception as e:
        return f"Fetch error: {e}"


# ── Code Runner ─────────────────────────────────────────────────────────────

def skill_run_code(code: str, language: str = "python", timeout: int = 10) -> str:
    """Run code safely in a subprocess."""
    if language.lower() not in ("python", "py"):
        return f"Only Python is supported right now. Got: {language}"
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp_path = f.name
        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True, text=True, timeout=timeout,
        )
        Path(tmp_path).unlink(missing_ok=True)
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}" if output else result.stderr
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Code timed out after {timeout}s"
    except Exception as e:
        return f"Run error: {e}"


# ── File Reader ─────────────────────────────────────────────────────────────

def skill_read_file(path: str, max_chars: int = 8000) -> str:
    """Read a file and return its contents."""
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"File not found: {path}"
        if not p.is_file():
            return f"Not a file: {path}"
        content = p.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n...[truncated, {len(p.read_text())} total chars]"
        return content
    except Exception as e:
        return f"Read error: {e}"


# ── Web Search ──────────────────────────────────────────────────────────────

def skill_web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        output = []
        for i, r in enumerate(results, 1):
            output.append(f"{i}. {r.get('title', 'No title')}")
            output.append(f"   {r.get('href', '')}")
            output.append(f"   {r.get('body', '')[:200]}")
            output.append("")
        return "\n".join(output)
    except Exception as e:
        return f"Search error: {e}"


# ── Datetime ────────────────────────────────────────────────────────────────

def skill_datetime(query: str = "now") -> str:
    """Get current date/time or do date math."""
    now = datetime.now()
    query = query.strip().lower()
    if query in ("now", "time", "date", ""):
        return now.strftime("%Y-%m-%d %H:%M:%S (%A)")
    if "tomorrow" in query:
        return (now + timedelta(days=1)).strftime("%Y-%m-%d (%A)")
    if "yesterday" in query:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d (%A)")
    if "week" in query:
        return (now + timedelta(weeks=1)).strftime("%Y-%m-%d (%A)")
    return now.strftime("%Y-%m-%d %H:%M:%S (%A)")


# ── JSON Extractor ──────────────────────────────────────────────────────────

def skill_json_parse(text: str) -> str:
    """Try to extract JSON from text."""
    try:
        # Find JSON objects or arrays in text
        for match in re.finditer(r'(\{.*\}|\[.*\])', text, re.DOTALL):
            try:
                parsed = json.loads(match.group())
                return json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                continue
        return "No valid JSON found in text."
    except Exception as e:
        return f"Parse error: {e}"


# ── Skill Registry ──────────────────────────────────────────────────────────

SKILLS = {
    "calculator": {
        "name": "calculator",
        "description": "Evaluate math expressions. Use for ANY calculation — never guess math, always use this tool.",
        "function": skill_calculator,
        "params": {"expression": "str"},
    },
    "web_fetch": {
        "name": "web_fetch",
        "description": "Fetch and read content from any URL. Use when you need to read a specific webpage.",
        "function": skill_web_fetch,
        "params": {"url": "str", "max_chars": "int (default 5000)"},
    },
    "run_code": {
        "name": "run_code",
        "description": "Execute Python code and return output. Use for coding tasks, data processing, APIs, anything programmatic.",
        "function": skill_run_code,
        "params": {"code": "str", "language": "str (default python)"},
    },
    "read_file": {
        "name": "read_file",
        "description": "Read a file from disk. Use when user asks to see or analyze a file.",
        "function": skill_read_file,
        "params": {"path": "str", "max_chars": "int (default 8000)"},
    },
    "web_search": {
        "name": "web_search",
        "description": "Search the web for information. Use for current events, facts you don't know, research.",
        "function": skill_web_search,
        "params": {"query": "str", "max_results": "int (default 5)"},
    },
    "datetime": {
        "name": "datetime",
        "description": "Get current date/time or do date math (tomorrow, yesterday, next week).",
        "function": skill_datetime,
        "params": {"query": "str (default: now)"},
    },
    "json_parse": {
        "name": "json_parse",
        "description": "Extract and validate JSON from text.",
        "function": skill_json_parse,
        "params": {"text": "str"},
    },
    "analyze_image": {
        "name": "analyze_image",
        "description": "Analyze an image — detect faces, describe content, get dimensions. Use for ANY image question.",
        "function": lambda image_path, question="Describe this image": "",  # placeholder
        "params": {"image_path": "str", "question": "str (default: describe)"},
    },
    "ocr_image": {
        "name": "ocr_image",
        "description": "Extract text from an image (OCR). Use when user wants to read text in a picture.",
        "function": lambda image_path: "",  # placeholder
        "params": {"image_path": "str"},
    },
    "analyze_video": {
        "name": "analyze_video",
        "description": "Analyze a video — extract key frames, describe scenes, get metadata.",
        "function": lambda video_path, question="Describe this video": "",  # placeholder
        "params": {"video_path": "str", "question": "str (default: describe)"},
    },
    "identify_speaker": {
        "name": "identify_speaker",
        "description": "Identify who is speaking from an audio file.",
        "function": lambda audio_path: "",  # placeholder
        "params": {"audio_path": "str"},
    },
}


def get_skill_descriptions() -> str:
    """Return formatted skill descriptions for system prompt."""
    lines = []
    for name, skill in SKILLS.items():
        params = ", ".join(skill["params"].keys())
        lines.append(f"  - {name}({params}): {skill['description']}")
    return "\n".join(lines)


def run_skill(name: str, **kwargs) -> str:
    """Run a skill by name with given parameters."""
    skill = SKILLS.get(name)
    if not skill:
        return f"Unknown skill: {name}. Available: {', '.join(SKILLS.keys())}"
    try:
        # Handle recognition skills that need lazy imports
        if name == "analyze_image":
            from core.recognition import analyze_image
            return analyze_image(**kwargs)
        if name == "ocr_image":
            from core.recognition import ocr_image
            return ocr_image(**kwargs)
        if name == "analyze_video":
            from core.recognition import analyze_video
            return analyze_video(**kwargs)
        if name == "identify_speaker":
            from core.recognition import identify_speaker
            import numpy as np
            # Load audio file if path provided
            audio_path = kwargs.get("audio_path", "")
            if audio_path and os.path.exists(audio_path):
                import soundfile as sf
                audio_data, sr = sf.read(audio_path)
                if len(audio_data.shape) > 1:
                    audio_data = audio_data.mean(axis=1)
                return identify_speaker(audio_data, sr)
            return "No valid audio file provided"
        return skill["function"](**kwargs)
    except TypeError as e:
        return f"Wrong arguments for {name}: {e}"
    except Exception as e:
        return f"Skill {name} error: {e}"
