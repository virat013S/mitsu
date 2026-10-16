"""Server-side TTS (§13): any model → Mitsu text → Mitsu voice, offline.

Engine chain: Piper (bundled user-level under data_dir/voices) → espeak-ng
(if present) → unavailable. Renders WAV bytes served by /api/tts so the
native app window (WebKit, no speechSynthesis) can still talk via <audio>.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from ..core.paths import data_dir

VOICES = {
    "lessac": ("en_US-lessac-medium.onnx", "Lessac (default)", 1.0),
    "amy": ("en_US-amy-medium.onnx", "Amy", 1.0),
    "ryan": ("en_US-ryan-medium.onnx", "Ryan", 1.0),
    "ljspeech": ("en_US-ljspeech-medium.onnx", "LJS — storyteller", 1.0),
    "arctic": ("en_US-arctic-medium.onnx", "Arctic", 1.0),
    "kristin": ("en_US-kristin-medium.onnx", "Kristin", 1.0),
    "dante": ("en_US-hfc_male-medium.onnx", "Dante", 1.0),
    "joe": ("en_US-joe-medium.onnx", "Joe", 1.0),
    # DSP-styled anime voicings: same models, pitch-lifted (no extra downloads)
    "sparkle": ("en_US-amy-medium.onnx", "Sparkle ✦ anime", 1.18),
    "mochi": ("en_US-ljspeech-medium.onnx", "Mochi ✦ extra anime", 1.25),
}
DEFAULT_VOICE = "lessac"


def voices_dir() -> Path:
    d = data_dir() / "voices"
    d.mkdir(parents=True, exist_ok=True)
    return d


def piper_bin() -> Path | None:
    cands = [voices_dir() / "piper" / "piper", voices_dir() / "piper",
             voices_dir() / "piper" / "piper.exe"]
    for c in cands:
        if c.is_file():
            return c
    found = shutil.which("piper") or shutil.which("piper.exe")
    return Path(found) if found else None


def model_path(voice: str = DEFAULT_VOICE) -> Path | None:
    fname = VOICES.get(voice, VOICES[DEFAULT_VOICE])[0]
    m = voices_dir() / fname
    return m if m.exists() else None


def pitch_of(voice: str) -> float:
    return VOICES.get(voice, VOICES[DEFAULT_VOICE])[2]


def pitch_shift_wav(wav: bytes, factor: float) -> bytes:
    """Brighter 'anime' lift via resampling (numpy-only). factor > 1 = higher."""
    import io
    import wave as _w
    import numpy as _np
    bio = io.BytesIO(wav)
    with _w.open(bio, "rb") as w:
        n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    a = _np.frombuffer(raw, dtype=_np.int16).astype(_np.float32)
    if ch > 1:
        a = a.reshape(-1, ch)
    idx = _np.clip((_np.arange(int(len(a) / factor)) * factor).astype(int), 0, len(a) - 1)
    b = (a[idx] if ch == 1 else a[idx, :]).astype(_np.int16)
    out = io.BytesIO()
    with _w.open(out, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b.tobytes())
    return out.getvalue()


def available_voices() -> list[dict]:
    return [{"id": vid, "label": label, "ready": (voices_dir() / f).exists()}
            for vid, (f, label, _p) in VOICES.items()]


def status() -> dict:
    vd = voices_dir()
    found = [f for f in {v[0] for v in VOICES.values()} if (vd / f).exists()]
    return {
        "piper": piper_bin() is not None and any(v["ready"] for v in available_voices()),
        "espeak": shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None,
        "browser_speech": True,  # used automatically when available (browser mode)
        "voices": available_voices(),
        "voices_dir": str(vd),
        "piper_bin": str(piper_bin()) if piper_bin() else None,
        "models_found": len(found),
    }


async def synthesize(text: str, rate: int = 175, voice: str = DEFAULT_VOICE) -> bytes:
    text = (text or "").strip()[:800]
    if not text:
        raise ValueError("empty text")
    if voice not in VOICES:
        voice = DEFAULT_VOICE
    if piper_bin() and model_path(voice):
        return await _piper(text, rate, voice)
    esp = shutil.which("espeak-ng") or shutil.which("espeak")
    if esp:
        return await _espeak(esp, text, rate)
    raise RuntimeError("no server TTS engine (Piper voice missing and no espeak)")


async def _piper(text: str, rate: int, voice: str = DEFAULT_VOICE) -> bytes:
    import tempfile
    scale = max(0.5, min(2.0, 175 / max(rate, 60)))
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out = f.name
    proc = await asyncio.create_subprocess_exec(
        str(piper_bin()), "--model", str(model_path(voice)),
        "--length-scale", str(round(scale, 2)),
        "--output_file", out,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    try:
        await asyncio.wait_for(proc.communicate(text.encode()), 30)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        raise TimeoutError("TTS timed out")
    if proc.returncode != 0:
        raise RuntimeError(f"piper failed rc={proc.returncode}")
    data = Path(out).read_bytes()
    Path(out).unlink(missing_ok=True)
    if pitch_of(voice) != 1.0:
        data = pitch_shift_wav(data, pitch_of(voice))
    return data


async def _espeak(bin: str, text: str, rate: int) -> bytes:
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out = f.name
    proc = await asyncio.create_subprocess_exec(
        bin, "-s", str(max(80, min(300, rate))), "-w", out, text,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    await asyncio.wait_for(proc.communicate(), 30)
    data = Path(out).read_bytes()
    Path(out).unlink(missing_ok=True)
    return data
