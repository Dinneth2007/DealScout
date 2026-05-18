from __future__ import annotations

from agents import function_tool

from dealscout.adapters.scraper import scrape_url
from dealscout.config import settings


@function_tool
async def fetch_url(url: str) -> dict:
    """Fetch a URL and return its title, main text, and section headers.

    Use this when given a startup's website URL and you need to read the page.
    Do NOT use this for search — there is no search tool in intake.

    Args:
        url: A fully-qualified https URL.

    Returns:
        {
          "title": str,
          "main_text": str,    # cleaned, ~8000 chars max
          "headers": list[str],
          "final_url": str,    # after redirects
          "error": str | None  # populated if fetch failed; main_text empty
        }
    """
    result = await scrape_url(
        url, timeout_seconds=settings.default_tool_timeout_seconds
    )
    return {
        "title": result.title,
        "main_text": result.main_text,
        "headers": result.headers,
        "final_url": result.final_url,
        "error": result.error,
    }
