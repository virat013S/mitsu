"""Local user profile — no cloud account required (§3)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from .paths import profile_path


@dataclass
class UserProfile:
    display_name: str = ""
    voice: str = "default"
    server_voice: str = "lessac"
    speak_up: bool = True  # boot greeting + occasional unprompted remarks
    language: str = "en"
    speech_rate: int = 175
    personality: str = "friendly"
    talkativeness: str = "normal"  # quiet | normal | chatty
    theme: str = "dark"
    default_provider: str = "auto"  # auto = Ollama if present, else keyless cloud
    default_model: str = "auto"
    notifications: bool = True
    always_listen: bool = True  # JARVIS-style: mic opens on boot, talk anytime
    favorite_apps: list[str] = field(default_factory=list)
    workspace_dir: str = ""
    completed_onboarding: bool = False

    @classmethod
    def load(cls) -> "UserProfile":
        p = profile_path()
        if p.exists():
            try:
                return cls(**{**asdict(cls()), **json.loads(p.read_text())})
            except Exception:
                return cls()
        return cls()

    def save(self) -> None:
        p = profile_path()
        p.write_text(json.dumps(asdict(self), indent=2))
        try:
            p.chmod(0o600)
        except OSError:
            pass
