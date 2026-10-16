#!/usr/bin/env python3
"""Mitsu installer — works from ANY shell (bash/zsh/fish/POSIX sh/Windows cmd).

Why python and not a shell script? Because Mitsu itself needs python3 anyway;
requiring a specific shell installs nothing and annoys everyone else.
Run:  python3 scripts/install.py
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def say(*a) -> None:
    print("\n== " + " ".join(a) + " ==", flush=True)


def run(cmd: list[str], **kw) -> bool:
    try:
        r = subprocess.run(cmd, **kw)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError) as e:
        print(f"  ! {e}")
        return False


def ask_sudo() -> bool:
    if os.name != "posix":
        return False
    r = subprocess.run(["sudo", "-v"])  # never captured, never stored
    return r.returncode == 0


def data_dir() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    return (Path(xdg).expanduser() if xdg else Path.home() / ".local/share") / "mitsu"


def install_system_tools() -> None:
    say("1/5 system tools")
    if os.name == "posix":
        pm = shutil.which("pacman") or shutil.which("apt") or shutil.which("dnf")
        if not pm:
            print("  (no pacman/apt/dnf found — install python3, ffmpeg, pipewire-audio manually)")
            return
        name = os.path.basename(pm)
        ask_sudo()
        base = ([pm, "-S", "--needed", "--noconfirm"] if name == "pacman"
                else [pm, "install", "-y"])
        pkgs = {"pacman": ["python", "python-pip", "ffmpeg", "curl", "git", "pipewire-audio"],
                "apt": ["python3-pip", "ffmpeg", "curl", "git", "libglib2.0-0"],
                "dnf": ["python3-pip", "ffmpeg", "curl", "git"]}[name]
        run(base + pkgs)
        if name == "pacman":
            run(base + ["ydotool"])  # optional desktop-click helper
    else:
        print("  (Windows: python/msys/scoop handle these; WebView2 ships with the exe)")


def install_python_deps() -> None:
    say("2/5 python deps (everything)")
    pip = [sys.executable, "-m", "pip", "install", "-e"]
    ok = run(pip + [f"{ROOT}[voice,native,tray,dev]"])
    if not ok:
        print("  ! pip failed — see the message above.")
        print("    (newer distros may need a venv: python3 -m venv ~/.venvs/mitsu"
              " && source ~/.venvs/mitsu/bin/activate, then rerun)")


def install_voice() -> None:
    say("3/5 Piper voice (offline TTS)")
    try:  # pip -e already ran, so the code path exists
        sys.path.insert(0, str(ROOT))
        from mitsu.voice import server_tts  # noqa: F401
        t = tempfile.mkdtemp()
        seg = Path(t, "en_US-lessac-medium.onnx")
        print("  downloading lessac…")
        urllib.request.urlretrieve(
            "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
            "en/en_US/lessac/medium/en_US-lessac-medium.onnx?download=true", seg)
        vdir = data_dir() / "voices"
        vdir.mkdir(parents=True, exist_ok=True)
        shutil.copy(seg, vdir / "en_US-lessac-medium.onnx")
        txt = urllib.request.urlopen(
            "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
            "en/en_US/lessac/medium/en_US-lessac-medium.onnx.json?download=true").read()
        (vdir / "en_US-lessac-medium.onnx.json").write_bytes(txt)
        print(f"  voice installed: {vdir}")
    except Exception as e:
        print(f"  ! voice download skipped ({e}) — mitsu doctor re-checks; rerun this step later")


def warm_whisper() -> None:
    say("4/5 whisper model (offline STT, downloads once)")
    r = subprocess.run(
        [sys.executable, "-c",
         "from faster_whisper import WhisperModel;"
         "WhisperModel('tiny', device='cpu', compute_type='int8'); print('  whisper tiny ready')"],
        capture_output=True, text=True, timeout=600)
    print("  " + (r.stdout.strip().splitlines()[-1] if r.returncode == 0
                  else "! skipped (faster-whisper not installed — step 2 incomplete)"))


def wire_up() -> None:
    say("5/5 autostart + menu shortcuts + doctor")
    subprocess.run([sys.executable, str(ROOT / "mitsu" / "__main__.py"), "autostart"])
    subprocess.run([sys.executable, "-m", "mitsu", "doctor"])


if __name__ == "__main__":
    say(f"Mitsu installer ({platform.system()}) — run from any shell, it is just python")
    install_system_tools()
    install_python_deps()
    install_voice()
    warm_whisper()
    wire_up()
    say("DONE — run:  mitsu")
