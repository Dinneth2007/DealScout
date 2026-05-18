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

    return Agent(
        name="Triage",
        instructions=load_prompt("triage"),
        handoffs=[url_intake, pdf_intake],
        model=build_model(settings.default_model),
    )
