"""Atomic JSON persistence — every read/write in one audited place (§ core)."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def read_json(path: Path, default=None):
    """Read a JSON file; missing/corrupt → `default` (never crashes the app)."""
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        return default


def write_json(path: Path, data) -> None:
    """Atomic write: temp file + rename, so a crash never truncates data."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
