"""Unit tests for the scraper adapter. No network — respx mocks httpx."""
from __future__ import annotations

import httpx
import pytest
import respx

from dealscout.adapters.scraper import scrape_url


@pytest.mark.asyncio
async def test_scrape_url_extracts_title_and_headers() -> None:
    sample_html = """
        <html><head><title>Acme - Payments</title></head>
        <body><h1>Acme</h1><h2>Pricing</h2><p>We do payments.</p></body></html>
    """
    with respx.mock:
        respx.get("https://acme.example").mock(
            return_value=httpx.Response(200, text=sample_html)
        )
        result = await scrape_url("https://acme.example")
    assert result.title == "Acme - Payments"
    assert "Acme" in result.headers
    assert result.error is None


@pytest.mark.asyncio
async def test_scrape_url_returns_error_on_404() -> None:
    with respx.mock:
        respx.get("https://acme.example").mock(
            return_value=httpx.Response(404)
        )
        result = await scrape_url("https://acme.example")
    assert result.error is not None
    assert result.main_text == ""
