"""Per-IP rate limit (cost guard layer 1 of 3 — Decision 5).

In-memory, resets on process restart. Acceptable for a single-instance
demo; production would use Redis. Independent of the DeepSeek daily cap
and Tavily monthly cap so a bug here can't drain the account alone.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from threading import Lock

# ip -> (count, window_start)
_BUCKETS: OrderedDict[str, tuple[int, datetime]] = OrderedDict()
_LOCK = Lock()
_LIMIT_PER_IP = 3
_WINDOW = timedelta(hours=24)
_MAX_TRACKED_IPS = 10_000  # cap memory; LRU eviction


def check_rate_limit(ip: str) -> str | None:
    """None if allowed; an error message string if rate-limited.

    Per-IP limit of 3 requests / 24h. Requests with no identifiable IP
    are allowed (don't punish unknowns).
    """
    if not ip:
        return None

    now = datetime.now(timezone.utc)
    with _LOCK:
        if len(_BUCKETS) > _MAX_TRACKED_IPS:
            _BUCKETS.popitem(last=False)  # LRU evict oldest

        count, window_start = _BUCKETS.get(ip, (0, now))
        if now - window_start > _WINDOW:
            count, window_start = 0, now

        if count >= _LIMIT_PER_IP:
            remaining = _WINDOW - (now - window_start)
            hours = int(remaining.total_seconds() / 3600)
            return (
                f"Demo rate limit hit ({_LIMIT_PER_IP} runs per 24h per IP). "
                f"Try again in ~{hours}h."
            )

        _BUCKETS[ip] = (count + 1, window_start)
        _BUCKETS.move_to_end(ip)
        return None


def reset_rate_limit() -> None:
    """Test-only — clears all buckets."""
    with _LOCK:
        _BUCKETS.clear()
