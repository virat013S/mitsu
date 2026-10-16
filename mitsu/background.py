"""Background mode (§24): scheduler tick + digest, runs inside the server process.

No separate daemon: the server starts this loop on startup. Disable via
Settings → Background. Long jobs keep running because tasks live server-side.
"""
from __future__ import annotations

import asyncio

_enabled = True


def set_enabled(v: bool) -> None:
    global _enabled
    _enabled = v


async def loop(scheduler, notify, chat_fn, interval: int = 30,
               context=None) -> None:
    """context: () -> (tasks_manager|None, idle_minutes). Enables event rules."""
    while True:
        try:
            if _enabled:
                for rule in scheduler.due():
                    scheduler.mark_ran(rule)
                    await _fire(rule, notify, chat_fn)
                if context:
                    tm, idle_min = context()
                    for rule in scheduler.due_events(tm, idle_min):
                        scheduler.mark_ran(rule)
                        await _fire(rule, notify, chat_fn)
        except Exception:
            pass
        await asyncio.sleep(interval)


async def _fire(rule, notify, chat_fn) -> None:
    p = rule.payload or {}
    if rule.action == "notify":
        notify(rule.name, p.get("body", "Scheduled reminder"))
    elif rule.action == "chat":
        try:
            text = await chat_fn(p.get("prompt", rule.name))
            notify(rule.name, text[:300])
        except Exception as e:
            notify(rule.name + " (failed)", str(e)[:200])
