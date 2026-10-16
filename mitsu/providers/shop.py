"""Ollama model shop (§28): search a curated library, pull, remove. All local-first."""
from __future__ import annotations

import asyncio
import shutil

LIBRARY = [
    # name, size, blurb
    ("gemma3:1b", "815MB", "Tiny Google model — fast chat, great default"),
    ("gemma3:4b", "3.3GB", "Bigger Gemma — smarter, still quick"),
    ("qwen2.5:7b", "4.7GB", "Strong all-rounder coder + chat"),
    ("qwen2.5-coder:7b", "4.7GB", "Code specialist"),
    ("llama3.1:8b", "4.9GB", "Meta flagship, reliable"),
    ("mistral:7b", "4.1GB", "Fast European chat model"),
    ("phi4:14b", "9.1GB", "Microsoft compact reasoner"),
    ("deepseek-r1:8b", "4.9GB", "Deep reasoning traces"),
    ("deepseek-r1:14b", "9GB", "Stronger reasoning"),
    ("codellama:13b", "7.4GB", "Code completion classic"),
    ("starcoder2:7b", "4GB", "Code generation"),
    ("llava:7b", "4.7GB", "Sees images + chat"),
    ("qwen2.5vl:7b", "6GB", "Vision + chat, newer"),
    ("mistral-nemo:12b", "7.1GB", "Long-context chat"),
    ("mixtral:8x7b", "26GB", "MoE powerhouse (big RAM)"),
    ("command-r:35b", "20GB", "RAG-optimized (big RAM)"),
    ("nomic-embed-text", "274MB", "Local embeddings for memory search"),
    ("mxbai-embed-large", "670MB", "Bigger local embeddings"),
    ("tinyllama:1.1b", "637MB", "Smallest usable chat"),
    ("orca-mini:3b", "2GB", "Small instruct model"),
]


def search(q: str = "") -> list[dict]:
    q = q.lower().strip()
    out = [{"name": n, "size": s, "blurb": b} for n, s, b in LIBRARY
           if not q or q in n.lower() or q in b.lower()]
    return out


def local() -> list[dict]:
    import subprocess
    if not shutil.which("ollama"):
        return []
    try:
        cp = subprocess.run(["ollama", "list"], capture_output=True, timeout=15, text=True)
        rows = []
        for line in cp.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                rows.append({"name": parts[0], "size": parts[2] if len(parts) > 2 else "?"})
        return rows
    except Exception:
        return []


async def pull(name: str, on_line=None) -> str:
    proc = await asyncio.create_subprocess_exec(
        "ollama", "pull", name,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    last = ""
    assert proc.stdout is not None
    async for raw in proc.stdout:
        last = raw.decode(errors="replace").strip()
        if on_line:
            await on_line(last)
    await proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ollama pull failed: {last[-300:]}")
    return f"pulled {name}"


async def remove(name: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "ollama", "rm", name,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, _ = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(out.decode(errors="replace")[-300:])
    return f"removed {name}"
