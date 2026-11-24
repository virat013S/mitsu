"""Automatic model router. Heuristic; user override always wins."""
from __future__ import annotations

import re

CODING = re.compile(
    r"\b(write|implement|debug|refactor|fix|review|build|create|make|generate|optimi[sz]e)\b"
    r".{0,60}\b(code|function|class|app|api|script|project|website|bot|test|bug|error|program|module|component)\b",
    re.I | re.S)
DEEP = re.compile(r"\b(research|compare|report|analyse|analyze|thesis|long|paper|citation)\b", re.I)
PRIVATE = re.compile(r"\b(private|local|secret|password|key|offline)\b", re.I)


def route(user_text: str, available: dict | None = None) -> dict:
    """Return {provider, reason}. available: {provider: [models]} (optional)."""
    t = user_text or ""
    if PRIVATE.search(t):
        return {"provider": "ollama", "reason": "private/local task → local model"}
    if DEEP.search(t):
        return {"provider": "openrouter", "reason": "deep research → strongest model"}
    if CODING.search(t):
        return {"provider": "openrouter", "reason": "coding → strong model"}
    if len(t.split()) < 12:
        return {"provider": "ollama", "reason": "short chat → fast model"}
    return {"provider": "ollama", "reason": "default → local model"}
