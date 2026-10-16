"""Sudo helper — asks for the sudo password whenever needed with no other way.

Flow (§10, §20 + user requirement):
  1. plan_privilege() checks for a non-privileged alternative first.
  2. If sudo is truly required, the caller MUST obtain approval + password
     via request_sudo(), which is fulfilled out-of-band (pkexec / keychain /
     masked UI field / /dev/tty getpass). The password is NEVER a chat string,
     NEVER in argv/env/logs.
  3. run_elevated() pipes it via `sudo -S` stdin, closes stdin immediately,
     enforces a timeout, supports cancellation, and audits WHAT ran (not the secret).

GUI wiring: server exposes WS events `permission.request` /
`permission.resolve`. Headless wiring falls back to getpass on /dev/tty.
"""
from __future__ import annotations

import asyncio
import getpass
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import policy

_SECRET_RE = re.compile(r"(api_key|bearer|passwd|password|sudo)", re.I)


def redact(text: str) -> str:
    return _SECRET_RE.sub("***", text)


@dataclass
class PrivilegePlan:
    mode: str  # "unprivileged" | "sudo-required"
    reason: str
    command: list[str]


PRIVILEGED_BINS = frozenset({
    "apt", "apt-get", "dpkg", "pacman", "yay", "paru", "dnf", "yum", "zypper",
    "snap", "modprobe", "insmod", "mount", "umount", "fdisk", "mkfs",
    "iptables", "ufw", "firewall-cmd", "systemctl", "service", "useradd",
    "usermod", "chown", "chmod",
})


def plan_privilege(command: list[str], target: str | None = None) -> PrivilegePlan:
    """Prefer a non-sudo path whenever one exists. Sudo only on evidence."""
    cmd = list(command)
    if not cmd:
        return PrivilegePlan("unprivileged", "empty command", cmd)
    # 0. Explicit sudo prefix → elevation genuinely requested.
    if cmd[0] == "sudo":
        return PrivilegePlan("sudo-required", "explicit sudo prefix", cmd[1:] or cmd)
    # 1. Target checks: writable → no sudo; system-owned → sudo.
    if target:
        try:
            p = Path(target)
            probe = p if p.exists() else p.parent
            if os.access(probe, os.W_OK):
                return PrivilegePlan("unprivileged", f"{target} is writable by you", cmd)
            return PrivilegePlan("sudo-required",
                                 f"{target} is not writable by you", cmd)
        except Exception:
            pass
    joined = " ".join(cmd)
    # 2. Known user-scoped alternatives.
    if "pip install" in joined and "--user" not in joined and "--break-system-packages" not in joined:
        alt = cmd + ["--user"] if cmd[0:2] == ["pip", "install"] or cmd[0:2] == ["pip3", "install"] else cmd
        return PrivilegePlan("unprivileged", "pip --user avoids sudo", alt)
    if cmd[0] == "systemctl" and "--user" not in cmd:
        return PrivilegePlan("unprivileged", "try `systemctl --user` first",
                             ["systemctl", "--user"] + cmd[1:])
    if cmd[0] == "flatpak" and "--user" not in cmd:
        return PrivilegePlan("unprivileged", "flatpak --user avoids sudo",
                             [cmd[0], "--user"] + cmd[1:])
    # 3. Privileged system binaries → sudo (after --user alternatives above).
    if cmd[0] in PRIVILEGED_BINS:
        return PrivilegePlan("sudo-required",
                             f"{cmd[0]} manages the system; no user-scoped alternative applies",
                             cmd)
    # 4. Already root → nothing to prompt for.
    try:
        if os.geteuid() == 0:
            return PrivilegePlan("unprivileged", "already running as root", cmd)
    except AttributeError:
        pass
    # 5. Default: ordinary user command → NO sudo.
    return PrivilegePlan("unprivileged",
                         "runs as your user; no system locations touched", cmd)


async def _acquire_password_gui(prompt: str, timeout: float,
                               password_provider) -> str | None:
    """password_provider: async callable set by the server to pop up masked UI."""
    if password_provider is None:
        return None
    try:
        return await asyncio.wait_for(password_provider(prompt), timeout)
    except Exception:
        return None


def _prompt_tty(prompt: str) -> str:
    try:
        # Prefer the controlling terminal so piped stdin still works.
        with open("/dev/tty", "r+") as tty:
            import termios  # noqa
            return getpass.getpass(prompt, stream=tty)
    except Exception:
        return getpass.getpass(prompt + " ")


async def request_sudo(reason: str, command: list[str],
                       password_provider=None, timeout: float = 120) -> str:
    """Return the sudo password acquired out-of-band, or '' when using pkexec.

    Raises PermissionError on denial/timeout/kill-switch.
    """
    if policy.is_killed():
        raise PermissionError("STOP EVERYTHING is active")
    policy.log("sudo", f"request: {redact(' '.join(command))} ({reason})", policy.SENSITIVE)

    # pkexec handles its own OS dialog — we never touch the password.
    if shutil.which("pkexec"):
        use_pkexec = os.environ.get("MITSU_PREFER_PKEXEC", "1") == "1"
        if use_pkexec and password_provider is None:
            return ""  # signal: run via pkexec
    pw = await _acquire_password_gui(f"[sudo] {reason}\nPassword for sudo:", timeout,
                                     password_provider)
    if pw:
        return pw
    # Headless / CLI fallback.
    loop = asyncio.get_running_loop()
    pw = await loop.run_in_executor(None, _prompt_tty, "[sudo] enter password: ")
    if not pw:
        policy.log("sudo", "denied (empty password)", policy.SENSITIVE, granted=False)
        raise PermissionError("sudo denied by user")
    return pw


async def run_elevated(command: list[str], password: str,
                       timeout: float = 120) -> subprocess.CompletedProcess:
    """Execute with elevation. Password via stdin pipe only; never logged."""
    if policy.is_killed():
        raise PermissionError("STOP EVERYTHING is active")
    if password == "" and shutil.which("pkexec"):
        argv = ["pkexec"] + command
        proc = await asyncio.create_subprocess_exec(
            *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
        return subprocess.CompletedProcess(argv, proc.returncode or 0, out, err)
    if not shutil.which("sudo"):
        raise RuntimeError("neither pkexec nor sudo is available")
    argv = ["sudo", "-S", "-p", "", "--"] + command
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        assert proc.stdin is not None
        proc.stdin.write((password + "\n").encode())
        await proc.stdin.drain()
        proc.stdin.close()
    finally:
        password = ""  # drop reference ASAP
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        raise TimeoutError(f"sudo command timed out after {timeout}s: {command[0]}")
    policy.log("sudo", f"ran: {redact(' '.join(command))} → rc={proc.returncode}",
               policy.SENSITIVE)
    return subprocess.CompletedProcess(argv, proc.returncode or 0, out, err)


async def ensure_elevated(command: list[str], target: str | None = None,
                          password_provider=None, timeout: float = 120,
                          dry_run: bool = False) -> PrivilegePlan | subprocess.CompletedProcess:
    """One-call helper: try unprivileged, else prompt + run elevated."""
    plan = plan_privilege(command, target)
    if plan.mode == "unprivileged" or dry_run:
        return plan
    pw = await request_sudo(plan.reason, plan.command, password_provider)
    return await run_elevated(plan.command, pw, timeout)
