"""SUPER USER access — local admin-grade actions, gate-kept.

Rules carried over from v1, kept as law:
  * Nothing here ever silently runs as root/sudo, nothing prompts from chat.
  * Access requires an explicit pass-phase set by the user at first enable
    (stored only as a peppered SHA-256 digest — never the words themselves).
  * Every command is logged (who/what/when/result-code) to su.log.
  * The user asking in chat counts as the approval gesture for *screen/vision*
    features only; file-destroying and network-wide actions always need the
    passphrase even in superuser mode.
"""
from __future__ import annotations

import hashlib
import os
import secrets as _pys
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..core.eventbus import emit_nowait
from ..core.paths import data_dir
from ..core.store import read_json, write_json

_FILE = data_dir() / "su.json"
LOG = data_dir() / "su.log"

DANGEROUS = ("rm -rf /", "mkfs", "dd if=", ":(){", "shutdown", "reboot",
             "curl | sh", "curl | bash", "chmod -R 777 /", "history -c")


@dataclass
class SUState:
    enabled: bool = False
    digest: str = ""          # sha256(passphrase + pepper)
    pepper: str = ""
    unlocked_until: float = 0.0
    allow_shell: bool = False  # non-destructive shell allowed in unlocked window
    history: list = field(default_factory=list)


def _load() -> SUState:
    d = read_json(_FILE, {}) or {}
    return SUState(**{k: d.get(k, v.default) if hasattr(v, "default") else d.get(k)
                      for k, v in SUState.__dataclass_fields__.items()
                      if k in d})


def _save(s: SUState) -> None:
    write_json(_FILE, {"enabled": s.enabled, "digest": s.digest,
                       "pepper": s.pepper, "unlocked_until": s.unlocked_until,
                       "allow_shell": s.allow_shell, "history": s.history[-200:]})


def setup(passphrase: str, allow_shell: bool = True) -> dict:
    """First enable (or re-set). Requires a non-trivial passphrase."""
    if len(passphrase) < 4:
        return {"ok": False, "error": "pass-phase needs at least 4 chars"}
    s = _load()
    s.enabled = True
    s.pepper = _pys.token_hex(8)
    s.digest = hashlib.sha256((passphrase + s.pepper).encode()).hexdigest()
    s.allow_shell = allow_shell
    s.unlocked_until = 0.0
    _save(s)
    return {"ok": True, "note": "super user armed. Unlock with the pass-phase per window."}


def unlock(passphrase: str, minutes: int = 5) -> dict:
    s = _load()
    if not s.enabled:
        return {"ok": False, "error": "super user is not armed — /su setup <pass-phase> first"}
    if hashlib.sha256((passphrase + s.pepper).encode()).hexdigest() != s.digest:
        return {"ok": False, "error": "wrong pass-phase"}
    minutes = max(1, min(30, minutes))
    s.unlocked_until = time.time() + minutes * 60
    _save(s)
    return {"ok": True, "minutes": minutes}


def disable() -> dict:
    _save(SUState())
    return {"ok": True, "note": "super user disarmed"}


def unlocked() -> bool:
    s = _load()
    return s.enabled and time.time() < s.unlocked_until


def status() -> dict:
    s = _load()
    return {"enabled": s.enabled, "unlocked": unlocked(),
            "allow_shell": s.allow_shell,
            "lock_left_s": max(0, int(s.unlocked_until - time.time()))}


def _log(cmd: str, rc: int, out: str) -> None:
    try:
        with open(LOG, "a") as f:
            f.write(f"{time.strftime('%F %T')} rc={rc} :: {cmd} :: {out[:400]}\n")
    except OSError:
        pass


def run(cmd: str, timeout: int = 30) -> dict:
    """Guarded shell ONLY while unlocked; never sudo; blocks known killers."""
    s = _load()
    low = cmd.strip().lower()
    if not unlocked():
        return {"ok": False, "error": "super user locked — unlock first (/su unlock)"}
    if not s.allow_shell:
        return {"ok": False, "error": "allow_shell is off for this pass-phase"}
    if any(d in low for d in DANGEROUS):
        _log(cmd, -2, "blocked: destructive pattern")
        return {"ok": False, "error": "blocked: destructive pattern (see su.log)"}
    try:
        r = subprocess.run(["/bin/bash", "-lc", cmd], capture_output=True,
                           text=True, timeout=timeout)
        _log(cmd, r.returncode, (r.stdout + r.stderr)[:400])
        out = (r.stdout + r.stderr)[-2000:]
        emit_nowait("su.command", {"cmd": cmd, "rc": r.returncode})
        return {"ok": r.returncode == 0, "rc": r.returncode, "text": out}
    except subprocess.TimeoutExpired:
        _log(cmd, -1, "timeout")
        return {"ok": False, "error": f"timeout after {timeout}s"}
