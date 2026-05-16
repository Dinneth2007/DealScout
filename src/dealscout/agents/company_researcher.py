from __future__ import annotations

from agents import Agent

from dealscout.adapters.llm import build_model
from dealscout.config import settings
from dealscout.prompts import load_prompt
from dealscout.tools.fetch_url import fetch_url
from dealscout.tools.search_web import search_web


def build_company_researcher() -> Agent:
    # No output_type: research is judgment work, free-form Markdown (Decision 3).
    # Two narrow tools, not one mega-tool (Decision 2). Bounded at the run
    # level via max_turns in the pipeline (Decision 7 / golden rule #5).
    return Agent(
        name="CompanyResearcher",
        instructions=load_prompt("company_researcher"),
        tools=[search_web, fetch_url],
        model=build_model(settings.researcher_model),
    )
