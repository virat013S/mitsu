"""Multi-provider AI backend: Gemini, Ollama (Gemma 3 1B), OpenRouter.

All providers support:
- Text chat with tool/skill calling
- Voice output via TTS (edge-tts for non-Gemini providers)
"""

from __future__ import annotations

import asyncio
import os
import re
import json
from pathlib import Path
from typing import Any

import httpx


PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "requires": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash",
        "description": "Cloud-based, requires API key (free tier available)",
        "voice": True,
    },
    "ollama": {
        "name": "Local Ollama (Gemma 3 1B)",
        "requires": None,
        "model": "gemma3:1b",
        "base_url": "http://localhost:11434",
        "description": "Fully offline, no API key needed, runs on your hardware",
        "voice": True,
    },
    "openrouter": {
        "name": "OpenRouter (Free Tier)",
        "requires": "OPENROUTER_API_KEY",
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "base_url": "https://openrouter.ai/api/v1",
        "description": "Free — NVIDIA Nemotron 3 Ultra 550B, 1M context window",
        "voice": True,
    },
}


def get_provider() -> str:
    """Get the configured provider from env or config."""
    provider = os.environ.get("MITSU_PROVIDER", "").strip().lower()
    if provider in PROVIDERS:
        return provider
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    return "ollama"


def check_provider_status(provider: str | None = None) -> dict:
    """Check if a provider is configured and available."""
    provider = provider or get_provider()
    info = PROVIDERS.get(provider)
    if not info:
        return {"available": False, "error": f"Unknown provider: {provider}"}

    if provider == "gemini":
        key = os.environ.get("GEMINI_API_KEY", "")
        return {
            "available": bool(key),
            "provider": provider,
            "name": info["name"],
            "model": info["model"],
            "error": None if key else "GEMINI_API_KEY not set",
        }

    if provider == "ollama":
        try:
            resp = httpx.get(f"{info['base_url']}/api/tags", timeout=5.0)
            models = resp.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            has_model = any(info["model"] in n for n in model_names)
            return {
                "available": True,
                "provider": provider,
                "name": info["name"],
                "model": info["model"],
                "installed_models": model_names,
                "model_ready": has_model,
                "error": None if has_model else f"Model {info['model']} not found. Run: ollama pull {info['model']}",
            }
        except Exception as e:
            return {
                "available": False,
                "provider": provider,
                "name": info["name"],
                "error": f"Ollama not running: {e}",
            }

    if provider == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY", "")
        return {
            "available": bool(key),
            "provider": provider,
            "name": info["name"],
            "model": info["model"],
            "error": None if key else "OPENROUTER_API_KEY not set",
        }

    return {"available": False, "error": "Unknown provider"}


def ensure_ollama_model(model: str = "gemma3:1b") -> bool:
    """Pull the model if not already installed."""
    base_url = PROVIDERS["ollama"]["base_url"]
    try:
        resp = httpx.post(
            f"{base_url}/api/pull",
            json={"name": model, "stream": False},
            timeout=300.0,
        )
        return resp.status_code == 200
    except Exception:
        return False


# ── Skill Execution ─────────────────────────────────────────────────────────

def _extract_skill_calls(text: str) -> list[dict]:
    """Extract [SKILL:name] {...} patterns from model output."""
    calls = []
    pattern = r'\[SKILL:(\w+)\]\s*(\{[^}]*\})'
    for match in re.finditer(pattern, text):
        skill_name = match.group(1)
        try:
            params = json.loads(match.group(2))
        except json.JSONDecodeError:
            params = {}
        calls.append({"skill": skill_name, "params": params})
    return calls


def _remove_skill_calls(text: str) -> str:
    """Remove skill call patterns from text, leaving clean response."""
    cleaned = re.sub(r'\[SKILL:\w+\]\s*\{[^}]*\}', '', text)
    return cleaned.strip()


def execute_skill_calls(text: str) -> tuple[str, list[dict]]:
    """Extract and execute skill calls, return (cleaned_text, results)."""
    from core.skills import run_skill

    calls = _extract_skill_calls(text)
    results = []
    for call in calls:
        skill_name = call["skill"]
        params = call["params"]
        result = run_skill(skill_name, **params)
        results.append({"skill": skill_name, "params": params, "result": result})

    cleaned = _remove_skill_calls(text)
    return cleaned, results


# ── Voice / TTS ─────────────────────────────────────────────────────────────

def _tts_edge(text: str, voice: str = "en-US-AriaNeural") -> bool:
    """Generate speech using edge-tts (free, no API key). Returns True if played."""
    try:
        import subprocess, tempfile, os
        tmp = tempfile.mktemp(suffix=".mp3")
        proc = subprocess.run(
            ["edge-tts", "--voice", voice, "--text", text, "--write-media", tmp],
            capture_output=True, timeout=30,
        )
        if proc.returncode == 0 and os.path.exists(tmp):
            subprocess.run(["mpv", "--no-video", tmp], capture_output=True, timeout=60)
            os.unlink(tmp)
            return True
    except Exception:
        pass
    return False


