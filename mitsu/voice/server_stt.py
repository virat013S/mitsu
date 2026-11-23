"""Server-side speech recognition: offline Whisper for app + terminal.

faster-whisper decodes in-process; audio decoded with stdlib wave/numpy or
ffmpeg (no PyAV needed). Mic capture via arecord/parecord (no sudo, user-level).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
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
        "source": os.environ.get("MITSU_MIC_SOURCE", "").strip() or _SOURCE.get("name") or "",
        "default_source": _default_source(),
    }


def doctor() -> dict:
    """Mic troubleshooting: real Pulse sources + live levels, hints."""
    import shutil as _sh
    import subprocess as _sp
    rec = _pick_recorder()
    pulse = pulse_sources()
    default = _default_source()
    chosen = mic_source(force=True)
    sources: list[str] = []
    levels: dict[str, int] = {}
    if pulse:
        # probe default + chosen + a few other inputs (explicit button → accuracy)
        probe = [s["name"] for s in pulse if s["name"] in (default, chosen)]
        probe += [s["name"] for s in pulse if not s["monitor"] and s["name"] not in probe]
        clips: dict[str, float] = {}
        for name in probe[:5]:
            st = _probe_stats(name, 0.5)
            levels[name] = st["peak"]
            clips[name] = st["clip"]
        for s in pulse:
            tags = []
            if s["name"] == default:
                tags.append("default")
            if s["name"] == chosen:
                tags.append("USING")
            if s["monitor"]:
                tags.append("monitor")
            peak = levels.get(s["name"])
            lvl = f"peak={peak}" if peak is not None else "peak=?"
            if clips.get(s["name"], 0) >= 8:
                lvl += f" CLIPPING {clips[s['name']]}%"
            sources.append(f'{s["name"]}  {lvl}  [{" ".join(tags)}]'.strip())
    elif _sh.which("arecord"):
        try:
            cp = _sp.run(["arecord", "-l"], capture_output=True, timeout=5, text=True)
            lines = [l.strip() for l in cp.stdout.splitlines() if l.strip()]
            if cp.returncode == 0 and "no soundcards" not in cp.stdout.lower():
                sources = lines[:10]
        except Exception:
            pass
    hints = []
    if chosen in _AUTOFIX["fixed"]:
        hints.append("mic was clipping — Mitsu lowered the capture gain automatically "
                     "(user-level). Raise it in `alsamixer` if speech is too quiet now.")
    if default and chosen and default != chosen:
        hints.append(f"system default mic ({default}) is silent — Mitsu uses {chosen} instead")
    if chosen and clips.get(chosen, 0) >= 8:
        hints.append(f"mic is clipping ({clips[chosen]}% of samples at full scale) — "
                     "lower the hardware gain in `alsamixer`: Capture and the Mic Boost "
                     "control, e.g. `amixer -c 1 sset Capture 35` + "
                     "`amixer -c 1 sset 'Internal Mic Boost' 0`")
    elif chosen and levels.get(chosen, 0) < SIGNAL_PEAK:
        hints.append("no mic is carrying signal right now — speak while testing, "
                     "and check the input isn't muted in `pavucontrol` → Input Devices")
    if pulse and not any(not s["monitor"] for s in pulse):
        hints.append("only monitor/output sources exist — plug in a mic or enable one in pavucontrol")
    if not rec and not _have_sd():
        hints.append("no recorder found: macOS: brew install sox ffmpeg · Windows: pip install sounddevice · Linux: pulseaudio-utils/alsa-utils")
    if not sources:
        hints.append("no sources: is PipeWire running? `systemctl --user status pipewire pipewire-pulse`")
    return {"recorder": rec, "sources": sources, "hints": hints,
            "default_source": default, "chosen_source": chosen,
            "chosen_peak": levels.get(chosen, 0),
            "signal_floor": SIGNAL_PEAK}


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
    """Fixed-length capture.

    Linux/macOS: CLI recorder first — it lets us pin the Pulse source that
    actually has signal (the system default is often a silent Bluetooth mic).
    Windows: sounddevice (no parecord/arecord exists there).
    """
    if _pick_recorder():
        return _record_cli(seconds)
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
    raise RuntimeError("no mic recorder (Linux: pulseaudio-utils/alsa-utils · "
                       "macOS: brew install sox ffmpeg · Windows: pip install sounddevice)")


def _pick_recorder() -> str:
    """Mic recorder per OS: parecord (desktop-Linux PipeWire) → arecord
    (ALSA) → sox `rec` / ffmpeg (macOS only — avfoundation). Windows uses
    sounddevice, never a Linux tool."""
    p = shutil.which("parecord") or shutil.which("arecord")
    if p:
        return p
    if sys.platform == "darwin":
        return shutil.which("rec") or shutil.which("ffmpeg") or ""
    return ""


# --- mic source selection -------------------------------------------------
# A machine can have several inputs and the Pulse *default* is not always a
# live one: a connected Bluetooth headset in A2DP mode exposes a source that
# streams pure silence, so every capture "works" yet whisper hears nothing.
# We probe candidates for actual signal and remember the first live one.
_SOURCE = {"name": "", "peak": 0, "clip": 0.0, "ts": 0.0}
# set by /api/stt/cancel when Mitsu starts speaking — stop the capture at once
_CANCEL = threading.Event()
_PAUSE_UNTIL = 0.0  # while Mitsu speaks: never record our own voice
_AUTOFIX = {"tried": set(), "fixed": set()}
SOURCE_TTL = 180.0     # re-probe at most every 3 min
SIGNAL_PEAK = 400      # int16 peak: noise floor ~100, speech > 1000


def pulse_sources() -> list[dict]:
    """Pulse/PipeWire sources as [{name, monitor}] (empty if pactl absent)."""
    try:
        cp = subprocess.run(["pactl", "list", "sources", "short"],
                            capture_output=True, timeout=5, text=True)
        out = []
        for line in cp.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[1]:
                name = parts[1]
                out.append({"name": name, "monitor": name.endswith(".monitor")})
        return out
    except Exception:
        return []


def _source_alsa_card(name: str) -> str:
    """ALSA card index behind a Pulse source ('' when unknown)."""
    try:
        cp = subprocess.run(["pactl", "list", "sources"],
                            capture_output=True, timeout=5, text=True)
    except Exception:
        return ""
    in_block = False
    for line in cp.stdout.splitlines():
        s = line.strip()
        if s.startswith("Name: "):
            in_block = s[6:].strip() == name
        elif in_block and s.startswith("alsa.card ="):
            return s.split("=", 1)[1].strip().strip('"')
    return ""


def _amixer(card: str, args: list[str]) -> bool:
    exe = shutil.which("amixer")
    if not exe:
        return False
    try:
        cp = subprocess.run([exe, "-c", card, *args],
                            capture_output=True, timeout=5, text=True)
        return cp.returncode == 0
    except Exception:
        return False


def _lower_capture_gain(name: str, level: str = "35") -> bool:
    """Turn down capture gain on a clipping ALSA source — user-level only.

    +60 dB of Capture + Mic Boost turns the noise floor into a square wave;
    whisper hears nothing. We only ever LOWER capture controls (never raise,
    never touch playback) and only when clipping was measured."""
    card = _source_alsa_card(name)
    if not card:
        return False
    changed = False
    try:
        cp = subprocess.run(["amixer", "-c", card, "scontrols"],
                            capture_output=True, timeout=5, text=True)
        for line in cp.stdout.splitlines():
            m = re.search(r"Simple mixer control '([^']+)'", line)
            if m and "boost" in m.group(1).lower():
                if _amixer(card, ["sset", m.group(1), "0"]):
                    changed = True
    except Exception:
        pass
    if _amixer(card, ["sset", "Capture", level]):
        changed = True
    return changed


def _default_source() -> str:
    try:
        cp = subprocess.run(["pactl", "get-default-source"],
                            capture_output=True, timeout=3, text=True)
        return cp.stdout.strip()
    except Exception:
        return ""


def _probe_stats(name: str, seconds: float = 0.7) -> dict:
    """Record a short sample; return {peak, clip} for one Pulse source.

    `clip` is the percentage of samples pinned at full scale. A mic running
    +60 dB of gain produces a huge peak that looks like signal but is pure
    saturation — whisper hears nothing. Selection must not reward that."""
    rec = shutil.which("parecord")
    if not rec or not name:
        return {"peak": 0, "clip": 0.0}
    want = int(16000 * 2 * seconds)
    cmd = [rec, f"--device={name}", "--rate=16000", "--channels=1",
           "--format=s16le", "--file-format=raw", "/dev/stdout"]
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception:
        return 0
    raw = b""
    try:
        import time as _t
        deadline = _t.time() + seconds + 2
        while len(raw) < want and _t.time() < deadline:
            chunk = p.stdout.read(4096) if p.stdout else b""
            if not chunk:
                break
            raw += chunk
    finally:
        try:
            p.kill()
        except ProcessLookupError:
            pass
    if len(raw) < 400:
        return {"peak": 0, "clip": 0.0}
    arr = np.frombuffer(raw[: len(raw) // 2 * 2], dtype=np.int16)
    if not arr.size:
        return {"peak": 0, "clip": 0.0}
    return {"peak": int(np.abs(arr).max()),
            "clip": round(float((np.abs(arr) >= 32000).mean() * 100), 1)}


def _probe_source(name: str, seconds: float = 0.7) -> int:
    return int(_probe_stats(name, seconds)["peak"])


def mic_source(force: bool = False) -> str:
    """Pick a Pulse source that actually carries signal.

    MITSU_MIC_SOURCE env wins (explicit user choice). Otherwise: probe the
    default source first, then every other non-monitor input, and remember
    the first one above the signal floor. Falls back to the default if no
    source is live (the user may just be quiet — recording still works)."""
    env = os.environ.get("MITSU_MIC_SOURCE", "").strip()
    if env:
        return env
    import time as _t
    now = _t.time()
    if not force and _SOURCE["name"] and now - _SOURCE["ts"] < SOURCE_TTL:
        return _SOURCE["name"]
    default = _default_source()
    order: list[str] = []
    if default:
        order.append(default)
    order += [s["name"] for s in pulse_sources()
              if not s["monitor"] and s["name"] != default]
    best = ("", 0, 0.0)
    clipped: list[str] = []
    for name in order:
        st = _probe_stats(name)
        peak, clip = st["peak"], st["clip"]
        if clip >= 8.0:
            clipped.append(name)
            continue
        # clipped audio is not usable signal, no matter how big the peak is
        if peak > best[1]:
            best = (name, peak, clip)
        if peak >= SIGNAL_PEAK:
            _SOURCE.update({"name": name, "peak": peak, "clip": clip, "ts": now})
            return name
    # No clean source: a saturated default is the classic "+60 dB gain" trap.
    # Repair it (lower-only, user-level) and re-probe before giving up.
    if clipped and os.environ.get("MITSU_MIC_AUTOFIX", "1") != "0":
        target = default if default in clipped else clipped[0]
        if target not in _AUTOFIX["tried"]:
            _AUTOFIX["tried"].add(target)
            for level in ("35", "20", "10"):
                if not _lower_capture_gain(target, level):
                    break
                st = _probe_stats(target)
                if st["clip"] < 8.0:
                    _AUTOFIX["fixed"].add(target)
                    print(f"mitsu mic: {target} was clipping — lowered capture gain",
                          flush=True)
                    if st["peak"] > best[1]:
                        best = (target, st["peak"], st["clip"])
                    if st["peak"] >= SIGNAL_PEAK:
                        _SOURCE.update({"name": target, "peak": st["peak"],
                                        "clip": st["clip"], "ts": now})
                        return target
                    break
    fallback = best[0] or default or (order[0] if order else "")
    _SOURCE.update({"name": fallback, "peak": best[1], "clip": best[2], "ts": now})
    return fallback


def source_status(probe: bool = False) -> dict:
    """What the mic path is actually doing (for status/doctor)."""
    default = _default_source()
    chosen = mic_source(force=probe)
    return {"default": default, "chosen": chosen,
            "peak": _SOURCE.get("peak", 0),
            "clip": _SOURCE.get("clip", 0.0),
            "env_override": bool(os.environ.get("MITSU_MIC_SOURCE")),
            "sources": pulse_sources()}


def _record_cmd(rec: str, raw_out=True, seconds: int | None = None,
                device: str = "") -> list[str]:
    """s16le mono 16 kHz RAW to stdout for the given recorder.

    `device` is a Pulse source name (parecord only) — this is what makes the
    mic work when the system default is a silent Bluetooth source."""
    if rec.endswith("parecord"):
        cmd = [rec]
        if device:
            cmd.append(f"--device={device}")
        cmd += ["--rate=16000", "--channels=1", "--format=s16le",
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
    device = mic_source() if rec.endswith("parecord") else ""
    cmd = _record_cmd(rec, seconds=seconds, device=device)
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

    Returns {path, heard_speech, stream_sec}. Raises a clear error if no mic.
    CLI pipe first on Linux/macOS (lets us pin a live Pulse source);
    sounddevice is the Windows path.
    """
    if time.time() < _PAUSE_UNTIL:
        return {"path": "", "heard_speech": False, "stream_sec": 0.0}
    if _pick_recorder():
        return _record_vad_pipe(max_seconds, silence_end, arm_timeout)
    if _have_sd():
        try:
            return _record_vad_sd(max_seconds, silence_end, arm_timeout)
        except Exception:
            pass
    raise RuntimeError("no mic recorder (Linux: pulseaudio-utils/alsa-utils · "
                       "macOS: brew install sox ffmpeg · Windows: pip install sounddevice)")


