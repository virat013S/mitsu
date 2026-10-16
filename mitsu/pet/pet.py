"""Desktop companion / digital pet (§15). Lightweight state machine — no polling loops.

Moods: happy, working, idle, sleeping, excited, confused. The UI widget polls
GET /api/companion (cheap) and pushes clicks; the overlay window is optional
and off by default (enable in Settings → Companion).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

MOODS = ("happy", "working", "idle", "sleeping", "excited", "confused")
FACES = {"happy": "(◕‿◕)", "working": "(⌨_⌨)", "idle": "(・_・)",
         "sleeping": "(−_−) zZ", "excited": "(ﾉ◕ヮ◕)ﾉ", "confused": "(・・?)"}


@dataclass
class Companion:
    enabled: bool = False
    mood: str = "idle"
    message: str = ""
    task_label: str = ""
    progress: float = 0.0
    last_interact: float = field(default_factory=time.time)
    nags: int = 0

    def state(self) -> dict:
        face = FACES.get(self.mood, FACES["idle"])
        return {"enabled": self.enabled, "mood": self.mood, "face": face,
                "message": self.message, "task": self.task_label,
                "progress": self.progress}

    def notify(self, message: str, task_label: str = "", progress: float = 0.0) -> None:
        self.mood = "working" if task_label else "excited"
        self.message, self.task_label, self.progress = message, task_label, progress

    def poke(self) -> str:
        self.last_interact = time.time()
        self.nags += 1
        lines = ["Hey! I'm Mitsu. Click me to open the full app.",
                 "Yes? I'm here. Mostly awake.",
                 "Poke poke. Noted. Anyway — what are we doing?"]
        line = lines[min(self.nags - 1, len(lines) - 1)]
        self.mood, self.message = "happy", line
        self.nags = 0 if self.nags > 3 else self.nags
        return line

    def heartbeat(self, active_tasks: int) -> None:
        """Called on each /api/companion poll — no timers, no CPU when idle."""
        if active_tasks:
            self.mood = "working"
        elif time.time() - self.last_interact > 600:
            self.mood = "sleeping"
        elif self.mood == "sleeping":
            self.mood = "idle"
