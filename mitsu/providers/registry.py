"""Provider registry — single place that instantiates providers."""
from __future__ import annotations

import json
import os

from ..core.paths import config_path
from .builtin import OllamaProvider, make_openai_compat
from .secrets import load_key


def _zen_provider(kind: str, api_key: str = "", base_url: str = ""):
    from .zen import ZenProvider
    base = base_url or {"zen": "https://opencode.ai/zen/v1",
                        "go": "https://opencode.ai/zen/go/v1"}.get(kind, base_url)
    return ZenProvider(base_url=base, api_key=api_key, label=kind)

DEFAULTS = {
    "ollama": {"kind": "ollama", "base_url": "", "default_model": ""},
    "openai": {"kind": "openai", "default_model": "gpt-4o-mini"},
    "openrouter": {"kind": "openrouter", "default_model": "google/gemma-4-26b-a4b-it:free"},
    "gemini": {"kind": "gemini", "default_model": ""},
    "anthropic": {"kind": "anthropic", "default_model": ""},
    "zen": {"kind": "zen", "default_model": "big-pickle"},
    "go": {"kind": "go", "default_model": "kimi-k2.7-code"},
    "pollinations": {"kind": "pollinations", "default_model": "openai"},
    "custom": {"kind": "custom", "base_url": "", "default_model": ""},
}


_SMART_CACHE: dict = {"provider": "", "model": "", "ts": 0.0}
_SMART_TTL = 15.0
_OLLAMA_BOOT = {"tried": False, "ok": False}

_EMBED_HINTS = ("embed", "embedding", "rerank", "bge", "minilm", "e5-",
                "nomic-embed", "arctic-embed")
_VISION_ONLY = ("moondream", "llava", "bakllava", "minicpm-v",
                "llama3.2-vision", "qwen2.5vl", "qwen2-vl")


def _ollama_base() -> str:
    """Ollama URL, honouring OLLAMA_HOST / MITSU_OLLAMA_BASE."""
    raw = (os.environ.get("MITSU_OLLAMA_BASE")
           or os.environ.get("OLLAMA_HOST")
           or "http://127.0.0.1:11434").strip()
    if not raw:
        raw = "http://127.0.0.1:11434"
    if "://" not in raw:
        raw = "http://" + raw
    # A server bound to all interfaces is still reached over loopback here.
    raw = raw.replace("://0.0.0.0", "://127.0.0.1")
    raw = raw.replace("://[::]", "://[::1]")
    return raw.rstrip("/")


def _ollama_url(path: str) -> str:
    return _ollama_base() + path


def _ollama_healthy(timeout: float = 2.0) -> bool:
    # sync check (no event loop needed — safe inside async handlers too)
    try:
        import urllib.request as _u
        with _u.urlopen(_ollama_url("/api/tags"), timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def _ollama_models() -> list[str]:
    """Model names the local Ollama actually has installed."""
    try:
        import json as _j
        import urllib.request as _u
        with _u.urlopen(_ollama_url("/api/tags"), timeout=2) as r:
            data = _j.loads(r.read().decode("utf-8", "replace"))
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def ensure_ollama() -> bool:
    """Ollama installed but stopped is a common state (systemd service often
    disabled). Start `ollama serve` once, user-level — never sudo, never
    repeated, and only when the binary exists."""
    if _ollama_healthy():
        return True
    if _OLLAMA_BOOT["tried"]:
        return _OLLAMA_BOOT["ok"]
    _OLLAMA_BOOT["tried"] = True
    import shutil as _sh
    import subprocess as _sp
    exe = _sh.which("ollama")
    if not exe:
        return False
    try:
        _sp.Popen([exe, "serve"], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                  start_new_session=True)
    except Exception:
        return False
    import time as _t
    deadline = _t.time() + 8
    while _t.time() < deadline:
        if _ollama_healthy(timeout=1.0):
            _OLLAMA_BOOT["ok"] = True
            return True
        _t.sleep(0.4)
    return False


def _pick_installed_model(models: list[str]) -> str:
    """First installed chat model, in Ollama's own order.

    No model family or size is baked in. The picker lets the user select any
    installed model, and that explicit choice is used before this fallback.
    """
    usable = [m for m in models if m and not any(x in m.lower() for x in _EMBED_HINTS)]
    if not usable:
        usable = [m for m in models if m]
    text = [m for m in usable if not any(x in m.lower() for x in _VISION_ONLY)]
    if text:
        usable = text
    # Qwen is still selectable by hand, but auto leaves it alone while another
    # installed model is available. This is a preference, not a default.
    non_qwen = [m for m in usable if "qwen" not in m.lower()]
    if non_qwen:
        usable = non_qwen
    return usable[0] if usable else ""


def resolve_auto(provider: str | None, model: str | None, text: str = "",
                 prefer_deep: bool = False) -> tuple[str, str]:
    """Turn auto/empty provider-model pairs into a real installed pair.

    Used by research, build and screen vision so they do not hand "auto" to
    a provider endpoint. Explicit user picks are returned untouched. The
    prefer_deep flag is kept for callers; auto no longer swaps to Qwen.
    """
    p = (provider or "").strip()
    m = (model or "").strip()
    if p not in ("", "auto") and m not in ("", "auto"):
        return p, m
    d = smart_default()
    if p in ("", "auto"):
        p = d["provider"]
    if m in ("", "auto"):
        if p == "ollama":
            models = _ollama_models()
            m = _pick_installed_model(models) or d["model"]
        elif d["provider"] == p:
            m = d["model"]
        else:
            m = (DEFAULTS.get(p) or {}).get("default_model", "")
            if not m:
                from .builtin import catalog
                ms = catalog(p)
                m = ms[0].id if ms else ""
    return p, m


def smart_default(force: bool = False) -> dict:
    """Public-ready default: local Ollama when healthy, else keyless cloud.

    Re-resolved every 15 s (Ollama can start/stop at any time) and pinned to
    a model that is actually installed. No model name is assumed."""
    import time as _t
    now = _t.time()
    if (not force and _SMART_CACHE.get("model")
            and now - _SMART_CACHE.get("ts", 0.0) < _SMART_TTL):
        return {"provider": _SMART_CACHE["provider"], "model": _SMART_CACHE["model"]}
    if _ollama_healthy() or ensure_ollama():
        models = _ollama_models()
        override = os.environ.get("MITSU_OLLAMA_MODEL", "").strip()
        pick = override if override in models else _pick_installed_model(models)
        if pick:
            _SMART_CACHE.update({"provider": "ollama", "model": pick, "ts": now})
            return {"provider": "ollama", "model": pick}
    _SMART_CACHE.update({"provider": "pollinations", "model": "openai", "ts": now})
    return {"provider": "pollinations", "model": "openai"}

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
        return OllamaProvider(cfg.get("base_url") or _ollama_base())
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
        kind = cfg.get("kind", name)
        out.append({
            "name": name, "kind": kind,
            "base_url": cfg.get("base_url", ""),
            "default_model": cfg.get("default_model", ""),
            "has_key": True if kind in ("ollama", "pollinations") else has_key(name),
            # local brains never ask for a key — they get a "start it" action
            "local": kind == "ollama",
            "needs_key": kind not in ("ollama", "pollinations"),
        })
    # surface user-added custom providers stored under other names
    return out
