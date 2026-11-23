import asyncio
from mitsu.voice import server_stt as SST
from mitsu.voice import server_tts as STT


def test_stt_status():
    s = SST.status()
    assert s["engine"] == "faster-whisper" and s["recorder"] is not None


def _voices_present() -> bool:
    from mitsu.voice import server_tts as T
    st = T.status()
    return bool(st.get("piper")) and st.get("models_found", 0) > 0


def test_all_server_voices_synthesize():
    if not _voices_present():
        import pytest as _p
        _p.skip("piper voices not installed on this machine yet (install.sh step 3)")
    voices = [v["id"] for v in STT.available_voices() if v["ready"]]
    async def go():
        for v in voices:
            wav = await STT.synthesize("test", 175, v)
            assert wav[:4] == b"RIFF", v
    asyncio.run(go())


def test_stt_roundtrip_on_tts_audio(tmp_path):
    if not _voices_present():
        import pytest as _p
        _p.skip("piper voices not installed on this machine yet (install.sh step 3)")
    async def go():
        return await STT.synthesize("hello mitsu testing", 175, "lessac")
    wav = asyncio.run(go())
    p = tmp_path / "t.wav"
    p.write_bytes(wav)
    res = SST.transcribe_file(str(p))
    assert "hello" in res["text"].lower() or "mitsu" in res["text"].lower() or "testing" in res["text"].lower()


def test_mic_source_skips_silent_default(monkeypatch):
    """A silent Bluetooth default must not win over a live built-in mic."""
    from mitsu.voice import server_stt as S
    S._SOURCE.update({"name": "", "peak": 0, "ts": 0.0})
    monkeypatch.delenv("MITSU_MIC_SOURCE", raising=False)
    monkeypatch.setattr(S, "_default_source", lambda: "bluez_input.silent")
    monkeypatch.setattr(S, "pulse_sources", lambda: [
        {"name": "bluez_input.silent", "monitor": False},
        {"name": "alsa_input.analog", "monitor": False},
        {"name": "alsa_output.monitor", "monitor": True},
    ])
    monkeypatch.setattr(S, "_probe_stats",
                        lambda n, s=0.7: {"peak": {"bluez_input.silent": 117,
                                                   "alsa_input.analog": 32768}.get(n, 0),
                                          "clip": 0.0})
    assert S.mic_source(force=True) == "alsa_input.analog"
    assert S._SOURCE["peak"] == 32768


def test_mic_source_env_override(monkeypatch):
    from mitsu.voice import server_stt as S
    monkeypatch.setenv("MITSU_MIC_SOURCE", "my_explicit_source")
    assert S.mic_source(force=True) == "my_explicit_source"


def test_mic_source_rejects_clipped_input(monkeypatch):
    """+60 dB gain looks like a huge peak but is pure saturation — skip it."""
    from mitsu.voice import server_stt as S
    S._SOURCE.update({"name": "", "peak": 0, "clip": 0.0, "ts": 0.0})
    monkeypatch.delenv("MITSU_MIC_SOURCE", raising=False)
    monkeypatch.setattr(S, "_default_source", lambda: "saturated")
    monkeypatch.setattr(S, "pulse_sources", lambda: [
        {"name": "saturated", "monitor": False},
        {"name": "clean", "monitor": False},
    ])
    monkeypatch.setattr(S, "_probe_stats", lambda n, s=0.7: {
        "saturated": {"peak": 32767, "clip": 35.0},
        "clean": {"peak": 6400, "clip": 0.0},
    }[n])
    assert S.mic_source(force=True) == "clean"
    assert S._SOURCE["clip"] == 0.0


def test_mic_source_autofixes_clipped_default(monkeypatch):
    """A saturated default is repaired (gain lowered) and then selected."""
    from mitsu.voice import server_stt as S
    S._SOURCE.update({"name": "", "peak": 0, "clip": 0.0, "ts": 0.0})
    S._AUTOFIX["tried"].clear(); S._AUTOFIX["fixed"].clear()
    monkeypatch.delenv("MITSU_MIC_SOURCE", raising=False)
    monkeypatch.delenv("MITSU_MIC_AUTOFIX", raising=False)
    monkeypatch.setattr(S, "_default_source", lambda: "saturated")
    monkeypatch.setattr(S, "pulse_sources", lambda: [{"name": "saturated", "monitor": False}])
    state = {"fixed": False}

    def probe(n, s=0.7):
        return ({"peak": 6400, "clip": 0.0} if state["fixed"]
                else {"peak": 32767, "clip": 35.0})

    def lower(n, level="35"):
        state["fixed"] = True
        return True

    monkeypatch.setattr(S, "_probe_stats", probe)
    monkeypatch.setattr(S, "_lower_capture_gain", lower)
    assert S.mic_source(force=True) == "saturated"
    assert state["fixed"] and "saturated" in S._AUTOFIX["fixed"]
    assert S._SOURCE["clip"] == 0.0


def test_mic_source_autofix_can_be_disabled(monkeypatch):
    from mitsu.voice import server_stt as S
    S._SOURCE.update({"name": "", "peak": 0, "clip": 0.0, "ts": 0.0})
    S._AUTOFIX["tried"].clear(); S._AUTOFIX["fixed"].clear()
    monkeypatch.delenv("MITSU_MIC_SOURCE", raising=False)
    monkeypatch.setenv("MITSU_MIC_AUTOFIX", "0")
    monkeypatch.setattr(S, "_default_source", lambda: "saturated")
    monkeypatch.setattr(S, "pulse_sources", lambda: [{"name": "saturated", "monitor": False}])
    monkeypatch.setattr(S, "_probe_stats", lambda n, s=0.7: {"peak": 32767, "clip": 35.0})
    called = {"lower": False}
    monkeypatch.setattr(S, "_lower_capture_gain",
                        lambda n, level="35": called.__setitem__("lower", True) or True)
    assert S.mic_source(force=True) == "saturated"
    assert called["lower"] is False

def test_record_vad_paused_while_speaking(monkeypatch):
    """TTS must mute the mic server-side, even if the frontend races."""
    import time
    from mitsu.voice import server_stt as S
    monkeypatch.setattr(S, "_PAUSE_UNTIL", time.time() + 60)
    assert S.record_vad(1) == {"path": "", "heard_speech": False, "stream_sec": 0.0}
