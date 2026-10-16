"""Native desktop window — Mitsu looks like an app, not a browser tab.

Backend: pywebview (GTK/WebKit on Linux, Cocoa on macOS, WebView2 on Windows).
Install: `pip install pywebview` (add `[native]` extra). If unavailable or
headless, raises so the CLI can fall back to browser mode.
"""
from __future__ import annotations

import threading
import time

from .paths import APP_HOST, APP_PORT


def _wait_for_server(timeout: float = 20) -> str:
    import urllib.request
    url = f"http://{APP_HOST}:{APP_PORT}"
    end = time.time() + timeout
    last = None
    while time.time() < end:
        try:
            with urllib.request.urlopen(url + "/api/health", timeout=2) as r:
                if r.status == 200:
                    return url
        except Exception as e:
            last = e
        time.sleep(0.4)
    raise RuntimeError(f"backend did not start ({last})")


_win = None


def show_window() -> None:
    """Restore the hidden window, or open the browser fallback."""
    global _win
    try:
        if _win is not None:
            try:
                _win.restore()
            except Exception:
                pass
            _win.show()
            return
    except Exception:
        pass
    import webbrowser
    from .core import paths as _cfg
    print(f"window not open — use http://{_cfg.APP_HOST}:{_cfg.APP_PORT}")
    try:
        webbrowser.open(f"http://{_cfg.APP_HOST}:{_cfg.APP_PORT}")
    except Exception:
        pass


def quit_app() -> None:
    """Real quit from the tray: destroy window, end process (server is daemon)."""
    global _win
    try:
        if _win is not None:
            _win.destroy()
    except Exception:
        pass
    import os as _os
    _os._exit(0)


def _win_webview2() -> bool:
    """True when Microsoft Edge WebView2 runtime exists (real Chromium engine).

    Without it pywebview falls back to MSHTML (IE) which cannot run the HUD
    and crashes the graphics stack — detect upfront and use the browser.
    """
    import os as _os
    try:
        import winreg as _wr
    except ImportError:
        return True  # not Windows; handled by platform backends below
    try:
        for root in (_wr.HKEY_LOCAL_MACHINE, _wr.HKEY_CURRENT_USER):
            for sub in (r"SOFTWARE\Microsoft\EdgeUpdate\ClientState\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
                        r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\ClientState\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"):
                try:
                    with _wr.OpenKey(root, sub) as k:
                        if _wr.QueryValueEx(k, "pv")[0]:
                            return True
                except OSError:
                    continue
        for base in (_os.environ.get("ProgramFiles(x86)", ""), _os.environ.get("ProgramFiles", ""),
                     _os.environ.get("LOCALAPPDATA", "")):
            if base and _os.path.isdir(_os.path.join(base, "Microsoft", "EdgeWebView")):
                return True
    except Exception:
        pass
    return False


def open_window() -> None:
    import sys as _sys
    global _win
    if _sys.platform == "win32" and not _win_webview2():
        raise RuntimeError(
            "Edge WebView2 runtime not found — Mitsu needs it for the app window. "
            "Install free from Microsoft ('Edge WebView2 Runtime'), or run `mitsu serve` for browser mode.")
    try:
        import webview  # type: ignore
    except ImportError as e:
        raise RuntimeError("pywebview not installed (pip install pywebview)") from e

    from .server.api import run as run_server
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    url = _wait_for_server()

    win = webview.create_window(
        "Mitsu", url,
        width=1200, height=800, min_size=(900, 600),
        background_color="#0c0c0e", text_select=True,
    )
    _win = win

    def _to_tray():
        """Close button → hide to tray, keep serving. Truthy cancels the close."""
        try:
            win.hide()
        except Exception:
            pass
        return True

    try:
        win.events.closing += _to_tray
    except Exception:
        pass
    # pywebview blocks here in the main thread until the window closes.
    # Any engine crash (e.g. missing system webview) falls back to browser.
    try:
        webview.start(debug=False)
    except Exception as e:
        raise RuntimeError(f"app window failed ({e}); use `mitsu serve` for browser mode") from e
    _ = win
