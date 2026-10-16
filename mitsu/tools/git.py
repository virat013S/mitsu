"""Git operations (§8/§9) via the permission-gated shell tool."""
from __future__ import annotations

from . import shell


async def run_git(args: list[str], cwd: str, granted_token: str) -> dict:
    safe = {"status", "log", "diff", "branch", "remote", "fetch"}
    cmd = "git " + " ".join(args)
    # read-only git commands still go through the gate (CONFIRM) but UI
    # auto-grants SAFE verbs; keep the audit trail either way.
    _ = safe
    return await shell.run(cmd, cwd=cwd, granted_token=granted_token)
