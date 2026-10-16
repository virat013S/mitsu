"""Intelligent notifications (§26): OS toast + in-app feed, configurable."""
from __future__ import annotations

import shutil
import subprocess
import time

_feed: list[dict] = []


def notify(title: str, body: str) -> dict:
    item = {"ts": time.time(), "title": title, "body": body}
    _feed.append(item)
    _feed[:] = _feed[-100:]
    try:
        if shutil.which("notify-send"):
            subprocess.Popen(["notify-send", title, body])
        elif shutil.which("osascript"):
            subprocess.Popen(["osascript", "-e", f'display notification "{body}" with title "{title}"'])
    except Exception:
        pass
    return item


def feed(limit: int = 50) -> list[dict]:
    return _feed[-limit:]
