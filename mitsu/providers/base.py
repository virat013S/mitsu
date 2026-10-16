"""Provider abstraction (§4). Every model speaks through ChatProvider."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class ChatResult:
    text: str
    model: str
    provider: str


@dataclass
class ModelInfo:
    id: str
    name: str
    context: int = 0
    installed: bool = True  # False = known catalog entry, not confirmed available
    free: bool = False  # True = costs nothing (OpenRouter :free, Zen -free, Ollama)


class ChatProvider(Protocol):
    name: str

    async def chat(self, messages: list[ChatMessage], model: str, **kw) -> ChatResult: ...
    async def stream(self, messages: list[ChatMessage], model: str, **kw) -> AsyncIterator[str]: ...
    async def list_models(self) -> list[ModelInfo]: ...


@dataclass
class ProviderConfig:
    name: str
    kind: str  # openai | gemini | anthropic | openrouter | ollama | custom
    base_url: str = ""
    api_key: str = ""  # resolved at runtime from keyring; never persisted in plaintext config
    default_model: str = ""
    extra: dict = field(default_factory=dict)
