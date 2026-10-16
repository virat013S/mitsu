"""Central paths + settings. Local-first: everything under data/ unless XDG set."""
from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    base = os.environ.get("MITSU_DATA_DIR")
    if base:
        p = Path(base).expanduser()
    else:
        xdg = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        p = Path(xdg) / "mitsu"
    p.mkdir(parents=True, exist_ok=True)
    return p


def profile_path() -> Path:
    return data_dir() / "profile.json"


def config_path() -> Path:
    return data_dir() / "config.json"


def memory_path() -> Path:
    return data_dir() / "memory.json"


def log_path() -> Path:
    return data_dir() / "mitsu.log"


APP_HOST = os.environ.get("MITSU_HOST", "127.0.0.1")
APP_PORT = int(os.environ.get("MITSU_PORT", "8765"))
