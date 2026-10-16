from mitsu.setup import deps as D
from mitsu.providers import shop as S
from mitsu.voice import server_tts as ST
from mitsu.pet import window as PW


def test_setup_status_shape():
    items = D.status()
    ids = {i["id"] for i in items}
    assert any(i.startswith("pip:") for i in ids)
    assert "piper" in ids and "whisper" in ids and "ollama-bin" in ids
    assert all({"id", "label", "size", "ok", "hint"} <= set(i) for i in items)
    # this machine: piper + all voices + ollama present
    by_id = {i["id"]: i for i in items}
    assert by_id["piper"]["ok"] is True


def test_shop_search_and_local():
    assert len(S.search("")) >= 15
    assert any("qwen" in m["name"] for m in S.search("code"))
    local = S.local()
    assert any("gemma3" in m["name"] for m in local)


def test_sparkle_voice_listed_and_shifted():
    ids = {v["id"] for v in ST.available_voices()}
    assert {"lessac", "amy", "ryan", "sparkle"} <= ids
    assert ST.pitch_of("sparkle") > 1.0
    assert ST.pitch_of("nope") == 1.0


def test_pet_window_has_characters():
    for c in ("neko", "panda", "kitsune", "hoshi", "kaito"):
        assert c in PW.HTML
    assert "localStorage" in PW.HTML  # persists picker choice
