"""Wake word (§14): offline 'hey jarvis' detection, mic thread, cooldown.

openwakeword runs fully local (~1.3MB model, low CPU). No mic audio is stored
or sent anywhere — 80ms frames are scored and discarded. A custom 'mitsu'
phrase needs trained weights; 'hey jarvis' ships with the engine.
"""
from __future__ import annotations

import shutil
import subprocess
import threading
import time
from pathlib import Path

MODEL_NAME = "hey_jarvis"
THRESHOLD = 0.5
COOLDOWN = 5.0

_model = None
_thread: threading.Thread | None = None
_running = False
_last_fire = 0.0
_on_wake = None


def model_path() -> Path | None:
    import openwakeword  # noqa
    base = Path(openwakeword.__file__).parent / "resources" / "models"
    for f in base.glob("hey_jarvis*.onnx"):
        return f
    return None


def status() -> dict:
    try:
        import openwakeword  # noqa
        ok, mp = True, model_path()
    except ImportError:
        ok, mp = False, None
    from .enroll import enrolled as _enr
    try:
        mitsu = _enr()
    except Exception:
        mitsu = False
    return {
        "available": ok and mp is not None,
        "model": MODEL_NAME,
        "mitsu_word": mitsu,
        "listening": bool(_running),
        "recorder": shutil.which("parecord") or shutil.which("arecord"),
    }


def _get():
    global _model
    if _model is None:
        from openwakeword.model import Model
        mp = model_path()
        if mp is None:
            raise RuntimeError("wake model missing")
        _model = Model(wakeword_model_paths=[str(mp)])
    return _model


def _emit(tag: str) -> None:
    if _on_wake:
        try:
            _on_wake(tag)
        except Exception:
            pass


def _loop():
    import numpy as np
    global _running, _last_fire
    rec = shutil.which("parecord") or shutil.which("arecord")
    cmd = ([rec, "--rate=16000", "--channels=1", "--format=s16le",
            "--file-format=raw", "/dev/stdout"] if rec and rec.endswith("parecord")
           else [rec, "-r", "16000", "-c", "1", "-f", "S16_LE", "-t", "raw", "-"])
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception:
        _running = False
        return
    try:
        model = _get()
        from collections import deque as _dq
        from .enroll import confidence as _conf, enrolled as _enr
        buf = _dq(maxlen=19200)  # 1.2 s rolling window for "mitsu"
        tick = 0
        while _running and proc.stdout is not None:
            raw = proc.stdout.read(2560)  # 80 ms
            if not raw:
                break
            frame = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            try:
                pred = model.predict(frame)
                score = max(pred.values()) if pred else 0.0
            except Exception:
                score = 0.0
            now = time.time()
            if score >= THRESHOLD and now - _last_fire >= COOLDOWN:
                _last_fire = now
                _emit(f"hey_jarvis:{score:.2f}")
            # custom "mitsu" templates, checked ~2x/sec on voiced audio
            buf.extend(frame)
            tick += 1
            if tick % 6 == 0 and len(buf) == buf.maxlen and _enr():
                import numpy as _np
                win = _np.array(buf)
                if float(_np.sqrt((win ** 2).mean())) > 0.02:
                    try:
                        c = _conf(win)
                    except Exception:
                        c = 0.0
                    if c >= 0.55 and now - _last_fire >= COOLDOWN:
                        _last_fire = now
                        _emit(f"mitsu:{c:.2f}")
    finally:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        _running = False


def start(on_wake=None) -> None:
    """Begin background listening. Idempotent. Raises honestly if unavailable."""
    global _thread, _running, _on_wake
    st = status()
    if not st["available"]:
        raise RuntimeError("wake engine unavailable (pip install openwakeword)")
    if not st["recorder"]:
        raise RuntimeError("no mic recorder")
    if _running:
        return
    _on_wake = on_wake
    _running = True
    _thread = threading.Thread(target=_loop, daemon=True)
    _thread.start()


def stop() -> None:
    global _running
    _running = False
