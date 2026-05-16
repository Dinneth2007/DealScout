"""Unit tests for the Tavily search adapter. No network — respx mocks httpx."""
from __future__ import annotations

import httpx
import pytest
import respx

from dealscout.adapters.search import search_tavily


@pytest.mark.asyncio
async def test_search_tavily_parses_results() -> None:
    sample = {
        "results": [
            {
                "title": "Stripe",
                "url": "https://stripe.com",
                "content": "Payments infra.",
            },
        ]
    }
    with respx.mock:
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json=sample)
        )
        result = await search_tavily("Stripe")
    assert len(result.hits) == 1
    assert result.hits[0].title == "Stripe"
    assert result.hits[0].url == "https://stripe.com"
    assert result.error is None


@pytest.mark.asyncio
async def test_search_tavily_returns_error_on_failure() -> None:
    with respx.mock:
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(500)
        )
        result = await search_tavily("anything")
    assert result.error is not None
    assert result.hits == []
