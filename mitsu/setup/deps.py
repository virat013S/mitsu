"""One-click dependency installer (§31/§36): everything Mitsu needs, user-level.

Pip packages, Piper voice engine + voices, Whisper model, openwakeword
weights (bundled), Ollama models. The Ollama *binary* needs sudo and goes
through the permission flow (never from chat). Nothing here needs sudo
except that one step.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

PIP_MAP = {  # check-import -> pip name
    "fastapi": "fastapi", "uvicorn": "uvicorn[standard]", "httpx": "httpx",
    "keyring": "keyring", "numpy": "numpy", "PIL": "Pillow",
    "webview": "pywebview", "faster_whisper": "faster-whisper",
    "openwakeword": "openwakeword",
}

VOICE_FILES = {
    "en_US-lessac-medium.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
    "en_US-lessac-medium.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
    "en_US-amy-medium.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx",
    "en_US-amy-medium.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json",
    "en_US-ryan-medium.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx",
    "en_US-ryan-medium.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx.json",
    "en_US-ljspeech-medium.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ljspeech/medium/en_US-ljspeech-medium.onnx",
    "en_US-ljspeech-medium.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ljspeech/medium/en_US-ljspeech-medium.onnx.json",
    "en_US-arctic-medium.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/arctic/medium/en_US-arctic-medium.onnx",
    "en_US-arctic-medium.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/arctic/medium/en_US-arctic-medium.onnx.json",
    "en_US-kristin-medium.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/kristin/medium/en_US-kristin-medium.onnx",
    "en_US-kristin-medium.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/kristin/medium/en_US-kristin-medium.onnx.json",
    "en_US-hfc_male-medium.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_male/medium/en_US-hfc_male-medium.onnx",
    "en_US-hfc_male-medium.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_male/medium/en_US-hfc_male-medium.onnx.json",
    "en_US-joe-medium.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx",
    "en_US-joe-medium.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx.json",
}
PIPER_URLS = {
    "linux": "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz",
    "windows": "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip",
    "macos": "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_macos_x64.tar.gz",
}
DEFAULT_OLLAMA_MODEL = "gemma3:1b"


@dataclass
class Item:
    id: str
    label: str
    size: str
    ok: bool
    hint: str = ""


def _have_import(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def platform() -> dict:
    """OS detection for the installer UI (button labels, hints, methods)."""
    import sys as _sys
    if _sys.platform == "win32":
        return {"os": "windows", "elevate": "uac",
                "elevate_label": "OLLAMA ENGINE (ASKS ADMIN)",
                "mic": "sounddevice (pip, automatic)"}
    if _sys.platform == "darwin":
        return {"os": "macos", "elevate": "none",
                "elevate_label": "OLLAMA ENGINE (VIA BREW)",
                "mic": "sounddevice (pip, automatic)"}
    return {"os": "linux", "elevate": "sudo",
            "elevate_label": "OLLAMA ENGINE (ASKS SUDO)",
            "mic": "parecord/arecord or sounddevice"}


def status() -> list[dict]:
    import shutil
    from ..voice import server_tts as ST
    items: list[dict] = []
    for mod, pip in PIP_MAP.items():
        items.append({"id": f"pip:{pip}", "label": f"Python: {pip}", "size": "~5–150MB",
                      "ok": _have_import(mod), "hint": ""})
    items.append({"id": "piper", "label": "Piper voice engine", "size": "~26MB",
                  "ok": ST.piper_bin() is not None, "hint": ""})
    _seen = set()
    for _vid, (_vf, _vlabel, _vp) in ST.VOICES.items():
        if _vf in _seen:
            continue
        _seen.add(_vf)
        vdir = ST.voices_dir()
        items.append({"id": f"voice:{_vf}", "label": f"Voice {_vlabel}", "size": "~63MB",
                      "ok": (vdir / _vf).exists(), "hint": ""})
    items.append({"id": "whisper", "label": "Whisper base.en (listening)", "size": "~145MB",
                  "ok": _whisper_ready(), "hint": ""})
    import shutil as _sh
    plat = platform()["os"]
    if plat == "windows":
        ollama_hint = "needs one admin (UAC) approval"
    elif plat == "macos":
        ollama_hint = "via Homebrew, no sudo"
    else:
        ollama_hint = "needs sudo"
    items.append({"id": "ollama-bin", "label": "Ollama engine", "size": "~250MB",
                  "ok": _sh.which("ollama") is not None, "hint": ollama_hint})
    items.append({"id": f"ollama-model:{DEFAULT_OLLAMA_MODEL}",
                  "label": f"Ollama model {DEFAULT_OLLAMA_MODEL}", "size": "~815MB",
                  "ok": _ollama_has(DEFAULT_OLLAMA_MODEL), "hint": ""})
    items.append({"id": "ollama-model:moondream",
                  "label": "Ollama vision moondream (sees your screen)", "size": "~1.7GB",
                  "ok": _ollama_has("moondream"), "hint": ""})
    return items


def _whisper_ready() -> bool:
    try:
        from huggingface_hub import scan_cache_dir  # noqa
        from faster_whisper import WhisperModel  # noqa
        import os
        base = os.path.expanduser("~/.cache/huggingface")
        for root, _d, files in os.walk(os.path.join(base, "hub")):
            norm = root.replace("_", "-")
            if any("model.bin" in f for f in files) and ("base-en" in norm or "base.en" in norm):
                return True
        return False
    except Exception:
        return False


def _ollama_has(model: str) -> bool:
    try:
        cp = subprocess.run(["ollama", "list"], capture_output=True, timeout=15, text=True)
        return model.split(":")[0] in cp.stdout
    except Exception:
        return False


def pip_install(packages: list[str]) -> str:
    cp = subprocess.run([sys.executable, "-m", "pip", "install", "--user", *packages],
                        capture_output=True, timeout=1200, text=True)
    if cp.returncode != 0:
        raise RuntimeError("pip failed: " + cp.stderr[-500:])
    return f"installed {', '.join(packages)}"


def fetch_url(url: str, dest: str) -> None:
    import urllib.request
    with urllib.request.urlopen(url, timeout=600) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


def install_piper() -> str:
    import sys as _sys
    from ..voice.server_tts import voices_dir, piper_bin
    plat = "windows" if _sys.platform == "win32" else "macos" if _sys.platform == "darwin" else "linux"
    d = voices_dir()
    if piper_bin() is None:
        arc = d / ("piper.zip" if plat == "windows" else "piper.tar.gz")
        fetch_url(PIPER_URLS[plat], str(arc))
        if plat == "windows":
            import zipfile
            with zipfile.ZipFile(arc) as z:
                z.extractall(d / "piper")
        else:
            import tarfile
            with tarfile.open(arc) as t:
                t.extractall(d, filter="data")
            import os
            for p in (d / "piper").rglob("piper"):
                if p.is_file():
                    os.chmod(p, 0o755)
    got = []
    for fname, url in VOICE_FILES.items():
        if not (d / fname).exists():
            fetch_url(url, str(d / fname))
            got.append(fname.split("-")[1])
    return "piper ready" + (f" (+{', '.join(got)})" if got else "")


def install_whisper() -> str:
    from ..voice.server_stt import MODEL
    from faster_whisper import WhisperModel
    WhisperModel(MODEL, device="cpu", compute_type="int8")
    return f"whisper {MODEL} cached"


async def install_ollama_binary(password_provider=None) -> str:
    """Needs elevation → OS-native prompt (sudo dialog / Windows UAC / brew).

    The password/approval is always collected by the OS or the out-of-band
    sudo flow — never from chat, matching the sudo rule."""
    import sys as _sys
    plat = platform()["os"]
    if plat == "windows":
        return await _install_ollama_windows()
    if plat == "macos":
        return _install_ollama_macos()
    return await _install_ollama_linux(password_provider)


async def _install_ollama_linux(password_provider=None) -> str:
    import tempfile
    from ..permissions.sudo import ensure_elevated, plan_privilege
    tmp = tempfile.mktemp(suffix=".sh", prefix="ollama-install-")
    fetch_url("https://ollama.com/install.sh", tmp)
    plan = plan_privilege(["sh", tmp])
    if plan.mode == "unprivileged":
        cp = subprocess.run(["sh", tmp], capture_output=True, timeout=600, text=True)
    else:
        from ..permissions.sudo import request_sudo, run_elevated
        pw = await request_sudo("install the Ollama engine system-wide", ["sh", tmp],
                                password_provider)
        cp = await run_elevated(["sh", tmp], pw, timeout=600)
        cp = subprocess.CompletedProcess(cp.args, cp.returncode,
                                         (cp.stdout or b"").decode(errors="replace"),
                                         (cp.stderr or b"").decode(errors="replace"))
    import os
    try:
        os.unlink(tmp)
    except OSError:
        pass
    if cp.returncode != 0:
        raise RuntimeError("ollama install failed: " + str(cp.stderr)[-500:])
    return "ollama engine installed"


async def _install_ollama_windows() -> str:
    """Download OllamaSetup.exe and launch it ELEVATED (UAC asks the user)."""
    import ctypes
    import shutil as _sh
    import tempfile as _t
    import time as _time
    from ..core.paths import data_dir
    exe = str(data_dir() / "OllamaSetup.exe")
    if _sh.which("ollama") is None and not __import__("os").path.exists(exe):
        fetch_url("https://ollama.com/download/OllamaSetup.exe", exe)
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, None, None, 1)
    if rc <= 32:
        raise RuntimeError(f"could not launch installer (UAC declined? code {rc})")
    for _i in range(120):  # up to ~10 min for slow installs
        await __import__("asyncio").sleep(5)
        if _sh.which("ollama"):
            return "ollama engine installed (via admin approval)"
    return "installer launched — approve the UAC prompt, then re-check INSTALL EVERYTHING"


def _install_ollama_macos() -> str:
    """Homebrew, no sudo needed."""
    import shutil as _sh
    brew = _sh.which("brew")
    if not brew:
        raise RuntimeError("install Homebrew first (https://brew.sh), then re-run")
    cp = subprocess.run([brew, "install", "--cask", "ollama"],
                        capture_output=True, timeout=900, text=True)
    if cp.returncode != 0:
        raise RuntimeError("brew failed: " + cp.stderr[-500:])
    return "ollama engine installed (via Homebrew)"
