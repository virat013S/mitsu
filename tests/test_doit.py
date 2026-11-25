import asyncio
import pathlib
import tempfile

import numpy as np

import mitsu.core.paths as C


def _isolate():
    tmp = pathlib.Path(tempfile.mkdtemp())
    C.data_dir = lambda: tmp
    return tmp


def _chirp(f0, f1, dur=0.5, seed=0, sr=16000):
    t = np.arange(int(sr * dur)) / sr
    ph = 2 * np.pi * (f0 * t + (f1 - f0) * t ** 2 / (2 * dur))
    r = np.random.default_rng(seed)
    lead = np.zeros(2000)
    return (np.concatenate([lead, 0.4 * np.sin(ph) + 0.03 * r.standard_normal(len(t))])).astype(np.float32)


def test_mitsu_voiceprint_discriminates():
    _isolate()
    from mitsu.voice import enroll as E
    for s in range(3):
        E.add_sample(_chirp(300, 900, seed=s))
    assert E.enrolled()
    same = E.confidence(_chirp(300, 900, seed=9))
    diff = E.confidence(_chirp(900, 300, seed=9))
    assert same > diff + 0.2, (same, diff)
    E.clear()
    assert not E.enrolled()


def test_remember_forget_commands():
    _isolate()
    from mitsu.brain.chat import reply
    from mitsu.brain.memory.store import MemoryStore
    from mitsu.core.profile import UserProfile

    async def go():
        mem = MemoryStore()
        prof = UserProfile(display_name="T")
        r = await reply("remember the sky is blue", prof, mem)
        assert "remember" in r.text.lower()
        assert any("sky" in f["fact"] for f in mem.long_term)
        r2 = await reply("forget sky", prof, mem)
        assert "forgot 1" in r2.text.lower()
        assert mem.long_term == []
    asyncio.run(go())


def test_base_en_default_and_status():
    from mitsu.voice import server_stt as SST
    assert SST.MODEL == "base.en" or "MITSU_STT_MODEL" in __import__("os").environ
    assert SST.status()["engine"] == "faster-whisper"
