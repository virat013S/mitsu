"""Agent definitions (§6). Phase 2: planner → coder → reviewer → debugger pipeline."""
from __future__ import annotations

from dataclasses import dataclass

@dataclass
class Agent:
    id: str
    name: str
    description: str
    system_addendum: str = ""


AGENTS = [
    Agent("general", "General Assistant", "Everyday chat, explanations, planning"),
    Agent("coding", "Coding Agent", "Writes/edits code, multi-file changes",
          "You write clean, complete, working code. Explain what you changed and why."),
    Agent("planning", "Planning Agent", "Breaks big goals into ordered steps",
          "Always respond with a numbered step plan before any implementation."),
    Agent("debugging", "Debugging Agent", "Diagnoses errors, proposes minimal fixes",
          "Given an error and code, identify the root cause, then give the smallest fix."),
    Agent("docs", "Documentation Agent", "READMEs, docstrings, guides",
          "Write clear docs with setup, usage, and troubleshooting sections."),
    Agent("research", "Research Agent", "Web/local research → cited summary (Phase 3 engine)"),
]


def get_agent(aid: str) -> Agent:
    for a in AGENTS:
        if a.id == aid:
            return a
    return AGENTS[0]


def list_agents() -> list[dict]:
    return [{"id": a.id, "name": a.name, "description": a.description} for a in AGENTS]
