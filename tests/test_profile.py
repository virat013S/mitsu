import json


def test_profile_migrates_onboarding_default_to_auto(tmp_path, monkeypatch):
    from mitsu.core import profile as P
    f = tmp_path / "profile.json"
    f.write_text(json.dumps({"display_name": "Mitsuki",
                             "default_provider": "pollinations",
                             "default_model": "openai-fast"}))
    monkeypatch.setattr(P, "profile_path", lambda: f)
    p = P.UserProfile.load()
    assert p.display_name == "Mitsuki"
    assert p.provider_mode == "auto"
    assert (p.default_provider, p.default_model) == ("auto", "auto")


def test_profile_keeps_explicit_provider_pinned(tmp_path, monkeypatch):
    from mitsu.core import profile as P
    f = tmp_path / "profile.json"
    f.write_text(json.dumps({"default_provider": "ollama",
                             "default_model": "qwen2.5:7b"}))
    monkeypatch.setattr(P, "profile_path", lambda: f)
    p = P.UserProfile.load()
    assert p.provider_mode == "manual"
    assert (p.default_provider, p.default_model) == ("ollama", "qwen2.5:7b")


def test_profile_schema_persists_listening_settings():
    from mitsu.server.api import ProfileIn
    p = ProfileIn(always_listen=False, provider_mode="manual",
                  favorite_apps=["code"], talkativeness="quiet")
    assert p.always_listen is False
    assert p.provider_mode == "manual"
    assert p.favorite_apps == ["code"]
    assert p.talkativeness == "quiet"
