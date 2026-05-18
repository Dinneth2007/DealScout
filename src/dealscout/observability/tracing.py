"""Langfuse wiring. No-op unless keys are configured."""
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
        logger.info("Langfuse client initialized (host=%s).", settings.langfuse_host)
    except Exception:
        logger.exception("Langfuse init failed — continuing without tracing.")

    _initialized = True
