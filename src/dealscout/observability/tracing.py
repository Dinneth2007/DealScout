"""Langfuse wiring. No-op unless keys are configured.

NOTE (F00 deferral, sanctioned by docs/features/00-foundations.md step 6):
Langfuse 4.x integrates with the OpenAI Agents SDK via OpenTelemetry, not the
old `langfuse.openai` drop-in. Full OTel auto-instrumentation is deferred to a
follow-up sub-feature. This module guarantees: (a) zero overhead and zero crash
risk when keys are absent, (b) a real Langfuse client when keys are present, so
later spans have something to attach to.
"""
from __future__ import annotations

import logging

from dealscout.config import settings

logger = logging.getLogger(__name__)

_initialized = False


def init_tracing() -> None:
    """Wire Langfuse if keys are set. Safe to call multiple times."""
    global _initialized
    if _initialized:
        return
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        logger.info("Langfuse keys not set — tracing disabled (no-op).")
        _initialized = True
        return

    try:
        from langfuse import Langfuse

        Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        # TODO(F00-followup): attach OpenTelemetry auto-instrumentation for the
        # Agents SDK so spans land in Langfuse automatically.
        logger.info("Langfuse client initialized (host=%s).", settings.langfuse_host)
    except Exception:  # never let observability break the app
        logger.exception("Langfuse init failed — continuing without tracing.")

    _initialized = True
