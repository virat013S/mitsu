"""Mitsu CLI.

  mitsu              → native desktop window (fallback: browser + URL print)
  mitsu serve        → serve UI (browser mode), print URL
  mitsu native       → force native window
  mitsu chat "..."   → one-shot terminal chat (no UI)
  mitsu say "..."    → speak text aloud (server voice)
  mitsu listen [N]   → record mic N sec, transcribe, chat
  mitsu --help       → this help
"""
from __future__ import annotations

import argparse
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mitsu", description="Mitsu — desktop AI companion")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--no-tray", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("serve", help="serve UI for browser")
    s.add_argument("--open", action="store_true", help="open browser automatically")
    s.add_argument("--no-tray", action="store_true")
    sub.add_parser("native", help="open native desktop window")
    c = sub.add_parser("chat", help="one-shot terminal chat")
    c.add_argument("text", nargs="+")
    c.add_argument("--provider", default=None)
    c.add_argument("--model", default=None)
    s = sub.add_parser("say", help="speak text aloud")
    s.add_argument("text", nargs="+")
    s.add_argument("--voice", default=None)
    li = sub.add_parser("listen", help="mic -> transcribe -> chat")
    li.add_argument("seconds", nargs="?", type=int, default=30)
    li.add_argument("--voice", default=None)
    sub.add_parser("autostart", help="install login autostart (.desktop / shortcut)")
    su = sub.add_parser("su", help="super user: setup <pass> | unlock <pass> | disable | status")
    su.add_argument("action", choices=["setup", "unlock", "disable", "status"])
    su.add_argument("passphrase", nargs="?", default="")
    pp = sub.add_parser("pet", help="detached companion window")
    pp.add_argument("--windowed", action="store_true",
                    help="normal desktop window instead of overlay")
    sub.add_parser("doctor", help="self-diagnosis: paths, voice, mic, providers")
    return p
    return p


