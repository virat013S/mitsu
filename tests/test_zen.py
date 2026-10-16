"""Providers: Zen Responses API shape, friendly errors, live free slugs."""
import asyncio

from mitsu.providers.base import ChatMessage, ChatResult
from mitsu.providers.zen import ZenProvider


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._p = payload
        self.text = str(payload)

    def json(self):
        return self._p


class _Client:
    resp = None

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **kw):
        assert url.endswith("/responses"), url
        return _Client.resp

    async def get(self, url, **kw):
        return _Client.resp


def _run(coro):
    return asyncio.run(coro)


def test_zen_hits_responses_endpoint(monkeypatch):
    import mitsu.providers.zen as Z
    seen = {}

    class C(_Client):
        async def post(self, url, **kw):
            seen["url"] = url
            seen["body"] = kw["json"]
            return _Resp(200, {"output_text": "OK"})

    monkeypatch.setattr(Z, "httpx", type("H", (), {"AsyncClient": C}))
    p = ZenProvider(api_key="k")
    r = _run(p.chat([ChatMessage(role="user", content="hi")], "big-pickle"))
    assert seen["url"] == "https://opencode.ai/zen/v1/responses"
    assert seen["body"]["model"] == "big-pickle"
    assert r.text == "OK" and r.provider == "zen"


def test_zen_parses_content_blocks(monkeypatch):
    import mitsu.providers.zen as Z

    class C(_Client):
        async def post(self, url, **kw):
            return _Resp(200, {"output": [{"content": [{"type": "x", "text": "hel"},
                                                        {"type": "y", "text": "lo"}]}]})

    monkeypatch.setattr(Z, "httpx", type("H", (), {"AsyncClient": C}))
    r = _run(ZenProvider(api_key="k").chat(
        [ChatMessage(role="user", content="hi")], "m"))
    assert r.text == "hello"


def test_zen_friendly_errors(monkeypatch):
    import mitsu.providers.zen as Z

    def err(status, body):
        class C(_Client):
            async def post(self, url, **kw):
                return _Resp(status, body)

        monkeypatch.setattr(Z, "httpx", type("H", (), {"AsyncClient": C}))
        try:
            _run(ZenProvider(api_key="k").chat(
                [ChatMessage(role="user", content="hi")], "m"))
        except RuntimeError as e:
            return str(e)
        raise AssertionError("expected error")

    assert "invalid API key" in err(401, "nope")
    assert "free-tier" in err(403, '{"type":"FreeTierError"}')
    assert "$20" in err(403, "denied")
    assert "live list" in err(404, "gone")


def test_zen_go_bases():
    from mitsu.providers import registry as R
    z = R._zen_provider("zen", api_key="k")
    g = R._zen_provider("go", api_key="k")
    assert z.base_url == "https://opencode.ai/zen/v1"
    assert g.base_url == "https://opencode.ai/zen/go/v1"
    assert isinstance(R.get_provider("zen"), ZenProvider)


def test_openrouter_catalog_all_free():
    from mitsu.providers.builtin import catalog
    ids = [m.id for m in catalog("openrouter")]
    assert len(ids) >= 4
    assert all(i.endswith(":free") for i in ids), ids


def test_free_failover(monkeypatch):
    """Throttled free model → next free model answers, route says so."""
    import asyncio as _a
    import mitsu.brain.chat as C
    from mitsu.brain.memory.store import MemoryStore
    from mitsu.core.profile import UserProfile
    from mitsu.providers.base import ChatResult

    calls = []

    class P:
        async def chat(self, messages, model, **kw):
            calls.append(model)
            if model.endswith("gemma-4-26b-a4b-it:free"):
                raise RuntimeError("openrouter: rate-limited (free models throttle)")
            return ChatResult(text="via " + model, model=model, provider="openrouter")

    monkeypatch.setattr(C, "get_provider", lambda name: P())
    r = _a.run(C.reply("hi", UserProfile(), MemoryStore(),
                       "openrouter", "google/gemma-4-26b-a4b-it:free",
                       auto_route=False))
    assert r.text.startswith("via ") and "gemma-4-26b" not in r.text
    assert "failover" in r.route_reason
    assert calls[0].endswith("gemma-4-26b-a4b-it:free")


def test_no_failover_for_paid(monkeypatch):
    import asyncio as _a
    import mitsu.brain.chat as C
    from mitsu.brain.memory.store import MemoryStore
    from mitsu.core.profile import UserProfile

    class P:
        async def chat(self, messages, model, **kw):
            raise RuntimeError("openrouter: rate-limited (free models throttle)")

    monkeypatch.setattr(C, "get_provider", lambda name: P())
    r = _a.run(C.reply("hi", UserProfile(), MemoryStore(),
                       "openrouter", "openai/gpt-4o", auto_route=False))
    assert "rate-limited" in r.text  # honest error, no wandering off-model


def test_dead_provider_falls_back_and_answers(monkeypatch):
    """zen locked → last-resort fallback via pollinations, honest note."""
    import asyncio as _a
    import mitsu.brain.chat as C
    from mitsu.brain.memory.store import MemoryStore
    from mitsu.core.profile import UserProfile
    from mitsu.providers.base import ChatResult

    monkeypatch.setattr(C, "get_provider", lambda name: _LockedP() if name == "zen"
                        else _OkP())
    monkeypatch.setattr("mitsu.providers.registry._SMART_CACHE",
                        {"provider": "pollinations", "model": "openai"})
    r = _a.run(C.reply("hi", UserProfile(), MemoryStore(),
                       "zen", "big-pickle", auto_route=False))
    assert r.provider == "pollinations" and r.text.startswith("OK")
    assert "fallback → pollinations" in r.route_reason
    assert "didn't answer" in r.text


def test_fallback_skips_same_brain(monkeypatch):
    import asyncio as _a
    import mitsu.brain.chat as C
    from mitsu.brain.memory.store import MemoryStore
    from mitsu.core.profile import UserProfile

    monkeypatch.setattr(C, "get_provider", lambda name: _DeadP())
    monkeypatch.setattr("mitsu.providers.registry._SMART_CACHE",
                        {"provider": "pollinations", "model": "openai"})
    r = _a.run(C.reply("hi", UserProfile(), MemoryStore(),
                       "pollinations", "openai", auto_route=False))
    assert "isn't reachable" in r.text  # dead same-as-default → honest error


class _LockedP:
    async def chat(self, messages, model, **kw):
        raise RuntimeError("zen: free-tier keys only work *inside OpenCode itself*")


class _OkP:
    async def chat(self, messages, model, **kw):
        return ChatResult(text="OK", model=model, provider="pollinations")


class _DeadP:
    async def chat(self, messages, model, **kw):
        raise RuntimeError("boom")
