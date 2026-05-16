from __future__ import annotations

from agents import Agent

from dealscout.adapters.llm import build_model
from dealscout.agents.pdf_intake import build_pdf_intake_agent
from dealscout.agents.url_intake import build_url_intake_agent
from dealscout.config import settings
from dealscout.prompts import load_prompt


def build_triage_agent() -> Agent:
    url_intake = build_url_intake_agent()
    pdf_intake = build_pdf_intake_agent()

    # handoffs=[...]: the SDK turns each child agent into a "transfer_to_<name>"
    # tool the routing LLM can call. Calling it = a one-way control transfer:
    # Triage is DONE, the child owns the conversation (Decision 2 — handoff,
    # not as_tool). Triage has no tools and no output_type because it never
    # produces a StartupBrief itself — it only routes.
    return Agent(
        name="Triage",
        instructions=load_prompt("triage"),
        handoffs=[url_intake, pdf_intake],
        model=build_model(settings.default_model),
    )
