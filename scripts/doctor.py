"""mitsu --doctor: diagnose environment, providers, and capabilities.

Every check reports STATUS / REASON / RECOMMENDED ACTION. Read-only:
never sends messages, never modifies state, never touches secrets.
"""
from __future__ import annotations

import os
import platform
import sys
from pathlib import Path


def _check(name: str, status: str, reason: str, action: str = "") -> dict:
    return {"name": name, "status": status, "reason": reason, "action": action}


def run_checks() -> list[dict]:
    base_dir = Path(__file__).resolve().parent.parent
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    checks: list[dict] = []

    # Python runtime
    ok = sys.version_info >= (3, 11)
    checks.append(_check(
        "python", "PASS" if ok else "FAIL",
        f"Python {platform.python_version()}",
        "" if ok else "Install Python 3.11 or newer."))

    # Core imports
    try:
        import core.providers  # noqa: F401
        import core.profile  # noqa: F401
        import core.events  # noqa: F401
        import core.platform  # noqa: F401
        import core.permissions  # noqa: F401
        import core.skills  # noqa: F401
        checks.append(_check("core_imports", "PASS", "core modules import cleanly"))
    except Exception as exc:
        checks.append(_check("core_imports", "FAIL", f"import failed: {exc}",
                             "Install dependencies: pip install -r requirements.txt"))

    # Providers (no network side effects beyond status probes)
    try:
        from core.providers import (check_provider_status, provider_requires_key,
                                    get_provider)
    except ImportError as exc:
        checks.append(_check("providers", "SKIP",
                             f"provider modules unavailable: {exc}",
                             "Install dependencies: pip install -r requirements.txt"))
    else:
        try:
            active = get_provider()
            checks.append(_check("provider_selection", "PASS",
                                 f"active provider: {active}"))
            for name in ("ollama", "openrouter", "gemini"):
                key = provider_requires_key(name)
                if key and not os.environ.get(key):
                    checks.append(_check(
                        f"provider:{name}", "SKIP",
                        f"{key} not set",
                        f"Set {key} to use {name}, or pick another provider."))
                    continue
                try:
                    status = check_provider_status(name)
                    if status.get("available"):
                        checks.append(_check(f"provider:{name}", "PASS",
                                             status.get("model", name)))
                    else:
                        checks.append(_check(
                            f"provider:{name}", "SKIP",
                            status.get("error") or "unavailable",
                            "Start the service or set credentials to enable."))
                except Exception as exc:
                    checks.append(_check(f"provider:{name}", "SKIP",
                                         f"probe failed: {exc}"))
        except Exception as exc:
            checks.append(_check("providers", "SKIP",
                                 f"provider check failed: {exc}"))

    # Identity
    try:
        from core.profile import profile_snapshot
        snap = profile_snapshot()
        if snap["guest"]:
            checks.append(_check("identity", "SKIP", "no name stored (guest mode)",
                                 "Launch Mitsu and answer 'What should I call you?'"))
        else:
            checks.append(_check("identity", "PASS",
                                 f"name stored: {snap['display_name']}"))
    except Exception as exc:
        checks.append(_check("identity", "FAIL", f"profile unreadable: {exc}"))

    # Model selection + capabilities
    try:
        from core.models import (check_model, get_selection, model_supports,
                                 TOOL_CALLS, IMAGES, AUDIO_IN, LIVE_VOICE)
        sel = get_selection()
        provider, model = sel["provider"], sel["model"]
        checks.append(_check("ai_selection", "PASS", f"{provider} / {model}"))
        conn = check_model(provider, model)
        if conn.get("available"):
            checks.append(_check("ai_connection", "PASS",
                                 f"{provider} / {model} reachable"))
        else:
            checks.append(_check("ai_connection", "SKIP",
                                 conn.get("error") or "unreachable",
                                 "Pick an available model in Settings → AI MODEL."))
        for cap, label in ((TOOL_CALLS, "tool calling"), (IMAGES, "vision"),
                           (AUDIO_IN, "voice input"), (LIVE_VOICE, "live voice")):
            supported = model_supports(provider, model, cap)
            checks.append(_check(
                f"ai_{label.replace(' ', '_')}",
                "PASS" if supported else "SKIP",
                f"{label}: {'supported' if supported else 'unavailable'}"))
    except ImportError as exc:
        checks.append(_check("ai_selection", "SKIP",
                             f"model modules unavailable: {exc}",
                             "Install dependencies: pip install -r requirements.txt"))
    except Exception as exc:
        checks.append(_check("ai_selection", "SKIP", f"selection unreadable: {exc}"))

    # Memory
    try:
        from memory.memory_manager import load_memory
        mem = load_memory()
        checks.append(_check("memory", "PASS",
                             f"memory readable ({len(mem)} categories)"))
    except Exception as exc:
        checks.append(_check("memory", "FAIL", f"memory unreadable: {exc}"))

    # Platform capabilities
    try:
        from core.platform import capability_summary
        summary = capability_summary()
        unsupported = [n for n, c in summary["capabilities"].items()
                       if c["state"] == "unavailable"]
        checks.append(_check(
            "platform", "PASS" if not unsupported else "SKIP",
            f"{summary['os']}/{summary['desktop']}/{summary['display']}",
            "" if not unsupported
            else f"Unavailable: {', '.join(unsupported)}"))
        for cname in ("screenshots", "clipboard", "microphone",
                      "notifications", "window_management", "battery"):
            cap = summary["capabilities"].get(cname, {})
            state = cap.get("state", "unavailable")
            checks.append(_check(
                f"capability:{cname}",
                "PASS" if state in ("supported", "partial") else "SKIP",
                f"{state}: {cap.get('reason', '')}"))
    except Exception as exc:
        checks.append(_check("platform", "FAIL", f"capability probe failed: {exc}"))

    # Optional dependencies
    for module, label in (("PyQt6", "desktop UI"), ("playwright", "browser automation"),
                          ("sounddevice", "audio"), ("mss", "screenshots"),
                          ("keyring", "credential storage")):
        try:
            __import__(module)
            checks.append(_check(f"dep:{module}", "PASS", f"{label} available"))
        except ImportError:
            checks.append(_check(f"dep:{module}", "SKIP", f"{module} not installed",
                                 f"pip install {module} to enable {label}"))

    # Storage
    try:
        home = Path.home() / ".mitsu"
        home.mkdir(parents=True, exist_ok=True)
        checks.append(_check("storage", "PASS", f"writable: {home}"))
    except Exception as exc:
        checks.append(_check("storage", "FAIL", f"cannot write ~/.mitsu: {exc}"))

    return checks


def main(argv: list[str] | None = None) -> int:
    checks = run_checks()
    width = max(len(c["name"]) for c in checks)
    failed = 0
    print("\nMITSU DOCTOR\n")
    for check in checks:
        mark = {"PASS": "[ok]  ", "SKIP": "[skip]", "FAIL": "[FAIL]"}[check["status"]]
        print(f"  {mark} {check['name']:<{width}}  {check['reason']}")
        if check["action"]:
            print(f"           -> {check['action']}")
        if check["status"] == "FAIL":
            failed += 1
    print(f"\n{len(checks)} checks: "
          f"{sum(1 for c in checks if c['status'] == 'PASS')} pass, "
          f"{sum(1 for c in checks if c['status'] == 'SKIP')} skipped, "
          f"{failed} failed.\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
