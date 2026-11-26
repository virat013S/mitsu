import asyncio
from mitsu.brain.chat import reply
from mitsu.brain.memory.store import MemoryStore
from mitsu.core.profile import UserProfile
from mitsu.providers.base import ChatResult


class Flaky:
    def __init__(self):
        self.calls = 0

    async def chat(self, messages, model, **kw):
        self.calls += 1
        if self.calls == 1:
            return ChatResult(text="   ", model=model, provider="t")
        return ChatResult(text="recovered", model=model, provider="t")


class Dead:
    async def chat(self, messages, model, **kw):
        return ChatResult(text=" ", model=model, provider="t")


def test_empty_reply_retries_slim(monkeypatch):
    import mitsu.brain.chat as C
    flaky = Flaky()
    monkeypatch.setattr(C, "get_provider", lambda name: flaky)
    r = asyncio.run(reply("hi", UserProfile(), MemoryStore(), "t", "m", auto_route=False))
    assert r.text == "recovered" and flaky.calls == 2


def test_empty_reply_never_silent(monkeypatch):
    import mitsu.brain.chat as C
    monkeypatch.setattr(C, "get_provider", lambda name: Dead())
    r = asyncio.run(reply("hi", UserProfile(), MemoryStore(), "t", "m", auto_route=False))
    assert r.text.strip() != ""
