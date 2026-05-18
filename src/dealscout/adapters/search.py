"""Tavily web search. Returns errors as data; never raises."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from dealscout.config import settings


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str


@dataclass
class SearchResult:
    hits: list[SearchHit]
    error: str | None = None


async def search_tavily(
    query: str, max_results: int = 5, timeout_seconds: float = 20.0
) -> SearchResult:
    """Search the web via Tavily. Never raises."""
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {settings.tavily_api_key}"},
                json={
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                    "include_answer": False,
                },
            )
            resp.raise_for_status()
    except httpx.HTTPError as e:
        return SearchResult(hits=[], error=str(e))

    data = resp.json()
    hits = [
        SearchHit(
            title=item.get("title", ""),
            url=item.get("url", ""),
            snippet=item.get("content", ""),
        )
        for item in data.get("results", [])
    ]
    return SearchResult(hits=hits)
