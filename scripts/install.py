#!/usr/bin/env python3
"""Mitsu installer — works from ANY shell (bash/zsh/fish/POSIX sh/Windows cmd).

Why python and not a shell script? Because Mitsu itself needs python3 anyway;
requiring a specific shell installs nothing and annoys everyone else.
Run:  python3 scripts/install.py   (or ./install — same thing)
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PIPER_RELEASE = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/"
PIPER_DELTA = {
    ("linux", "x86_64"): ("piper_linux_x86_64.tar.gz", "tar"),
    ("linux", "aarch64"): ("piper_linux_aarch64.tar.gz", "tar"),
    ("windows", "amd64"): ("piper_windows_amd64.zip", "zip"),
}


def say(*a) -> None:
    print("\n== " + " ".join(a) + " ==", flush=True)


def run(cmd: list[str], **kw) -> bool:
    try:
        r = subprocess.run(cmd, **kw)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError) as e:
        print(f"  ! {e}")
        return False


def ask_sudo() -> None:
    if os.name != "posix":
        return
    r = subprocess.run(["sudo", "-v"])  # never captured, never stored
    if r.returncode != 0:
        print("  (no sudo — system packages will be skipped; you can apt/dnf them later)")


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
    say("3/5 Piper voice + engine (offline TTS)")
    try:
        sys.path.insert(0, str(ROOT))
        t = tempfile.mkdtemp()
        seg = Path(t, "en_US-lessac-medium.onnx")
        print("  downloading lessac voice…")
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
        print(f"  ! voice download skipped ({e}) — rerun this step later")
        return
    install_piper_engine()


def install_piper_engine() -> None:
    """The .onnx file is the voice; piper is the ENGINE that speaks it.
    Downloaded into voices/piper/ so status()/synthesize() find it forever,
    inside the app's own data dir (survives pip wipes, no system paths)."""
    vdir = data_dir() / "voices"
    win = platform.system().lower().startswith("win")
    machine = platform.machine().lower()
    arch = ("x86_64" if machine in ("amd64", "x86_64", "")
            else "aarch64" if machine in ("arm64", "aarch64") else machine)
    key = ("windows" if win else "linux", arch)
    entry = PIPER_DELTA.get(key)
    if not entry:
        print(f"  ! no prebuilt piper for {key} — voices will fall back to espeak; report your arch")
        return
    fname, kind = entry
    target = vdir / "piper"
    binp = target / ("piper.exe" if win else "piper")
    if binp.exists():
        print(f"  engine present (skipped): {binp}")
        return
    url = PIPER_RELEASE + fname
    t = tempfile.mkdtemp()
    arch_path = Path(t, fname)
    try:
        print(f"  downloading engine ({fname}, ~20 MB)…")
        urllib.request.urlretrieve(url, arch_path)
        if kind == "zip":
            with zipfile.ZipFile(arch_path) as z:
                z.extractall(target.parent)
        else:
            run(["tar", "-xzf", str(arch_path), "-C", str(vdir)])
        if not binp.exists():  # some archives extract as piper/piper_piper? find it
            for p in vdir.rglob("piper.exe" if win else "piper"):
                if p.is_file() and p.name != fname:
                    target.mkdir(parents=True, exist_ok=True)
                    for item in p.parent.iterdir():
                        if item.is_dir():
                            shutil.move(item, target / item.name)
                        else:
                            shutil.copy2(item, target / item.name)
                    break
        if not win and binp.exists():
            import stat as _s
            binp.chmod(binp.stat().st_mode | _s.S_IEXEC)
        print(f"  engine installed: {binp}" if binp.exists()
              else "  ! engine placed but binary not found — see output above;"
                   " hint: any `piper` binary on PATH also works")
    except Exception as e:
        print(f"  ! engine download skipped ({e}) — rerun this step later;"
              " hint: any `piper` binary on PATH also works")


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
