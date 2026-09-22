"""Typed DIGR 5.0 Alpha 7 Effective Contract.

L is no longer a public/input/output parameter.  D isolation is internally
fixed to the semantic L1 baseline and therefore does not participate in the
frozen user contract or stop proof.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any
from .validation import (
    require_binary, require_finite_nonnegative_number,
    require_nonnegative_int, require_nonempty_text,
)


class SourceDisposition(str, Enum):
    REQUIRED='REQUIRED'
    WAIVED='WAIVED'


@dataclass(frozen=True)
class SourceContract:
    n:int
    t_seconds:float
    r:int
    b:int
    def __post_init__(self):
        require_nonnegative_int('S.n',self.n)
        require_finite_nonnegative_number('S.t_seconds',self.t_seconds)
        require_nonnegative_int('S.r',self.r)
        require_binary('S.b',self.b)


@dataclass(frozen=True)
class EffectiveContract:
    N:int
    T_seconds:float
    R:int
    B:int
    S:SourceContract
    D_s:int
    source_disposition:SourceDisposition=SourceDisposition.REQUIRED
    source_waiver_reason:str|None=None

    def __post_init__(self):
        require_nonnegative_int('N',self.N)
        require_finite_nonnegative_number('T_seconds',self.T_seconds)
        require_nonnegative_int('R',self.R)
        require_binary('B',self.B)
        if not isinstance(self.S,SourceContract):raise TypeError('S must be SourceContract')
        require_nonnegative_int('D_s',self.D_s)
        if not isinstance(self.source_disposition,SourceDisposition):
            object.__setattr__(self,'source_disposition',SourceDisposition(self.source_disposition))
        if self.source_disposition is SourceDisposition.WAIVED:
            if self.source_waiver_reason is None:raise ValueError('WAIVED source disposition requires an explicit reason')
            if self.S.n or self.S.t_seconds or self.S.r:
                raise ValueError('source cannot be WAIVED while S minimums require source work')
            object.__setattr__(self,'source_waiver_reason',require_nonempty_text('source_waiver_reason',self.source_waiver_reason))
        elif self.source_waiver_reason is not None:
            raise ValueError('source_waiver_reason is only valid when source is WAIVED')

    @property
    def source_required(self)->bool:return self.source_disposition is SourceDisposition.REQUIRED
    @property
    def D_minimum_positive(self)->bool:return self.D_s>0
    @property
    def hard_timing_required(self)->bool:return self.B==1 or (self.source_required and self.S.b==1)

    def to_dict(self)->dict[str,Any]:
        d=asdict(self);d['source_disposition']=self.source_disposition.value;return d
