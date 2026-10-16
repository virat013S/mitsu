import numpy as np
from mitsu.voice import audio as A

SR = 16000


def _noisy_voice(seed=7):
    rng = np.random.default_rng(seed)
    t = np.arange(SR * 2) / SR
    hum = 0.05 * np.sin(2 * np.pi * 120 * t)
    noise = 0.08 * rng.standard_normal(len(t))
    voice = np.zeros_like(t)
    voice[SR // 2:SR * 3 // 2] = 0.5 * np.sin(2 * np.pi * 220 * t[SR // 2:SR * 3 // 2])
    return (hum + noise + voice).astype(np.float32)


def test_gate_suppresses_background_noise():
    r = A.clean(_noisy_voice())
    assert r["snr_after"] > r["snr_before"] + 3  # meaningful suppression


def test_vad_bounds_and_silence():
    r = A.clean(_noisy_voice())
    assert abs(r["speech_sec"] - 1.0) < 0.4
    rng = np.random.default_rng(1)
    sil = A.clean((0.05 * rng.standard_normal(SR)).astype(np.float32))
    assert sil["speech_sec"] == 0.0


def test_clean_never_crashes_on_edge_input():
    assert A.clean(np.zeros(0, dtype=np.float32))["speech_sec"] == 0.0
    assert A.clean(np.zeros(100, dtype=np.float32))["speech_sec"] == 0.0
