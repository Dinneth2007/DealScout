from __future__ import annotations

from agents import Agent

from dealscout.adapters.llm import build_model
from dealscout.config import settings
from dealscout.prompts import load_prompt
from dealscout.tools.fetch_url import fetch_url
from dealscout.tools.search_web import search_web


def build_founder_researcher() -> Agent:
    # Third clone of the researcher pattern (F02/F03). Only the prompt differs:
    # founder data is thin/fragmented, so the prompt leans hard on gap-honesty.
    return Agent(
        name="FounderResearcher",
        instructions=load_prompt("founder_researcher"),
        tools=[search_web, fetch_url],
        model=build_model(settings.researcher_model),
    )
