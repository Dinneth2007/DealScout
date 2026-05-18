from __future__ import annotations

from agents import Agent

from dealscout.adapters.llm import build_model
from dealscout.config import settings
from dealscout.prompts import load_prompt
from dealscout.tools.parse_pdf import parse_pdf


def build_pdf_intake_agent() -> Agent:
    return Agent(
        name="PDFIntake",
        instructions=load_prompt("pdf_intake"),
        tools=[parse_pdf],
        model=build_model(settings.intake_model),
    )
