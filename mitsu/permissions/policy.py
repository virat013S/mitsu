"""Permission levels + history + kill switch (§20)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

SAFE, CONFIRM, SENSITIVE, RESTRICTED = "safe", "confirm", "sensitive", "restricted"

_history: list[dict] = []
_grants: set[str] = set()
_killed: bool = False


def stop_everything() -> None:
    global _killed
    _killed = True
    _grants.clear()
    log("system", "STOP EVERYTHING", "restricted")


def reset_kill() -> None:
    global _killed
    _killed = False


def is_killed() -> bool:
    return _killed


def log(tool: str, action: str, level: str, granted: bool = True) -> None:
    _history.append({"ts": time.time(), "tool": tool, "action": action,
                     "level": level, "granted": granted})


def history(limit: int = 200) -> list[dict]:
    return _history[-limit:]


def classify(action: str) -> str:
    a = action.lower()
    destructive = ("rm ", "delete", "format", "uninstall", "sudo", "pkexec",
                   "passwd", "chmod 777", "mkfs", "dd if=", "> /dev/")
    if any(k in a for k in destructive):
        return SENSITIVE
    if any(k in a for k in ("run ", "exec", "install", "write", "modify", "pip install",
                            "npm install", "systemctl", "flatpak")):
        return CONFIRM
    return SAFE


def is_granted(token: str) -> bool:
    return token in _grants


def grant(token: str) -> None:
    _grants.add(token)


def revoke(token: str) -> None:
    _grants.discard(token)
