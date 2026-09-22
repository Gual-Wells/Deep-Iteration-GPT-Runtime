"""Mechanical DIGR 5.0 Alpha 7 contract-minimum checks."""
from __future__ import annotations
from dataclasses import dataclass
from .effective_contract import EffectiveContract
from .validation import require_bool, require_finite_nonnegative_number, require_nonnegative_int


@dataclass(frozen=True)
class ContractActuals:
    N:int
    T_seconds:float|None
    T_hard_verified:bool
    T_coverage_complete:bool
    unattributed_T_seconds:float
    R:int
    S_count:int
    n_min:int
    t_seconds:float|None
    t_hard_verified:bool
    t_coverage_complete:bool
    unattributed_t_seconds:float
    r_min:int
    D_s:int

    def __post_init__(self):
        for name in ('N','R','S_count','n_min','r_min','D_s'):
            require_nonnegative_int(name,getattr(self,name))
        for name in ('T_seconds','t_seconds'):
            value=getattr(self,name)
            if value is not None:require_finite_nonnegative_number(name,value)
        require_finite_nonnegative_number('unattributed_T_seconds',self.unattributed_T_seconds)
        require_finite_nonnegative_number('unattributed_t_seconds',self.unattributed_t_seconds)
        for name in ('T_hard_verified','t_hard_verified','T_coverage_complete','t_coverage_complete'):
            require_bool(name,getattr(self,name))


@dataclass(frozen=True)
class MechanicalStopCheck:
    N_ok:bool
    R_ok:bool
    source_instance_ok:bool
    n_ok:bool
    r_ok:bool
    T_coverage_ok:bool
    t_coverage_ok:bool
    hard_T_ok:bool
    hard_t_ok:bool
    D_ok:bool

    @property
    def minima_satisfied(self)->bool:
        return all((
            self.N_ok,self.R_ok,self.source_instance_ok,self.n_ok,self.r_ok,
            self.hard_T_ok,self.hard_t_ok,self.D_ok,
        ))


def check_mechanical_minima(contract:EffectiveContract,actual:ContractActuals)->MechanicalStopCheck:
    if not isinstance(contract,EffectiveContract):raise TypeError('contract must be EffectiveContract')
    if not isinstance(actual,ContractActuals):raise TypeError('actual must be ContractActuals')

    source_required=contract.source_required
    source_instance_ok=actual.S_count>=1 if source_required else True
    n_ok=actual.n_min>=contract.S.n if source_required else True
    r_ok=actual.r_min>=contract.S.r if source_required else True

    # Coverage completeness remains diagnostic. Missing intervals are excluded
    # from counted time, so they cannot falsify a lower-bound timing proof.
    T_coverage_ok=actual.T_coverage_complete
    t_coverage_ok=(not source_required) or actual.t_coverage_complete

    hard_T_ok=True
    if contract.B==1:
        hard_T_ok=(
            actual.T_hard_verified
            and actual.T_seconds is not None and actual.T_seconds>=contract.T_seconds
        )
    hard_t_ok=True
    if source_required and contract.S.b==1:
        hard_t_ok=(
            actual.t_hard_verified
            and actual.t_seconds is not None and actual.t_seconds>=contract.S.t_seconds
        )

    return MechanicalStopCheck(
        N_ok=actual.N>=contract.N,
        R_ok=actual.R>=contract.R,
        source_instance_ok=source_instance_ok,
        n_ok=n_ok,
        r_ok=r_ok,
        T_coverage_ok=T_coverage_ok,
        t_coverage_ok=t_coverage_ok,
        hard_T_ok=hard_T_ok,
        hard_t_ok=hard_t_ok,
        D_ok=actual.D_s>=contract.D_s,
    )
