"""Fixed-length mic capture must always terminate; enroll works on real speech."""
import time

import numpy as np

from mitsu.voice import server_stt as SST

SR = 16000


class _FakeStdout:
    def __init__(self, total: int):
        self.left = total

    def read(self, n: int) -> bytes:
        if self.left <= 0:
            return b""
        n = min(n, self.left)
        self.left -= n
        return bytes(n)


class _FakeProc:
    def __init__(self, total: int):
        self.stdout = _FakeStdout(total)
        self.killed = False

    def kill(self):
        self.killed = True


def test_record_cli_terminates(monkeypatch):
    """parecord-style recorder that never stops on its own must still
    return after ~`seconds` (the old code hung in TimeoutExpired)."""
    monkeypatch.setattr(SST.shutil, "which", lambda c: "/usr/bin/parecord")
    monkeypatch.setattr(SST.subprocess, "Popen",
                        lambda *a, **k: _FakeProc(3 * SR * 2))
    t0 = time.time()
    out = SST._record_cli(3)
    dt = time.time() - t0
    assert dt < 8, f"record hung ({dt:.1f}s)"
    a = SST.decode(out)
    assert len(a) == 3 * SR
    import os
    os.unlink(out)


def test_record_cli_no_audio_raises(monkeypatch):
    monkeypatch.setattr(SST.shutil, "which", lambda c: "/usr/bin/parecord")
    monkeypatch.setattr(SST.subprocess, "Popen",
                        lambda *a, **k: _FakeProc(0))
    try:
        SST._record_cli(2)
    except RuntimeError as e:
        assert "no audio" in str(e)
    else:
        raise AssertionError("expected RuntimeError on empty capture")


def test_record_cli_no_recorder(monkeypatch):
    monkeypatch.setattr(SST.shutil, "which", lambda c: None)
    try:
        SST._record_cli(1)
    except RuntimeError as e:
        assert "no mic recorder" in str(e)
    else:
        raise AssertionError("expected RuntimeError with no recorder")


def _word(seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(int(SR * 0.7)) / SR
    f = 180 + 40 * np.sin(2 * np.pi * 5 * t)  # pitch glide, word-like
    sig = 0.5 * np.sin(2 * np.pi * f * t)
    env = np.ones_like(t)
    env[: SR // 20] = 0.0  # sharp onset + leading silence (like a real word)
    env[-SR // 20:] = 0.0
    word = (sig * env + 0.02 * rng.standard_normal(len(t))).astype(np.float32)
    # real enroll = short word inside a longer recording (silence pads the floor)
    pad = np.zeros(SR, dtype=np.float32)
    return np.concatenate([pad, word, pad])


def test_enroll_self_consistent(tmp_path, monkeypatch):
    """Same voice 3x → ready; same voice matches, silence doesn't."""
    from mitsu.voice import enroll as E
    import mitsu.core.paths as C
    monkeypatch.setattr(C, "data_dir", lambda: tmp_path)
    E.clear()
    for i in range(3):
        r = E.add_sample(_word(seed=i))
    assert r["ready"] is True and r["count"] == 3
    assert E.enrolled() is True
    assert E.confidence(_word(seed=9)) > 0.5
    assert E.confidence(np.zeros(SR, dtype=np.float32)) == 0.0


def test_always_listen_default_on(tmp_path, monkeypatch):
    """JARVIS-style: mic opens on boot unless the user opts out."""
    from mitsu.core.profile import UserProfile
    import mitsu.core.paths as C
    monkeypatch.setattr(C, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(C, "profile_path", lambda: tmp_path / "profile.json")
    assert UserProfile.load().always_listen is True
    p = UserProfile.load()
    p.always_listen = False
    p.save()
    assert UserProfile.load().always_listen is False
