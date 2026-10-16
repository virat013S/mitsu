"""Automatic model router (§5). Heuristic; user override always wins."""
from __future__ import annotations

import re

CODING = re.compile(r"\b(code|python|react|bug|refactor|test|git|function|class|api|build|website|bot|mod|app)\b", re.I)
DEEP = re.compile(r"\b(research|compare|report|analyse|analyze|thesis|long|paper|citation)\b", re.I)
PRIVATE = re.compile(r"\b(private|local|secret|password|key|offline)\b", re.I)


def route(user_text: str, available: dict | None = None) -> dict:
    """Return {provider, reason}. available: {provider: [models]} (optional)."""
    t = user_text or ""
    if PRIVATE.search(t):
        return {"provider": "ollama", "reason": "private/local task → Ollama"}
    if DEEP.search(t):
        return {"provider": "openrouter", "reason": "deep research → strongest cloud model"}
    if CODING.search(t):
        return {"provider": "openrouter", "reason": "coding → strong coding model"}
    if len(t.split()) < 12:
        return {"provider": "ollama", "reason": "short chat → fast local model"}
    return {"provider": "ollama", "reason": "default → fast local model"}
