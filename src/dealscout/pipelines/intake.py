from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from dealscout.adapters.llm import get_llm_client
from dealscout.agents.triage import build_triage_agent
from dealscout.domain.brief import StartupBrief

# Map each intake tool to (source_type, output-key -> StartupBrief-field).
_TOOL_MAP = {
    "fetch_url": {
        "source_type": "url",
        "raw_text": "main_text",
        "headers": "headers",
        "detected_url": None,  # URL intake has no embedded-URL concept
    },
    "parse_pdf": {
        "source_type": "pdf",
        "raw_text": "text",
        "headers": "slide_titles",
        "detected_url": "detected_url",
    },
}


def _as_dict(value: Any) -> dict:
    """Coerce a tool output (dict, JSON string, or wrapper) into a dict."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _extract_json(text: str) -> str:
    """Pull the outermost JSON object out of an LLM reply (fence/prose tolerant).

    v3 prompts emit a tiny {"name","one_liner"} object, so this almost never
    has to do real work now — but weak models still occasionally add fences.
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


def _find_tool_output(new_items: list) -> tuple[str, dict]:
    """Return (tool_name, output_dict) for the fetch_url / parse_pdf call.

    The LLM no longer carries the page text — we read it straight from the
    tool result in the run items. Pairs calls to outputs by call_id.
    """
    calls: dict[str, str] = {}  # call_id -> tool name
    outputs: dict[str, Any] = {}  # call_id -> output payload
    for it in new_items:
        kind = type(it).__name__
        raw = getattr(it, "raw_item", None)
        if kind == "ToolCallItem":
            name = getattr(raw, "name", None)
            call_id = getattr(raw, "call_id", None) or getattr(raw, "id", None)
            if name in _TOOL_MAP and call_id is not None:
                calls[call_id] = name
        elif kind == "ToolCallOutputItem":
            call_id = None
            if isinstance(raw, dict):
                call_id = raw.get("call_id")
            call_id = call_id or getattr(raw, "call_id", None)
            payload = getattr(it, "output", None)
            if payload is None and isinstance(raw, dict):
                payload = raw.get("output")
            if call_id is not None:
                outputs[call_id] = payload

    for call_id, name in reversed(list(calls.items())):
        if call_id in outputs:
            return name, _as_dict(outputs[call_id])
    raise RuntimeError(
        "Intake ran but no fetch_url/parse_pdf tool output was found "
        "(did the agent skip the tool?)."
    )


async def run_intake(raw_input: str) -> StartupBrief:
    """Run the full intake pipeline: Triage -> URL/PDF Intake -> StartupBrief.

    Caller must call configure_provider() once first. max_turns=8 bounds the
    handoff chain (golden rule #5).

    The LLM only judges name + one_liner (a tiny JSON). The bulky/derivable
    fields (raw_text, headers, source_type, detected_url) are filled in
    Python from the actual tool result — so a huge page can never corrupt
    LLM-emitted JSON. source_ref is the original input (deterministic).
    """
    triage = build_triage_agent()
    result = await get_llm_client().run(triage, raw_input, max_turns=8)

    raw = result.final_output
    if not isinstance(raw, str):
        raise RuntimeError(
            f"Intake produced {type(raw)}, expected JSON text: {raw!r}"
        )
    try:
        judged = json.loads(_extract_json(raw))
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Intake name/one_liner JSON did not parse.\n"
            f"Raw: {raw[:300]!r}\nError: {e}"
        ) from e

    tool_name, out = _find_tool_output(result.new_items)
    spec = _TOOL_MAP[tool_name]

    tool_error = out.get("error")
    raw_text = (
        f"[tool error] {tool_error}"
        if tool_error
        else str(out.get(spec["raw_text"], ""))
    )
    headers = out.get(spec["headers"], []) if not tool_error else []
    detected_url = (
        out.get(spec["detected_url"]) if spec["detected_url"] else None
    )

    try:
        return StartupBrief(
            name=str(judged.get("name", "Unknown")),
            one_liner=str(judged.get("one_liner", "")),
            source_type=spec["source_type"],
            source_ref=raw_input,
            raw_text=raw_text,
            detected_url=detected_url,
            headers_or_sections=[str(h) for h in headers][:20],
        )
    except ValidationError as e:
        raise RuntimeError(f"Intake could not build StartupBrief: {e}") from e
