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
    async def go():
        for v in ("lessac", "amy", "ryan"):
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
