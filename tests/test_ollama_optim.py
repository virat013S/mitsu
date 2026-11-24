"""Ollama tuning: auto uses an installed model; no model name is assumed."""
import asyncio

from mitsu.brain.chat import reply_stream
from mitsu.brain.memory.store import MemoryStore
from mitsu.core.profile import UserProfile
from mitsu.providers.base import ChatMessage
from mitsu.providers.builtin import OllamaProvider
from mitsu.providers.registry import _pick_installed_model


def test_auto_uses_an_installed_model_without_a_baked_default(monkeypatch):
    models = ["mistral:7b", "gemma3:4b", "lfm3-omni:2b"]
    monkeypatch.setattr("mitsu.providers.registry._ollama_models", lambda: models)
    assert _pick_installed_model(models) == "mistral:7b"


def test_auto_avoids_qwen_when_another_model_is_installed(monkeypatch):
    models = ["huihui_ai/qwen3.5-abliterated:4b", "lfm3-omni:latest", "lfm3-omni:2b"]
    monkeypatch.setattr("mitsu.providers.registry._ollama_models", lambda: models)
    assert _pick_installed_model(models) == "lfm3-omni:latest"


def test_ollama_payload_limits_and_thinking():
    p = OllamaProvider("http://127.0.0.1:11434")
    fast = p._payload([ChatMessage(role="user", content="hi")], "lfm3-omni:latest", False, {})
    assert fast["options"]["num_ctx"] == 4096
    assert fast["options"]["num_predict"] == 256
    assert fast["keep_alive"] == "30m"
    assert "think" not in fast

    deep = p._payload([ChatMessage(role="user", content="hi")],
                      "huihui_ai/qwen3.5-abliterated:4b", False,
                      {"num_ctx": 8192, "max_tokens": 512, "keep_alive": "10m"})
    assert deep["options"]["num_ctx"] == 8192
    assert deep["options"]["num_predict"] == 512
    assert deep["keep_alive"] == "10m"
    assert deep["think"] is False


def test_reply_stream_emits_deltas_and_remembers(monkeypatch):
    class P:
        async def stream(self, messages, model, **kw):
            for chunk in ("Two plus two ", "is four."):
                yield chunk

    monkeypatch.setattr("mitsu.brain.chat.get_provider", lambda name: P())
    mem = MemoryStore()
    events = []

    async def run():
        async for ev in reply_stream("what is 2 plus 2?", UserProfile(), mem,
                                     "ollama", "lfm3-omni:latest", auto_route=False):
            events.append(ev)

    asyncio.run(run())
    assert [e["text"] for e in events if e["type"] == "delta"] == [
        "Two plus two ", "is four."]
    final = events[-1]
    assert final["type"] == "message"
    assert final["text"] == "Two plus two is four."
    assert (final["provider"], final["model"]) == ("ollama", "lfm3-omni:latest")
    assert mem.short[-1]["content"] == "Two plus two is four."


def test_resolve_auto_for_non_chat_features(monkeypatch):
    from mitsu.providers import registry as R
    monkeypatch.setattr(R, "smart_default",
                        lambda *a, **k: {"provider": "ollama", "model": "lfm3-omni:latest"})
    monkeypatch.setattr(R, "_ollama_models",
                        lambda: ["lfm3-omni:2b", "lfm3-omni:latest",
                                 "huihui_ai/qwen3.5-abliterated:4b"])
    assert R.resolve_auto("auto", "auto", "look at my screen") == (
        "ollama", "lfm3-omni:2b")
    assert R.resolve_auto("auto", "auto", "research this paper", prefer_deep=True) == (
        "ollama", "lfm3-omni:2b")
    assert R.resolve_auto("openai", "gpt-4o-mini", "hi") == ("openai", "gpt-4o-mini")
