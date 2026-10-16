"""Custom 'mitsu' wake word via voice enrollment (§14).

No pretrained 'mitsu' weights exist anywhere, so Mitsu learns YOUR voice:
say 'mitsu' 3 times → MFCC templates stored locally → rolling DTW match.
Runs alongside the 'hey jarvis' engine; either can wake. All offline.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from ..core import paths as _cfg
from ..core.paths import data_dir  # noqa: F401 (kept for external importers)
from .audio import vad_trim

SR = 16000
N_MFCC = 13
N_MELS = 26


def _mel_filters(n_mels: int = N_MELS, n_fft: int = 400, sr: int = SR) -> np.ndarray:
    def hz2mel(h): return 2595 * np.log10(1 + h / 700)
    def mel2hz(m): return 700 * (10 ** (m / 2595) - 1)
    lo, hi = hz2mel(0), hz2mel(sr / 2)
    pts = mel2hz(np.linspace(lo, hi, n_mels + 2))
    bins = np.floor((n_fft + 1) * pts / sr).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(1, n_mels + 1):
        f0, f1, f2 = bins[m - 1], bins[m], bins[m + 1]
        if f1 > f0:
            fb[m - 1, f0:f1] = (np.arange(f0, f1) - f0) / max(f1 - f0, 1)
        if f2 > f1:
            fb[m - 1, f1:f2] = (f2 - np.arange(f1, f2)) / max(f2 - f1, 1)
    return fb


def _dct_matrix(n_in: int, n_out: int) -> np.ndarray:
    k = np.arange(n_out)[:, None]
    n = np.arange(n_in)[None, :]
    return np.cos(np.pi / n_in * (n + 0.5) * k) * np.sqrt(2 / n_in)


_FB = _mel_filters()
_DCT = _dct_matrix(N_MELS, N_MFCC)


def mfcc(a: np.ndarray, sr: int = SR) -> np.ndarray:
    """13-coeff MFCCs, ~10ms hop, per-utterance normalized. numpy-only."""
    x = np.append(a[0], a[1:] - 0.97 * a[:-1]).astype(np.float32)
    n_fft, hop = 400, 160
    n = 1 + max(0, (len(x) - n_fft) // hop)
    if n < 5:
        return np.zeros((5, N_MFCC), dtype=np.float32)
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n)[:, None]
    frames = x[idx] * np.hamming(n_fft)
    mag = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    logmel = np.log((mag @ _FB.T) + 1e-10)
    feats = logmel @ _DCT.T
    feats = feats - feats.mean(axis=0, keepdims=True)
    std = feats.std(axis=0, keepdims=True) + 1e-9
    return (feats / std).astype(np.float32)


def dtw(a: np.ndarray, b: np.ndarray) -> float:
    """Mean-normalized DTW distance between MFCC sequences."""
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return float("inf")
    prev = np.full(m + 1, np.inf)
    prev[0] = 0.0
    for i in range(1, n + 1):
        cur = np.full(m + 1, np.inf)
        d = np.sqrt(((b - a[i - 1]) ** 2).sum(axis=1))
        for j in range(1, m + 1):
            cur[j] = d[j - 1] + min(prev[j], cur[j - 1], prev[j - 1])
        prev = cur
    return float(prev[m] / (n + m))


def _path() -> Path:
    return _cfg.data_dir() / "wake_mitsu.json"


def load() -> dict:
    try:
        return json.loads(_path().read_text())
    except Exception:
        return {"templates": [], "threshold": 0.0}


def save(store: dict) -> None:
    _path().write_text(json.dumps(store))
    try:
        _path().chmod(0o600)
    except OSError:
        pass


def add_sample(audio: np.ndarray) -> dict:
    """Enroll one utterance. Returns {count, ready}."""
    seg, speech = vad_trim(audio)
    if speech < 0.2 or len(seg) < 3200:
        raise ValueError("too short/quiet — say 'mitsu' clearly")
    feats = mfcc(seg[: SR * 2])  # cap 2 s
    store = load()
    store["templates"].append(feats.tolist())
    store["templates"] = store["templates"][-5:]
    if len(store["templates"]) >= 2:
        ts = [np.array(t) for t in store["templates"]]
        ds = [dtw(ts[i], ts[j]) for i in range(len(ts)) for j in range(i + 1, len(ts))]
        store["threshold"] = round(float(max(ds) * 1.6 + 0.15), 3)
    save(store)
    return {"count": len(store["templates"]), "ready": len(store["templates"]) >= 3,
            "threshold": store.get("threshold", 0.0)}


def confidence(audio: np.ndarray) -> float:
    """0..1 that `audio` is the enrolled word. 0 when not enrolled."""
    store = load()
    if len(store["templates"]) < 3:
        return 0.0
    seg, speech = vad_trim(audio)
    if speech < 0.15:
        return 0.0
    q = mfcc(seg[: SR * 2])
    ds = [dtw(q, np.array(t)) for t in store["templates"]]
    best = min(ds)
    thr = store.get("threshold", 1.0) or 1.0
    return round(float(max(0.0, min(1.0, 1.0 - best / (thr * 2.2)))), 3)


def clear() -> None:
    save({"templates": [], "threshold": 0.0})


def enrolled() -> bool:
    return len(load().get("templates", [])) >= 3
