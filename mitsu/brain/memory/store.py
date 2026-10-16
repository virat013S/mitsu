"""Layered memory (§18): short / project / user-prefs / long-term. JSON file, 0600."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from ...core.paths import memory_path


@dataclass
class MemoryStore:
    short: list[dict] = field(default_factory=list)   # current conversation window
    project: dict = field(default_factory=dict)       # per-project facts
    long_term: list[dict] = field(default_factory=list)  # user-approved lasting facts

    @classmethod
    def load(cls) -> "MemoryStore":
        p = memory_path()
        if p.exists():
            try:
                d = json.loads(p.read_text())
                return cls(short=d.get("short", [])[-50:],
                           project=d.get("project", {}),
                           long_term=d.get("long_term", []))
            except Exception:
                return cls()
        return cls()

    def save(self) -> None:
        p = memory_path()
        p.write_text(json.dumps({"short": self.short[-50:], "project": self.project,
                                 "long_term": self.long_term}, indent=2))
        try:
            p.chmod(0o600)
        except OSError:
            pass

    def remember_turn(self, role: str, content: str) -> None:
        self.short.append({"role": role, "content": content, "ts": time.time()})
        self.short = self.short[-50:]
        self.save()

    def remember_long(self, fact: str) -> None:
        self.long_term.append({"fact": fact, "ts": time.time()})
        self.save()

    def forget_all(self) -> None:
        self.short, self.project, self.long_term = [], {}, {}
        self.save()
