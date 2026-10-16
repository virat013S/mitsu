"""OpenCode Zen / Go provider (§4): OpenAI Responses API, not chat/completions.

Zen and Go expose `{base}/responses` (and `{base}/models` for listing).
Same API key works for both. Zen is pay-per-request ($20 balance);
Go needs a subscription — 403 almost always means no balance/plan.
"""
from __future__ import annotations

import httpx

from .base import ChatMessage, ChatResult, ModelInfo
from .builtin import catalog, merge


class ZenProvider:
    """Responses-API chat for opencode.ai Zen and Go."""

    def __init__(self, base_url: str = "https://opencode.ai/zen/v1",
                 api_key: str = "", label: str = "zen"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._label = label
        self.name = label

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    @staticmethod
    def _input(messages: list[ChatMessage], images: list[str]) -> list[dict]:
        out = []
        for m in messages:
            if m.role == "system":
                out.append({"role": "system",
                            "content": [{"type": "input_text", "text": m.content}]})
                continue
            parts = [{"type": "input_text", "text": m.content}]
            out.append({"role": "user" if m.role == "user" else "assistant",
                        "content": parts})
        if images:
            for m in reversed(out):
                if m["role"] == "user":
                    m["content"].extend(
                        {"type": "input_image",
                         "image_url": f"data:image/png;base64,{b}"} for b in images)
                    break
        return out

    @staticmethod
    def _text(data: dict) -> str:
        if isinstance(data.get("output_text"), str) and data["output_text"]:
            return data["output_text"]
        chunks = []
        for item in data.get("output", []) or []:
            for c in item.get("content", []) or []:
                if isinstance(c.get("text"), str):
                    chunks.append(c["text"])
                elif isinstance(c.get("output_text"), str):
                    chunks.append(c["output_text"])
        return "".join(chunks)

    def _friendly(self, status: int, body: str) -> RuntimeError:
        if status == 401:
            return RuntimeError(f"{self._label}: invalid API key — paste a fresh one "
                                f"(opencode.ai → Zen → API key).")
        if "FreeTierError" in body or "only be used from within OpenCode" in body:
            return RuntimeError(f"{self._label}: free-tier keys only work *inside OpenCode itself* — "
                                f"that lock is on OpenCode's side, not a Mitsu bug. "
                                f"For Mitsu: add $20 balance (opencode.ai/zen), or use "
                                f"OpenRouter free / Ollama local instead.")
        if status == 403:
            return RuntimeError(f"{self._label}: forbidden — no balance/plan on this key. "
                                f"Zen needs a $20 balance, Go needs a subscription "
                                f"(opencode.ai/zen). {body[:120]}")
        if status == 404:
            return RuntimeError(f"{self._label}: model not found — pick one from the "
                                f"model dropdown (live list). {body[:120]}")
        return RuntimeError(f"{self._label} error {status}: {body[:200]}")

    async def chat(self, messages: list[ChatMessage], model: str, **kw) -> ChatResult:
        async with httpx.AsyncClient(timeout=300) as c:
            r = await c.post(
                f"{self.base_url}/responses",
                headers=self._headers(),
                json={"model": model,
                      "input": self._input(messages, kw.get("images") or [])},
            )
            if r.status_code != 200:
                raise self._friendly(r.status_code, r.text)
            return ChatResult(text=self._text(r.json()), model=model,
                              provider=self._label)

    async def stream(self, messages, model, **kw):
        res = await self.chat(messages, model, **kw)
        yield res.text

    async def list_models(self) -> list[ModelInfo]:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(f"{self.base_url}/models", headers=self._headers())
                r.raise_for_status()
                data = r.json()
                items = data.get("data", data if isinstance(data, list) else [])
                live = [ModelInfo(id=m["id"], name=m.get("name", m["id"]))
                        for m in items if isinstance(m, dict) and m.get("id")]
                return merge(live, self._label)
        except Exception:
            return catalog(self._label)
