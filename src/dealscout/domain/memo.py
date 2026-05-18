from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FounderProfile(BaseModel):
    name: str
    role: str = Field(..., description="e.g., 'CEO, co-founder'")
    background: str = Field(
        ..., min_length=40, description="Brief bio with citations as [N] markers"
    )


class NewsItem(BaseModel):
    date_or_quarter: str = Field(..., description="e.g., '2025-Q1' or '2024-10'")
    description: str = Field(
        ..., description="One-line news description with citation"
    )


class Reference(BaseModel):
    index: int = Field(..., ge=1, description="The [N] marker number")
    description: str = Field(
        ..., description="Source description: 'Crunchbase — Modal funding page'"
    )


class InvestmentMemo(BaseModel):
    """The final structured investment memo. Mirrors the sample PDF 1:1."""

    # At-a-glance card
    company_name: str
    one_liner: str = Field(
        ..., max_length=200,
        description="One-sentence company description, ideally the company's own.",
    )
    founded: str = Field(..., description="e.g., '2021, San Francisco'")
    stage: str = Field(..., description="e.g., 'Series A (2024) [1]'")
    founders_summary: str = Field(..., description="Comma-separated founder names")
    investors: str = Field(
        ..., description="Lead and notable investors, with citations"
    )
    segment: str = Field(..., description="Market segment, e.g., 'AI infrastructure'")
    team_size: str = Field(
        ..., description="e.g., '~40 (per LinkedIn) [4]' or 'Not disclosed'"
    )

    # Recommendation
    recommendation: Literal["PASS", "TRACK", "MEET"]
    recommendation_rationale: str = Field(
        ..., min_length=50, max_length=400,
        description="One-paragraph reasoning for the recommendation.",
    )

    # Body
    executive_summary: str = Field(
        ..., min_length=400, max_length=1500,
        description="Two-paragraph summary integrating company + market + founders.",
    )
    strengths: list[str] = Field(
        ..., min_length=3, max_length=3,
        description="Exactly three top strengths, each with citations.",
    )
    concerns: list[str] = Field(
        ..., min_length=3, max_length=3,
        description="Exactly three top concerns, each with citations or reasoning.",
    )
    open_questions: list[str] = Field(
        ..., min_length=2, max_length=6,
        description="Critical questions the research couldn't answer.",
    )

    product: str = Field(
        ..., min_length=200, description="Product/technology section."
    )
    customers: str = Field(
        ..., min_length=100, description="Customer profile and named accounts."
    )
    traction_signals: list[str] = Field(
        ..., min_length=2, max_length=6,
        description="Concrete traction evidence with citations.",
    )

    market_segment: str = Field(
        ..., min_length=150,
        description="What market this competes in; TAM with assumptions.",
    )
    competitive_landscape: str = Field(
        ..., min_length=200,
        description="Named competitors with brief positioning each.",
    )
    why_now: str = Field(
        ..., min_length=150, description="Tailwinds making this the right moment."
    )

    founders_detail: list[FounderProfile] = Field(
        ..., min_length=1, max_length=5
    )
    founder_market_fit: str = Field(
        ..., min_length=80,
        description="Assessment of whether founders match the problem.",
    )

    recent_news: list[NewsItem] = Field(default_factory=list, max_length=8)

    bull_case: str = Field(..., min_length=100, max_length=600)
    bear_case: str = Field(..., min_length=100, max_length=600)
    mind_changers: str = Field(
        ..., min_length=80,
        description="What evidence would change the recommendation.",
    )

    references: list[Reference] = Field(
        ..., min_length=4, description="The source map, indexed."
    )

    # Metadata
    cost_usd_estimate: float | None = Field(
        None, ge=0, description="Estimated USD cost for this run; footer."
    )
    latency_seconds: float | None = Field(
        None, ge=0, description="Wall-clock latency; footer."
    )
