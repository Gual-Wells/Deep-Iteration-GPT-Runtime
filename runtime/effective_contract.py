"""Typed DIGR 5.0 Alpha 4 Effective Contract.

The Effective Contract freezes contract commitments, never an execution
strategy. Count/D fields are minima; T/t are B/b-governed timing targets. Missing semantic values have already been completed by the native
model/host before this deterministic record is created.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any
from .validation import (
    require_binary, require_bool, require_finite_nonnegative_number,
    require_isolation_level, require_nonnegative_int, require_nonempty_text,
)


class SourceDisposition(str, Enum):
    REQUIRED = 'REQUIRED'
    WAIVED = 'WAIVED'


@dataclass(frozen=True)
class SourceContract:
    n: int
    t_seconds: float
    r: int
    b: int
    def __post_init__(self):
        require_nonnegative_int('S.n', self.n)
        require_finite_nonnegative_number('S.t_seconds', self.t_seconds)
        require_nonnegative_int('S.r', self.r)
        require_binary('S.b', self.b)


@dataclass(frozen=True)
class EffectiveContract:
    N: int
    T_seconds: float
    R: int
    B: int
    S: SourceContract
    D_s: int
    L_e: int
    source_disposition: SourceDisposition = SourceDisposition.REQUIRED
    source_waiver_reason: str | None = None
    L_mismatch_blocks_delivery: bool = False

    def __post_init__(self):
        require_nonnegative_int('N', self.N)
        require_finite_nonnegative_number('T_seconds', self.T_seconds)
        require_nonnegative_int('R', self.R)
        require_binary('B', self.B)
        if not isinstance(self.S, SourceContract):
            raise TypeError('S must be SourceContract')
        require_nonnegative_int('D_s', self.D_s)
        require_isolation_level('L_e', self.L_e)
        if not isinstance(self.source_disposition, SourceDisposition):
            object.__setattr__(self, 'source_disposition', SourceDisposition(self.source_disposition))
        if self.source_disposition is SourceDisposition.WAIVED:
            if self.source_waiver_reason is None:
                raise ValueError('WAIVED source disposition requires an explicit reason')
            if self.S.n or self.S.t_seconds or self.S.r or self.S.b:
                raise ValueError('source cannot be WAIVED while S minimums require source work')
            object.__setattr__(self, 'source_waiver_reason', require_nonempty_text('source_waiver_reason', self.source_waiver_reason))
        elif self.source_waiver_reason is not None:
            raise ValueError('source_waiver_reason is only valid when source is WAIVED')
        require_bool('L_mismatch_blocks_delivery', self.L_mismatch_blocks_delivery)

    @property
    def source_required(self) -> bool:
        return self.source_disposition is SourceDisposition.REQUIRED

    @property
    def D_minimum_positive(self) -> bool:
        """Whether the frozen contract requires at least one completed D.

        D_s is a lower bound, not an enable/disable switch.  A zero minimum
        therefore permits quality-driven D interventions even though none are
        mechanically required.
        """
        return self.D_s > 0

    @property
    def hard_timing_required(self) -> bool:
        return self.B == 1 or self.S.b == 1

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d['source_disposition'] = self.source_disposition.value
        return d
