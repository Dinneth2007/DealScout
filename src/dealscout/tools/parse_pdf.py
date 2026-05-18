from __future__ import annotations

from agents import function_tool

from dealscout.adapters.pdf import parse_pdf_file


@function_tool
async def parse_pdf(path: str) -> dict:
    """Parse a pitch deck PDF and return its text, slide titles, and any embedded URL.

    Use this when given a path to a PDF file. Do NOT use this for URLs.

    Args:
        path: Local filesystem path to a .pdf file.

    Returns:
        {
          "text": str,                  # extracted text, ~16000 chars max
          "slide_titles": list[str],    # first line of each page, rough
          "page_count": int,
          "detected_url": str | None,   # first URL found inside the deck
          "error": str | None
        }
    """
    result = await parse_pdf_file(path)
    return {
        "text": result.text,
        "slide_titles": result.slide_titles,
        "page_count": result.page_count,
        "detected_url": result.detected_url,
        "error": result.error,
    }
