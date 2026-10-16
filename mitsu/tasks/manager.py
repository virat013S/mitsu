"""Long-running task manager (§7)."""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Callable

STATES = ("waiting", "planning", "running", "waiting-permission",
          "completed", "failed", "cancelled", "paused")


@dataclass
class Task:
    id: str
    name: str
    status: str = "waiting"
    progress: float = 0.0
    logs: list[str] = field(default_factory=list)
    agent: str = "assistant"
    model: str = ""
    started: float = 0.0
    ended: float = 0.0
    output: str = ""


class TaskManager:
    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self._cancel: set[str] = set()
        self._pause: set[str] = set()

    def create(self, name: str, agent: str = "assistant", model: str = "") -> Task:
        t = Task(id=uuid.uuid4().hex[:8], name=name, agent=agent, model=model,
                 started=time.time())
        self.tasks[t.id] = t
        return t

    def get(self, tid: str) -> Task | None:
        return self.tasks.get(tid)

    def list(self) -> list[dict]:
        return [asdict(t) for t in self.tasks.values()]

    def cancel(self, tid: str) -> None:
        self._cancel.add(tid)
        if t := self.tasks.get(tid):
            t.status = "cancelled"
            t.ended = time.time()

    def pause(self, tid: str) -> None:
        self._pause.add(tid)
        if t := self.tasks.get(tid):
            t.status = "paused"

    def resume(self, tid: str) -> None:
        self._pause.discard(tid)
        if t := self.tasks.get(tid):
            if t.status == "paused":
                t.status = "running"

    def stop_all(self) -> None:
        for tid in list(self.tasks):
            self.cancel(tid)

    async def run(self, task: Task, steps: list[tuple[str, Callable]]) -> Task:
        """steps: [(label, async callable returning str output)]. Streams into task.logs."""
        task.status = "running"
        total = max(len(steps), 1)
        for i, (label, fn) in enumerate(steps):
            while task.id in self._pause:
                await asyncio.sleep(0.2)
            if task.id in self._cancel:
                task.status = "cancelled"
                task.ended = time.time()
                return task
            task.logs.append(f"→ {label}")
            try:
                out = await fn()
                task.logs.append(f"✓ {label}: {str(out)[:300]}")
            except asyncio.CancelledError:
                task.status = "cancelled"
                task.ended = time.time()
                return task
            except Exception as e:  # never silently fail (§32)
                task.logs.append(f"✗ {label} FAILED: {e}")
                task.status = "failed"
                task.output = f"{label} failed: {e}. "
                task.ended = time.time()
                return task
            task.progress = (i + 1) / total
        task.status = "completed"
        task.ended = time.time()
        return task
