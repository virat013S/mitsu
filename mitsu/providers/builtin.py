"""Concrete provider endpoints (§4). No keys hard-coded; resolved via secrets."""
from __future__ import annotations

import httpx

from .base import ChatMessage, ChatResult, ModelInfo
from .openai_compat import OpenAICompatProvider

ENDPOINTS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "anthropic": "https://api.anthropic.com/v1",
    "zen": "https://opencode.ai/zen/v1",
    "go": "https://opencode.ai/zen/go/v1",
    "pollinations": "https://text.pollinations.ai/openai",
}

# Curated model IDs per provider so every provider has selectable AIs even
# when its list endpoint is unreachable. Live API results (when available)
# are merged over these. Users can always type a custom ID (see UI).
CATALOG = {
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
    "gemini": ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"],
    "anthropic": ["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest",
                  "claude-3-7-sonnet-latest"],
    "openrouter": ["google/gemma-4-26b-a4b-it:free",
                   "google/gemma-4-31b-it:free",
                   "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
                   "nvidia/nemotron-3.5-lightning:free",
                   "nvidia/nemotron-3-super-120b-a12b:free",
                   "nvidia/nemotron-3-ultra-550b-a55b:free",
                   "nvidia/nemotron-3.5-content-safety:free",
                   "cohere/north-mini-code:free",
                   "liquid/lfm-2.5-2.6b:free",
                   "thinkingmachines/inkling-small:free",
                   "thinkingmachines/inkling:free",
                   "poolside/laguna-s-2.1:free",
                   "poolside/laguna-xs-2.1:free",
                   "apodex/apodex-1.1-mini:free",
                   "dots-studio/dots-3-note-preview:free"],
    "zen": ["ling-3.1-flash-free", "mimo-v2.6-flash-free",
            "muse-spark-1.2-contributor-free", "muse-spark-1.3-contributor-free",
            "nemotron-3.5-lightning-free", "jev-1.13-free",
            "step-5-preview-free", "longcat-2.5-preview-free",
            "space-bunny-free",
            "big-pickle", "jev-1.13", "claude-fable-5-1",
            "claude-haiku-4-5", "claude-haiku-5-5", "claude-opus-5-5",
            "claude-opus-5-5-backup", "claude-sonnet-5-5",
            "deepseek-v4.1-flash", "deepseek-v4-pro", "gemini-3.1-pro",
            "gemini-3.5-flash-lite", "gemini-3.8-flash", "glm-5.3",
            "glm-5.3-flash", "gpt-5.3-codex", "gpt-5.3-codex-spark",
            "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.5", "gpt-5.5-pro",
            "gpt-6-astra", "gpt-6.1-sol", "gpt-6-luna", "gpt-5.6-terra",
            "grok-4.7", "grok-build-0.1", "kimi-k2.7-code", "kimi-k3",
            "minimax-m3", "muse-spark-1.3", "mistral-large-4",
            "qwen3.6-plus", "qwen3.8-flash"],
    "go": ["deepseek-v4-flash", "deepseek-v4-flash-vision-exp", "deepseek-flash",
           "deepseek-v4.1-flash", "deepseek-v4-pro", "glm-5.1", "glm-5.2",
           "glm-5.3", "grok-4.6", "grok-4.7",
           "muse-spark-1.2-contributor", "muse-spark-1.3-contributor",
           "glm-5.3-flash", "omen-alpha", "gpt-5.6-luna", "gpt-6-luna",
           "claude-haiku-5-5", "hy3", "hy4-preview", "kimi-k2.6",
           "kimi-k2.7-code", "kimi-k3", "mimo-v2.5", "mimo-v2.6-flash",
           "mimo-v2.5-pro", "mimo-v2.6-pro", "minimax-m2.5", "minimax-m2.7",
           "minimax-m3", "space-bunny", "longcat-2.0",
           "longcat-2.5-preview-free", "step-5-preview-free",
           "qwen3.6-plus", "qwen3.7-max", "qwen3.8-max", "qwen3.8-flash",
           "qwen3.7-plus"],
    "ollama": ["gemma3:1b", "qwen2.5:7b", "llama3.1:8b", "mistral:7b"],
    "pollinations": ["openai", "openai-fast"],
    "custom": [],
}


