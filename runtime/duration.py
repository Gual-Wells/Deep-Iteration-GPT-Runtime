"""Canonical duration normalization for already-understood DIGR values."""
from __future__ import annotations
import re

_SIMPLE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours)\s*$", re.I)
_FACTORS = {
    "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
}

def parse_canonical_duration_seconds(value: str) -> float:
    m = _SIMPLE.fullmatch(value)
    if not m:
        raise ValueError("use an already-normalized duration such as 30s, 15m or 2h")
    amount = float(m.group(1))
    if amount < 0:
        raise ValueError("duration must be non-negative")
    return amount * _FACTORS[m.group(2).lower()]
