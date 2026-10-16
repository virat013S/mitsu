"""Secure desktop control (§10). Permission-gated; dry-run planning first.

Backends (best available, Wayland-aware):
  launch  → niri spawn / gtk-launch / xdg-open / open (mac) / start (win)
  type/key → wtype (Wayland) / xdotool (X11) / powershell (win) — optional
Everything destructive or session-wide is SENSITIVE and needs a grant token.
`plan()` never touches the system — the UI shows the plan for approval.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from ..permissions import policy

SYS = platform.system().lower()
DE = (os.environ.get("XDG_CURRENT_DESKTOP") or "").lower()
SESSION = (os.environ.get("XDG_SESSION_TYPE") or "").lower()


def capabilities() -> dict:
    yd = shutil.which("ydotool")
    return {
        "os": SYS, "desktop": DE or "unknown", "session": SESSION or "unknown",
        "launch": True,
        "type": bool(shutil.which("wtype") or yd or shutil.which("xdotool")),
        "screenshot": bool(shutil.which("grim") or shutil.which("gnome-screenshot")
                           or shutil.which("scrot") or shutil.which("import")),
        "click": bool(yd),
        "click_note": "" if yd else "click needs ydotool (not installed)",
        "windows": shutil.which("niri") is not None,
        "workspaces": DE in ("kde", "gnome") or "niri" in DE or shutil.which("niri") is not None,
    }


def plan(action: str, target: str = "", **kw) -> dict:
    level = {"launch": policy.CONFIRM, "close": policy.CONFIRM,
             "windows": policy.SAFE, "screenshot": policy.CONFIRM,
             "type": policy.SENSITIVE, "key": policy.SENSITIVE,
             "click": policy.SENSITIVE}.get(action, policy.SENSITIVE)
    return {"action": action, "target": target, "level": level,
            "impact": f"{action}: {target}".strip(),
            "backend": _backend_for(action)}


def _backend_for(action: str) -> str:
    if action == "launch":
        if shutil.which("niri"):
            return "niri spawn"
        return {"linux": "xdg-open/gtk-launch", "darwin": "open",
                "windows": "start"}.get(SYS, "xdg-open")
    if action in ("type", "key"):
        return shutil.which("wtype") or shutil.which("ydotool") or shutil.which("xdotool") or "none"
    return "system"


async def act(action: str, target: str = "", granted_token: str = "", **kw) -> dict:
    p = plan(action, target, **kw)
    if not granted_token or not policy.is_granted(granted_token):
        policy.log("desktop", f"{action} {target} (denied: no grant)", p["level"], granted=False)
        raise PermissionError(f"desktop {action} needs approval ({p['level']}).")
    policy.log("desktop", f"{action} {target}", p["level"])
    if action == "launch":
        return _launch(target)
    if action == "windows":
        return _windows()
    if action == "screenshot":
        return _screenshot()
    if action in ("type", "key", "click", "close"):
        return _automation_stub(action, target, **kw)
    raise ValueError(f"unknown desktop action {action}")


def _windows() -> dict:
    """Read-only window list (SAFE). niri JSON, else honest gap."""
    if shutil.which("niri"):
        try:
            cp = subprocess.run(["niri", "msg", "-j", "windows"], capture_output=True,
                                timeout=10)
            import json as _j
            wins = _j.loads(cp.stdout or "[]")
            return {"ok": True, "via": "niri",
                    "windows": [{"title": w.get("title", ""), "app": w.get("app_id", ""),
                                 "workspace": w.get("workspace_id", "")} for w in wins]}
        except Exception as e:
            return {"ok": False, "error": f"niri query failed: {e}"}
    return {"ok": False, "error": "window listing needs niri (this compositor unsupported)"}


def _screenshot() -> dict:
    """Capture screen to PNG, downscaled. Returns data URL (CONFIRM-gated by caller)."""
    import base64
    import tempfile
    out = tempfile.mktemp(suffix=".png", prefix="mitsu-shot-")
    try:
        if shutil.which("grim"):
            cp = subprocess.run(["grim", out], capture_output=True, timeout=15)
        elif shutil.which("gnome-screenshot"):
            cp = subprocess.run(["gnome-screenshot", "-f", out], capture_output=True, timeout=15)
        elif shutil.which("scrot"):
            cp = subprocess.run(["scrot", out], capture_output=True, timeout=15)
        elif shutil.which("import"):
            cp = subprocess.run(["import", "-window", "root", out], capture_output=True, timeout=15)
        else:
            return {"ok": False, "error": "no screenshot tool (grim/gnome-screenshot/scrot)"}
        if cp.returncode != 0:
            return {"ok": False, "error": "screenshot tool failed (headless?)"}
        from PIL import Image
        im = Image.open(out)
        im.thumbnail((960, 960))
        im.save(out, "PNG")
        data = base64.b64encode(Path(out).read_bytes()).decode()
        return {"ok": True, "data_url": "data:image/png;base64," + data,
                "size": im.size}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        try:
            Path(out).unlink(missing_ok=True)
        except OSError:
            pass


def _launch(target: str) -> dict:
    if shutil.which("niri"):
        subprocess.Popen(["niri", "msg", "action", "spawn", "--", target])
        return {"ok": True, "via": "niri spawn"}
    if SYS == "darwin":
        subprocess.Popen(["open", target])
    elif SYS == "windows":
        subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)
    else:
        opener = shutil.which("gtk-launch") or "xdg-open"
        subprocess.Popen([opener, target])
    return {"ok": True, "via": "os launcher"}


def _automation_stub(action: str, target: str, **kw) -> dict:
    backend = _backend_for(action)
    if backend in (None, "none"):
        return {"ok": False, "error": "no automation backend (install wtype/xdotool); action not taken"}
    if backend == "wtype":
        args = ["wtype"] + ([target] if action == "type" else ["-k", target])
    elif backend == "ydotool":
        args = ["ydotool", "type", target] if action == "type" else ["ydotool", "key", target]
    else:
        args = ["xdotool", "type", target] if action == "type" else ["xdotool", "key", target]
    cp = subprocess.run(args, capture_output=True, timeout=15)
    return {"ok": cp.returncode == 0, "via": backend, "rc": cp.returncode}
