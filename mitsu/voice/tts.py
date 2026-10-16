"""TTS — provider-independent (§13): any model → Mitsu text → Mitsu voice.

MVP: browser SpeechSynthesis (zero deps, per-voice/rate/pitch). Server hooks
for Piper/espeak/pyttsx3 live here for Phase 2 offline voice.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VoiceSpec:
    voice: str = "default"
    language: str = "en"
    rate: int = 175
    pitch: float = 1.0


class TTSEngine:
    name = "base"

    async def speak(self, text: str, spec: VoiceSpec) -> bytes | None:
        raise NotImplementedError


class BrowserTTS(TTSEngine):
    """Client-side synthesis — server returns text + voice spec over WS."""
    name = "browser"

    async def speak(self, text: str, spec: VoiceSpec) -> bytes | None:
        return None  # no server audio; UI speaks it

    def directive(self, text: str, spec: VoiceSpec) -> dict:
        return {"type": "speak", "text": text, "voice": spec.voice,
                "rate": spec.rate, "pitch": spec.pitch, "lang": spec.language}
