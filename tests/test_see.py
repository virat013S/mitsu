"""Voice-OS eyes: visual-question routing + vision plumbing (all stubbed)."""
import asyncio

from mitsu.desktop import see as S
from mitsu.providers.base import ChatResult


def test_visual_intent():
    for q in ["what is this?", "hey mitsu, what's on my screen",
              "describe my screen", "what am I looking at",
              "read my screen please", "what is open on my screen?"]:
        assert S.is_visual_question(q), q
    for q in ["what is the time?", "what is this song?", "tell me about this",
              "what is 2+2?", "what is this task about"]:
        assert not S.is_visual_question(q), q


def test_describe_happy_path(monkeypatch):
    import mitsu.desktop.see as SM
    monkeypatch.setattr(SM, "capture_b64", lambda max_side=1280: "B64IMG")

    class P:
        def __init__(self):
            self.got = None

        async def chat(self, messages, model, **kw):
            self.got = (model, kw.get("images"))
            return ChatResult(text="A terminal.", model=model, provider="t")

    p = P()
    import mitsu.providers.registry as R
    monkeypatch.setattr(R, "get_provider", lambda name: p)
    monkeypatch.setattr(SM, "pick_vision_model",
                        lambda prov, model: ("ollama", "moondream", "(seeing via moondream)"))
    r = asyncio.run(SM.describe("What is this?", "ollama", "gemma3:1b"))
    assert r["text"] == "A terminal. (seeing via moondream)"
    assert r["via"] == "ollama/moondream"
    assert p.got == ("moondream", ["B64IMG"])


def test_describe_no_vision_model_honest(monkeypatch):
    import mitsu.desktop.see as SM
    monkeypatch.setattr(SM, "capture_b64", lambda max_side=1280: "B64IMG")

    class P:
        async def chat(self, messages, model, **kw):
            raise RuntimeError("400 model does not support images")

    import mitsu.providers.registry as R
    monkeypatch.setattr(R, "get_provider", lambda name: P())
    monkeypatch.setattr(SM, "pick_vision_model", lambda prov, model: (prov, model, ""))
    try:
        asyncio.run(SM.describe("What is this?", "ollama", "tiny-text"))
    except RuntimeError as e:
        assert "moondream" in str(e)
    else:
        raise AssertionError("expected honest no-vision error")


def test_describe_screenshot_failure_honest(monkeypatch):
    import mitsu.desktop.see as SM
    monkeypatch.setattr(SM, "capture_b64", _boom)
    try:
        asyncio.run(SM.describe("What is this?", "ollama", "gemma3:1b"))
    except RuntimeError as e:
        assert "headless" in str(e)
    else:
        raise AssertionError("expected screenshot error")


def _boom(max_side=1280):
    raise RuntimeError("no screenshot tool (headless?)")


def test_chat_routes_visual(monkeypatch):
    import mitsu.brain.chat as C
    from mitsu.brain.memory.store import MemoryStore
    from mitsu.core.profile import UserProfile

    async def fake_describe(q, prov, model):
        return {"text": "Your editor.", "via": "ollama/moondream"}

    import mitsu.desktop.see as SM
    monkeypatch.setattr(SM, "describe", fake_describe)
    r = asyncio.run(C.reply("mitsu, what is this?", UserProfile(),
                            MemoryStore(), "ollama", "gemma3:1b", auto_route=False))
    assert r.text == "Your editor."
    assert "screen" in r.route_reason


def test_ollama_attaches_images():
    import inspect
    from mitsu.providers.builtin import OllamaProvider
    src = inspect.getsource(OllamaProvider.chat)
    assert '"images"' in src or "'images'" in src
