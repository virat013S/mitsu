"""Voice-OS style screen awareness: 'what is this?' answered from a screenshot.

Flow: explicit user question → capture screen → vision-capable model reads
it → spoken + shown answer. The question itself is the approval (same rule
as automations); the capture is logged like any CONFIRM-level desktop action.
No screenshots are stored — base64 lives only for the single request.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path

# explicit visual questions — nothing fires without the user asking
VISUAL_PATTERNS = [
    r"what(?:'s| is) this(?=\?|$| on| here| open| behind| showing)",
    r"what(?:'s| is) (?:on my screen|that)\b",
    r"what am i looking at\b",
    r"(?:describe|read)(?: my)? screen\b",
    r"what(?:'s| is) (?:in|open)(?: on)?(?: my)? screen\b",
    r"which (?:window|app).*?(?:open|focused)\b",
]
_VISUAL_RE = re.compile("|".join(f"(?:{p})" for p in VISUAL_PATTERNS), re.I)

VISION_MODELS = ["moondream", "llava", "qwen2-vl", "gemma3", "minicpm-v"]


def is_visual_question(text: str) -> bool:
    return bool(_VISUAL_RE.search((text or "").strip()))


def capture_b64(max_side: int = 1280) -> str:
    """Screenshot → downscaled base64 PNG. Raises honestly with the reason."""
    from . import control as _c
    from ..permissions import policy as _pol
    res = _c._screenshot()
    if not res.get("ok"):
        raise RuntimeError(res.get("error", "screenshot failed"))
    b64 = res["data_url"].split(",", 1)[-1]
    _pol.log("desktop", "screenshot (visual question — asked, answered, discarded)",
             "confirm", granted=True)
    try:
        import io
        from PIL import Image
        raw = base64.b64decode(b64)
        im = Image.open(io.BytesIO(raw))
        im.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return b64


def pick_vision_model(provider: str, model: str) -> tuple[str, str, str]:
    """(provider, model, note). Prefers an installed local vision model."""
    if provider == "ollama":
        try:
            import json as _j
            import urllib.request as _u
            with _u.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as r:
                installed = [m.get("name", "") for m in _j.load(r).get("models", [])]
            for cand in VISION_MODELS:
                hit = next((m for m in installed if m.startswith(cand)), None)
                if hit:
                    note = "" if hit == model else f"(seeing via {hit})"
                    return "ollama", hit, note
        except Exception:
            pass
        # gemma3 is natively multimodal — current model may already see
        return "ollama", model, ""
    return provider, model, ""


async def describe(question: str, provider: str, model: str) -> dict:
    """See the screen and answer. Returns {text, via} or raises honestly."""
    from ..providers.registry import get_provider
    image = capture_b64()
    prov_name, use_model, note = pick_vision_model(provider, model)
    sys = ("You are looking at the user's screen. Answer briefly and concretely: "
           "name the app/windows visible and answer their question. If you cannot "
           "see well enough, say what you CAN see, not what you guess.")
    from ..providers.base import ChatMessage
    msgs = [ChatMessage(role="system", content=sys),
            ChatMessage(role="user", content=question)]
    try:
        res = await get_provider(prov_name).chat(msgs, use_model, images=[image])
    except Exception as e:
        msg = str(e)
        if "does not support" in msg or "400" in msg or "invalid" in msg.lower():
            raise RuntimeError(
                f"{use_model} can't read images. Try `ollama pull moondream` "
                f"(~1.7GB, sees locally) or switch to a cloud provider.")
        raise RuntimeError(f"vision request failed: {msg[:160]}")
    text = (res.text or "").strip()
    if not text:
        raise RuntimeError("the model looked but said nothing — try a vision model "
                           "(`ollama pull moondream`) or rephrase.")
    return {"text": f"{text} {note}".strip(), "via": f"{prov_name}/{use_model}"}
