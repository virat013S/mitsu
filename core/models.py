"""Multi-provider, user-selectable model system.

Architecture: Provider -> Model Catalog -> Selected Model -> AI Runtime.

- Discovery is dynamic where possible (Ollama /api/tags, OpenRouter
  /models catalog, Gemini models.list) with curated fallbacks so the UI
  works offline.
- Selection persists in ~/.mitsu/provider.json as {"provider", "model",
  "fallback"} and survives restarts. Env overrides: MITSU_PROVIDER,
  MITSU_MODEL. Switching provider/model never touches identity or memory.
- No silent overrides: an explicit model argument always wins over the
  stored selection, and automatic fallback only happens when the user
  configured the fallback policy to "auto".
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

PROVIDER_PATH = Path.home() / ".mitsu" / "provider.json"

# ── Capabilities ──────────────────────────────────────────────────────────
TEXT = "text_generation"
STREAMING = "streaming"
TOOL_CALLS = "tool_calling"
IMAGES = "vision"
AUDIO_IN = "audio_input"
AUDIO_OUT = "audio_output"
LIVE_VOICE = "live_voice"
STRUCTURED = "structured_output"
LONG_CONTEXT = "long_context"
EMBEDDINGS = "embeddings"

# Workflow-level capabilities Mitsu itself provides for any coherent text
# model (e.g. the [SKILL:name]{...} text protocol for Ollama/OpenRouter).
PROVIDER_CAPABILITIES = {
    "ollama": frozenset({TEXT, STREAMING, TOOL_CALLS, LONG_CONTEXT, EMBEDDINGS}),
    "openrouter": frozenset({TEXT, STREAMING, TOOL_CALLS, STRUCTURED, LONG_CONTEXT}),
    "gemini": frozenset({TEXT, STREAMING, TOOL_CALLS, IMAGES, STRUCTURED,
                         LONG_CONTEXT, EMBEDDINGS}),
}

# Fallback policies: never switch silently unless the user chose "auto".
FALLBACK_NEVER = "never"
FALLBACK_ASK = "ask"
FALLBACK_AUTO = "auto"
FALLBACK_POLICIES = (FALLBACK_NEVER, FALLBACK_ASK, FALLBACK_AUTO)

# Recommended local size band (params in billions). Larger models only
# produce a warning — the user's selection is never changed silently.
LOCAL_SIZE_WARN_B = 3.5

_PARAMS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*b", re.IGNORECASE)


@dataclass
class ModelInfo:
    id: str
    label: str
    provider: str
    local: bool = False
    params_b: float | None = None
    free: bool | None = None
    context: int | None = None
    capabilities: frozenset = field(default_factory=frozenset)
    available: bool = False
    warning: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "label": self.label, "provider": self.provider,
            "local": self.local, "params_b": self.params_b, "free": self.free,
            "context": self.context, "capabilities": sorted(self.capabilities),
            "available": self.available, "warning": self.warning,
        }


# ── Curated catalogs (easy to update; dynamic discovery extends them) ─────

GEMINI_KNOWN_MODELS = [
    {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash",
     "capabilities": [TEXT, STREAMING, TOOL_CALLS, IMAGES, STRUCTURED,
                      LONG_CONTEXT, AUDIO_IN, AUDIO_OUT]},
    {"id": "gemini-2.5-flash-lite", "label": "Gemini 2.5 Flash-Lite",
     "capabilities": [TEXT, STREAMING, TOOL_CALLS, IMAGES, STRUCTURED,
                      LONG_CONTEXT]},
    {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro",
     "capabilities": [TEXT, STREAMING, TOOL_CALLS, IMAGES, STRUCTURED,
                      LONG_CONTEXT, AUDIO_IN, AUDIO_OUT]},
    {"id": "models/gemini-2.5-flash-native-audio-preview-12-2025",
     "label": "Gemini Live (native audio)",
     "capabilities": [TEXT, STREAMING, TOOL_CALLS, IMAGES, AUDIO_IN,
                      AUDIO_OUT, LIVE_VOICE, LONG_CONTEXT]},
]

OPENROUTER_KNOWN_FREE = [
    {"id": "nvidia/nemotron-3-ultra-550b-a55b:free", "label": "Nemotron 3 Ultra (free)",
     "capabilities": [TEXT, STREAMING, TOOL_CALLS, STRUCTURED, LONG_CONTEXT]},
    {"id": "meta-llama/llama-3.3-70b-instruct:free", "label": "Llama 3.3 70B (free)",
     "capabilities": [TEXT, STREAMING, TOOL_CALLS, STRUCTURED, LONG_CONTEXT]},
    {"id": "qwen/qwen3-32b:free", "label": "Qwen 3 32B (free)",
     "capabilities": [TEXT, STREAMING, TOOL_CALLS, STRUCTURED, LONG_CONTEXT]},
]

OLLAMA_FALLBACK_MODELS = [
    {"id": "gemma3:1b", "label": "Gemma 3 1B", "params_b": 1.0},
    {"id": "qwen2.5:1.5b", "label": "Qwen 2.5 1.5B", "params_b": 1.5},
    {"id": "qwen3:1.7b", "label": "Qwen 3 1.7B", "params_b": 1.7},
    {"id": "llama3.2:1b", "label": "Llama 3.2 1B", "params_b": 1.0},
    {"id": "llama3.2:3b", "label": "Llama 3.2 3B", "params_b": 3.0},
]


def _parse_params_b(name: str) -> float | None:
    match = _PARAMS_RE.search(name or "")
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _size_warning(params_b: float | None) -> str:
    if params_b is not None and params_b > LOCAL_SIZE_WARN_B:
        return (f"{params_b:g}B exceeds the recommended 1B-3B local band; "
                "it may be slow on modest hardware.")
    return ""


def _pretty_label(model_id: str) -> str:
    base = model_id.split("/")[-1].split(":")[0]
    return base.replace("-", " ").replace("_", " ").title() or model_id


# ── Discovery ─────────────────────────────────────────────────────────────

def list_ollama_models(base_url: str = "http://localhost:11434",
                       timeout: float = 5.0) -> list[ModelInfo]:
    """Detect models installed in local Ollama. Raises on connection error."""
    import httpx
    resp = httpx.get(f"{base_url}/api/tags", timeout=timeout)
    resp.raise_for_status()
    found = []
    for entry in resp.json().get("models", []):
        name = entry.get("name", "")
        if not name:
            continue
        params = _parse_params_b(name)
        found.append(ModelInfo(
            id=name, label=_pretty_label(name), provider="ollama",
            local=True, params_b=params,
            capabilities=PROVIDER_CAPABILITIES["ollama"],
            available=True, warning=_size_warning(params)))
    return found


def ollama_catalog(base_url: str = "http://localhost:11434") -> list[ModelInfo]:
    """Installed Ollama models, or the curated fallback when offline."""
    try:
        models = list_ollama_models(base_url)
        if models:
            return models
    except Exception:
        pass
    return [ModelInfo(id=m["id"], label=m["label"], provider="ollama",
                      local=True, params_b=m["params_b"],
                      capabilities=PROVIDER_CAPABILITIES["ollama"],
                      available=False,
                      warning="Ollama unreachable; showing known models.")
            for m in OLLAMA_FALLBACK_MODELS]


def list_gemini_models(api_key: str = "") -> list[ModelInfo]:
    """Curated Gemini models, verified against the API when a key is given.

    Never requires a key just to list: without one the curated entries
    are returned marked unverified.
    """
    verified: set[str] = set()
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            for model in client.models.list():
                name = getattr(model, "name", "") or ""
                if name:
                    verified.add(name)
                    short = name.removeprefix("models/")
                    verified.add(short)
        except Exception:
            pass
    infos = []
    for entry in GEMINI_KNOWN_MODELS:
        model_id = entry["id"]
        short = model_id.removeprefix("models/")
        ok = (not api_key) or (model_id in verified or short in verified)
        infos.append(ModelInfo(
            id=short if model_id.startswith("models/") else model_id,
            label=entry["label"], provider="gemini",
            capabilities=frozenset(entry["capabilities"]),
            available=ok,
            warning="" if (api_key or ok) else "unverified (no API key)"))
    return infos


def list_openrouter_models(api_key: str = "", query: str = "",
                           timeout: float = 10.0) -> list[ModelInfo]:
    """Browse the OpenRouter catalog (public endpoint; key optional).

    Falls back to the curated free list when offline.
    """
    try:
        import httpx
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        resp = httpx.get("https://openrouter.ai/api/v1/models",
                         headers=headers, timeout=timeout)
        resp.raise_for_status()
        infos = []
        for entry in resp.json().get("data", []):
            model_id = entry.get("id", "")
            if query and query.lower() not in (
                    model_id + entry.get("name", "")).lower():
                continue
            pricing = entry.get("pricing", {}) or {}
            try:
                free = (float(pricing.get("prompt", 1) or 0) == 0
                        and float(pricing.get("completion", 1) or 0) == 0)
            except (TypeError, ValueError):
                free = None
            supported = entry.get("supported_parameters") or []
            caps = {TEXT, STREAMING, LONG_CONTEXT}
            if "tools" in supported:
                caps.add(TOOL_CALLS)
            if "structured_outputs" in supported:
                caps.add(STRUCTURED)
            arch = entry.get("architecture", {}) or {}
            modality = str(arch.get("modality", ""))
            if "image" in modality:
                caps.add(IMAGES)
            infos.append(ModelInfo(
                id=model_id, label=entry.get("name") or _pretty_label(model_id),
                provider="openrouter", free=free,
                context=entry.get("context_length"),
                capabilities=frozenset(caps), available=True))
        if infos:
            return infos
    except Exception:
        pass
    return [ModelInfo(id=m["id"], label=m["label"], provider="openrouter",
                      free=True, capabilities=frozenset(m["capabilities"]),
                      available=False,
                      warning="Catalog unreachable; showing known free models.")
            for m in OPENROUTER_KNOWN_FREE
            if not query or query.lower() in (m["id"] + m["label"]).lower()]


def catalog(provider: str, **kwargs) -> list[ModelInfo]:
    """List selectable models for a provider (dynamic + curated fallback)."""
    provider = (provider or "").strip().lower()
    if provider == "ollama":
        return ollama_catalog(kwargs.get("base_url", "http://localhost:11434"))
    if provider == "gemini":
        return list_gemini_models(kwargs.get("api_key", ""))
    if provider == "openrouter":
        return list_openrouter_models(kwargs.get("api_key", ""),
                                      kwargs.get("query", ""))
    raise ValueError(f"Unknown provider: {provider}")


# ── Selection persistence ─────────────────────────────────────────────────

# Canonical provider defaults, mirrored from core.providers.PROVIDERS.
# Used when optional dependencies (httpx) are unavailable; a test pins
# them in sync.
FALLBACK_DEFAULT_MODELS = {
    "ollama": "gemma3:1b",
    "openrouter": "nvidia/nemotron-3-ultra-550b-a55b:free",
    "gemini": "gemini-2.5-flash",
}


def default_model(provider: str) -> str:
    provider = (provider or "").strip().lower()
    try:
        from core.providers import PROVIDERS
        info = PROVIDERS.get(provider)
        if info:
            return info["model"]
    except ImportError:
        pass
    if provider in FALLBACK_DEFAULT_MODELS:
        return FALLBACK_DEFAULT_MODELS[provider]
    raise ValueError(f"Unknown provider: {provider}")


def _default_provider() -> str:
    try:
        from core.providers import get_provider
        return get_provider()
    except ImportError:
        provider = os.environ.get("MITSU_PROVIDER", "").strip().lower()
        if provider in FALLBACK_DEFAULT_MODELS:
            return provider
        if os.environ.get("GEMINI_API_KEY"):
            return "gemini"
        if os.environ.get("OPENROUTER_API_KEY"):
            return "openrouter"
        return "ollama"


# Legacy per-provider model env vars (honored below stored selection).
LEGACY_MODEL_ENV = {"ollama": "OLLAMA_MODEL", "openrouter": "OPENROUTER_MODEL"}


def _read_store() -> dict:
    try:
        if PROVIDER_PATH.exists():
            data = json.loads(PROVIDER_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def explicit_selection() -> dict | None:
    """The user's stored model choice, or None if they never chose one.

    Derived defaults never shadow explicit configuration elsewhere.
    """
    stored = _read_store()
    provider = str(stored.get("provider", "")).strip().lower()
    model = str(stored.get("model", "")).strip()
    if provider in ("ollama", "openrouter", "gemini") and model:
        return {"provider": provider, "model": model}
    return None


def get_selection() -> dict:
    """Effective {provider, model, fallback}.

    Precedence for the model: MITSU_MODEL env > stored selection >
    legacy provider env (OLLAMA_MODEL/OPENROUTER_MODEL) > default.
    """
    stored = _read_store()
    provider = (os.environ.get("MITSU_PROVIDER", "").strip().lower()
                or str(stored.get("provider", "")).strip().lower()
                or _default_provider())
    if provider not in ("ollama", "openrouter", "gemini"):
        provider = "ollama"
    legacy = ""
    legacy_var = LEGACY_MODEL_ENV.get(provider, "")
    if legacy_var:
        legacy = os.environ.get(legacy_var, "").strip()
    model = (os.environ.get("MITSU_MODEL", "").strip()
             or str(stored.get("model", "")).strip()
             or legacy
             or default_model(provider))
    fallback = str(stored.get("fallback", FALLBACK_ASK)).strip().lower()
    if fallback not in FALLBACK_POLICIES:
        fallback = FALLBACK_ASK
    return {"provider": provider, "model": model, "fallback": fallback}


def set_selection(provider: str, model: str,
                  fallback: str | None = None) -> dict:
    """Persist provider+model choice. Never touches identity or memory."""
    provider = (provider or "").strip().lower()
    if provider not in ("ollama", "openrouter", "gemini"):
        raise ValueError(f"Unknown provider: {provider}")
    model = (model or "").strip()
    if not model:
        raise ValueError("Model must be a non-empty model id.")
    stored = _read_store()
    stored["provider"] = provider
    stored["model"] = model
    if fallback is not None:
        fallback = fallback.strip().lower()
        if fallback not in FALLBACK_POLICIES:
            raise ValueError(f"Fallback must be one of {FALLBACK_POLICIES}.")
        stored["fallback"] = fallback
    PROVIDER_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROVIDER_PATH.write_text(json.dumps(stored, indent=2), encoding="utf-8")
    return {"provider": provider, "model": stored.get("model"),
            "fallback": stored.get("fallback", FALLBACK_ASK)}


def resolve_model(provider: str | None = None,
                  explicit: str | None = None) -> str:
    """Model id to actually use. An explicit argument always wins."""
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    selection = get_selection()
    if provider and provider.strip().lower() != selection["provider"]:
        return default_model(provider)
    return selection["model"]


def get_fallback_policy() -> str:
    return get_selection()["fallback"]


def gemini_text_model(explicit: str | None = None) -> str:
    """Gemini model id for text/generation calls.

    Single choke point so no action hard-codes a Gemini model: the
    user's selected Gemini model is used, falling back to the provider
    default. An explicit argument always wins.
    """
    return resolve_model("gemini", explicit)
def set_fallback_policy(policy: str) -> str:
    selection = get_selection()
    set_selection(selection["provider"], selection["model"], fallback=policy)
    return get_selection()["fallback"]


# ── Capabilities & availability ───────────────────────────────────────────

def _catalog_entry(provider: str, model: str) -> ModelInfo | None:
    for info in catalog(provider):
        if info.id == model or info.id.removeprefix("models/") == model:
            return info
    return None


def model_capabilities(provider: str, model: str) -> frozenset:
    """Effective capability set: catalog entry, else provider defaults."""
    entry = _catalog_entry(provider, model)
    if entry is not None:
        return entry.capabilities
    return PROVIDER_CAPABILITIES.get((provider or "").lower(), frozenset())


def model_supports(provider: str, model: str, capability: str,
                   strict: bool = False) -> bool:
    """Capability check. strict=True: unknown models support nothing."""
    if strict and _catalog_entry(provider, model) is None:
        known_defaults = {
            m["id"] for m in (GEMINI_KNOWN_MODELS + OPENROUTER_KNOWN_FREE
                              + OLLAMA_FALLBACK_MODELS)
        }
        if model not in known_defaults:
            try:
                if model != default_model(provider):
                    return False
            except ValueError:
                return False
    return capability in model_capabilities(provider, model)


def check_model(provider: str, model: str) -> dict:
    """Availability of a specific model with a clear, provider-local error."""
    provider = (provider or "").strip().lower()
    if provider == "ollama":
        try:
            installed = [m.id for m in list_ollama_models()]
        except ImportError:
            return {"available": False,
                    "error": "Local AI needs dependencies "
                             "(pip install -r requirements.txt)."}
        except Exception as exc:
            return {"available": False,
                    "error": f"Local AI is unavailable ({exc}). Start Ollama "
                             "with 'ollama serve' or pull the model with "
                             f"'ollama pull {model}'."}
        if model in installed:
            return {"available": True, "error": None}
        return {"available": False,
                "error": f"Ollama model '{model}' is not installed. "
                         f"Run: ollama pull {model}"}
    try:
        from core.providers import check_provider_status
    except ImportError:
        return {"available": False,
                "error": f"{provider} needs dependencies "
                         "(pip install -r requirements.txt)."}
    status = check_provider_status(provider)
    if not status.get("available"):
        return {"available": False, "error": status.get("error") or
                f"{provider} is not configured."}
    entry = _catalog_entry(provider, model)
    if entry is not None and not entry.available and entry.warning:
        return {"available": True,
                "error": None, "warning": entry.warning}
    return {"available": True, "error": None}
