# PyInstaller spec for the portable Mitsu build.
#
# The app is a small FastAPI server plus a web UI. The UI and skill notes are
# data files, not importable modules, so they are added explicitly. Voice
# models stay in the user data directory and are downloaded by the setup
# screen; they are not part of the build.
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).parent
DIST = ROOT / "dist"

datas = [
    (str(ROOT / "ui"), "ui"),
    (str(ROOT / "mitsu" / "skills"), "mitsu/skills"),
]
binaries = []
hiddenimports = collect_submodules("mitsu")

# Packages with dynamic imports, data files, or native libraries. collect_all
# is deliberately used here: missing a backend shows up as a blank window or a
# dead microphone in a one-folder build, which is much worse than a larger zip.
PACKAGES = [
    "uvicorn", "fastapi", "starlette", "pydantic", "pydantic_core",
    "httpx", "httpcore", "anyio", "websockets", "yaml", "watchfiles",
    "httptools", "uvloop", "python_multipart",
    "keyring", "webview", "pystray", "PIL",
    "numpy", "sounddevice", "faster_whisper", "ctranslate2", "tokenizers",
    "huggingface_hub", "av", "onnxruntime",
    "gi", "clr_loader", "pythonnet", "win32ctypes",
]
for name in PACKAGES:
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(name)
    except Exception:
        continue
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# pywebview's Linux backend imports these only after the GTK runtime is
# present, so static analysis alone does not see them.
hiddenimports += [
    "gi", "gi.repository.Gtk", "gi.repository.Gdk", "gi.repository.Gio",
    "gi.repository.GLib", "gi.repository.AppIndicator3",
    "webview.platforms.gtk", "webview.platforms.cocoa",
    "webview.platforms.winforms", "webview.platforms.qt",
    "pystray._xorg", "pystray._win32", "pystray._darwin",
    "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto", "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on", "uvicorn.lifespan.off",
]

a = Analysis(
    [str(ROOT / "mitsu" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest", "tkinter", "matplotlib", "pandas", "IPython", "jupyter",
        "notebook", "torch", "tensorflow", "transformers", "PyQt5", "PySide6",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="mitsu",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="mitsu",
)

if __import__("sys").platform == "darwin":
    app = BUNDLE(
        coll,
        name="Mitsu.app",
        icon=None,
        bundle_identifier="com.mitsu.app",
        info_plist={
            "CFBundleDisplayName": "Mitsu",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