def _record_vad_sd(max_seconds: int = 30, silence_end: float = 1.6,
                   arm_timeout: float = 10.0) -> dict:
    import time as _t
    import sounddevice as _sd
    from .audio import rms_envelope
    buf = bytearray()
    heard = False
    silent_run = 0.0
    heard_run = 0.0
    started = _t.time()
    _CANCEL.clear()
    with _sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=960) as stream:
        while True:
            if _CANCEL.is_set():
                break
            piece, _overflow = stream.read(960)
            buf += bytes(piece)
            elapsed = _t.time() - started
            if len(buf) >= 16000 and len(buf) % (960 * 8) < 960:
                window = np.frombuffer(bytes(buf[-16000:]), dtype=np.int16).astype(np.float32) / 32768.0
                loud = bool((rms_envelope(window) > 0.03).any())
                if loud:
                    heard_run = min(heard_run + 0.25, 1.0)
                    if heard_run >= 0.5:
                        heard = True
                    if heard:
                        silent_run = 0.0
                else:
                    heard_run = max(heard_run - 0.25, 0.0)
                    if heard:
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
    device = mic_source() if rec.endswith("parecord") else ""
    cmd = _record_cmd(rec, device=device)
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
    _CANCEL.clear()
    try:
        while True:
            if _CANCEL.is_set():
                break
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
                # require ~0.5 s of speech — a single noise spike is not a turn
                if loud:
                    heard_run = min(heard_run + 0.25, 1.0)
                    if heard_run >= 0.5:
                        heard = True
                    if heard:
                        silent_run = 0.0
                else:
                    heard_run = max(heard_run - 0.25, 0.0)
                    if heard:
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
