"""The write_dossier completion tool.

Plain @function_tool (NOT an agent-as-tool): it's how the Orchestrator
signals "research complete, here is my synthesis". Having it as a tool gives
an explicit stopping condition and puts the dossier in a tool-call argument
that's easy to extract from the run result.
"""
from __future__ import annotations

from agents import function_tool


@function_tool
def write_dossier(dossier_markdown: str) -> str:
    """Submit the final synthesized research dossier.

    Call this LAST, after all three research specialists have returned their
    notes and you have synthesized findings across them. Pass the full
    Markdown dossier as a single string, following the template in your
    system prompt (at-a-glance, what's strongest, what's most concerning,
    contradictions, confidence assessment, integrated narrative, open
    questions, source map).

    Args:
        dossier_markdown: The complete synthesized dossier in Markdown.

    Returns:
        Confirmation that the dossier was received. After this call your
        work is done — do not continue researching.
    """
    # Passthrough: the pipeline extracts the dossier from this tool call's
    # arguments in the run result. Nothing to persist here for F05.
    return "Dossier received. Research complete."
