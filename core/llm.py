import json
import os
import sys
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

DEFAULT_CHAIN   = "agentrouter,gemini"
SENSITIVE_PROVIDER_DEFAULT = "gemini"

_OPENAI_PROVIDERS = {
    "agentrouter": {
        "key_env":     "AGENTROUTER_API_KEY",
        "base_url_env": "AGENTROUTER_BASE_URL",
        "base_url":    "https://agentrouter.org/v1",
        "model_env":   "AGENTROUTER_MODEL",
        "model":       "claude-opus-4-8",
        "user_agent_env": "AGENTROUTER_USER_AGENT",
        "user_agent":  "opencode/1.0.52",
    },
    "openrouter": {
        "key_env":     "OPENROUTER_API_KEY",
        "base_url_env": "OPENROUTER_BASE_URL",
        "base_url":    "https://openrouter.ai/api/v1",
        "model_env":   "OPENROUTER_MODEL",
        "model":       "nvidia/nemotron-3-ultra-550b-a55b:free",
    },
}

_clients = {}


class LLMResponse:
    def __init__(self, text: str):
        self.text = (text or "").strip()


def gemini_api_key() -> str | None:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("gemini_api_key") or data.get("GEMINI_API_KEY")
    except Exception:
        return None


def provider_chain() -> list[str]:
    raw = os.environ.get("MITSU_MODEL_CHAIN", DEFAULT_CHAIN)
    return [p.strip().lower() for p in raw.split(",") if p.strip()]


def sensitive_provider() -> str:
    return os.environ.get("MITSU_SENSITIVE_PROVIDER", SENSITIVE_PROVIDER_DEFAULT).strip().lower()


def _openai_client(name: str, cfg: dict):
    if name in _clients:
        return _clients[name]
    from openai import OpenAI
    api_key  = os.environ.get(cfg["key_env"], "").strip()
    base_url = os.environ.get(cfg["base_url_env"], cfg["base_url"]).strip()
    headers  = {}
    ua = cfg.get("user_agent") or ""
    if cfg.get("user_agent_env"):
        ua = os.environ.get(cfg["user_agent_env"], ua).strip()
    if ua:
        headers["User-Agent"] = ua
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0, max_retries=1, default_headers=headers)
    _clients[name] = client
    return client


def _call_openai_provider(name: str, prompt: str, system: str | None) -> str:
    cfg = _OPENAI_PROVIDERS[name]
    model = os.environ.get(cfg["model_env"], cfg["model"]).strip() or cfg["model"]
    client = _openai_client(name, cfg)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(model=model, messages=messages)
    return resp.choices[0].message.content or ""


def _call_gemini(prompt: str, system: str | None) -> str:
    import google.generativeai as genai
    key = gemini_api_key()
    if not key:
        raise RuntimeError("Gemini API key not found")
    genai.configure(api_key=key)
    model = genai.GenerativeModel(
        model_name=os.environ.get("MITSU_GEMINI_MODEL", "gemini-2.5-flash"),
        system_instruction=system,
    )
    response = model.generate_content(prompt)
    return response.text or ""


def _provider_available(name: str) -> bool:
    if name == "gemini":
        return bool(gemini_api_key())
    if name in _OPENAI_PROVIDERS:
        return bool(os.environ.get(_OPENAI_PROVIDERS[name]["key_env"], "").strip())
    return False


def generate(prompt: str, system: str | None = None, sensitive: bool = False) -> str:
    chain = [sensitive_provider()] if sensitive else provider_chain()
    errors = []
    for name in chain:
        if not _provider_available(name):
            errors.append(f"{name}: no API key configured")
            continue
        try:
            if name == "gemini":
                return _call_gemini(prompt, system)
            if name in _OPENAI_PROVIDERS:
                return _call_openai_provider(name, prompt, system)
            errors.append(f"{name}: unknown provider")
        except Exception as e:
            print(f"[LLM] ⚠️ {name} failed: {str(e)[:160]} — trying next provider")
            errors.append(f"{name}: {e}")
    raise RuntimeError("All LLM providers failed — " + " | ".join(errors))


class LLMClient:
    """Drop-in replacement for genai.GenerativeModel: .generate_content() -> LLMResponse(.text)"""

    def __init__(self, system_instruction: str | None = None, sensitive: bool = False):
        self.system_instruction = system_instruction
        self.sensitive = sensitive

    def generate_content(self, prompt: str) -> LLMResponse:
        return LLMResponse(generate(prompt, system=self.system_instruction, sensitive=self.sensitive))


def get_model(system_instruction: str | None = None, sensitive: bool = False) -> LLMClient:
    return LLMClient(system_instruction=system_instruction, sensitive=sensitive)


def ask(prompt: str, system: str | None = None, sensitive: bool = False) -> str:
    return generate(prompt, system=system, sensitive=sensitive)
