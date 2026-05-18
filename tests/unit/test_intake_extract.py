"""Unit tests for intake's tool-output extraction. No LLM, no network.

Covers both the URL and PDF paths (the PDF path has no live fixture, so
this is how we verify it cheaply) plus the error case.
"""
from __future__ import annotations

import pytest

from dealscout.pipelines.intake import _as_dict, _find_tool_output


class _Call:
    def __init__(self, name: str, call_id: str) -> None:
        self.name = name
        self.call_id = call_id


class ToolCallItem:  # name matched by type(it).__name__
    def __init__(self, name: str, call_id: str) -> None:
        self.raw_item = _Call(name, call_id)


class ToolCallOutputItem:
    def __init__(self, call_id: str, output) -> None:
        self.raw_item = {"call_id": call_id, "output": output}
        self.output = output


def test_as_dict_handles_dict_str_garbage() -> None:
    assert _as_dict({"a": 1}) == {"a": 1}
    assert _as_dict('{"a": 1}') == {"a": 1}
    assert _as_dict("not json") == {}
    assert _as_dict(42) == {}


def test_find_tool_output_url_path() -> None:
    items = [
        ToolCallItem("fetch_url", "c1"),
        ToolCallOutputItem("c1", {"main_text": "hello", "headers": ["H"]}),
    ]
    name, out = _find_tool_output(items)
    assert name == "fetch_url"
    assert out["main_text"] == "hello"


def test_find_tool_output_pdf_path_json_string() -> None:
    items = [
        ToolCallItem("parse_pdf", "c9"),
        ToolCallOutputItem("c9", '{"text": "deck", "slide_titles": ["S1"]}'),
    ]
    name, out = _find_tool_output(items)
    assert name == "parse_pdf"
    assert out["text"] == "deck"


def test_find_tool_output_raises_when_no_tool() -> None:
    with pytest.raises(RuntimeError):
        _find_tool_output([])
