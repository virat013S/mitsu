"""Mic DSP (§13/§14): noise suppression + voice activity detection, numpy-only.

Pipeline: raw mic → spectral gate (noise profile from leading audio) →
VAD trim (adaptive floor, padded) → Whisper. All offline, no extra deps.
"""
from __future__ import annotations

import numpy as np

SR = 16000
FRAME = 480  # 30 ms @ 16k


def _frames(a: np.ndarray, size: int, hop: int) -> np.ndarray:
    n = 1 + max(0, (len(a) - size) // hop)
    shape = (n, size)
    strides = (a.strides[0] * hop, a.strides[0])
    return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides).copy()


def rms_envelope(a: np.ndarray, frame: int = FRAME) -> np.ndarray:
    n = len(a) // frame * frame
    if n == 0:
        return np.array([float(np.sqrt((a ** 2).mean())) if len(a) else 0.0])
    return np.sqrt((a[:n].reshape(-1, frame) ** 2).mean(axis=1))


def snr_db(a: np.ndarray, noise_ms: int = 400, sr: int = SR) -> float:
    if len(a) == 0:
        return 0.0
    prof = a[: max(1, int(noise_ms * sr / 1000))]
    floor = float(np.sqrt((prof ** 2).mean())) + 1e-9
    sig = float(np.sqrt((a ** 2).mean())) + 1e-9
    return round(20 * float(np.log10(sig / floor)), 1)


def spectral_gate(a: np.ndarray, sr: int = SR, noise_ms: int = 400,
                  n_fft: int = 512, over_sub: float = 1.2,
                  floor_db: float = -18.0) -> np.ndarray:
    """Suppress stationary background noise (fans, hum, room tone).

    Noise profile = mean magnitude of the leading `noise_ms` (assumed
    background). Over-subtraction with a floor avoids musical artifacts.
    """
    if len(a) < n_fft * 2:
        return a
    hop = n_fft // 2
    win = np.hanning(n_fft + 1)[:n_fft]
    fr = _frames(a, n_fft, hop) * win
    spec = np.fft.rfft(fr, axis=1)
    mag = np.abs(spec)
    # noise profile from the QUIETEST frames (robust when audio starts
    # with speech, e.g. TTS output or fast talkers — not just leading ms)
    frame_e = np.sqrt((fr ** 2).mean(axis=1)) + 1e-9
    order = np.argsort(frame_e)
    quiet = order[: max(8, len(order) // 4)][:64]
    if len(quiet) < 4:
        quiet = np.arange(min(4, len(mag)))
    profile = mag[quiet].mean(axis=0) + 1e-9
    floor = 10 ** (floor_db / 20.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        gain = np.clip((mag - over_sub * profile) / np.maximum(mag, 1e-9), floor, 1.0)
    # light temporal smoothing against flutter
    gain[1:] = 0.7 * gain[1:] + 0.3 * gain[:-1]
    out_spec = spec * gain
    frames = np.fft.irfft(out_spec, axis=1) * win
    out = np.zeros(len(a) + n_fft)
    wsum = np.zeros(len(a) + n_fft)
    for i in range(frames.shape[0]):
        s = i * hop
        out[s:s + n_fft] += frames[i]
        wsum[s:s + n_fft] += win ** 2
    wsum[wsum < 1e-6] = 1.0
    y = (out[:len(a)] / wsum[:len(a)]).astype(np.float32)
    # fade edges to kill STFT onset/offset transients (else VAD trips on frame 0)
    nf = min(hop * 2, len(y))
    if nf > 1:
        ramp = np.linspace(0.0, 1.0, nf, dtype=np.float32)
        y[:nf] *= ramp
        y[-nf:] *= ramp[::-1]
    return y


def vad_trim(a: np.ndarray, sr: int = SR, pad_ms: int = 250,
             min_speech_ms: int = 300) -> tuple[np.ndarray, float]:
    """Cut leading/trailing silence. Returns (audio, speech_seconds)."""
    if len(a) == 0:
        return a, 0.0
    env = rms_envelope(a)
    # floor from quiet frames, not head — audio may start with speech.
    # (explicit order-statistic: independent of numpy quantile semantics)
    srt = np.sort(env)
    floor = float(srt[: max(4, len(srt) // 4)].mean()) + 1e-4
    # NB: after spectral gating the floor collapses, so the absolute
    # minimum does the real work — quiet room tone stays below it.
    thresh = max(floor * 4.0, 0.03)
    speech = env > thresh
    if speech.sum() < max(1, min_speech_ms // 30):
        return np.zeros(0, dtype=np.float32), 0.0
    frame_ms = 30
    first = int(np.argmax(speech))
    last = int(len(speech) - 1 - np.argmax(speech[::-1]))
    pad = pad_ms // frame_ms
    s = max(0, (first - pad) * FRAME)
    e = min(len(a), (last + 1 + pad) * FRAME)
    seg = a[s:e]
    return seg.astype(np.float32), round(float((last - first + 1) * frame_ms / 1000), 2)


def clean(a: np.ndarray, sr: int = SR) -> dict:
    """Full chain. Returns dict(audio, snr_before, snr_after, speech_sec)."""
    before = snr_db(a, sr=sr)
    gated = spectral_gate(a, sr=sr)
    after = snr_db(gated, sr=sr)
    seg, speech = vad_trim(gated, sr=sr)
    return {"audio": seg, "snr_before": before, "snr_after": after,
            "speech_sec": speech}
