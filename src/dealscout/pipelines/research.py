from __future__ import annotations

from dealscout.adapters.llm import get_llm_client
from dealscout.agents.company_researcher import build_company_researcher
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
