"""Modular skills (§19). Each skill: mitsu/skills/<name>/skill.md + enabled flag.

skill.md front-matter:
    ---
    name: notes
    description: local notes
    ---
    <instructions for the model>
Developers: copy `notes/` to add a skill. Toggle via API/UI; disabled skills
are hidden from the agent system prompt.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..core.paths import data_dir

BUILTIN = Path(__file__).parent


def _flags() -> dict:
    p = data_dir() / "skills.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _save_flags(f: dict) -> None:
    (data_dir() / "skills.json").write_text(json.dumps(f))


def discover() -> list[dict]:
    flags = _flags()
    out = []
    if BUILTIN.exists():
        for d in sorted(BUILTIN.iterdir()):
            md = d / "skill.md"
            if d.is_dir() and md.exists() and d.name != "__pycache__":
                head = md.read_text()[:600]
                out.append({"name": d.name, "enabled": flags.get(d.name, True),
                            "description": _desc(head)})
    return out


def _desc(head: str) -> str:
    for line in head.splitlines():
        if line.lower().startswith("description:"):
            return line.split(":", 1)[1].strip()
    return ""


def set_enabled(name: str, enabled: bool) -> None:
    flags = _flags()
    flags[name] = enabled
    _save_flags(flags)


def active_instructions() -> str:
    """Injected into the chat system prompt (Phase 4 advanced skills)."""
    parts = []
    for s in discover():
        if s["enabled"]:
            try:
                parts.append(f"[{s['name']}]\n" + (BUILTIN / s["name"] / "skill.md").read_text()[:1500])
            except Exception:
                continue
    return "\n\n".join(parts)[:4000]
