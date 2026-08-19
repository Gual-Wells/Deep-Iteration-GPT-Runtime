"""Small deterministic minimum and exact interval helpers for DIGR 5.0.0-alpha.2."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Tuple
from .validation import require_nonnegative_int, require_finite_nonnegative_number


def union_duration_ns(intervals: Iterable[Tuple[int, int]]) -> int:
    normalized: list[tuple[int, int]] = []
    for a, b in intervals:
        a = require_nonnegative_int('interval.start_ns', a)
        b = require_nonnegative_int('interval.end_ns', b)
        if b < a:
            raise ValueError('interval end must not precede start')
        normalized.append((a, b))
    normalized.sort()
    if not normalized:
        return 0
    total = 0
    cur_a, cur_b = normalized[0]
    for a, b in normalized[1:]:
        if a <= cur_b:
            cur_b = max(cur_b, b)
        else:
            total += cur_b - cur_a
            cur_a, cur_b = a, b
    return total + (cur_b - cur_a)


def union_duration_seconds(intervals: Iterable[Tuple[float, float]]) -> float:
    """Compatibility helper for already-normalized finite second intervals."""
    normalized: list[tuple[float, float]] = []
    for a, b in intervals:
        a = require_finite_nonnegative_number('interval.start_seconds', a)
        b = require_finite_nonnegative_number('interval.end_seconds', b)
        if b < a:
            raise ValueError('interval end must not precede start')
        normalized.append((a, b))
    normalized.sort()
    if not normalized:
        return 0.0
    total = 0.0
    cur_a, cur_b = normalized[0]
    for a, b in normalized[1:]:
        if a <= cur_b:
            cur_b = max(cur_b, b)
        else:
            total += cur_b - cur_a
            cur_a, cur_b = a, b
    return total + (cur_b - cur_a)

@dataclass(frozen=True)
class MinimumCheck:
    requested: int
    actual: int
    def __post_init__(self):
        require_nonnegative_int('requested', self.requested)
        require_nonnegative_int('actual', self.actual)
    @property
    def satisfied(self) -> bool:
        return self.actual >= self.requested
