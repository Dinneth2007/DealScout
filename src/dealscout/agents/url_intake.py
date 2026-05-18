from __future__ import annotations

from agents import Agent

from dealscout.adapters.llm import build_model
from dealscout.config import settings
from dealscout.prompts import load_prompt
from dealscout.tools.fetch_url import fetch_url


def build_url_intake_agent() -> Agent:
    # No output_type — the prompt instructs JSON, validated in the pipeline.
    return Agent(
        name="URLIntake",
        instructions=load_prompt("url_intake"),
        tools=[fetch_url],
        model=build_model(settings.intake_model),
    )
