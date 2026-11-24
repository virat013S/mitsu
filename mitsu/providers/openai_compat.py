"""Shared OpenAI-compatible chat client (OpenAI, OpenRouter, custom endpoints)."""
from __future__ import annotations

import httpx

from .base import ChatMessage, ChatResult, ModelInfo


class OpenAICompatProvider:
    name = "openai-compat"

    def __init__(self, base_url: str, api_key: str = "", provider: str = "custom"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._label = provider

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def chat(self, messages: list[ChatMessage], model: str, **kw) -> ChatResult:
        payload = []
        images = kw.get("images") or []
        for m in messages:
            payload.append({"role": m.role, "content": m.content})
        if images:
            for m in reversed(payload):
                if m["role"] == "user":
                    m["content"] = [
                        {"type": "text", "text": m["content"]},
                        *[{"type": "image_url",
                           "image_url": {"url": f"data:image/png;base64,{b}"}} for b in images],
                    ]
                    break
        import asyncio as _a
        tries = 1 if kw.get("no_retry") else 2
        for attempt in range(1, tries + 1):
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": model,
                        "messages": payload,
                        "temperature": kw.get("temperature", 0.7),
                    },
                )
                if r.status_code == 429 and attempt < tries:
                    await _a.sleep(12)
                    continue
                if r.status_code == 429:
                    raise RuntimeError(
                        f"{self._label}: rate-limited (free models throttle) — "
                        f"wait a minute and resend, or switch to Ollama local.")
                r.raise_for_status()
                data = r.json()
                text = data["choices"][0]["message"]["content"]
                return ChatResult(text=text, model=model, provider=self._label)

    async def stream(self, messages: list[ChatMessage], model: str, **kw):
        async with httpx.AsyncClient(timeout=120) as c:
            async with c.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": model,
                    "stream": True,
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                },
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if line.startswith("data: ") and "[DONE]" not in line:
                        import json as _j
                        try:
                            d = _j.loads(line[6:])
                            delta = d["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            continue

    async def list_models(self) -> list[ModelInfo]:
        from .builtin import catalog, merge
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(f"{self.base_url}/models", headers=self._headers())
                r.raise_for_status()
                live = [ModelInfo(id=m["id"], name=m.get("name", m["id"]))
                        for m in r.json().get("data", [])]
                return merge(live, self._label)
        except Exception:
            return catalog(self._label)
