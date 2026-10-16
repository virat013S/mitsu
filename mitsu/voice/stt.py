"""Speech recognition — replaceable STT (§13/§14). Browser WebSpeech default; server Vosk optional."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class STTResult:
    text: str
    confidence: float = 1.0
    engine: str = "webspeech"


class STTEngine:
    name = "base"

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> STTResult:
        raise NotImplementedError


class PassthroughSTT(STTEngine):
    """MVP: browser already transcribed via Web Speech API; server just receives text."""
    name = "webspeech-passthrough"

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> STTResult:
        return STTResult(text="", engine=self.name)
