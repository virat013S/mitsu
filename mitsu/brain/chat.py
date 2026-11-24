"""Chat orchestration: profile + personality + memory + router + provider."""
from __future__ import annotations

from dataclasses import dataclass

from .memory.store import MemoryStore
from .personality import system_prompt
from ..core.profile import UserProfile
from ..providers.base import ChatMessage
from ..providers.registry import get_provider
from .router import route


async def _fallback_chat(messages, failed: str, route_reason: str):
    """Last resort when the chosen brain is unusable (locked/auth/dead):
    hand the turn to a brain that does answer, and say who took over."""
    from ..providers.registry import smart_default
    d = smart_default()
    if d["provider"] == failed:
        return None  # no point retrying the same dead brain
    try:
        p = get_provider(d["provider"])
        r = await p.chat(messages, d["model"])
    except Exception:
        return None
    t = r.text.strip()
    if not t:
        return None
    t += ("\n\n(_{0} didn't answer — this came from {1}/{2}. Add balance or a "
          "key to use {0} directly.)").format(failed, d["provider"], d["model"])
    return ChatReply(text=t, provider=d["provider"], model=d["model"],
                     route_reason=route_reason + f" (fallback → {d['provider']}/{d['model']})")


@dataclass
class ChatReply:
    text: str
    provider: str
    model: str
    route_reason: str


async def reply(user_text: str, profile: UserProfile, mem: MemoryStore,
                provider_name: str | None = None, model: str | None = None,
                auto_route: bool = True) -> ChatReply:
    if auto_route and (not provider_name or provider_name == "auto"):
        r = route(user_text)
        provider_name = profile.default_provider
        # router suggests ollama for cheap/local; honor cloud default only for heavy tasks
        if r["provider"] == "openrouter" and profile.default_provider == "ollama":
            pass  # keep local unless user configured cloud
        route_reason = r["reason"]
    else:
        route_reason = "manual selection"
    auto_model = model in (None, "", "auto")  # did the caller leave the model open?
    provider_name = provider_name or profile.default_provider
    model = model or profile.default_model
    if provider_name == "auto" or model == "auto":
        # public default: local brain when present, keyless cloud otherwise.
        # "auto" must not inherit a model from another provider (the old
        # ollama/openai-fast 404) — pair the resolved brain with ITS model.
        from ..providers.registry import smart_default as _sd
        d = _sd()
        if provider_name == "auto":
            provider_name = d["provider"]
            if auto_model:
                model = d["model"]
        if model == "auto":
            if provider_name == "ollama":
                from ..providers.registry import _ollama_models, _pick_installed_model
                model = _pick_installed_model(_ollama_models()) or d["model"]
            else:
                model = d["model"]
        route_reason += f" (auto default → {provider_name}/{model})"
    strong = any(x in model.lower() for x in (
        "qwen3.5", "qwen35", "qwen3", "llama3.3", "llama3.1", "mistral",
        "gemma3:4", "gemma3:12", "phi4", "deepseek"))
    local_kw = {}
    if provider_name == "ollama":
        local_kw = {
            "max_tokens": 512 if strong else 256,
            "num_ctx": 8192 if strong else 4096,
            "keep_alive": "10m" if strong else "30m",
        }

    low = user_text.strip().lower()
    if low.startswith("remember ") and len(user_text.strip()) > 9:
        fact = user_text.strip()[9:].strip()
        mem.remember_long(fact)
        mem.remember_turn("user", user_text)
        mem.remember_turn("assistant", "Remembered.")
        name = profile.display_name or "friend"
        return ChatReply(text=f"Got it, {name} — I'll remember that.",
                         provider=provider_name, model=model, route_reason="memory store")
    if low.startswith("forget ") and len(user_text.strip()) > 7:
        target = user_text.strip()[7:].strip().lower()
        before = len(mem.long_term)
        mem.long_term = [f for f in mem.long_term if target not in f["fact"].lower()]
        mem.save()
        n = before - len(mem.long_term)
        mem.remember_turn("user", user_text)
        mem.remember_turn("assistant", "Forgot.")
        return ChatReply(text=f"Forgot {n} memor{'y' if n == 1 else 'ies'}." if n else "Nothing matched that.",
                         provider=provider_name, model=model, route_reason="memory store")

    # Voice-OS eyes: "what is this?" → look at the screen, answer from it.
    # The question itself is the approval; nothing is stored.
    from ..desktop import see as _see
    if _see.is_visual_question(user_text):
        try:
            seen = await _see.describe(user_text, provider_name, model)
            mem.remember_turn("user", user_text)
            mem.remember_turn("assistant", seen["text"])
            return ChatReply(text=seen["text"], provider=provider_name,
                             model=model, route_reason=f"saw your screen ({seen['via']})")
        except Exception as e:
            return ChatReply(text=str(e), provider=provider_name, model=model,
                             route_reason="screen look failed — clear error")

    sys = system_prompt(profile.personality, profile.display_name, "normal")
    local = provider_name == "ollama"
    hist = [ChatMessage(role=m["role"], content=m["content"])
            for m in mem.short[-4 if local else -10:]]
    longterm = [ChatMessage(role="system", content=f"Long-term memory: {f['fact']}")
                for f in mem.long_term[-2 if local else -5:]]
    messages = [ChatMessage(role="system", content=sys), *longterm,
                *hist, ChatMessage(role="user", content=user_text)]
    slim = [ChatMessage(role="system", content=sys),
            ChatMessage(role="user", content=user_text)]
    try:
        provider = get_provider(provider_name)
        try:
            res = await provider.chat(messages, model, **local_kw)
        except Exception as e:
            # free-tier throttle: walk the other free models before giving up
            if "rate-limited" in str(e) and model.endswith(":free"):
                from ..providers.builtin import catalog as _cat
                res = None
                for alt in [m.id for m in _cat(provider_name)
                            if m.free and m.id != model][:3]:
                    try:
                        res = await provider.chat(messages, alt, no_retry=True)
                        model = alt
                        route_reason += f" (failover → {alt})"
                        break
                    except Exception:
                        continue
                if res is None:
                    raise
            else:
                raise
        if not res.text.strip():
            # small/local models sometimes blank on long context — retry slim
            try:
                res = await provider.chat(slim, model, **local_kw)
            except Exception:
                res = None
        text = res.text.strip() if res is not None else ""
        if not text:
            alt = await _fallback_chat(slim, provider_name, route_reason)
            if alt is not None:
                return ChatReply(text=alt.text, provider=alt.provider,
                                 model=alt.model, route_reason=alt.route_reason)
            text = (f"{provider_name}/{model} returned an empty reply. "
                    "Try a shorter prompt or a larger model.")
    except Exception as e:
        # never leave the user unanswered: if the chosen brain is dead
        # (locked/auth/conn error), hand the turn to a working one
        res = await _fallback_chat(slim or messages, provider_name, route_reason)
        if res is not None:
            return ChatReply(text=res.text, provider=res.provider,
                             model=res.model, route_reason=res.route_reason)
        text = (f"Hmm — {provider_name}/{model} isn't reachable ({e}). "
                "Check the provider key or try Ollama local mode.")
        return ChatReply(text=text, provider=provider_name, model=model, route_reason=route_reason)
    mem.remember_turn("user", user_text)
    mem.remember_turn("assistant", text)
    return ChatReply(text=text, provider=provider_name, model=model, route_reason=route_reason)


