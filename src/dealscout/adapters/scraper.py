"""HTTP + HTML extraction. Never raises; errors returned as data."""
from __future__ import annotations

from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup


@dataclass
class ScrapeResult:
    title: str
    main_text: str
    headers: list[str]
    final_url: str
    error: str | None = None


async def scrape_url(url: str, timeout_seconds: float = 30.0) -> ScrapeResult:
    """Fetch a URL and extract title, main text, and section headers.

    Never raises — returns ScrapeResult with .error set on failure.
    """
    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds, follow_redirects=True
        ) as client:
            resp = await client.get(url, headers={"User-Agent": "DealScout/0.1"})
            resp.raise_for_status()
    except httpx.HTTPError as e:
        return ScrapeResult(
            title="", main_text="", headers=[], final_url=url, error=str(e)
        )

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title = (soup.title.string or "").strip() if soup.title else ""
    headers = [
        h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])
    ][:20]
    main_text = " ".join(soup.get_text(" ", strip=True).split())[:8000]

    return ScrapeResult(
        title=title,
        main_text=main_text,
        headers=headers,
        final_url=str(resp.url),
    )
