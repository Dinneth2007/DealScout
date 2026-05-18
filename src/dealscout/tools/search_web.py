from __future__ import annotations

from agents import function_tool

from dealscout.adapters.search import search_tavily


@function_tool
async def search_web(query: str, max_results: int = 5) -> dict:
    """Search the web for current information about companies, markets, or people.

    Use this when you need facts you don't already have from previous tool calls.
    Specifically use this for: company products, traction, customers, recent news,
    competitors mentioned in articles, market data.

    Do NOT use this to read a specific known URL — use fetch_url for that.

    Args:
        query: A focused search query, 3-8 words. Examples:
               "Stripe payment volume 2024"
               "Plaid competitors fintech API"
               "Anthropic funding round valuation"
        max_results: How many hits to return. Default 5. Use 3 for narrow
                     queries, 10 for broad market overviews.

    Returns:
        {
          "hits": [
            {"title": str, "url": str, "snippet": str},
            ...
          ],
          "error": str | None
        }
    """
    result = await search_tavily(query, max_results=max_results)
    return {
        "hits": [
            {"title": h.title, "url": h.url, "snippet": h.snippet}
            for h in result.hits
        ],
        "error": result.error,
    }
