"""Platform capability detection — the core asks what the machine exposes.

States: SUPPORTED / PARTIAL / REQUIRES_PERMISSION / REQUIRES_DEPENDENCY /
UNAVAILABLE. Detection is layered (native API -> desktop API ->
compositor/window-manager API -> generic fallback -> unavailable) and
never crashes: unsupported features report UNAVAILABLE with a reason.

No hard dependency on any single OS, distro, desktop environment, or
display protocol. All probing functions accept injectable parameters so
tests can simulate Windows/macOS/Linux/X11/Wayland without mocks of
the whole OS.
"""
from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass, field

SUPPORTED = "supported"
PARTIAL = "partial"
REQUIRES_PERMISSION = "requires_permission"
REQUIRES_DEPENDENCY = "requires_dependency"
UNAVAILABLE = "unavailable"


@dataclass
class Capability:
    name: str
    state: str
    reason: str = ""
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"name": self.name, "state": self.state,
                "reason": self.reason, "detail": dict(self.detail)}


def detect_os(system: str | None = None) -> str:
    """Canonical OS id: 'windows' | 'mac' | 'linux' | 'unknown'."""
    system = system if system is not None else platform.system()
    return {"Windows": "windows", "Darwin": "mac",
            "Linux": "linux"}.get(system, "unknown")


def detect_desktop(env: dict | None = None) -> str:
    """Desktop environment id (Linux): kde/gnome/xfce/cinnamon/other/unknown."""
    env = env if env is not None else os.environ
    current = (env.get("XDG_CURRENT_DESKTOP") or "").lower()
    session = (env.get("DESKTOP_SESSION") or "").lower()
    blob = f"{current} {session}"
    for ident in ("kde", "plasma", "gnome", "xfce", "cinnamon",
                  "mate", "lxqt", "lxde", "budgie", "pantheon", "sway",
                  "hyprland", "i3"):
        if ident in blob:
            if ident == "plasma":
                return "kde"
            return ident
    return "unknown" if not blob.strip() else "other"


def detect_display(env: dict | None = None) -> str:
    """Display protocol: 'wayland' | 'x11' | 'unknown' (non-Linux: 'native')."""
    env = env if env is not None else os.environ
    if env.get("WAYLAND_DISPLAY"):
        return "wayland"
    if env.get("DISPLAY"):
        return "x11"
    return "unknown"


def _which(names: list[str], path_env: str | None = None) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    if path_env:
        for directory in path_env.split(os.pathsep):
            for name in names:
                candidate = os.path.join(directory, name)
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
    return None


def detect_capabilities(os_id: str | None = None,
                        env: dict | None = None) -> dict[str, Capability]:
    """Probe platform capabilities. Pure stdlib; safe to call anywhere."""
    os_id = os_id or detect_os()
    env = dict(env) if env is not None else dict(os.environ)
    caps: dict[str, Capability] = {}

    def put(name: str, state: str, reason: str = "", **detail) -> None:
        caps[name] = Capability(name=name, state=state, reason=reason,
                                detail=detail)

    # Filesystem + terminal + processes: stdlib everywhere.
    put("filesystem", SUPPORTED, "Python file APIs")
    put("terminal", SUPPORTED, "subprocess")
    put("process_list", SUPPORTED, "psutil or stdlib")
    put("system_info", SUPPORTED, "platform module")

    # Screenshots: mss is a declared dependency;Pillow for processing.
    try:
        import mss  # noqa: F401
        put("screenshots", SUPPORTED, "mss")
    except ImportError:
        put("screenshots", REQUIRES_DEPENDENCY, "install mss")

    # Clipboard: pyperclip is a declared dependency.
    try:
        import pyperclip  # noqa: F401
        put("clipboard", SUPPORTED, "pyperclip")
    except ImportError:
        put("clipboard", REQUIRES_DEPENDENCY, "install pyperclip")

    # Notifications: platform layered.
    if os_id == "windows":
        put("notifications", SUPPORTED, "Windows toast APIs")
    elif os_id == "mac":
        put("notifications", SUPPORTED, "terminal-notifier or osascript")
    elif _which(["notify-send"]):
        put("notifications", SUPPORTED, "notify-send")
    else:
        put("notifications", PARTIAL, "no notify-send; in-app toasts only")

    # Tray / menu bar: GUI-framework dependent at runtime.
    if os_id == "mac":
        put("tray", PARTIAL, "menu-bar integration via app bundle")
    else:
        put("tray", PARTIAL, "tray where the desktop supports it")

    # Application launch: opener exists on all three desktop OSes.
    put("app_launch", SUPPORTED, "os/start/xdg-open launchers")

    # Window management: layered per OS.
    if os_id == "windows":
        put("window_management", SUPPORTED, "Win32 APIs")
        put("virtual_desktops", SUPPORTED, "Windows virtual desktops")
    elif os_id == "mac":
        put("window_management", PARTIAL, "AppleScript/CGWindow; needs Automation permission")
        put("virtual_desktops", PARTIAL, "Spaces via shortcuts; no public API")
    else:
        display = detect_display(env)
        desktop = detect_desktop(env)
        if _which(["wmctrl", "xdotool"]) and display == "x11":
            put("window_management", SUPPORTED, "wmctrl/xdotool on X11",
                desktop=desktop, display=display)
        elif display == "wayland":
            put("window_management", PARTIAL,
                "Wayland restricts window control; compositor-specific",
                desktop=desktop, display=display)
        else:
            put("window_management", UNAVAILABLE,
                "no supported window-control tool found",
                desktop=desktop, display=display)
        put("virtual_desktops", PARTIAL,
             "workspace control depends on desktop environment",
             desktop=desktop, display=display)

    # Audio devices: sounddevice is a declared dependency.
    try:
        import sounddevice  # noqa: F401
        put("microphone", SUPPORTED, "sounddevice")
        put("speakers", SUPPORTED, "sounddevice")
    except ImportError:
        put("microphone", REQUIRES_DEPENDENCY, "install sounddevice")
        put("speakers", REQUIRES_DEPENDENCY, "install sounddevice")

    # Power/battery: psutil sensors where exposed.
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery is not None:
            put("battery", SUPPORTED, "psutil sensors")
        else:
            put("battery", UNAVAILABLE, "no battery sensor exposed")
    except ImportError:
        put("battery", REQUIRES_DEPENDENCY, "install psutil")
    except Exception as exc:
        put("battery", UNAVAILABLE, f"battery probe failed: {exc}")

    # Network status: stdlib socket probe capability.
    put("network", SUPPORTED, "socket connectivity checks")

    # Startup/background: platform launchers exist; report generic support.
    put("background_execution", SUPPORTED, "thread workers + OS autostart")
    if os_id == "windows":
        put("startup", SUPPORTED, "Startup folder / Task Scheduler")
    elif os_id == "mac":
        put("startup", SUPPORTED, "LaunchAgents")
    else:
        put("startup", SUPPORTED, "autostart desktop entries / systemd user units")

    # Privileged power actions exist but always need approval.
    put("power_actions", PARTIAL, "lock/sleep/restart/shutdown need approval")

    return caps


def capability_summary(caps: dict[str, Capability] | None = None) -> dict:
    """JSON-safe snapshot for the System/Platform centers and --doctor."""
    caps = caps if caps is not None else detect_capabilities()
    return {
        "os": detect_os(),
        "desktop": detect_desktop(),
        "display": detect_display(),
        "capabilities": {name: cap.to_dict() for name, cap in caps.items()},
    }
