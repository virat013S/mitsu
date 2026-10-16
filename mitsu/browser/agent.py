"""Browser fetch tool (§10/§17). httpx + title/text extraction; Playwright optional later."""
from __future__ import annotations

import re

import httpx

from ..permissions import policy

TAG = re.compile(r"<[^>]+>")


async def fetch(url: str, granted_token: str = "") -> dict:
    if not granted_token or not policy.is_granted(granted_token):
        policy.log("browser", f"fetch {url} (denied: no grant)", policy.CONFIRM, granted=False)
        raise PermissionError("browser fetch needs approval (CONFIRM).")
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "Mozilla/5.0"},
                                 follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        html = r.text
    title = (re.search(r"<title>(.*?)</title>", html, re.S | re.I) or [None, url])[1]
    text = re.sub(r"\s+", " ", TAG.sub(" ", html))[:15000]
    policy.log("browser", f"fetch {url} → {len(text)} chars", policy.CONFIRM)
    return {"url": url, "title": TAG.sub("", title or url)[:200], "text": text}
