from __future__ import annotations

from dealscout.adapters.llm import get_llm_client
from dealscout.agents.company_researcher import build_company_researcher
from dealscout.agents.founder_researcher import build_founder_researcher
from dealscout.agents.market_researcher import build_market_researcher
from dealscout.domain.brief import StartupBrief


async def run_company_research(brief: StartupBrief) -> str:
    """Run the Company Researcher on a StartupBrief. Returns Markdown notes.

    Caller must call configure_provider() once first. max_turns=10 bounds the
    ReAct loop (Decision 7 / golden rule #5). No output_type — free-form text.
    """
    researcher = build_company_researcher()

    # Hand the agent the brief content as its input message. raw_text trimmed
    # to keep the starting context small; the agent fetches more via tools.
    prompt_input = f"""Please research this company.

Name: {brief.name}
One-liner: {brief.one_liner}
Source: {brief.source_ref}

Notes from the source page/deck:
{brief.raw_text[:4000]}

Section headers / slide titles for structure hints:
{', '.join(brief.headers_or_sections[:15])}
"""

    result = await get_llm_client().run(researcher, prompt_input, max_turns=10)
    return result.final_output  # str of Markdown


async def run_market_research(brief: StartupBrief) -> str:
    """Run the Market Researcher on a StartupBrief. Returns Markdown notes.

    Sibling of run_company_research; the "research the MARKET" framing in the
    input message keeps the agent focused on landscape, not the company.
    """
    researcher = build_market_researcher()

    prompt_input = f"""Please research the market for this company.

Company: {brief.name}
One-liner: {brief.one_liner}
Source: {brief.source_ref}

Context from the source:
{brief.raw_text[:4000]}
"""

    result = await get_llm_client().run(researcher, prompt_input, max_turns=10)
    return result.final_output


async def run_founder_research(brief: StartupBrief) -> str:
    """Run the Founder Researcher on a StartupBrief. Returns Markdown notes.

    Sibling researcher; "research the founders" framing keeps the agent on
    the team, not the product or market.
    """
    researcher = build_founder_researcher()

    prompt_input = f"""Please research the founders of this company.

Company: {brief.name}
One-liner: {brief.one_liner}
Source: {brief.source_ref}

Context from the source (may mention founders):
{brief.raw_text[:4000]}
"""

    result = await get_llm_client().run(researcher, prompt_input, max_turns=10)
    return result.final_output

