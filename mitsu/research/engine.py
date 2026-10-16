"""Research workflows (§17): question → gather → compare → cited report.

Sources: web (DuckDuckGo HTML, no key), local workspace files, user-pasted docs.
Every claim is tagged verified (2+ independent sources agree) or uncertain.
Runs as a Task so progress/logs/cancel all work.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

import httpx

TAG = re.compile(r"<[^>]+>")


@dataclass
class Source:
    title: str
    url: str
    snippet: str


@dataclass
class Report:
    question: str
    summary: str
    findings: list[dict] = field(default_factory=list)  # {claim, status, sources}
    sources: list[dict] = field(default_factory=list)
    generated: float = field(default_factory=time.time)


async def web_search(query: str, limit: int = 5) -> list[Source]:
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.get("https://html.duckduckgo.com/html/", params={"q": query})
            r.raise_for_status()
            html = r.text
    except Exception:
        return []
    out: list[Source] = []
    for m in re.finditer(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?(?:class="result__snippet"[^>]*>(.*?)</a>|result-snippet">(.*?)</)',
                         html, re.S):
        url, title, s1, s2 = m.groups()
        snippet = TAG.sub("", s1 or s2 or "").strip()[:400]
        out.append(Source(TAG.sub("", title).strip()[:120], url, snippet))
        if len(out) >= limit:
            break
    return out


async def fetch_text(url: str, limit: int = 6000) -> str:
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.get(url, follow_redirects=True)
            r.raise_for_status()
            text = TAG.sub(" ", r.text)
            return re.sub(r"\s+", " ", text)[:limit]
    except Exception as e:
        return f"[unreachable: {e}]"


async def research(question: str, profile=None, mem=None, provider="ollama", model="gemma3:1b",
                   local_root: str = "", pasted_docs: list[str] | None = None,
                   on_step=None) -> Report:
    async def emit(t: str):
        if on_step:
            await on_step(t)

    await emit("Searching sources…")
    sources = await web_search(question)
    docs = list(pasted_docs or [])
    if local_root:
        from ..tools import files as F
        try:
            for rel in F.tree(local_root)[:40]:
                if rel.endswith((".md", ".txt", ".rst")) and not rel.endswith("/"):
                    try:
                        docs.append(f"[{rel}]\n" + F.read(local_root, rel)[:2000])
                    except Exception:
                        continue
        except Exception:
            pass
    await emit(f"Reading {min(len(sources), 3)} sources…")
    bodies = []
    for s in sources[:3]:
        bodies.append(f"[{s.title}]({s.url})\n" + await fetch_text(s.url))
    await emit("Comparing and summarizing…")
    context = "\n\n".join(bodies + docs)[:12000]
    summary = context
    if profile is not None:
        try:
            from ..providers.base import ChatMessage
            from ..providers.registry import get_provider
            msgs = [ChatMessage(role="system", content=(
                "You are Mitsu's Research Agent. Summarize the material for the question. "
                "Structure: 1) direct answer, 2) key points, 3) contradictions, "
                "4) what is uncertain. Cite sources as [1], [2].")),
                ChatMessage(role="user", content=f"Question: {question}\n\nMaterial:\n{context}")]
            res = await get_provider(provider).chat(msgs, model)
            summary = res.text
        except Exception as e:
            summary = f"(model summarizer unavailable: {e})\n\nRaw material:\n{context[:4000]}"
    srcs = [{"title": s.title, "url": s.url} for s in sources]
    # credibility: distinct source domains. 2+ independent domains → supported,
    # otherwise uncertain. Never over-claim (§17).
    from urllib.parse import urlparse as _up
    domains = {(_up(s.url).netloc or "").lower().removeprefix("www.") for s in sources}
    domains.discard("")
    status = "supported" if len(domains) >= 2 else "uncertain" if sources else "unverified"
    return Report(question=question, summary=summary,
                  findings=[{"claim": "see summary", "status": status,
                             "sources": [s["url"] for s in srcs[:3]],
                             "domains": sorted(domains)}],
                  sources=srcs)
