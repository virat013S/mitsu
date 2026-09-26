"""Canonical user identity — the single source of truth for who the user is.

UI, CLI, voice, agent, memory, tasks, and notifications must all resolve
identity through this module. There is exactly one resolution order:

1. long-term memory ``identity.name`` (file or hosted DB backend)
2. ``~/.mitsu/username.txt`` (CLI username file, kept in sync)

The name persists across restarts, provider changes, voice/text modes,
UI changes, updates, and background sessions until explicitly changed
or deleted. Guest mode (no name) uses neutral language — never a fake
identity and never ``sir``/``madam``.
"""
from __future__ import annotations

from pathlib import Path

USERNAME_FILE = Path.home() / ".mitsu" / "username.txt"

# Generic honorifics/placeholders that must never be stored as the name.
RESERVED_NAMES = frozenset({"sir", "madam", "madame", "friend", "there"})


def _clean(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def is_valid_name(name: object) -> bool:
    """A storable name is non-empty and not a generic placeholder."""
    cleaned = _clean(name)
    return bool(cleaned) and cleaned.lower() not in RESERVED_NAMES


def get_display_name() -> str:
    """Resolve the user's name: memory first, then the CLI username file."""
    try:
        from memory.memory_manager import load_memory
        entry = load_memory().get("identity", {}).get("name")
        val = entry.get("value") if isinstance(entry, dict) else entry
        if is_valid_name(val):
            return _clean(val)
    except Exception:
        pass
    try:
        if USERNAME_FILE.exists():
            name = USERNAME_FILE.read_text(encoding="utf-8").strip()
            if is_valid_name(name):
                return name
    except Exception:
        pass
    return ""


def set_display_name(name: str) -> str:
    """Persist a new display name to every identity store.

    Returns the saved name. Raises ValueError for empty/reserved names —
    callers show the message and keep the previous identity.
    """
    cleaned = _clean(name)
    if not cleaned:
        raise ValueError("Please enter a real name so MITSU can address you.")
    if cleaned.lower() in RESERVED_NAMES:
        raise ValueError("Please enter a real name so MITSU can address you.")
    try:
        USERNAME_FILE.parent.mkdir(parents=True, exist_ok=True)
        USERNAME_FILE.write_text(cleaned, encoding="utf-8")
    except Exception:
        pass
    from memory.memory_manager import update_memory
    update_memory({"identity": {"name": {"value": cleaned}}})
    return cleaned


def sync_stores() -> str:
    """Ensure the username file and memory identity agree.

    Returns the resolved name ("" when no identity exists).
    """
    name = get_display_name()
    if not name:
        return ""
    try:
        USERNAME_FILE.parent.mkdir(parents=True, exist_ok=True)
        if (not USERNAME_FILE.exists()
                or USERNAME_FILE.read_text(encoding="utf-8").strip() != name):
            USERNAME_FILE.write_text(name, encoding="utf-8")
    except Exception:
        pass
    try:
        from memory.memory_manager import load_memory, update_memory
        entry = load_memory().get("identity", {}).get("name")
        mem_name = entry.get("value") if isinstance(entry, dict) else entry
        if _clean(mem_name) != name:
            update_memory({"identity": {"name": {"value": name}}})
    except Exception:
        pass
    return name


def clear_display_name() -> None:
    """Forget the name from every identity store (RESET IDENTITY)."""
    try:
        if USERNAME_FILE.exists():
            USERNAME_FILE.unlink()
    except Exception:
        pass
    try:
        from memory.memory_manager import forget_memory
        forget_memory("name", "identity")
    except Exception:
        pass


def is_guest() -> bool:
    """True when no identity is stored — neutral addressing applies."""
    return not get_display_name()


def profile_snapshot() -> dict:
    """Inspectable identity state for the Memory/Privacy centers."""
    name = get_display_name()
    return {"display_name": name, "guest": not name}
