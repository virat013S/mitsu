"""Virtual-desktop / workspace mode (§11): Mitsu works on a dedicated workspace.

KDE/GNOME: real virtual desktops via wm APIs (qdotool/wmctrl where present).
niri: workspaces are first-class (`niri msg action focus-workspace`).
Fallback: dedicated window titled 'Mitsu Work View' (Live Work View in UI).
"""
from __future__ import annotations

import shutil
import subprocess

WORKSPACE_NAME = "Mitsu Work"


def detect() -> dict:
    niri = shutil.which("niri") is not None
    return {
        "niri": niri,
        "kde": shutil.which("qdbus") is not None,
        "wmctrl": shutil.which("wmctrl") is not None,
        "work_view": "Live Work View (in-app activity panel + task logs)",
    }


def focus_work() -> dict:
    """Move the compositor to Mitsu's workspace; safe, no sudo, no grant needed."""
    if shutil.which("niri"):
        try:
            subprocess.run(["niri", "msg", "action", "focus-workspace", WORKSPACE_NAME],
                           capture_output=True, timeout=10)
            return {"ok": True, "via": "niri workspace"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    if shutil.which("qdbus"):  # KDE Plasma
        try:
            cp = subprocess.run(["qdbus", "org.kde.KWin", "/KWin", "setCurrentDesktop", "2"],
                                capture_output=True, timeout=10)
            if cp.returncode == 0:
                return {"ok": True, "via": "KDE virtual desktop 2"}
        except Exception:
            pass
    if shutil.which("gdbus"):  # GNOME Mutter
        try:
            cp = subprocess.run(["gdbus", "call", "--session", "--dest", "org.gnome.Mutter",
                                 "--object-path", "/org/gnome/Mutter",
                                 "--method", "org.gnome.Mutter.DisplayConfig.GetCurrentState"],
                                capture_output=True, timeout=10)
            if cp.returncode == 0:
                return {"ok": True, "via": "GNOME (state queried; switch via Activities)"}
        except Exception:
            pass
    if shutil.which("wmctrl"):  # X11 fallback
        try:
            cp = subprocess.run(["wmctrl", "-s", "1"], capture_output=True, timeout=10)
            if cp.returncode == 0:
                return {"ok": True, "via": "wmctrl desktop 1"}
        except Exception:
            pass
    return {"ok": True, "via": "in-app Live Work View (no compositor switch needed)"}
