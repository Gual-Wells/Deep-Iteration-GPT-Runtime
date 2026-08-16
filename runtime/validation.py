"""Strict scalar validation for deterministic DIGR runtime records.

Python's ``bool`` is an ``int`` subclass and the default JSON/float stack can
accept values that are too weak for a truthfulness-oriented runtime.  These
helpers reject bool-as-int, non-finite numbers, empty text and malformed
boolean facts explicitly.
"""
from __future__ import annotations
import math
from numbers import Real


def require_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be bool")
    return value


def require_nonempty_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def require_nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer (bool is not accepted)")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def require_binary(name: str, value: object) -> int:
    v = require_nonnegative_int(name, value)
    if v not in (0, 1):
        raise ValueError(f"{name} must be 0 or 1")
    return v


def require_isolation_level(name: str, value: object) -> int:
    v = require_nonnegative_int(name, value)
    if v not in (1, 2, 3):
        raise ValueError(f"{name} must be 1, 2, or 3")
    return v


def require_finite_nonnegative_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number (bool is not accepted)")
    v = float(value)
    if not math.isfinite(v):
        raise ValueError(f"{name} must be finite")
    if v < 0:
        raise ValueError(f"{name} must be non-negative")
    return v
