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
    model: str = "gemma3:1b",
    tools: list[dict] | None = None,
    stream: bool = False,
) -> dict:
    """Call Ollama chat API with optional tool support."""
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
    """Call OpenRouter API (OpenAI-compatible)."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    base_url = PROVIDERS["openrouter"]["base_url"]
    if model is None:
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
) -> str:
    """Unified chat interface. Send messages, get response, optionally speak it."""
    provider = provider or get_provider()

    if provider == "gemini":
        # Gemini uses its own live engine in main.py
        return ""

    if provider == "ollama":
        result = call_ollama(messages)
        text = result.get("message", {}).get("content", "")
        # Execute any skill calls in the response
        text, skill_results = execute_skill_calls(text)
        if voice and text:
            speak(text)
        return text

    if provider == "openrouter":
        result = call_openrouter(messages)
        text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        text, skill_results = execute_skill_calls(text)
        if voice and text:
            speak(text)
        return text

    return "Unknown provider"
