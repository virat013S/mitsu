"""System tray (§16). Close ≠ quit; background work continues."""
from __future__ import annotations

MENU = ["Open Mitsu", "Stop everything", "Quit Mitsu"]


def run_tray(on_open, on_quit, on_stop=None) -> None:
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        print("tray deps missing: pip install -e '.[tray]' — running without tray")
        return
    img = Image.new("RGB", (64, 64), (10, 10, 12))
    d = ImageDraw.Draw(img)
    d.ellipse([14, 14, 50, 50], fill=(244, 244, 245))
    d.ellipse([24, 26, 30, 32], fill=(10, 10, 12))
    d.ellipse([34, 26, 40, 32], fill=(10, 10, 12))
    items = [pystray.MenuItem("Open Mitsu", lambda: on_open())]
    if on_stop is not None:
        items.append(pystray.MenuItem("Stop everything", lambda: on_stop()))
    items.append(pystray.MenuItem("Quit Mitsu", lambda icon: (on_quit(), icon.stop())))
    icon = pystray.Icon("mitsu", img, "Mitsu", pystray.Menu(*items))
    icon.run()
