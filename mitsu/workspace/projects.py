"""Project workspace ops (§8): scaffold common project types."""
from __future__ import annotations

from pathlib import Path

from ..permissions import policy
from ..tools import files

TEMPLATES = ("python", "web", "node", "docs")


def scaffold(root: str, kind: str, name: str, granted_token: str = "") -> str:
    if kind not in TEMPLATES:
        raise ValueError(f"unknown template {kind}; choose {TEMPLATES}")
    base = Path(root).resolve() / name
    if base.exists() and any(base.iterdir()):
        raise FileExistsError(f"{base} already exists and is not empty")
    if not granted_token or not policy.is_granted(granted_token):
        raise PermissionError("creating projects needs approval (CONFIRM).")
    if kind == "python":
        files.write(str(base), "pyproject.toml",
                    '[project]\nname = "%s"\nversion = "0.1.0"\n' % name, granted_token)
        files.write(str(base), "README.md", f"# {name}\n", granted_token)
        files.write(str(base), "src/__init__.py", "", granted_token)
    elif kind == "web":
        files.write(str(base), "index.html",
                    "<!doctype html><html><body><h1>%s</h1></body></html>" % name, granted_token)
        files.write(str(base), "styles.css", "body{font-family:system-ui}\n", granted_token)
        files.write(str(base), "app.js", "console.log('hi');\n", granted_token)
    elif kind == "node":
        files.write(str(base), "package.json",
                    '{"name":"%s","version":"0.1.0","type":"module"}\n' % name, granted_token)
        files.write(str(base), "index.js", "console.log('hi');\n", granted_token)
    else:
        files.write(str(base), "README.md", f"# {name}\n", granted_token)
    policy.log("workspace", f"scaffold {kind}:{name}", policy.CONFIRM)
    return str(base)
