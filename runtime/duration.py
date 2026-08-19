"""Canonical duration normalization for DIGR parameter resolution.

The deterministic runtime only accepts text that already contains recognizable
*duration semantics*.  A bare number is deliberately never interpreted as a
T/t value.  Host/model semantic classification may normalize richer natural
language (for example ``half an hour``) to one of these canonical forms before
calling this helper.
"""
from __future__ import annotations
import re

_SIMPLE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(ms|millisecond|milliseconds|s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|毫秒|秒|分钟|分|小时|时)\s*$",
    re.I,
)
_FACTORS = {
    "ms": 0.001, "millisecond": 0.001, "milliseconds": 0.001, "毫秒": 0.001,
    "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1, "秒": 1,
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60, "分钟": 60, "分": 60,
    "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600, "小时": 3600, "时": 3600,
}
_NAMED = {
    "半小时": 1800.0,
    "半个小时": 1800.0,
    "一刻钟": 900.0,
    "half hour": 1800.0,
    "half an hour": 1800.0,
}


def parse_canonical_duration_seconds(value: str) -> float:
    if not isinstance(value, str):
        raise TypeError("duration must be text")
    text = value.strip()
    named = _NAMED.get(text.lower(), _NAMED.get(text))
    if named is not None:
        return named
    m = _SIMPLE.fullmatch(text)
    if not m:
        raise ValueError("duration text must contain an explicit recognizable time unit")
    amount = float(m.group(1))
    if amount < 0:
        raise ValueError("duration must be non-negative")
    unit = m.group(2).lower()
    return amount * _FACTORS[unit]


def has_duration_semantics(value: str) -> bool:
    try:
        parse_canonical_duration_seconds(value)
        return True
    except (TypeError, ValueError):
        return False
