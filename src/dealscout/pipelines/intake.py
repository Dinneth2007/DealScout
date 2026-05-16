from __future__ import annotations

from pydantic import ValidationError

from dealscout.adapters.llm import get_llm_client
from dealscout.agents.triage import build_triage_agent
from dealscout.domain.brief import StartupBrief


def _extract_json(text: str) -> str:
    """Pull the outermost JSON object out of an LLM reply.

    The v2 prompts ask for bare JSON, but Gemini still sometimes wraps it in
    ```json fences or adds a sentence. We tolerate that here rather than fail
    the whole run on a cosmetic deviation.
    """
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.startswith("json"):
            s = s[4:]
        s = s.strip()
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return s[start : end + 1]
    return s


async def run_intake(raw_input: str) -> StartupBrief:
    """Run the full intake pipeline: Triage -> URL/PDF Intake -> StartupBrief.

    Caller must call configure_provider() once before invoking this.
    max_turns=8 bounds the WHOLE handoff chain (golden rule #5).

    Structured output is validated HERE (the boundary) rather than via SDK
    output_type, because Gemini's compat endpoint can't do tools + JSON
    response-format together. Decision 4's principle is preserved: nothing
    malformed flows downstream.
    """
    triage = build_triage_agent()
    result = await get_llm_client().run(triage, raw_input, max_turns=8)

    raw = result.final_output
    if not isinstance(raw, str):
        raise RuntimeError(
            f"Intake produced {type(raw)}, expected JSON text: {raw!r}"
        )
    try:
        return StartupBrief.model_validate_json(_extract_json(raw))
    except ValidationError as e:
        raise RuntimeError(
            f"Intake output did not match StartupBrief schema.\n"
            f"Raw: {raw[:500]!r}\nError: {e}"
        ) from e
