"""Terminal tool (§8/§10). CONFIRM for run, SENSITIVE for destructive/sudo.

Never silently destructive (§7/§32): destructive commands require a grant token
issued from the UI approve button. Sudo flows through permissions/sudo.py which
always prompts for the password out-of-band when no unprivileged way exists.
"""
from __future__ import annotations

import asyncio
import shlex

from ..permissions import policy
from ..permissions.sudo import plan_privilege, request_sudo, run_elevated

DESTRUCTIVE_HINTS = ("rm -rf", "mkfs", "dd if=", "> /dev/", "format", ":(){:|:&};:")


def needs_approval(cmd: str) -> bool:
    return True  # every exec is at least CONFIRM


def is_destructive(cmd: str) -> bool:
    c = cmd.lower()
    return any(h in c for h in DESTRUCTIVE_HINTS) or "sudo" in c


async def run(cmd: str, cwd: str = ".", granted_token: str = "",
              password_provider=None, timeout: float = 120) -> dict:
    level = policy.SENSITIVE if is_destructive(cmd) else policy.CONFIRM
    if not granted_token or not policy.is_granted(granted_token):
        policy.log("terminal", f"{cmd} (denied: no grant)", level, granted=False)
        raise PermissionError(f"running commands needs approval ({level}). Approve in Mitsu UI first.")
    argv = shlex.split(cmd)
    plan = plan_privilege(argv)
    if plan.mode == "sudo-required" or (argv and argv[0] == "sudo"):
        inner = argv[1:] if argv and argv[0] == "sudo" else argv
        pw = await request_sudo("terminal command needs elevation", inner, password_provider)
        cp = await run_elevated(inner, pw, timeout)
        policy.log("terminal", f"sudo {cmd} → rc={cp.returncode}", policy.SENSITIVE)
        return {"rc": cp.returncode, "stdout": _dec(cp.stdout), "stderr": _dec(cp.stderr), "elevated": True}
    proc = await asyncio.create_subprocess_shell(
        cmd, cwd=cwd or ".",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        raise TimeoutError(f"command timed out after {timeout}s")
    policy.log("terminal", f"{cmd} → rc={proc.returncode}", level)
    return {"rc": proc.returncode or 0, "stdout": out.decode(errors="replace")[-8000:],
            "stderr": err.decode(errors="replace")[-8000:], "elevated": False}


def _dec(b) -> str:
    if isinstance(b, (bytes, bytearray)):
        return bytes(b).decode(errors="replace")[-8000:]
    return str(b or "")