def _free(i: str) -> bool:
    return i.endswith(":free") or i.endswith("-free")


def catalog(kind: str) -> list[ModelInfo]:
    return [ModelInfo(id=m, name=m, installed=False,
                      # local models and keyless cloud cost nothing
                      free=_free(m) or kind in ("ollama", "pollinations"))
            for m in CATALOG.get(kind, [])]


def merge(live: list[ModelInfo], kind: str) -> list[ModelInfo]:
    for m in live:
        if not m.free and (_free(m.id) or kind in ("ollama", "pollinations")):
            m.free = True
    seen = {m.id for m in live}
    return list(live) + [m for m in catalog(kind) if m.id not in seen]


def make_openai_compat(kind: str, api_key: str = "", base_url: str = "") -> OpenAICompatProvider:
    base = base_url or ENDPOINTS.get(kind, base_url)
    if kind == "anthropic":
        return AnthropicProvider(api_key)
    return OpenAICompatProvider(base_url=base, api_key=api_key, provider=kind)


class AnthropicProvider:
    """Minimal Anthropic Messages API adapter."""

    name = "anthropic"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def chat(self, messages: list[ChatMessage], model: str, **kw) -> ChatResult:
        system = "\n".join(m.content for m in messages if m.role == "system")
        rest = []
        images = kw.get("images") or []
        for m in messages:
            if m.role != "system":
                rest.append({"role": m.role, "content": m.content})
        if images:
            for m in reversed(rest):
                if m["role"] == "user":
                    m["content"] = [
                        {"type": "text", "text": m["content"]},
                        *[{"type": "image",
                           "source": {"type": "base64", "media_type": "image/png",
                                      "data": b}} for b in images],
                    ]
                    break
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={"model": model, "max_tokens": kw.get("max_tokens", 1024),
                      "system": system, "messages": rest},
            )
            r.raise_for_status()
            blocks = r.json().get("content", [])
            text = "".join(b.get("text", "") for b in blocks)
            return ChatResult(text=text, model=model, provider="anthropic")

    async def stream(self, messages, model, **kw):
        res = await self.chat(messages, model, **kw)
        yield res.text

    async def list_models(self) -> list[ModelInfo]:
        return catalog("anthropic")  # no public list endpoint; curated IDs + free entry


class OllamaProvider:
    """First-class local provider (§28). Uses /api/chat + /api/tags."""

    name = "ollama"

    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url.rstrip("/")

    async def chat(self, messages: list[ChatMessage], model: str, **kw) -> ChatResult:
        async with httpx.AsyncClient(timeout=300) as c:
            payload = [{"role": m.role, "content": m.content} for m in messages]
            images = kw.get("images") or []
            if images and payload:
                # attach to the last user message (Ollama vision: gemma3, llava, moondream…)
                for m in reversed(payload):
                    if m["role"] == "user":
                        m["images"] = images
                        break
            r = await c.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "stream": False,
                    "messages": payload,
                },
            )
            r.raise_for_status()
            return ChatResult(text=r.json().get("message", {}).get("content", ""),
                              model=model, provider="ollama")

    async def stream(self, messages: list[ChatMessage], model: str, **kw):
        import json as _j
        async with httpx.AsyncClient(timeout=300) as c:
            async with c.stream("POST", f"{self.base_url}/api/chat",
                                json={"model": model, "stream": True,
                                      "messages": [{"role": m.role, "content": m.content}
                                                   for m in messages]}) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        d = _j.loads(line)
                        chunk = d.get("message", {}).get("content", "")
                        if chunk:
                            yield chunk
                    except Exception:
                        continue

    async def list_models(self) -> list[ModelInfo]:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                live = [ModelInfo(id=m["name"], name=m["name"], free=True)
                        for m in r.json().get("models", [])]
                return merge(live, "ollama")
        except Exception:
            return catalog("ollama")

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False
