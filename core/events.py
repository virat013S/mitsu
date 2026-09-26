"""Structured event bus — the single channel for task/agent/UI state changes.

Producers (task queue, executor, tools, memory, providers) emit typed
events. Consumers (UI state store, logs, notifications, history,
developer diagnostics) subscribe. No consumer parses human-readable
logs to discover state.

Event types mirror the real lifecycle; only emit events that reflect
real state transitions — never fabricate progress.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

# Task lifecycle
TASK_CREATED = "task_created"
TASK_STARTED = "task_started"
TASK_PLANNING = "task_planning"
TASK_PROGRESS = "task_progress"
TASK_PAUSED = "task_paused"
TASK_RESUMED = "task_resumed"
TASK_CANCELLED = "task_cancelled"
TASK_FAILED = "task_failed"
TASK_COMPLETED = "task_completed"
# Plan / steps
PLAN_CREATED = "plan_created"
STEP_STARTED = "step_started"
STEP_COMPLETED = "step_completed"
STEP_FAILED = "step_failed"
# Tools
TOOL_STARTED = "tool_started"
TOOL_PROGRESS = "tool_progress"
TOOL_COMPLETED = "tool_completed"
TOOL_FAILED = "tool_failed"
# Approvals
APPROVAL_REQUESTED = "approval_requested"
APPROVAL_GRANTED = "approval_granted"
APPROVAL_DENIED = "approval_denied"
# Artifacts / workspace / voice / misc
ARTIFACT_CREATED = "artifact_created"
WORKSPACE_CHANGED = "workspace_changed"
VOICE_STARTED = "voice_started"
VOICE_STOPPED = "voice_stopped"
SPEECH_STARTED = "speech_started"
SPEECH_STOPPED = "speech_stopped"
PROVIDER_CHANGED = "provider_changed"
MEMORY_UPDATED = "memory_updated"
NOTIFICATION_CREATED = "notification_created"


@dataclass
class MitsuEvent:
    type: str
    task_id: str | None = None
    timestamp: float = field(default_factory=time.time)
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


_Subscriber = Callable[[MitsuEvent], None]


class EventBus:
    """Thread-safe publish/subscribe bus with optional type filtering."""

    def __init__(self, max_history: int = 200) -> None:
        self._lock = threading.Lock()
        self._subs: dict[str, _Subscriber] = {}
        self._history: list[MitsuEvent] = []
        self._max_history = max_history

    def subscribe(self, fn: _Subscriber,
                  event_types: list[str] | tuple[str, ...] | None = None) -> str:
        """Subscribe to event types (None = all). Returns a token."""
        token = str(uuid.uuid4())[:8]
        with self._lock:
            self._subs[token] = (fn, set(event_types) if event_types else None)
        return token

    def unsubscribe(self, token: str) -> bool:
        with self._lock:
            return self._subs.pop(token, None) is not None

    def emit(self, event_type: str, task_id: str | None = None,
             **payload: Any) -> MitsuEvent:
        event = MitsuEvent(type=event_type, task_id=task_id, payload=dict(payload))
        with self._lock:
            listeners = list(self._subs.values())
            self._history.append(event)
            del self._history[:-self._max_history]
        for fn, types in listeners:
            if types is not None and event_type not in types:
                continue
            try:
                fn(event)
            except Exception:
                pass
        return event

    def recent(self, event_type: str | None = None,
               task_id: str | None = None,
               limit: int = 50) -> list[MitsuEvent]:
        with self._lock:
            items = list(self._history)
        if event_type is not None:
            items = [e for e in items if e.type == event_type]
        if task_id is not None:
            items = [e for e in items if e.task_id == task_id]
        return items[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._subs.clear()
            self._history.clear()


_bus = EventBus()
_bus_lock = threading.Lock()


def get_bus() -> EventBus:
    return _bus


def emit(event_type: str, task_id: str | None = None, **payload: Any) -> MitsuEvent:
    return _bus.emit(event_type, task_id=task_id, **payload)


def subscribe(fn: _Subscriber,
              event_types: list[str] | tuple[str, ...] | None = None) -> str:
    return _bus.subscribe(fn, event_types)


def unsubscribe(token: str) -> bool:
    return _bus.unsubscribe(token)
