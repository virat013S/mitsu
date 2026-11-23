import numpy as np
from mitsu.voice import wake as W


def test_wake_status_shape():
    s = W.status()
    assert {"available", "model", "listening", "recorder"} <= set(s)


def test_wake_engine_scores_silence_low():
    if not W.status()["available"]:
        return
    m = W._get()
    silence = np.zeros(1280, dtype=np.float32)
    pred = m.predict(silence)
    assert max(pred.values()) < W.THRESHOLD
    W.stop()
