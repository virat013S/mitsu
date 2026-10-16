"""Secure credential storage (§35). Keyring first, 0600-file fallback."""
from __future__ import annotations

import json
import os
from pathlib import Path

from ..core.paths import data_dir

_FALLBACK = "provider_keys.json"


def _fallback_path() -> Path:
    return data_dir() / _FALLBACK


def save_key(provider: str, api_key: str) -> None:
    try:
        import keyring
        keyring.set_password("mitsu", f"provider:{provider}", api_key)
        return
    except Exception:
        pass
    p = _fallback_path()
    data = {}
    if p.exists():
        try:
            data = json.loads(p.read_text())
        except Exception:
            data = {}
    data[provider] = api_key
    p.write_text(json.dumps(data))
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def load_key(provider: str) -> str:
    try:
        import keyring
        v = keyring.get_password("mitsu", f"provider:{provider}")
        if v:
            return v
    except Exception:
        pass
    p = _fallback_path()
    if p.exists():
        try:
            return json.loads(p.read_text()).get(provider, "")
        except Exception:
            return ""
    return ""


def delete_key(provider: str) -> None:
    try:
        import keyring
        keyring.delete_password("mitsu", f"provider:{provider}")
    except Exception:
        pass
    p = _fallback_path()
    if p.exists():
        try:
            data = json.loads(p.read_text())
            data.pop(provider, None)
            p.write_text(json.dumps(data))
        except Exception:
            pass


def has_key(provider: str) -> bool:
    return bool(load_key(provider))
