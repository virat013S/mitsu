"""Local user profile — no cloud account required."""
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
    provider_mode: str = "auto"  # auto = local-first resolver; manual = pinned provider
    notifications: bool = True
    always_listen: bool = True  # Always-on: mic opens on boot, talk anytime
    favorite_apps: list[str] = field(default_factory=list)
    workspace_dir: str = ""
    completed_onboarding: bool = False

    @classmethod
    def load(cls) -> "UserProfile":
        p = profile_path()
        if p.exists():
            try:
                raw = json.loads(p.read_text())
                migrated = "provider_mode" not in raw
                if migrated:
                    # pre-auto profiles: only the untouched onboarding default
                    # migrates to auto; an explicitly pinned brain stays pinned
                    defaultish = (raw.get("default_provider") in ("", "pollinations")
                                  and raw.get("default_model") in ("", "auto", "openai-fast"))
                    raw["provider_mode"] = "auto" if defaultish else "manual"
                    if defaultish:
                        raw["default_provider"] = "auto"
                        raw["default_model"] = "auto"
                prof = cls(**{**asdict(cls()), **raw})
                if migrated:
                    try:
                        prof.save()  # make the migration durable
                    except OSError:
                        pass
                return prof
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