def main(argv: list[str] | None = None) -> None:
    import os
    args = build_parser().parse_args(argv)
    os.environ.setdefault("MITSU_PORT", str(args.port))
    os.environ.setdefault("MITSU_HOST", args.host)

    if args.cmd == "chat":
        import asyncio
        from mitsu.brain.chat import reply
        from mitsu.brain.memory.store import MemoryStore
        from mitsu.core.profile import UserProfile
        text = " ".join(args.text)
        async def go():
            r = await reply(text, UserProfile.load(), MemoryStore.load(),
                            args.provider, args.model)
            print(f"[Mitsu · {r.provider}/{r.model}]\n{r.text}")
        asyncio.run(go())
        return

    if args.cmd == "say":
        import asyncio as _a
        from mitsu.core.profile import UserProfile as _UP
        from mitsu.voice import server_tts as _ST
        text = " ".join(args.text)
        async def say():
            wav = await _ST.synthesize(text, _UP.load().speech_rate,
                                       args.voice or _UP.load().server_voice)
            import tempfile as _t, subprocess as _sp, shutil as _sh
            with _t.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav)
                p = f.name
            player = _sh.which("paplay") or _sh.which("aplay") or _sh.which("ffplay")
            if not player:
                print("(no audio player found; text was: " + text + ")")
                return
            _sp.run([player, p] + (["-nodisp", "-autoexit"] if player.endswith("ffplay") else []),
                    capture_output=True)
        _a.run(say())
        return

    if args.cmd == "listen":
        import asyncio as _a
        from mitsu.brain.chat import reply as _reply
        from mitsu.brain.memory.store import MemoryStore as _MS
        from mitsu.core.profile import UserProfile as _UP2
        from mitsu.voice import server_stt as _SST
        print(f"listening (auto-stops on silence, max {args.seconds}s) — speak now…")
        cap = _SST.record_vad(args.seconds)
        if not cap["heard_speech"]:
            print("(heard nothing — mic may be muted or missing)")
            return
        res = _SST.transcribe_file(cap["path"])
        print(f"heard: {res['text'] or '(nothing)'} [snr {res.get('snr_after', 0)}dB, {res.get('speech_sec', 0)}s speech]")
        if res["text"]:
            async def go():
                r = await _reply(res["text"], _UP2.load(), _MS.load())
                print(f"[Mitsu · {r.provider}/{r.model}]\n{r.text}")
            _a.run(go())
        return

    if args.cmd == "pet":
        from mitsu.pet.window import open_pet
        open_pet(args.host, args.port, windowed=getattr(args, "windowed", False))
        return

    if args.cmd == "autostart":
        import pathlib
        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                                 winreg.KEY_SET_VALUE)
            if getattr(sys, "frozen", False):
                target = sys.argv[0]
                launch = pathlib.Path(target).with_name("mitsu.bat")
                launch.write_text(f'@echo off\r\nstart "" "{target}"\r\n')
                local = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WindowsApps"
                try:
                    local.mkdir(parents=True, exist_ok=True)
                    shutil.copy(launch, local / "mitsu.bat")
                except OSError:
                    pass
                # Start Menu shortcut
                smenu = (pathlib.Path(os.environ.get("APPDATA", "")) / "Microsoft"
                         / "Windows" / "Start Menu" / "Programs" / "Mitsu.lnk")
                try:
                    from subprocess import run as _run
                    _run(["powershell", "-NoProfile", "-Command",
                          f"$s=(New-Object -ComObject WScript.Shell);"
                          f"$s.CreateShortcut('{smenu}').TargetPath='{target}';"
                          f"$s.CreateShortcut('{smenu}').Save()"],
                         capture_output=True, timeout=20)
                except Exception:
                    pass
                cmd = f'"{target}"'
            else:
                cmd = f'"{sys.executable}" "{pathlib.Path(__file__).resolve()}"'
            winreg.SetValueEx(key, "Mitsu", 0, winreg.REG_SZ, cmd)
            print("autostart + Start Menu + `mitsu` command installed")
            return
        try:
            exe = shutil.which("mitsu") or "mitsu"
        except Exception:
            exe = "mitsu"
        desk = pathlib.Path("~/.config/autostart/mitsu.desktop").expanduser()
        desk.parent.mkdir(parents=True, exist_ok=True)
        desk.write_text(
            "[Desktop Entry]\nType=Application\nName=Mitsu\n"
            f"Exec={exe}\n"
            "Terminal=false\nX-GNOME-Autostart-enabled=true\n")
        apps = pathlib.Path("~/.local/share/applications/mitsu.desktop").expanduser()
        apps.parent.mkdir(parents=True, exist_ok=True)
        apps.write_text(
            "[Desktop Entry]\nType=Application\nName=Mitsu\n"
            "Comment=JARVIS-style desktop AI companion\n"
            "Categories=Utility;Development;Network;\n"
            f"Exec={exe}\n"
            "Terminal=false\nStartupNotify=true\n")
        print("menu shortcut + autostart installed:", apps, desk)
        return

    if args.cmd == "su":
        from mitsu.security import su
        if args.action == "setup":
            import getpass
            if not args.passphrase:
                print("(pass-phase: 4+ words/chars; never stored, only a digest)")
            r = su.setup(args.passphrase or getpass.getpass("pass-phase: "))
        elif args.action == "unlock":
            import getpass
            r = su.unlock(args.passphrase or getpass.getpass("pass-phase: "))
        elif args.action == "disable":
            r = su.disable()
        else:
            r = su.status()
            print(r)
            return
        print(r)
        return

    if args.cmd == "doctor":
        import json as _j
        from mitsu.core import paths as _cfg
        from mitsu.core.profile import UserProfile as _UP
        from mitsu.providers.registry import list_configured
        from mitsu.voice import server_tts as _ST
        print(f"data dir : {_cfg.data_dir()}")
        p = _UP.load()
        print(f"profile  : {p.display_name or '(no name)'} · voice={p.server_voice} · {p.default_provider}/{p.default_model}")
        st = _ST.status()
        print(f"tts      : piper={st['piper']} espeak={st['espeak']} dir={st['voices_dir']} models={st['models_found']}")
        try:
            from mitsu.voice import server_stt as _SST
            d = _SST.doctor()
            print(f"mic      : recorder={d['recorder']} sources={len(d['sources'])}")
            for h in d["hints"]:
                print(f"           ! {h}")
        except Exception as e:
            print(f"mic      : STT unavailable ({e})")
        try:
            from mitsu.voice import wake as _W
            w = _W.status()
            print(f"wake     : available={w['available']} mitsu_word={w.get('mitsu_word')}")
        except Exception as e:
            print(f"wake     : unavailable ({e})")
        for pr in list_configured():
            print(f"provider : {pr['name']} [{pr['kind']}] key={'yes' if pr['has_key'] else 'NO'}")
        return

    if args.cmd == "serve":
        if args.open:
            import threading, webbrowser
            from mitsu.core.paths import APP_HOST, APP_PORT
            threading.Timer(1.2, lambda: webbrowser.open(f"http://{APP_HOST}:{APP_PORT}")).start()
        from mitsu.server.api import run
        run()
        return

    # default + `native`: desktop window, graceful fallback to serve+open browser.
    # GTK rule (Linux): ONE GLib main context per process. The pywebview window
    # must own the main thread ALONE — a tray GLib loop started earlier steals
    # the default context and kills the window (g_application_run critical).
    # So: window first; tray only in the fallback server mode (or on Windows,
    # where the tray is WinForms-based and harmless).
    no_tray = getattr(args, "no_tray", False)
    if sys.platform == "win32" and not no_tray:
        _start_tray()
    try:
        from mitsu.native import open_window
        open_window()
        return
    except Exception as e:
        print(f"app window unavailable ({e})")
        if not no_tray and sys.platform != "win32":
            _start_tray()
        from mitsu.core.paths import APP_HOST as _H, APP_PORT as _P
        print(f"serving for browser instead:  ==>  http://{_H}:{_P}  <==")
        import webbrowser
        from mitsu.core.paths import APP_HOST, APP_PORT
        import threading
        threading.Timer(1.2, lambda: webbrowser.open(f"http://{APP_HOST}:{APP_PORT}")).start()
        from mitsu.server.api import run
        run()


def _start_tray() -> None:
    try:
        import threading
        import urllib.request
        from mitsu.core import paths as _cfg
        from mitsu.tray import app as tray

        def _open():
            try:
                from mitsu.native import show_window
                show_window()
            except Exception:
                print(f"Mitsu is running at http://{_cfg.APP_HOST}:{_cfg.APP_PORT}")

        def _stop():
            try:
                req = urllib.request.Request(
                    f"http://{_cfg.APP_HOST}:{_cfg.APP_PORT}/api/stop", method="POST")
                urllib.request.urlopen(req, timeout=5)
                print("stopped everything")
            except Exception as e:
                print(f"stop failed ({e})")

        def _quit():
            from mitsu.native import quit_app
            quit_app()

        threading.Thread(
            target=tray.run_tray,
            kwargs={"on_open": _open, "on_quit": _quit, "on_stop": _stop},
            daemon=True).start()
    except Exception as e:
        print(f"tray unavailable ({e}); continuing without it")


if __name__ == "__main__":
    main()
