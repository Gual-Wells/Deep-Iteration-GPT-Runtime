"""Deterministic aggregation for multiple DIGR Source Evolution instances."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from .state_checks import union_duration_ns
from .validation import require_nonnegative_int


def _interval(value: object) -> tuple[int, int]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise TypeError('source interval must be a 2-item tuple/list')
    a = require_nonnegative_int('source interval start', value[0])
    b = require_nonnegative_int('source interval end', value[1])
    if b < a:
        raise ValueError('source interval end must be >= start')
    return a, b

@dataclass(frozen=True)
class SourceActual:
    id: int
    n_actual: int
    r_actual: int
    intervals_ns: tuple[tuple[int, int], ...] = ()

    def __post_init__(self):
        ident = require_nonnegative_int('id', self.id)
        if ident < 1:
            raise ValueError('id must be >= 1')
        require_nonnegative_int('n_actual', self.n_actual)
        require_nonnegative_int('r_actual', self.r_actual)
        normalized = tuple(_interval(x) for x in self.intervals_ns)
        object.__setattr__(self, 'intervals_ns', normalized)

@dataclass(frozen=True)
class SourceAggregate:
    count: int
    n_min: int
    r_min: int
    t_ns: int

    @property
    def t_seconds(self) -> float:
        return self.t_ns / 1_000_000_000


def aggregate_sources(sources: Iterable[SourceActual]) -> SourceAggregate:
    items = tuple(sources)
    if not items:
        return SourceAggregate(0, 0, 0, 0)
    if any(not isinstance(x, SourceActual) for x in items):
        raise TypeError('all sources must be SourceActual')
    ids = [x.id for x in items]
    if len(set(ids)) != len(ids):
        raise ValueError('source ids must be unique')
    intervals = [iv for item in items for iv in item.intervals_ns]
    return SourceAggregate(
        count=len(items),
        n_min=min(x.n_actual for x in items),
        r_min=min(x.r_actual for x in items),
        t_ns=union_duration_ns(intervals),
    )
