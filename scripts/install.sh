#!/usr/bin/env bash
# Mitsu installer — system deps, python deps, voices, autostart.
set -e
[ "$(id -u)" = 0 ] && { echo "run as your user (no sudo from inside scripts); it will ask when needed"; exit 1; }

say() { printf "\n\033[1;35m== %s ==\033[0m\n" "$*"; }

ask_sudo() {  # explicit, never stored
  sudo -v
}

say "1/5 system tools"
if command -v pacman >/dev/null 2>&1; then
  ask_sudo
  sudo pacman -S --needed --noconfirm python python-pip ffmpeg pipewire-audio curl git || true
  # desktop control helpers (optional but recommended)
  sudo pacman -S --needed --noconfirm ydotool 2>/dev/null || true
elif command -v apt >/dev/null 2>&1; then
  ask_sudo
  sudo apt-get update -y
  sudo apt-get install -y python3-pip ffmpeg curl git libglib2.0-0 libcairo2-dev || true
elif command -v dnf >/dev/null 2>&1; then
  ask_sudo
  sudo dnf install -y python3-pip ffmpeg curl git || true
fi

say "2/5 python deps (everything)"
pip install --user -e ".[voice,native,tray,dev]" || pip install -e ".[voice,native,tray,dev]"

say "3/5 Piper voices (offline TTS)"
python3 - <<'PY'
from mitsu.voice import server_tts
from pathlib import Path
import shutil, urllib.request, zipfile, tempfile
td = tempfile.mkdtemp()
z = Path(td, "v.zip")
try:
    url = ("https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
           "en/en_US/lessac/medium/en_US-lessac-medium.onnx?download=true")
    seg = Path(td, "en_US-lessac-medium.onnx")
    print("downloading lessac (server voice)…")
    urllib.request.urlretrieve(url, seg)
    vdir = Path(__import__("mitsu.core.paths", fromlist=["data_dir"]).data_dir()) / "voices"
    vdir.mkdir(parents=True, exist_ok=True)
    shutil.copy(seg, vdir / "en_US-lessac-medium.onnx")
    txt = urllib.request.urlopen(
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
        "en/en_US/lessac/medium/en_US-lessac-medium.onnx.json?download=true").read()
    (vdir / "en_US-lessac-medium.onnx.json").write_bytes(txt)
    print("voice installed:", vdir)
except Exception as e:
    print("voice download failed (", e, ") — doctor will re-check; retry install.sh later")
PY

say "4/5 whisper model (offline STT, downloaded on first voice use)"
python3 -c "
from faster_whisper import WhisperModel
print('warming tiny model…'); WhisperModel('tiny', device='cpu', compute_type='int8')
print('whisper ready ( Model)')" 2>/dev/null || echo "(faster-whisper not present — voice extra missing; rerun step 2)"

say "5/5 autostart + doctor"
python3 -m mitsu autostart || true
python3 -m mitsu doctor || true

say "DONE — run:  mitsu"