def speak(text: str, voice: str | None = None) -> bool:
    """Speak text using available TTS. Returns True if spoken."""
    if not text or not text.strip():
        return False
    # Try edge-tts first (free, works everywhere)
    edge_voice = voice or "en-US-AriaNeural"
    if _tts_edge(text, edge_voice):
        return True
    # Fallback: try system espeak
    try:
        subprocess.run(["espeak", text], capture_output=True, timeout=30)
        return True
    except Exception:
        pass
    return False


# ── Provider Calls ──────────────────────────────────────────────────────────

def call_ollama(
    messages: list[dict],
    model: str | None = None,
    tools: list[dict] | None = None,
    stream: bool = False,
) -> dict:
    """Call Ollama chat API with optional tool support.

    The model defaults to the user's selected Ollama model
    (MITSU_MODEL env > stored selection > provider default).
    """
    if not (model or "").strip():
        try:
            from core.models import resolve_model
            model = resolve_model("ollama")
        except Exception:
            model = PROVIDERS["ollama"]["model"]
    base_url = PROVIDERS["ollama"]["base_url"]
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {"num_ctx": 32768},
    }
    if tools:
        payload["tools"] = tools
    resp = httpx.post(f"{base_url}/api/chat", json=payload, timeout=120.0)
    return resp.json()


def call_openrouter(
    messages: list[dict],
    model: str | None = None,
    tools: list[dict] | None = None,
) -> dict:
    """Call OpenRouter API (OpenAI-compatible).

    The model defaults to the user's selected OpenRouter model
    (explicit > MITSU_MODEL env > stored selection > OPENROUTER_MODEL
    env > provider default).
    """
    key = os.environ.get("OPENROUTER_API_KEY", "")
    base_url = PROVIDERS["openrouter"]["base_url"]
    if not (model or "").strip():
        try:
            from core.models import resolve_model
            model = resolve_model("openrouter")
        except Exception:
            model = None
    if not (model or "").strip():
        model = os.environ.get("OPENROUTER_MODEL", PROVIDERS["openrouter"]["model"])
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools
    resp = httpx.post(
        f"{base_url}/chat/completions",
        json=payload,
        headers=headers,
        timeout=60.0,
    )
    return resp.json()


def chat_with_provider(
    messages: list[dict],
    provider: str | None = None,
    voice: bool = False,
    model: str | None = None,
) -> str:
    """Unified chat interface. Send messages, get response, optionally speak it.

    The model defaults to the user's selection for the active provider;
    an explicit model always wins (never silently overridden).
    """
    provider = provider or get_provider()

    if provider == "gemini":
        # Gemini uses its own live engine in main.py
        return ""

    if provider == "ollama":
        result = call_ollama(messages, model=model)
        text = result.get("message", {}).get("content", "")
        # Execute any skill calls in the response
        text, skill_results = execute_skill_calls(text)
        if voice and text:
            speak(text)
        return text

    if provider == "openrouter":
        result = call_openrouter(messages, model=model)
        text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        text, skill_results = execute_skill_calls(text)
        if voice and text:
            speak(text)
        return text

    return "Unknown provider"


def provider_requires_key(provider: str | None = None) -> str | None:
    """Return the env var a provider needs, or None if it needs no key.

    Local/Ollama never requires any API key. OpenRouter requires only its
    own key. Only Gemini requires a Gemini key — and only when selected.
    """
    provider = (provider or get_provider() or "").strip().lower()
    if provider == "gemini":
        return "GEMINI_API_KEY"
    if provider == "openrouter":
        return "OPENROUTER_API_KEY"
    return None


def missing_credential_message(provider: str | None = None) -> str:
    """User-facing message for a provider that cannot authenticate.

    Never mentions Gemini unless Gemini is the selected provider.
    """
    provider = (provider or get_provider() or "").strip().lower()
    if provider == "gemini":
        return (
            "Gemini is not configured. Set GEMINI_API_KEY, then select "
            "the Gemini provider again."
        )
    if provider == "openrouter":
        return (
            "OpenRouter credentials are missing. Set OPENROUTER_API_KEY "
            "to use the OpenRouter provider. No Gemini key is needed."
        )
    return (
        "Local AI is unavailable. Start or verify Ollama "
        "(ollama serve), or change provider. No API key is needed "
        "for local mode."
    )


def translate_tool_error(tool_name: str, error: Exception,
                         provider: str | None = None) -> str:
    """Convert a raw tool exception into a WHAT/WHY/WHAT-TO-DO message.

    Gemini-backed tools raise 'Gemini API key not found' when no key is
    configured. Surface that as a configuration error tied to the active
    provider instead of a raw traceback-style message.
    """
    raw = f"{error}".strip() or error.__class__.__name__
    lowered = raw.lower()
    if "gemini api key" in lowered or "gemini_api_key" in lowered.replace(" ", "_"):
        active = (provider or get_provider() or "").strip().lower()
        if active and active != "gemini":
            return (
                f"Tool '{tool_name}' needs Gemini credentials, but the "
                f"active provider is {active}. Configure a Gemini key in "
                f"Settings, or use a provider-native alternative. "
                f"Your provider has not been changed."
            )
        return (
            f"Tool '{tool_name}' needs Gemini credentials. "
            "Gemini is not configured — add a Gemini key in Settings "
            "to enable it."
        )
    return f"Tool '{tool_name}' failed: {raw}"
