#!/usr/bin/env python3
"""Build a portable Mitsu folder and pack it for the current platform.

Run from the repo root:
    python packaging/build.py

Output:
    dist/mitsu-linux-x64.tar.gz
    dist/mitsu-windows-x64.zip
    dist/mitsu-macos-arm64.zip

The build is intentionally one-folder. A one-file executable would unpack
hundreds of megabytes to a temp directory on every launch, which makes the
first-run voice setup feel broken.
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


def machine() -> str:
    m = platform.machine().lower()
    if m in ("amd64", "x86_64", "x64"):
        return "x64"
    if m in ("arm64", "aarch64"):
        return "arm64"
    return m or "unknown"


def run(cmd: list[str], **kw) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def archive_name() -> str:
    if sys.platform == "win32":
        osname = "windows"
    elif sys.platform == "darwin":
        osname = "macos"
    else:
        osname = "linux"
    return f"mitsu-{osname}-{machine()}"


def executable() -> Path:
    if sys.platform == "darwin":
        return DIST / "Mitsu.app" / "Contents" / "MacOS" / "mitsu"
    if sys.platform == "win32":
        return DIST / "mitsu" / "mitsu.exe"
    return DIST / "mitsu" / "mitsu"


def smoke() -> None:
    exe = executable()
    if not exe.exists():
        raise SystemExit(f"build did not produce {exe}")
    run([str(exe), "--help"], timeout=30)
    with tempfile.TemporaryDirectory(prefix="mitsu-smoke-") as td:
        env = dict(os.environ)
        env["MITSU_DATA_DIR"] = td
        # Doctor imports the voice, provider, and keyring paths without
        # opening a window. It catches missing audio hardware on its own.
        run([str(exe), "doctor"], timeout=90, env=env)


def pack() -> Path:
    name = archive_name()
    DIST.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        src = DIST / "Mitsu.app"
        out = DIST / f"{name}.zip"
        if out.exists():
            out.unlink()
        run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(src), str(out)])
        return out
    if sys.platform == "win32":
        src = DIST / "mitsu"
        out = DIST / f"{name}.zip"
        if out.exists():
            out.unlink()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for p in sorted(src.rglob("*")):
                z.write(p, Path("mitsu") / p.relative_to(src))
        return out
    src = DIST / "mitsu"
    out = DIST / f"{name}.tar.gz"
    if out.exists():
        out.unlink()
    with tarfile.open(out, "w:gz", compresslevel=6) as t:
        t.add(src, arcname="mitsu")
    return out


def main() -> None:
    run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--distpath", str(DIST),
        "--workpath", str(ROOT / "build"),
        str(ROOT / "packaging" / "mitsu.spec"),
    ])
    smoke()
    out = pack()
    size = out.stat().st_size / (1024 * 1024)
    print(f"\nbuilt {out} ({size:.1f} MiB)", flush=True)


if __name__ == "__main__":
    main()
