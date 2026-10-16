"""Local full-text search over memory (§28/§29 — works offline)."""
from __future__ import annotations

from .store import MemoryStore


def search(mem: MemoryStore, query: str, limit: int = 10) -> list[dict]:
    q = query.lower().split()
    hits = []
    for m in list(mem.short) + [{"role": "long-term", **f} for f in mem.long_term]:
        text = (m.get("content") or m.get("fact") or "")
        score = sum(text.lower().count(w) for w in q)
        if score:
            hits.append({"role": m.get("role", "?"), "text": text[:500], "score": score})
    return sorted(hits, key=lambda h: -h["score"])[:limit]
