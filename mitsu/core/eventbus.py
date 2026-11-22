"""In-process event bus — one place where the UI and every module meet.

Topics are strings ("chat.reply", "voice.wake", "su.command"…); any module may
publish, the server relays everything to the HUD over the socket. No globals,
no circular imports.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable

_sub: dict[str, list[Callable[[dict], Awaitable[None]]]] = defaultdict(list)


def on(topic: str, fn: Callable[[dict], Awaitable[None]]) -> None:
    _sub[topic].append(fn)


def off(topic: str, fn: Callable[[dict], Awaitable[None]]) -> None:
    try:
        _sub[topic].remove(fn)
    except ValueError:
        pass


async def emit(topic: str, data: dict | None = None) -> None:
    data = {"topic": topic, **(data or {})}
    for fn in list(_sub.get(topic, ()) + _sub.get("*", ())):
        try:
            r = fn(data)
            if asyncio.iscoroutine(r):
                await r
        except Exception:  # a crashed listener never breaks the publisher
            pass


def emit_nowait(topic: str, data: dict | None = None) -> None:
    """Fire-and-forget from sync code; safe when no loop is running."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(emit(topic, data))
    except RuntimeError:
        pass
