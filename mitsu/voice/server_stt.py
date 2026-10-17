"""Server-side speech recognition (§13/§14): offline Whisper for app + terminal.

faster-whisper decodes in-process; audio decoded with stdlib wave/numpy or
ffmpeg (no PyAV needed). Mic capture via arecord/parecord (no sudo, user-level).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

MODEL = os.environ.get("MITSU_STT_MODEL", "base.en")
_MODEL = None


def status() -> dict:
    return {
        "engine": "faster-whisper",
        "model": MODEL,
        "available": True,
        "recorder": _pick_recorder(),
    }


def doctor() -> dict:
    """Mic troubleshooting (§32): recorders, PipeWire/ALSA sources, hints."""
    import shutil as _sh
    import subprocess as _sp
    rec = _pick_recorder()
    sources: list[str] = []
    via = ""
    if _sh.which("parecord"):
        try:
            cp = _sp.run(["parecord", "--list-sources"], capture_output=True, timeout=5, text=True)
            lines = [l.strip() for l in cp.stdout.splitlines() if l.strip()]
            if cp.returncode == 0 and lines:
                sources, via = lines[:10], "pulse"
        except Exception:
            pass
    if not sources and _sh.which("arecord"):
        try:
            cp = _sp.run(["arecord", "-l"], capture_output=True, timeout=5, text=True)
            lines = [l.strip() for l in cp.stdout.splitlines() if l.strip()]
            if cp.returncode == 0 and "no soundcards" not in cp.stdout.lower():
                sources, via = (lines[:10] or ["(sound system present, no capture lines listed)"],
                                "alsa")
        except Exception:
            pass
    hints = []
    sd_mics = 0
    try:
        import sounddevice as _sd
        sd_mics = sum(1 for d in _sd.query_devices() if d.get("max_input_channels", 0) > 0)
        if sd_mics:
            hints.append(f"sounddevice sees {sd_mics} mic(s) — server-voice input will work")
    except Exception:
        pass
    if not rec and not sd_mics:
        hints.append("no recorder found: macOS: brew install sox ffmpeg · Windows: pip install sounddevice · Linux: pulseaudio-utils/alsa-utils")
    if rec and not sources:
        hints.append("no sources: is PipeWire running? `systemctl --user status pipewire pipewire-pulse`")
        hints.append("check input volume + default source in `pavucontrol` (Input Devices tab, unmute)")
    if via == "pulse" and not any("input" in s.lower() or "mic" in s.lower() for s in sources):
        hints.append("only monitor/output sources seen — plug a mic or enable one in pavucontrol")
    if via == "alsa":
        hints.append("hardware seen via ALSA; for per-app levels use `pavucontrol` (needs pipewire-pulse)")
    return {"recorder": rec, "sources": sources, "hints": hints}


def _model():
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        _MODEL = WhisperModel(MODEL, device="cpu", compute_type="int8")
    return _MODEL


def decode(path: str, target_sr: int = 16000) -> np.ndarray:
    p = str(path)
    if p.lower().endswith(".wav"):
        try:
            with wave.open(p, "rb") as w:
                sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
                raw = w.readframes(n)
            a = np.frombuffer(raw, dtype=np.int16 if sw == 2 else np.int32).astype(np.float32)
            a /= 32768.0 if sw == 2 else 2147483648.0
            if ch > 1:
                a = a.reshape(-1, ch).mean(axis=1)
            if sr != target_sr:
                idx = np.clip(np.linspace(0, len(a), int(len(a) * target_sr / sr)).astype(int),
                              0, len(a) - 1)
                a = a[idx]
            return a
        except wave.Error:
            pass
    ff = shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("unsupported audio format and no ffmpeg to convert it")
    cp = subprocess.run([ff, "-v", "error", "-i", p, "-ac", "1", "-ar", str(target_sr),
                         "-f", "f32le", "-"], capture_output=True, timeout=60)
    if cp.returncode != 0:
        raise RuntimeError("ffmpeg could not decode audio")
    return np.frombuffer(cp.stdout, dtype=np.float32)


def transcribe_file(path: str, language: str = "en") -> dict:
    audio = decode(path)
    if len(audio) < 1600:
        return {"text": "", "language": language, "snr_before": 0.0,
                "snr_after": 0.0, "speech_sec": 0.0}
    from .audio import clean
    c = clean(audio)
    if len(c["audio"]) < 1600:
        return {"text": "", "language": language, "snr_before": c["snr_before"],
                "snr_after": c["snr_after"], "speech_sec": 0.0}
    segs, info = _model().transcribe(c["audio"], language=language, beam_size=1)
    text = "".join(s.text for s in segs).strip()
    return {"text": text, "language": info.language, "snr_before": c["snr_before"],
            "snr_after": c["snr_after"], "speech_sec": c["speech_sec"]}


def _have_sd() -> bool:
    try:
        import sounddevice  # noqa
        return True
    except ImportError:
        return False


def _write_wav(path: str, a: "np.ndarray", sr: int = 16000) -> None:
    import numpy as _np
    pcm = _np.clip(a, -1.0, 1.0)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((pcm * 32767).astype(_np.int16).tobytes())


def record(seconds: int = 5) -> str:
    """Fixed-length capture (sounddevice first → parecord/arecord)."""
    if _have_sd():
        try:
            import sounddevice as _sd
            import numpy as _np
            rec = _sd.rec(int(seconds * 16000), samplerate=16000, channels=1, dtype="int16")
            _sd.wait()
            out = tempfile.mktemp(suffix=".wav", prefix="mitsu-mic-")
            _write_wav(out, rec.flatten().astype(_np.float32) / 32768.0)
            return out
        except Exception:
            pass
    return _record_cli(seconds)


def _pick_recorder() -> str:
    """Mic recorder per OS: parecord (desktop-Linux PipeWire) → arecord
    (ALSA) → sox `rec` (macOS/any) → ffmpeg (macOS/any, avfoundation)."""
    p = shutil.which("parecord") or shutil.which("arecord")
    if p:
        return p
    return shutil.which("rec") or shutil.which("ffmpeg") or ""


def _record_cmd(rec: str, raw_out=True, seconds: int | None = None) -> list[str]:
    """s16le mono 16 kHz RAW to stdout for the given recorder."""
    if rec.endswith("parecord"):
        cmd = [rec, "--rate=16000", "--channels=1", "--format=s16le",
               "--file-format=raw", "/dev/stdout"]
    elif rec.endswith("arecord"):
        cmd = [rec, "-r", "16000", "-c", "1", "-f", "S16_LE", "-t", "raw", "-"]
    elif rec.endswith("ffmpeg"):  # macOS avfoundation / coreaudio
        cmd = ["ffmpeg", "-loglevel", "quiet", "-f", "avfoundation",
               "-i", ":0", "-ac", "1", "-ar", "16000",
               "-f", "s16le", "-c:a", "pcm_s16le", "pipe:1"]
        if seconds:
            cmd = ["ffmpeg", "-loglevel", "quiet", "-t", str(seconds),
                   "-f", "avfoundation", "-i", ":0", "-ac", "1", "-ar", "16000",
                   "-f", "s16le", "-c:a", "pcm_s16le", "pipe:1"]
    else:  # sox `rec` (duration optional — CLI wrappers read a fixed byte
        # count then kill the child, so no trim needed)
        cmd = ["rec", "-q", "-c", "1", "-r", "16000", "-t", "s16", "-"]
    return cmd


def _record_cli(seconds: int = 5) -> str:
    """Fixed-length capture that always terminates.

    parecord/arecord record forever unless told to stop (parecord has no
    duration flag at all), so the old `subprocess.run(cmd, timeout=...)`
    always died in TimeoutExpired and enroll/listen hung. Now: stream RAW
    s16le, read only what we need with a deadline, kill the child, wrap
    the bytes into a WAV ourselves (no header-finalize races).
    """
    import time as _t
    rec = _pick_recorder()
    if not rec:
        raise RuntimeError("no mic recorder (macOS: brew install sox ffmpeg · "
                           "Windows: pip install sounddevice · "
                           "Linux: pulseaudio-utils/alsa-utils)")
    sr, want = 16000, seconds * 16000 * 2  # s16le bytes
    cmd = _record_cmd(rec, seconds=seconds)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception as e:
        raise RuntimeError(f"mic capture failed: {e}")
    raw = b""
    try:
        deadline = _t.time() + seconds + 5
        while len(raw) < want and _t.time() < deadline and proc.stdout is not None:
            try:
                chunk = proc.stdout.read(min(65536, want - len(raw)))
            except Exception:
                break
            if not chunk:
                break
            raw += chunk
    finally:
        try:
            proc.kill()
        except Exception:
            pass
    if len(raw) < 3200:  # <0.1 s — nothing captured
        raise RuntimeError("mic capture failed: no audio (mic muted, busy, or missing)")
    a = np.frombuffer(raw[:want], dtype=np.int16).astype(np.float32) / 32768.0
    out = tempfile.mktemp(suffix=".wav", prefix="mitsu-mic-")
    _write_wav(out, a)
    return out


def record_vad(max_seconds: int = 30, silence_end: float = 1.6,
               arm_timeout: float = 10.0) -> dict:
    """DeepSeek-style listening: stream mic, stop automatically on silence.

    Returns {path, heard_speech, stream_sec}. Raises honestly if no mic.
    sounddevice first (Windows + everywhere), CLI pipe fallback (Linux).
    """
    if _have_sd():
        try:
            return _record_vad_sd(max_seconds, silence_end, arm_timeout)
        except Exception:
            pass
    return _record_vad_pipe(max_seconds, silence_end, arm_timeout)


def _record_vad_sd(max_seconds: int = 30, silence_end: float = 1.6,
                   arm_timeout: float = 10.0) -> dict:
    import time as _t
    import sounddevice as _sd
    from .audio import rms_envelope
    buf = bytearray()
    heard = False
    silent_run = 0.0
    started = _t.time()
    with _sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=960) as stream:
        while True:
            piece, _overflow = stream.read(960)
            buf += bytes(piece)
            elapsed = _t.time() - started
            if len(buf) >= 16000 and len(buf) % (960 * 8) < 960:
                window = np.frombuffer(bytes(buf[-16000:]), dtype=np.int16).astype(np.float32) / 32768.0
                if bool((rms_envelope(window) > 0.03).any()):
                    heard, silent_run = True, 0.0
                elif heard:
                    silent_run += 0.25
                if heard and silent_run >= silence_end:
                    break
            if elapsed >= max_seconds or (not heard and elapsed >= arm_timeout):
                break
    stream_sec = round(_t.time() - started, 1)
    raw = np.frombuffer(bytes(buf), dtype=np.int16).astype(np.float32) / 32768.0
    out = tempfile.mktemp(suffix=".wav", prefix="mitsu-vad-")
    _write_wav(out, raw)
    return {"path": out, "heard_speech": heard, "stream_sec": stream_sec}


def _record_vad_pipe(max_seconds: int = 30, silence_end: float = 1.6,
                     arm_timeout: float = 10.0) -> dict:
    rec = _pick_recorder()
    if not rec:
        raise RuntimeError("no mic recorder (macOS: brew install sox ffmpeg · "
                           "install pulseaudio-utils or alsa-utils on Linux)")
    cmd = _record_cmd(rec)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception:
        return {"path": record(min(max_seconds, 8)), "heard_speech": True, "stream_sec": 0.0}
    if proc.stdout is None:
        return {"path": record(min(max_seconds, 8)), "heard_speech": True, "stream_sec": 0.0}

    from .audio import rms_envelope
    chunk = 960  # 30 ms of s16 mono
    buf = bytearray()
    heard = False
    silent_run = 0.0
    heard_run = 0.0
    started = __import__("time").time()
    try:
        while True:
            piece = proc.stdout.read(chunk)
            if not piece:
                break
            buf += piece
            elapsed = __import__("time").time() - started
            # analyze the newest 0.5 s window every ~0.25 s
            if len(buf) % (chunk * 8) < chunk and len(buf) >= 16000:
                window = np.frombuffer(bytes(buf[-16000:]), dtype=np.int16).astype(np.float32) / 32768.0
                env = rms_envelope(window)
                loud = bool((env > 0.03).any())
                if loud:
                    heard, heard_run, silent_run = True, heard_run + 0.25, 0.0
                elif heard:
                    silent_run += 0.25
                if heard and silent_run >= silence_end:
                    break
            if elapsed >= max_seconds:
                break
            if not heard and elapsed >= arm_timeout:
                break
    finally:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
    stream_sec = round(__import__("time").time() - started, 1)
    raw = np.frombuffer(bytes(buf), dtype=np.int16).astype(np.float32) / 32768.0
    out = tempfile.mktemp(suffix=".wav", prefix="mitsu-vad-")
    _write_wav(out, raw)
    return {"path": out, "heard_speech": heard, "stream_sec": stream_sec}
