"""Permission system for Mitsu — request user approval before system-level commands."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

LOG_FILE = Path.home() / ".mitsu" / "permission_log.json"


def _log_permission(command: str, reason: str, approved: bool) -> None:
    """Log permission requests for audit trail."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "reason": reason,
        "approved": approved,
    }
    try:
        logs = json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []
    except Exception:
        logs = []
    logs.append(entry)
    # Keep last 100 entries
    logs = logs[-100:]
    LOG_FILE.write_text(json.dumps(logs, indent=2))


def request_permission(command: str, reason: str) -> bool:
    """Show approval prompt in terminal. Returns True if approved."""
    print(f"\n{'='*50}")
    print(f"  ⚠️  MITSU PERMISSION REQUEST")
    print(f"{'='*50}")
    print(f"  Command:  {command}")
    print(f"  Reason:   {reason}")
    print(f"{'='*50}")
    try:
        answer = input("  Allow? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"
    approved = answer in ("y", "yes")
    _log_permission(command, reason, approved)
    return approved


def run_with_permission(
    command: str,
    reason: str,
    needs_sudo: bool = False,
    capture_output: bool = True,
) -> dict:
    """Execute a command with optional sudo, after user approval."""
    full_command = f"sudo {command}" if needs_sudo else command

    if not request_permission(full_command, reason):
        return {
            "success": False,
            "error": "Permission denied by user",
            "stdout": "",
            "stderr": "",
        }

    try:
        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=capture_output,
            text=True,
            timeout=120,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out after 120 seconds",
            "stdout": "",
            "stderr": "",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "stdout": "",
            "stderr": "",
        }


def check_sudo_available() -> bool:
    """Check if sudo is available on this system."""
    try:
        result = subprocess.run(
            "sudo -n true",
            shell=True,
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


# ── Tool risk classification ───────────────────────────────────────────────
# LOW:      read-only / system information.
# MEDIUM:   application control, file modification, browser automation.
# HIGH:     sending messages, shell execution, installs, data deletion.
# CRITICAL: irreversible / destructive operations (power, disk destructive).

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_CRITICAL = "critical"

TOOL_RISK: dict[str, str] = {
    # Read-only / informational
    "web_search": RISK_LOW,
    "deep_research": RISK_LOW,
    "flight_finder": RISK_LOW,
    "youtube_video": RISK_LOW,
    "task_status": RISK_LOW,
    "check_messages": RISK_LOW,
    "screen_process": RISK_LOW,
    "graphics_quality": RISK_LOW,
    "mitsu_ui_control": RISK_LOW,
    "save_memory": RISK_LOW,
    # Application control / file modification / browser automation
    "open_app": RISK_MEDIUM,
    "browser_control": RISK_MEDIUM,
    "file_controller": RISK_MEDIUM,
    "file_processor": RISK_MEDIUM,
    "code_helper": RISK_MEDIUM,
    "dev_agent": RISK_MEDIUM,
    "media_control": RISK_MEDIUM,
    "desktop_control": RISK_MEDIUM,
    "computer_settings": RISK_MEDIUM,
    "reminder": RISK_MEDIUM,
    "prepare_message_reply": RISK_MEDIUM,
    "create_presentation": RISK_MEDIUM,
    "agent_task": RISK_MEDIUM,
    "game_updater": RISK_MEDIUM,
    # Sending / shell execution / deletion-capable
    "send_message": RISK_HIGH,
    "email_control": RISK_HIGH,
    "computer_control": RISK_HIGH,
}

# Sub-actions that escalate to CRITICAL regardless of their tool's level.
CRITICAL_PATTERNS = (
    "shutdown", "restart", "reboot", "poweroff", "halt",
    "rm -rf /", "mkfs", "format",
)


def tool_risk(tool_name: str, parameters: dict | None = None) -> str:
    """Risk level for a tool call, escalated by critical parameters."""
    base = TOOL_RISK.get(tool_name, RISK_MEDIUM)
    if parameters:
        blob = " ".join(str(v).lower() for v in parameters.values())
        if any(pat in blob for pat in CRITICAL_PATTERNS):
            return RISK_CRITICAL
    return base


def needs_approval(tool_name: str, parameters: dict | None = None) -> bool:
    """True when a tool call requires explicit user approval."""
    return tool_risk(tool_name, parameters) in (RISK_HIGH, RISK_CRITICAL)
