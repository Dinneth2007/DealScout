"""Loader for the versioned prompt files in prompts/."""
from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


def load_prompt(name: str, version: int | None = None) -> str:
    """Load prompts/<name>_v<N>.md. version=None picks the highest N."""
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
