import os
import shlex
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


TERMINAL_CANDIDATES = [
    "ghostty",
    "kitty",
    "alacritty",
    "konsole",
    "gnome-terminal",
    "xfce4-terminal",
    "xterm",
]

PRIVILEGED_PREFIXES = (
    "sudo", "doas", "pkexec",
    "apt", "apt-get", "dpkg", "snap",
    "systemctl", "service",
    "pacman", "dnf", "yum", "zypper",
    "mount", "umount", "swapon", "swapoff",
    "useradd", "userdel", "usermod", "groupadd",
    "passwd", "chpasswd", "visudo",
    "iptables", "nft", "ufw", "firewall-cmd",
    "modprobe", "insmod", "rmmod",
    "shutdown", "reboot", "poweroff", "halt",
)

FORBIDDEN_PATTERNS = (
    "rm -rf /",
    "rm -rf /*",
    "mkfs.",
    ":(){ :|:& };:",
    "> /dev/sda",
    "dd if= of=/dev/",
    "chmod -R 777 /",
)


def _is_privileged(command: str) -> bool:
    cmd = command.strip()
    try:
        first = shlex.split(cmd)[0].lower()
    except Exception:
        first = ""
    base = os.path.basename(first)
    if base in PRIVILEGED_PREFIXES:
        return True
    lowered = cmd.lower()
    if lowered.startswith("sudo ") or lowered.startswith("doas ") or lowered.startswith("pkexec "):
        return True
    for prefix in PRIVILEGED_PREFIXES:
        if re_match_word(lowered, prefix):
            return True
    return False


def re_match_word(text: str, word: str) -> bool:
    import re
    return re.search(rf"(?:^|[;&|]\s*|\bsudo\s+|\bdoas\s+){word}\b", text) is not None


def _find_terminal() -> str | None:
    for term in TERMINAL_CANDIDATES:
        path = shutil.which(term)
        if path:
            return term
    return None


def _terminal_launch_args(terminal: str, script_path: str) -> list[str]:
    if terminal == "gnome-terminal":
        return [terminal, "--", "bash", script_path]
    if terminal == "konsole":
        return [terminal, "-e", "bash", script_path]
    if terminal == "xfce4-terminal":
        return [terminal, "-x", "bash", script_path]
    if terminal in ("ghostty", "kitty"):
        return [terminal, "bash", script_path]
    return [terminal, "-e", "bash", script_path]


def run_command(parameters: dict, player=None, speak=None) -> str:
    command = str(parameters.get("command", "")).strip()
    as_root = bool(parameters.get("as_root", False))
    timeout = int(parameters.get("timeout_seconds", 120) or 120)

    if not command:
        raise ValueError("run_command requires a 'command' parameter.")

    lowered = command.lower()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in lowered:
            msg = f"Refusing to run this command — it looks destructive: {command}"
            print(f"[RunCommand] ⛔ {msg}")
            return msg

    needs_root = as_root or _is_privileged(command)
    print(f"[RunCommand] ▶️ {'(root)' if needs_root else '(user)'} {command}")

    if not needs_root:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path.home()),
            )
            return _format_result(command, result.returncode, result.stdout, result.stderr)
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout} seconds: {command}"
        except Exception as e:
            return f"Command failed to start: {e}"

    terminal = _find_terminal()
    if not terminal:
        return "This command needs administrator rights, but no terminal emulator was found to ask for your password."

    tmp_dir = Path(tempfile.mkdtemp(prefix="mitsu_cmd_"))
    out_file   = tmp_dir / "out.txt"
    err_file   = tmp_dir / "err.txt"
    done_file  = tmp_dir / "done.txt"
    script_file = tmp_dir / "run.sh"

    inner = (
        "#!/bin/bash\n"
        "clear\n"
        "echo 'MITSU needs administrator access for:'\n"
        f"echo '  {command}'\n"
        "echo ''\n"
        f"sudo -p '[sudo] password for MITSU: ' bash -c {_shell_quote(command)}"
        f" > {shlex.quote(str(out_file))} 2> {shlex.quote(str(err_file))}\n"
        f"status=$?\n"
        f"echo $status > {shlex.quote(str(done_file))}\n"
        "echo ''\n"
        "echo 'Done. You may close this window.'\n"
    )
    script_file.write_text(inner, encoding="utf-8")
    os.chmod(script_file, 0o700)

    if speak:
        speak("I need your permission, sir. Please enter your password in the window that just opened.")

    launch_args = _terminal_launch_args(terminal, str(script_file))
    try:
        subprocess.Popen(
            launch_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        return f"Could not open a terminal for the admin password: {e}"

    root_timeout = max(timeout, 300)
    deadline = time.time() + root_timeout
    while time.time() < deadline:
        if done_file.exists():
            break
        time.sleep(0.5)

    status = None
    try:
        status = int(done_file.read_text(encoding="utf-8").strip())
    except Exception:
        pass

    stdout = err = ""
    try:
        stdout = out_file.read_text(encoding="utf-8", errors="replace")
        err = err_file.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import shutil as _shutil
    _shutil.rmtree(tmp_dir, ignore_errors=True)

    if status is None:
        return (
            f"Administrator command did not finish within {root_timeout} seconds "
            f"(window may have been closed): {command}"
        )

    combined_err = err
    if status != 0 and "password" in (stdout + err).lower():
        combined_err += "\n(Sudo password was wrong or cancelled.)"

    return _format_result(command, status, stdout, combined_err)


def _shell_quote(s: str) -> str:
    import shlex as _shlex
    return "'" + s.replace("'", "'\\''") + "'"


def _format_result(command: str, code: int, stdout: str, stderr: str) -> str:
    parts = [f"$ {command}", f"[exit code: {code}]"]
    out = (stdout or "").strip()
    err = (stderr or "").strip()
    if out:
        parts.append(out[:4000])
    if err:
        parts.append(f"errors:\n{err[:2000]}")
    if code == 0 and not out and not err:
        parts.append("(no output)")
    return "\n".join(parts)


if __name__ == "__main__":
    print(run_command({"command": "whoami"}))
