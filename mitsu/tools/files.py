"""Safe file tools (§8/§9). All writes go through permission CONFIRM; deletes SENSITIVE."""
from __future__ import annotations

from pathlib import Path

from ..permissions import policy

MAX_READ = 200_000  # chars


def _resolve(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    if p != root.resolve() and root.resolve() not in p.parents:
        raise PermissionError(f"path escapes workspace: {rel}")
    return p


def tree(root: str, depth: int = 3) -> list[str]:
    out: list[str] = []
    base = Path(root).resolve()
    for p in sorted(base.rglob("*")):
        if len(p.relative_to(base).parts) > depth:
            continue
        if any(part.startswith((".git", "__pycache__", ".venv", "node_modules")) for part in p.parts):
            continue
        out.append(str(p.relative_to(base)) + ("/" if p.is_dir() else ""))
        if len(out) > 2000:
            break
    return out


def read(root: str, rel: str) -> str:
    policy.log("files", f"read {rel}", policy.SAFE)
    p = _resolve(Path(root).resolve(), rel)
    text = p.read_text(errors="replace")
    return text[:MAX_READ]


def write(root: str, rel: str, content: str, granted_token: str = "") -> str:
    if not granted_token or not policy.is_granted(granted_token):
        policy.log("files", f"write {rel} (denied: no grant)", policy.CONFIRM, granted=False)
        raise PermissionError("file write needs user approval (CONFIRM). Approve in Mitsu UI first.")
    p = _resolve(Path(root).resolve(), rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    policy.log("files", f"write {rel}", policy.CONFIRM)
    return f"wrote {rel} ({len(content)} chars)"


def remove(root: str, rel: str, granted_token: str = "") -> str:
    if not granted_token or not policy.is_granted(granted_token):
        policy.log("files", f"delete {rel} (denied: no grant)", policy.SENSITIVE, granted=False)
        raise PermissionError("deleting files needs explicit approval (SENSITIVE).")
    p = _resolve(Path(root).resolve(), rel)
    if p.is_dir():
        import shutil
        shutil.rmtree(p)
    else:
        p.unlink(missing_ok=True)
    policy.log("files", f"delete {rel}", policy.SENSITIVE)
    return f"deleted {rel}"
