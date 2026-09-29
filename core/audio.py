"""Provider-independent audio service: microphones, speakers, STT, playback.

Every model gets the same audio capabilities:
- Microphone (input device) selection, persisted across restarts.
- Speaker (output device) selection, honored by every TTS path.
- Speech-to-text via SpeechRecognition (no API key) for providers
  without native voice input (Ollama/OpenRouter).
- File/PCM playback through the selected speaker (ffmpeg decodes when
  installed; otherwise formats sounddevice reads natively).

A missing microphone/speaker/dependency is reported as a clear status,
never a crash — text mode always keeps working.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

CONFIG_PATH = Path(
    os.environ.get("MITSU_AUDIO_CONFIG", str(Path.home() / ".mitsu" / "audio.json"))
)


def _read_store() -> dict:
    try:
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _write_store(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _sounddevice():
    try:
        import sounddevice as sd
        return sd
    except ImportError:
        return None


def list_devices() -> dict:
    """Enumerate audio devices. Safe without sounddevice installed."""
    sd = _sounddevice()
    if sd is None:
        return {"inputs": [], "outputs": [],
                "error": "sounddevice not installed"}
    try:
        raw = sd.query_devices()
    except Exception as exc:
        return {"inputs": [], "outputs": [], "error": f"probe failed: {exc}"}
    try:
        default_in, default_out = sd.default.device
    except Exception:
        default_in, default_out = None, None
    inputs, outputs = [], []
    for index, dev in enumerate(raw):
        entry = {"index": index, "name": str(dev.get("name", index)),
                 "channels": int(dev.get("max_input_channels", 0)
                                 or dev.get("max_output_channels", 0)),
                 "samplerate": int(float(dev.get("default_samplerate", 0) or 0))}
        if int(dev.get("max_input_channels", 0)) > 0:
            inputs.append({**entry, "default": index == default_in})
        if int(dev.get("max_output_channels", 0)) > 0:
            outputs.append({**entry, "default": index == default_out})
    return {"inputs": inputs, "outputs": outputs}


def get_selection() -> dict:
    """Persisted {input, output} device indices (None = system default)."""
    stored = _read_store()
    sel = {"input": stored.get("input"), "output": stored.get("output")}
    for key in ("input", "output"):
        value = sel[key]
        if value is not None:
            try:
                sel[key] = int(value)
            except (TypeError, ValueError):
                sel[key] = None
    return sel


def selected_input() -> int | None:
    """Selected microphone index, or None for the system default."""
    return get_selection()["input"]


def selected_output() -> int | None:
    """Selected speaker index, or None for the system default."""
    return get_selection()["output"]


def set_selection(input: int | None = None, output: int | None = None) -> dict:
    """Persist microphone/speaker choice. Never touches identity/memory."""
    stored = _read_store()
    if input is not None:
        stored["input"] = int(input)
    if output is not None:
        stored["output"] = int(output)
    _write_store(stored)
    return get_selection()


def clear_selection() -> dict:
    try:
        if CONFIG_PATH.exists():
            CONFIG_PATH.unlink()
    except Exception:
        pass
    return get_selection()


def _decode_to_wav(src: Path) -> Path | None:
    """Decode any ffmpeg-readable audio to wav for sounddevice playback."""
    if shutil.which("ffmpeg") is None:
        return None
    try:
        out = Path(tempfile.mkstemp(suffix=".wav")[1])
        proc = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(src),
             "-ar", "16000", "-ac", "1", str(out)],
            capture_output=True, timeout=60)
        if proc.returncode == 0 and out.exists():
            return out
    except Exception:
        pass
    return None


def play_file(path: str | Path, samplerate: int = 16000) -> dict:
    """Play an audio file through the selected speaker.

    Returns {"ok": True} or {"ok": False, "error": reason}.
    """
    sd = _sounddevice()
    if sd is None:
        return {"ok": False, "error": "sounddevice not installed"}
    src = Path(path)
    if not src.exists():
        return {"ok": False, "error": f"file not found: {src}"}
    wav = None
    try:
        import soundfile as sf
        try:
            data, rate = sf.read(str(src), dtype="int16", always_2d=True)
        except Exception:
            wav = _decode_to_wav(src)
            if wav is None:
                return {"ok": False,
                        "error": "format unreadable (install ffmpeg)"}
            data, rate = sf.read(str(wav), dtype="int16", always_2d=True)
        output = get_selection()["output"]
        with sd.OutputStream(samplerate=int(rate), channels=data.shape[1],
                             dtype="int16", device=output) as stream:
            stream.write(data)
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": f"playback failed: {exc}"}
    finally:
        if wav is not None:
            try:
                wav.unlink()
            except Exception:
                pass


def play_pcm(pcm, samplerate: int = 16000, channels: int = 1) -> dict:
    """Play a numpy int16 PCM array through the selected speaker."""
    sd = _sounddevice()
    if sd is None:
        return {"ok": False, "error": "sounddevice not installed"}
    try:
        import numpy as np
        data = np.asarray(pcm, dtype=np.int16)
        output = get_selection()["output"]
        with sd.OutputStream(samplerate=samplerate, channels=channels,
                             dtype="int16", device=output) as stream:
            stream.write(data.tobytes())
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": f"playback failed: {exc}"}


def listen_once(timeout: float = 8.0, phrase_limit: float = 8.0,
                language: str = "en-US") -> dict:
    """Capture one utterance from the selected microphone and transcribe it.

    Uses SpeechRecognition (no API key; needs internet for Google's free
    endpoint). Returns {"ok": True, "text": ...} or
    {"ok": False, "error": reason} — callers fall back to text input.
    """
    try:
        import speech_recognition as sr
    except ImportError:
        return {"ok": False,
                "error": "SpeechRecognition not installed"}
    sd = _sounddevice()
    if sd is None:
        return {"ok": False, "error": "sounddevice not installed"}
    devices = list_devices()
    if devices.get("error"):
        return {"ok": False, "error": devices["error"]}
    if not devices["inputs"]:
        return {"ok": False, "error": "Microphone permission denied or no input device."}
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    device_index = get_selection()["input"]
    try:
        with sr.Microphone(device_index=device_index) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            audio = recognizer.listen(source, timeout=timeout,
                                      phrase_time_limit=phrase_limit)
    except Exception as exc:
        return {"ok": False, "error": f"microphone unavailable: {exc}"}
    try:
        text = recognizer.recognize_google(audio, language=language)
    except Exception as exc:
        name = type(exc).__name__
        if "UnknownValue" in name:
            return {"ok": False, "error": "could not understand audio"}
        return {"ok": False, "error": f"transcription offline: {exc}"}
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "could not understand audio"}
    return {"ok": True, "text": text}


def describe() -> dict:
    """JSON-safe snapshot for the AUDIO tab, doctor, and capability UI."""
    devices = list_devices()
    sel = get_selection()
    try:
        import speech_recognition  # noqa: F401
        stt = "available (no API key; needs internet)"
    except ImportError:
        stt = "unavailable (install SpeechRecognition)"
    return {"inputs": devices.get("inputs", []),
            "outputs": devices.get("outputs", []),
            "devices_error": devices.get("error", ""),
            "selected_input": sel["input"],
            "selected_output": sel["output"],
            "ffmpeg": shutil.which("ffmpeg") is not None,
            "stt": stt}
