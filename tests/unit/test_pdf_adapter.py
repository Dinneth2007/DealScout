"""Unit tests for the PDF adapter. No network, no fixtures needed."""
from __future__ import annotations

import pytest

from dealscout.adapters.pdf import parse_pdf_file


@pytest.mark.asyncio
async def test_parse_pdf_returns_error_on_missing_file() -> None:
    result = await parse_pdf_file("/nonexistent/path.pdf")
    assert result.error is not None
    assert result.text == ""
