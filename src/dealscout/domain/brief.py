from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StartupBrief(BaseModel):
    """The contract between intake and everything downstream.

    Every field must be derivable from a URL or a deck — NO external research.
    Downstream researchers (F02+) read `raw_text` and use `headers_or_sections`
    as structure hints.
    """

    name: str = Field(..., description="Company name as best detected.")
    one_liner: str = Field(
        ..., description="One-sentence description, ideally the company's own."
    )
    source_type: Literal["url", "pdf"]
    source_ref: str = Field(
        ..., description="Original URL or filepath the user provided."
    )
    raw_text: str = Field(
        ..., description="Cleaned text passed to downstream researchers."
    )
    detected_url: str | None = Field(
        None, description="For PDFs, a URL found in the deck (if any)."
    )
    headers_or_sections: list[str] = Field(
        default_factory=list,
        description="Page section headers or deck slide titles — structure hints.",
    )
