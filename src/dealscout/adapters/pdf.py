"""pypdf wrapper. Never raises; errors returned as data."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

_URL_RE = re.compile(r"https?://[^\s)\]\}]+")


@dataclass
class PdfResult:
    text: str
    slide_titles: list[str]
    page_count: int
    detected_url: str | None
    error: str | None = None


async def parse_pdf_file(path: str) -> PdfResult:
    """Extract text + slide titles from a PDF. Never raises."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return PdfResult(
            text="", slide_titles=[], page_count=0,
            detected_url=None, error=f"File not found: {path}",
        )
    try:
        reader = PdfReader(str(p))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as e:
        return PdfResult(
            text="", slide_titles=[], page_count=0,
            detected_url=None, error=f"PDF parse error: {e}",
        )

    # first non-empty line of each page ≈ slide title
    slide_titles: list[str] = []
    for page_text in pages:
        first_line = next(
            (ln.strip() for ln in page_text.splitlines() if ln.strip()), ""
        )
        if first_line:
            slide_titles.append(first_line[:120])

    urls = _URL_RE.findall("\n".join(pages))
    detected_url = urls[0] if urls else None

    full_text = "\n".join(pages)[:16000]
    return PdfResult(
        text=full_text,
        slide_titles=slide_titles,
        page_count=len(pages),
        detected_url=detected_url,
    )
