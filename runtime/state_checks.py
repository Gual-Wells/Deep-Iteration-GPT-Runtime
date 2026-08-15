"""Small deterministic state checks for DIGR 3.0.

No language parsing, search policy or quality judgment lives here.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Tuple

def union_duration_seconds(intervals: Iterable[Tuple[float, float]]) -> float:
    """Return the union length of [start, end] intervals."""
    normalized = sorted((float(a), float(b)) for a, b in intervals if float(b) >= float(a))
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

    @property
    def satisfied(self) -> bool:
        return self.actual >= self.requested
