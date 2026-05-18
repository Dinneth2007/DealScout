from __future__ import annotations

from agents import Agent

from dealscout.adapters.llm import build_model
from dealscout.agents.company_researcher import build_company_researcher
from dealscout.agents.founder_researcher import build_founder_researcher
from dealscout.agents.market_researcher import build_market_researcher
from dealscout.config import settings
from dealscout.prompts import load_prompt
from dealscout.tools.write_dossier import write_dossier

# Each wrapped researcher runs its own ReAct loop. Golden Rule #5 says every
# agent has an explicit max_turns — the F05 doc omits it on as_tool(), so we
# set it here. 10 matches the standalone researcher pipelines (F02-F04).
_RESEARCHER_MAX_TURNS = 10


def build_orchestrator() -> Agent:
    # as_tool() wraps a full agent as one callable. tool_description is the
    # Orchestrator LLM's only basis for picking the right specialist — write
    # it like API docs (Decision 4).
    company_tool = build_company_researcher().as_tool(
        tool_name="research_company",
        tool_description=(
            "Investigate the company's product, customers, traction signals, "
            "and recent news. Returns Markdown research notes with citations. "
            "Use when you need to understand WHAT the company does and HOW "
            "it's doing. Do NOT use for market sizing or founder background."
        ),
        max_turns=_RESEARCHER_MAX_TURNS,
    )
    market_tool = build_market_researcher().as_tool(
        tool_name="research_market",
        tool_description=(
            "Investigate the market segment, TAM, competitive landscape, and "
            "why-now tailwinds. Returns Markdown notes with citations. Use "
            "for broader category context. Do NOT use for the specific "
            "company or its founders."
        ),
        max_turns=_RESEARCHER_MAX_TURNS,
    )
    founder_tool = build_founder_researcher().as_tool(
        tool_name="research_founders",
        tool_description=(
            "Investigate the founders' backgrounds, prior companies, and "
            "domain fit. Returns Markdown notes with citations. Expect thin "
            "sources — founder data is fragmented. Use to assess team "
            "credibility."
        ),
        max_turns=_RESEARCHER_MAX_TURNS,
    )

    return Agent(
        name="InvestmentLead",
        instructions=load_prompt("orchestrator"),
        tools=[company_tool, market_tool, founder_tool, write_dossier],
        # orchestrator_model should be the bigger model (Decision 2). Reads
        # from settings (golden rule #2) — set ORCHESTRATOR_MODEL in .env.
        model=build_model(settings.orchestrator_model),
    )
