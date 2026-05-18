from __future__ import annotations

from agents import Agent

from dealscout.adapters.llm import build_model
from dealscout.config import settings
from dealscout.prompts import load_prompt


def build_memo_writer() -> Agent:
    # No tools, NO output_type: DeepSeek's compat endpoint rejects the SDK's
    # json_schema response_format ("This response_format type is unavailable
    # now"). v2 prompt instructs JSON output; pipelines/memo.py validates it
    # with InvestmentMemo.model_validate_json at the boundary (same pattern
    # as intake v3). load_prompt auto-selects memo_writer_v2.
    return Agent(
        name="MemoWriter",
        instructions=load_prompt("memo_writer"),
        model=build_model(settings.default_model),
    )
