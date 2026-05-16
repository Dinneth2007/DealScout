from __future__ import annotations

from agents import Agent

from dealscout.adapters.llm import build_model
from dealscout.config import settings
from dealscout.prompts import load_prompt
from dealscout.tools.fetch_url import fetch_url
from dealscout.tools.search_web import search_web


def build_market_researcher() -> Agent:
    # Same shape as the Company Researcher (F02 clone). Free-form Markdown,
    # two narrow tools, run-level max_turns. Only the prompt differs.
    return Agent(
        name="MarketResearcher",
        instructions=load_prompt("market_researcher"),
        tools=[search_web, fetch_url],
        model=build_model(settings.researcher_model),
    )