async def reply_stream(user_text: str, profile: UserProfile, mem: MemoryStore,
                       provider_name: str | None = None, model: str | None = None,
                       auto_route: bool = True):
    """Yield delta events for local Ollama, then one final message event.

    Special commands and vision use the normal reply path; everything else
    local streams so a CPU-bound model feels alive instead of frozen.
    """
    low = user_text.strip().lower()
    from ..desktop import see as _see
    if (low.startswith("remember ") and len(user_text.strip()) > 9) \
            or (low.startswith("forget ") and len(user_text.strip()) > 7) \
            or _see.is_visual_question(user_text):
        r = await reply(user_text, profile, mem, provider_name, model, auto_route)
        yield {"type": "message", "text": r.text, "provider": r.provider,
               "model": r.model, "route": r.route_reason}
        return

    if auto_route and (not provider_name or provider_name == "auto"):
        r = route(user_text)
        provider_name = profile.default_provider
        route_reason = r["reason"]
    else:
        route_reason = "manual selection"
    auto_model = model in (None, "", "auto")
    provider_name = provider_name or profile.default_provider
    model = model or profile.default_model
    if provider_name == "auto" or model == "auto":
        from ..providers.registry import smart_default as _sd
        d = _sd()
        if provider_name == "auto":
            provider_name = d["provider"]
            if auto_model:
                model = d["model"]
        if model == "auto":
            if provider_name == "ollama":
                from ..providers.registry import _ollama_models, _pick_installed_model
                model = _pick_installed_model(_ollama_models()) or d["model"]
            else:
                model = d["model"]
        route_reason += f" (auto default → {provider_name}/{model})"

    if provider_name != "ollama":
        r = await reply(user_text, profile, mem, provider_name, model, auto_route)
        yield {"type": "message", "text": r.text, "provider": r.provider,
               "model": r.model, "route": r.route_reason}
        return

    sys = system_prompt(profile.personality, profile.display_name, "normal")
    hist = [ChatMessage(role=m["role"], content=m["content"])
            for m in mem.short[-4:]]
    longterm = [ChatMessage(role="system", content=f"Long-term memory: {f['fact']}")
                for f in mem.long_term[-2:]]
    messages = [ChatMessage(role="system", content=sys), *longterm,
                *hist, ChatMessage(role="user", content=user_text)]
    strong = any(x in model.lower() for x in (
        "qwen3.5", "qwen35", "qwen3", "llama3.3", "llama3.1", "mistral",
        "gemma3:4", "gemma3:12", "phi4", "deepseek"))
    local_kw = {
        "max_tokens": 512 if strong else 256,
        "num_ctx": 8192 if strong else 4096,
        "keep_alive": "10m" if strong else "30m",
    }
    provider = get_provider("ollama")
    full: list[str] = []
    try:
        async for chunk in provider.stream(messages, model, **local_kw):
            if chunk:
                full.append(chunk)
                yield {"type": "delta", "text": chunk}
    except Exception as e:
        if not full:
            r = await reply(user_text, profile, mem, provider_name, model, auto_route)
            yield {"type": "message", "text": r.text, "provider": r.provider,
                   "model": r.model, "route": r.route_reason}
            return
        text = "".join(full).strip() + f"\n\n(stream stopped: {e})"
        mem.remember_turn("user", user_text)
        mem.remember_turn("assistant", text)
        yield {"type": "message", "text": text, "provider": "ollama",
               "model": model, "route": route_reason}
        return

    text = "".join(full).strip()
    if not text:
        r = await reply(user_text, profile, mem, provider_name, model, auto_route)
        yield {"type": "message", "text": r.text, "provider": r.provider,
               "model": r.model, "route": r.route_reason}
        return
    mem.remember_turn("user", user_text)
    mem.remember_turn("assistant", text)
    yield {"type": "message", "text": text, "provider": "ollama",
           "model": model, "route": route_reason}
