"""Multi-agent pipeline (§6/§27 MVP): planner → coder → reviewer → fixer.

Each stage records which agent+model did it so the UI can show attribution.
Heavy work runs inside TaskManager so progress/logs/cancel all work.
"""
from __future__ import annotations

from ..agents.registry import get_agent
from ..brain.memory.store import MemoryStore
from ..core.profile import UserProfile
from ..providers.base import ChatMessage
from ..providers.registry import get_provider
from ..tasks.manager import TaskManager


async def _ask(agent_id: str, user_text: str, profile: UserProfile,
               provider: str, model: str) -> str:
    agent = get_agent(agent_id)
    sys = (f"You are Mitsu's {agent.name}. {agent.system_addendum}".strip())
    msgs = [ChatMessage(role="system", content=sys),
            ChatMessage(role="user", content=user_text)]
    res = await get_provider(provider).chat(msgs, model)
    return res.text


async def build_project(goal: str, dest: str, profile: UserProfile, mem: MemoryStore,
                        tm: TaskManager, provider: str, model: str,
                        on_event=None, stage_models: dict | None = None):
    """Create a task that plans, scaffolds, writes files, and reviews.

    stage_models: {"plan": (provider, model), "implement": ..., "review": ...}
    lets different models handle different stages (§27 AI-to-AI collaboration).
    Each stage log records which agent+model did it (attribution).
    """
    from ..tools import files as F
    from ..permissions import policy
    import uuid
    grant = uuid.uuid4().hex
    policy.grant(grant)
    task = tm.create(f"Build: {goal[:60]}", agent="coding", model=f"{provider}/{model}")
    sm = stage_models or {}

    async def ask_stage(stage: str, agent_id: str, prompt: str) -> str:
        prov, mod = sm.get(stage, (provider, model))
        text = await _ask(agent_id, prompt, profile, prov, mod)
        task.logs.append(f"[{stage} · {agent_id} · {mod}] done")
        return text

    async def emit(kind: str, text: str):
        if on_event:
            await on_event({"type": "activity", "task": task.id, "kind": kind, "text": text})

    async def plan():
        await emit("step", "Planning…")
        plan_text = await ask_stage("plan", "planning", f"Goal: {goal}\nTarget dir: {dest}\n"
                               "Respond with an ordered file list + build steps.")
        task.logs.append("PLAN:\n" + plan_text[:2000])
        mem.remember_long(f"Project plan for {goal[:80]}")
        return "plan ready"

    async def scaffold():
        await emit("step", "Creating project…")
        from ..workspace.projects import scaffold
        kind = "web" if any(w in goal.lower() for w in ("website", "portfolio", "react", "site")) else "python"
        scaffold(dest, kind, "app", grant)
        return f"scaffolded {kind}/app"

    async def implement():
        await emit("step", "Writing code (coding agent)…")
        code = await ask_stage("implement", "coding", f"Goal: {goal}\nWrite the main source file content only, no prose.")
        F.write(dest + "/app", "main.txt", code[:20000], grant)
        return "code written"

    async def review():
        await emit("step", "Reviewing (reviewer)…")
        verdict = await ask_stage("review", "debugging", f"Goal: {goal}\nReview for bugs; reply FIXED: or ISSUE: …")
        task.logs.append("REVIEW:\n" + verdict[:2000])
        return "review done"

    async def run_all():
        await tm.run(task, [("plan", plan), ("scaffold", scaffold),
                            ("implement", implement), ("review", review)])
        await emit("done", f"Task {task.status}")
        policy.revoke(grant)

    return task, run_all
