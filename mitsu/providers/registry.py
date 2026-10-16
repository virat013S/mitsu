"""Provider registry — single place that instantiates providers (§4)."""
from __future__ import annotations

import json

from ..core.paths import config_path
from .builtin import OllamaProvider, make_openai_compat
from .secrets import load_key


def _zen_provider(kind: str, api_key: str = "", base_url: str = ""):
    from .zen import ZenProvider
    base = base_url or {"zen": "https://opencode.ai/zen/v1",
                        "go": "https://opencode.ai/zen/go/v1"}.get(kind, base_url)
    return ZenProvider(base_url=base, api_key=api_key, label=kind)

DEFAULTS = {
    "ollama": {"kind": "ollama", "base_url": "http://127.0.0.1:11434", "default_model": "gemma3:1b"},
    "openai": {"kind": "openai", "default_model": "gpt-4o-mini"},
    "openrouter": {"kind": "openrouter", "default_model": "google/gemma-4-26b-a4b-it:free"},
    "gemini": {"kind": "gemini", "default_model": ""},
    "anthropic": {"kind": "anthropic", "default_model": ""},
    "zen": {"kind": "zen", "default_model": "big-pickle"},
    "go": {"kind": "go", "default_model": "kimi-k2.7-code"},
    "pollinations": {"kind": "pollinations", "default_model": "openai"},
    "custom": {"kind": "custom", "base_url": "", "default_model": ""},
}


_SMART_CACHE: dict = {}


def _ollama_healthy() -> bool:
    # sync check (no event loop needed — safe inside async handlers too)
    try:
        import urllib.request as _u
        with _u.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def smart_default() -> dict:
    """Public-ready default: local Ollama when healthy, else keyless cloud.
    Cached per process (re-resolved on restart). Never needs keys."""
    if _SMART_CACHE.get("model"):
        return _SMART_CACHE
    if _ollama_healthy():
        _SMART_CACHE.update({"provider": "ollama", "model": "gemma3:1b"})
    else:
        _SMART_CACHE.update({"provider": "pollinations", "model": "openai"})
    return _SMART_CACHE

PROVIDERS_FILE = "providers.json"


def _store() -> dict:
    p = config_path().parent / PROVIDERS_FILE
    if p.exists():
        try:
            import json as _j
            return _j.loads(p.read_text())
        except Exception:
            return {}
    return {}


def save_provider(name: str, cfg: dict) -> None:
    from ..core.paths import data_dir
    import json as _j
    p = data_dir() / PROVIDERS_FILE
    all_cfg = _store()
    all_cfg[name] = cfg
    p.write_text(_j.dumps(all_cfg, indent=2))


def configured_providers() -> dict:
    merged = {k: dict(v) for k, v in DEFAULTS.items()}
    for k, v in _store().items():
        merged.setdefault(k, {}).update(v)
    return merged


def get_provider(name: str):
    cfgs = configured_providers()
    cfg = cfgs.get(name, cfgs["ollama"])
    kind = cfg.get("kind", name)
    if kind == "ollama":
        return OllamaProvider(cfg.get("base_url", "http://127.0.0.1:11434"))
    if kind == "custom":
        from .openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(base_url=cfg.get("base_url", ""),
                                    api_key=load_key(name), provider=name)
    if kind in ("zen", "go"):
        return _zen_provider(kind, api_key=load_key(name),
                             base_url=cfg.get("base_url", ""))
    return make_openai_compat(kind, api_key=load_key(name),
                              base_url=cfg.get("base_url", ""))


_KEYLESS = ("ollama", "pollinations")

_PROBE_CACHE: dict = {}  # provider name -> usable bool (this process)
_PROBE_AUTH_SIGNS = ("free-tier", "opencode's free tier", "401", "403",
                     "unauthorized", "invalid api key", "incorrect api key",
                     "authentication", "not allowed", "no balance",
                     "forbidden", "denied", "subscription", "access is")


async def _probe_one(name: str, cfg: dict) -> bool | None:
    """One tiny real request. True = answers, False = locked/auth/no key,
    None = can't tell (net flap — stay visible)."""
    kind = cfg.get("kind", name)
    if kind == "pollinations":
        return True  # keyless, live-verified
    if kind == "ollama":
        return _ollama_healthy()
    import asyncio as _a
    from .secrets import load_key  # call-time import → tests can patch secrets.load_key
    if kind == "custom" and not cfg.get("base_url"):
        return False  # custom endpoint with nowhere to talk
    from .base import ChatMessage
    if kind not in ("zen", "go") and cfg.get("kind", name) != "custom" \
            and not load_key(name):
        return False  # nothing to talk through
    try:
        p = get_provider(name)
        model = cfg.get("default_model") or "gpt-4o-mini"
        await _a.wait_for(p.chat([ChatMessage(role="user", content="ping")],
                                 model), timeout=20)
        return True  # alive (even throttled = valid key)
    except Exception as e:
        s = str(e).lower()
        if any(t in s for t in _PROBE_AUTH_SIGNS):
            return False
        if "rate-limit" in s or "429" in s:
            return True
        return None


async def usable_providers() -> list[dict]:
    """list_configured + probe-verified `usable` flag for the picker."""
    import asyncio as _a
    out = list_configured()
    cfgs = configured_providers()
    probes = {}
    for row in out:
        name = row["name"]
        if name in _PROBE_CACHE:
            row["usable"] = _PROBE_CACHE[name]
        else:
            probes[name] = _a.ensure_future(_probe_one(name, cfgs.get(name, {})))
    for name, fut in probes.items():
        try:
            res = await fut
        except Exception:
            res = None
        row = next(r for r in out if r["name"] == name)
        if res is None:
            row["usable"] = row["has_key"]  # can't tell → stay visible
        else:
            _PROBE_CACHE[name] = res
            row["usable"] = res
    return out


def clear_probe(name: str = "") -> None:
    if name:
        _PROBE_CACHE.pop(name, None)
    else:
        _PROBE_CACHE.clear()


def list_configured() -> list[dict]:
    """Safe for UI: never includes keys."""
    out = []
    for name, cfg in configured_providers().items():
        from .secrets import has_key
        out.append({
            "name": name, "kind": cfg.get("kind", name),
            "base_url": cfg.get("base_url", ""),
            "default_model": cfg.get("default_model", ""),
            "has_key": True if cfg.get("kind", name) in ("ollama", "pollinations")
                       else has_key(name),
        })
    # surface user-added custom providers stored under other names
    return out
