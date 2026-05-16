"""Prompt loader. Prompts are versioned files in the repo-root prompts/ dir
(golden rule #3: never edit in place, add prompts/<name>_v<N>.md and bump).
"""
from __future__ import annotations

from pathlib import Path

# src/dealscout/prompts/__init__.py -> parents[3] is the repo root.
PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


def load_prompt(name: str, version: int | None = None) -> str:
    """Load prompts/<name>_v<N>.md.

    version=None picks the highest-numbered file (latest). Pass an int to pin
    a specific version (e.g. when an eval froze against an older prompt).
    """
    candidates = sorted(PROMPTS_DIR.glob(f"{name}_v*.md"))
    if not candidates:
        raise FileNotFoundError(
            f"No prompt file matching {name}_v*.md in {PROMPTS_DIR}"
        )
    if version is not None:
        target = PROMPTS_DIR / f"{name}_v{version}.md"
        if not target.exists():
            raise FileNotFoundError(f"Prompt {target} does not exist")
        return target.read_text(encoding="utf-8")
    return candidates[-1].read_text(encoding="utf-8")
