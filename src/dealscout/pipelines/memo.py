from __future__ import annotations

from pydantic import ValidationError

from dealscout.adapters.llm import get_llm_client
from dealscout.agents.memo_writer import build_memo_writer
from dealscout.domain.memo import InvestmentMemo

# Bounded validation-feedback retry (golden rule #5). Reconstructs what the
# SDK's native output_type did before DeepSeek rejected json_schema: on a
# Pydantic failure, re-prompt with the exact errors so the model self-corrects.
_MAX_ATTEMPTS = 3


def _extract_json(text: str) -> str:
    """Outermost JSON object, tolerant of code fences / stray prose."""
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


async def run_memo_writer(dossier_markdown: str) -> InvestmentMemo:
    """Convert a synthesized dossier into a structured InvestmentMemo.

    Caller must call configure_provider() once first. DeepSeek can't do SDK
    structured output, so we validate at the boundary and feed Pydantic
    errors back for up to _MAX_ATTEMPTS (the correction prompt carries the
    bad JSON + errors, NOT the whole dossier — cheaper and targeted).
    """
    writer = build_memo_writer()
    client = get_llm_client()

    message = f"""Convert the following research dossier into an InvestmentMemo
JSON object, following the STRICT OUTPUT FORMAT in your instructions exactly.
Preserve all citations. strengths and concerns must each have EXACTLY three
items. Respect every character/count limit. recommendation must reflect the
dossier's overall signal.

=== DOSSIER ===
{dossier_markdown}
"""

    last_raw = ""
    last_err: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        result = await client.run(writer, message, max_turns=3)
        raw = result.final_output
        if not isinstance(raw, str):
            raise RuntimeError(
                f"Memo Writer produced {type(raw)}, expected JSON: {raw!r}"
            )
        last_raw = raw
        try:
            return InvestmentMemo.model_validate_json(_extract_json(raw))
        except ValidationError as e:
            last_err = e
            if attempt == _MAX_ATTEMPTS:
                break
            # Re-prompt with the bad JSON + exact errors. No dossier resend:
            # violations are length/count, fixable by trimming what's there.
            message = f"""Your previous JSON violated the schema. Fix ONLY the
listed constraint violations by trimming/condensing existing content — do not
fabricate, do not add prose, do not change unrelated fields. Return the full
corrected JSON object.

=== VALIDATION ERRORS ===
{e}

=== YOUR PREVIOUS JSON ===
{_extract_json(raw)}
"""

    raise RuntimeError(
        f"Memo Writer failed schema validation after {_MAX_ATTEMPTS} attempts.\n"
        f"Last error: {last_err}\nLast raw (600): {last_raw[:600]!r}"
    )
