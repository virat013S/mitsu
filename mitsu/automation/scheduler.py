"""Automations (§25): user rules with clear permission controls.

Rule: {id, name, kind: interval|daily|event, every_sec|at, action: notify|chat|build,
       payload, enabled, grant} — creating a rule IS the approval (revoke on delete).
Scheduler ticks from the server background loop; no separate daemon needed.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass

from ..core import paths as _cfg
from ..core.paths import data_dir  # noqa: F401  (kept for external importers)
from ..permissions import policy

FILE = "automations.json"


@dataclass
class Rule:
    id: str
    name: str
    kind: str  # interval | daily | event
    every_sec: int = 3600
    at: str = ""  # HH:MM for daily
    action: str = "notify"  # notify | chat | build
    payload: dict = None  # type: ignore
    enabled: bool = True
    last_run: float = 0.0
    # event rules: payload.event = {type: task_done|file_change|idle,
    #   task: <name-substring> | path: <file> | minutes: <N>}
    last_state: str = ""  # fingerprint so events fire once per transition

    def __post_init__(self):
        if self.payload is None:
            self.payload = {}


class Scheduler:
    def __init__(self):
        self.rules: dict[str, Rule] = {}
        self._grants: dict[str, str] = {}
        self._seen: set[str] = set()  # armed event rules (not persisted)
        self.load()

    def _path(self):
        return _cfg.data_dir() / FILE

    def load(self) -> None:
        try:
            for r in json.loads(self._path().read_text()):
                self.rules[r["id"]] = Rule(**{k: v for k, v in r.items() if k in Rule.__annotations__})
        except Exception:
            pass

    def save(self) -> None:
        self._path().write_text(json.dumps([asdict(r) for r in self.rules.values()], indent=2))

    def add(self, name: str, kind: str, action: str, payload: dict,
            every_sec: int = 3600, at: str = "") -> Rule:
        rid = uuid.uuid4().hex[:8]
        rule = Rule(id=rid, name=name, kind=kind, action=action, payload=payload,
                    every_sec=every_sec, at=at)
        grant = uuid.uuid4().hex
        policy.grant(grant)
        self._grants[rid] = grant
        self.rules[rid] = rule
        policy.log("automation", f"created rule {name} → {action}", policy.CONFIRM)
        self.save()
        return rule

    def remove(self, rid: str) -> None:
        if g := self._grants.pop(rid, None):
            policy.revoke(g)
        self.rules.pop(rid, None)
        self.save()

    def due(self, now: float | None = None) -> list[Rule]:
        now = now if now is not None else time.time()
        out = []
        for r in self.rules.values():
            if not r.enabled:
                continue
            if r.kind == "interval" and now - r.last_run >= r.every_sec:
                out.append(r)
            elif r.kind == "daily" and r.at:
                import datetime as _d
                hh, mm = (r.at.split(":") + ["0"])[:2]
                today = _d.datetime.now().replace(hour=int(hh), minute=int(mm), second=0)
                if now >= today.timestamp() > r.last_run:
                    out.append(r)
        return out

    def mark_ran(self, r: Rule) -> None:
        r.last_run = time.time()
        self.save()

    def due_events(self, tasks=None, idle_minutes: float = 0.0) -> list[Rule]:
        """Fire-once event rules: task_done, file_change, idle."""
        import os as _os
        out = []
        for r in self.rules.values():
            if not r.enabled or r.kind != "event":
                continue
            ev = (r.payload or {}).get("event", {})
            et = ev.get("type", "")
            finger = ""
            if et == "task_done" and tasks is not None:
                done = sorted(t.id for t in tasks.tasks.values()
                              if ev.get("task", "") in t.name
                              and t.status in ("completed", "failed"))
                finger = ",".join(done)
            elif et == "file_change":
                try:
                    finger = str(_os.path.getmtime(ev.get("path", "")))
                except OSError:
                    finger = "missing"
            elif et == "idle":
                try:
                    finger = "idle" if idle_minutes >= float(ev.get("minutes", 30)) else "active"
                except ValueError:
                    continue
            else:
                continue
            if r.id not in self._seen:
                self._seen.add(r.id)  # arm: observe baseline, never fire on it
            elif finger and finger != r.last_state:
                out.append(r)
            r.last_state = finger
        if out:
            self.save()
        return out
