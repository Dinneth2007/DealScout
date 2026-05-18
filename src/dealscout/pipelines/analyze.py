from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NamedTuple

from dealscout.adapters.llm import get_llm_client
from dealscout.agents.orchestrator import build_orchestrator
from dealscout.domain.brief import StartupBrief
from dealscout.domain.memo import InvestmentMemo
from dealscout.pipelines.intake import run_intake
from dealscout.pipelines.memo import run_memo_writer
from dealscout.rendering.markdown import render_markdown
from dealscout.rendering.pdf import render_pdf


class AnalysisResult(NamedTuple):
    """Result of the full F05 pipeline."""

    dossier_markdown: str
    brief: StartupBrief


def _extract_dossier_from_result(result: Any) -> str:
    """Pull the dossier out of the run result.

    The Orchestrator submits the dossier via the write_dossier tool, so it
    lives in that tool call's `dossier_markdown` argument.

    Verified shape for installed openai-agents 0.17.2: result.new_items holds
    items whose type name is 'ToolCallItem'; the underlying call is
    `item.raw_item` with `.name` and `.arguments`. The doc's `item.tool_name`
    / dict `item.arguments` is WRONG for this version. `.arguments` is a JSON
    string in the chat-completions path; we defensively accept str or dict.
    """
    for item in reversed(result.new_items):
        if type(item).__name__ != "ToolCallItem":
            continue
        raw = getattr(item, "raw_item", None)
        if raw is None or getattr(raw, "name", None) != "write_dossier":
            continue
        args = getattr(raw, "arguments", None)
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                continue
        if isinstance(args, dict) and args.get("dossier_markdown"):
            return args["dossier_markdown"]

    # Fallback: some runs end with the dossier as the final assistant text.
    if isinstance(result.final_output, str) and result.final_output.strip():
        return result.final_output
    raise RuntimeError("Could not extract dossier from run result")


async def run_analysis(brief: StartupBrief) -> AnalysisResult:
    """Run the Orchestrator: it delegates to the three researchers and
    produces a synthesized dossier.

    Caller must call configure_provider() once first and is responsible for
    running intake to produce the brief. max_turns=15 bounds the Orchestrator
    (Decision 3 / golden rule #5); each researcher-as-tool is separately
    bounded inside build_orchestrator.
    """
    orchestrator = build_orchestrator()

    prompt_input = f"""You are analyzing the following startup. Coordinate your
research specialists and produce a synthesized dossier.

Name: {brief.name}
One-liner: {brief.one_liner}
Source type: {brief.source_type}
Source: {brief.source_ref}

Notes from the source page or deck:
{brief.raw_text[:4000]}

Section headers / slide titles (structure hints):
{', '.join(brief.headers_or_sections[:15])}
"""

    result = await get_llm_client().run(orchestrator, prompt_input, max_turns=15)
    return AnalysisResult(
        dossier_markdown=_extract_dossier_from_result(result), brief=brief
    )


class FullAnalysisResult(NamedTuple):
    brief: StartupBrief
    dossier_markdown: str
    memo: InvestmentMemo
    pdf_path: str
    markdown_path: str


async def run_full_analysis(
    input_str: str, output_dir: str = "./output"
) -> FullAnalysisResult:
    """End-to-end: input string -> memo PDF + Markdown.

    Plain Python flow control (Decision A / F05 Decision 7): the order of
    stages is deterministic; the LLM only decides inside each agent.
    Caller must call configure_provider() once first.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    brief = await run_intake(input_str)
    analysis = await run_analysis(brief)
    memo = await run_memo_writer(analysis.dossier_markdown)

    safe = memo.company_name.lower().replace(" ", "_").replace("/", "_")
    pdf_path = f"{output_dir}/memo_{safe}.pdf"
    md_path = f"{output_dir}/memo_{safe}.md"
    render_pdf(memo, pdf_path)
    Path(md_path).write_text(render_markdown(memo))

    return FullAnalysisResult(
        brief, analysis.dossier_markdown, memo, pdf_path, md_path
    )
