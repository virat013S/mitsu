import asyncio
from mitsu.providers.builtin import catalog, merge, CATALOG
from mitsu.providers.base import ModelInfo


def test_every_provider_has_catalog():
    for kind in ("openai", "gemini", "anthropic", "openrouter", "ollama", "zen", "go",
                 "pollinations"):
        assert len(catalog(kind)) >= 2, kind


def test_free_flags():
    from mitsu.providers.builtin import catalog as _c
    assert all(m.free for m in _c("ollama"))
    assert all(m.free for m in _c("pollinations"))
    assert all(m.free for m in _c("openrouter"))
    assert sum(1 for m in _c("zen") if m.free) >= 9
    assert not any(m.free for m in _c("openai"))


def test_smart_default_uses_local_when_healthy(monkeypatch):
    from mitsu.providers import registry as R
    R._SMART_CACHE.clear()
    monkeypatch.setattr(R, "_ollama_healthy", lambda: True)
    assert R.smart_default() == {"provider": "ollama", "model": "gemma3:1b"}


def test_smart_default_falls_to_keyless_cloud(monkeypatch):
    from mitsu.providers import registry as R
    R._SMART_CACHE.clear()
    monkeypatch.setattr(R, "_ollama_healthy", lambda: False)
    assert R.smart_default() == {"provider": "pollinations", "model": "openai"}


def test_smart_default_safe_inside_event_loop():
    """Must not asyncio.run() — chat handlers already own the loop."""
    import asyncio as _a
    from mitsu.providers import registry as R
    R._SMART_CACHE.clear()
    assert _a.run(_resolve())["provider"] in ("ollama", "pollinations")


async def _resolve():
    from mitsu.providers.registry import smart_default
    return smart_default()


def test_pollinations_needs_no_key():
    from mitsu.providers.registry import list_configured
    p = {x["name"]: x for x in list_configured()}["pollinations"]
    assert p["has_key"] is True and p["kind"] == "pollinations"


def test_chat_resolves_auto(monkeypatch):
    import asyncio as _a
    import mitsu.brain.chat as C
    from mitsu.brain.memory.store import MemoryStore
    from mitsu.core.profile import UserProfile
    from mitsu.providers.base import ChatResult

    class P:
        async def chat(self, messages, model, **kw):
            return ChatResult(text="auto-ok", model=model, provider="pollinations")

    monkeypatch.setattr(C, "get_provider", lambda name: P())
    monkeypatch.setattr("mitsu.providers.registry._SMART_CACHE",
                        {"provider": "pollinations", "model": "openai"})
    prof = UserProfile()
    prof.default_provider, prof.default_model = "auto", "auto"
    r = _a.run(C.reply("hi", prof, MemoryStore(), auto_route=False))
    assert r.text == "auto-ok" and r.provider == "pollinations"
    assert "auto default" in r.route_reason


def test_merge_dedupes_and_marks_installed():
    live = [ModelInfo(id="gpt-4o-mini", name="gpt-4o-mini")]
    merged = merge(live, "openai")
    ids = [m.id for m in merged]
    assert ids.count("gpt-4o-mini") == 1
    assert any(not m.installed for m in merged)  # catalog remainder flagged


def test_anthropic_and_ollama_offline_lists():
    async def go():
        from mitsu.providers.builtin import AnthropicProvider, OllamaProvider
        a = await AnthropicProvider("x").list_models()
        assert len(a) >= 3
        o = await OllamaProvider("http://127.0.0.1:1").list_models()  # dead port → catalog
        assert any(m.id == "gemma3:1b" for m in o)
    asyncio.run(go())


def test_openai_compat_falls_back_to_catalog():
    async def go():
        from mitsu.providers.openai_compat import OpenAICompatProvider
        p = OpenAICompatProvider(base_url="http://127.0.0.1:1", provider="openai")
        ms = await p.list_models()
        assert any(m.id == "gpt-4o-mini" for m in ms)
    asyncio.run(go())


def test_probe_hides_locked_and_keyless(monkeypatch):
    """Locked key / missing key → usable False; pollinations stays True."""
    import asyncio as _a
    from mitsu.providers import registry as R
    R._PROBE_CACHE.clear()

    class P:
        async def chat(self, messages, model, **kw):
            raise RuntimeError("zen: free-tier keys only work *inside OpenCode itself*")
    monkeypatch.setattr(R, "get_provider", lambda name: P())
    monkeypatch.setattr("mitsu.providers.secrets.load_key", lambda name: "")

    rows = _a.run(R.usable_providers())
    d = {x["name"]: x["usable"] for x in rows}
    assert d["zen"] is False          # locked key probed live
    assert d["openai"] is False       # no key
    assert d["ollama"] in (True, False)   # health-probed
    assert d["pollinations"] is True  # keyless and verified
    R._PROBE_CACHE.clear()


def test_probe_rate_limited_counts_as_working(monkeypatch):
    import asyncio as _a
    from mitsu.providers import registry as R
    R._PROBE_CACHE.clear()

    class P:
        async def chat(self, messages, model, **kw):
            raise RuntimeError("openrouter: rate-limited (free models throttle)")
    monkeypatch.setattr(R, "get_provider", lambda name: P())
    monkeypatch.setattr("mitsu.providers.secrets.load_key", lambda name: "sk-whatever")
    rows = _a.run(R.usable_providers())
    d = {x["name"]: x["usable"] for x in rows}
    assert d["openrouter"] is True  # valid key, just busy
    R._PROBE_CACHE.clear()


def test_probe_net_flap_keeps_visible(monkeypatch):
    import asyncio as _a
    from mitsu.providers import registry as R
    R._PROBE_CACHE.clear()

    monkeypatch.setattr(R, "configured_providers",
                        lambda: {"openrouter": {"kind": "openrouter"}})
    monkeypatch.setattr(R, "list_configured",
                        lambda: [{"name": "openrouter", "kind": "openrouter",
                                  "base_url": "", "default_model": "",
                                  "has_key": True}])

    class P:
        async def chat(self, messages, model, **kw):
            raise RuntimeError("timeout: read timed out")
    monkeypatch.setattr(R, "get_provider", lambda name: P())
    monkeypatch.setattr("mitsu.providers.secrets.load_key", lambda name: "sk-x")
    rows = _a.run(R.usable_providers())
    d = {x["name"]: x["usable"] for x in rows}
    assert d["openrouter"] is True  # unknown → don't hide a real provider
    R._PROBE_CACHE.clear()
