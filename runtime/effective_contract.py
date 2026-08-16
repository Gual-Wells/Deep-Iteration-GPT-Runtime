"""Typed DIGR 4.1.0 Effective Contract.

The LLM/user-interface layer must already have semantically completed the
contract. This module validates representation; it never chooses workload.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
from .validation import (
    require_binary,
    require_finite_nonnegative_number,
    require_isolation_level,
    require_nonnegative_int,
)

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
    def __post_init__(self):
        require_nonnegative_int('N', self.N)
        require_finite_nonnegative_number('T_seconds', self.T_seconds)
        require_nonnegative_int('R', self.R)
        require_binary('B', self.B)
        if not isinstance(self.S, SourceContract):
            raise TypeError('S must be SourceContract')
        require_nonnegative_int('D_s', self.D_s)
        require_isolation_level('L_e', self.L_e)
    @property
    def source_required(self) -> bool:
        return bool(self.S.n > 0 or self.S.t_seconds > 0 or self.S.r > 0 or self.S.b == 1)
    @property
    def dictator_enabled(self) -> bool:
        return self.D_s > 0
    @property
    def hard_timing_required(self) -> bool:
        return self.B == 1 or self.S.b == 1
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
