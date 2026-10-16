import asyncio
from mitsu.voice import server_tts as ST


def test_voice_status_shape():
    s = ST.status()
    assert {"piper", "espeak", "browser_speech", "voices"} <= set(s)
    assert {v["id"] for v in s["voices"]} >= {"lessac", "amy", "ryan", "ljspeech",
                                              "arctic", "kristin", "dante", "joe",
                                              "sparkle", "mochi"}


def test_synthesize_if_engine():
    if not (ST.piper_bin() and ST.model_path()):
        return  # engine not downloaded here; endpoint reports honestly
    wav = asyncio.run(ST.synthesize("Mitsu voice check", 175))
    assert wav[:4] == b"RIFF" and len(wav) > 10000
