"""Mechanical DIGR 5.0 Alpha 2 contract-minimum checks.

This layer checks frozen minimum commitments against evidence-backed actuals.
It deliberately does not judge whether an idea is insightful or whether the
model should continue after minimums are met.
"""
from __future__ import annotations
from dataclasses import dataclass
from .effective_contract import EffectiveContract
from .validation import (
    require_bool, require_finite_nonnegative_number,
    require_isolation_level, require_nonnegative_int,
)


@dataclass(frozen=True)
class ContractActuals:
    N: int
    T_seconds: float | None
    T_hard_verified: bool
    R: int
    S_count: int
    n_min: int
    t_seconds: float | None
    t_hard_verified: bool
    r_min: int
    D_s: int
    L_e: int | None

    def __post_init__(self):
        for name in ('N','R','S_count','n_min','r_min','D_s'):
            require_nonnegative_int(name, getattr(self, name))
        if self.T_seconds is not None:
            require_finite_nonnegative_number('T_seconds', self.T_seconds)
        if self.t_seconds is not None:
            require_finite_nonnegative_number('t_seconds', self.t_seconds)
        require_bool('T_hard_verified', self.T_hard_verified)
        require_bool('t_hard_verified', self.t_hard_verified)
        if self.L_e is not None:
            require_isolation_level('L_e', self.L_e)


@dataclass(frozen=True)
class MechanicalStopCheck:
    N_ok: bool
    R_ok: bool
    source_instance_ok: bool
    n_ok: bool
    r_ok: bool
    hard_T_ok: bool
    hard_t_ok: bool
    D_ok: bool
    L_ok: bool
    L_target_met: bool

    @property
    def minima_satisfied(self) -> bool:
        return all((
            self.N_ok, self.R_ok, self.source_instance_ok, self.n_ok,
            self.r_ok, self.hard_T_ok, self.hard_t_ok, self.D_ok, self.L_ok,
        ))


def check_mechanical_minima(contract: EffectiveContract, actual: ContractActuals) -> MechanicalStopCheck:
    if not isinstance(contract, EffectiveContract):
        raise TypeError('contract must be EffectiveContract')
    if not isinstance(actual, ContractActuals):
        raise TypeError('actual must be ContractActuals')

    source_required = contract.source_required
    source_instance_ok = actual.S_count >= 1 if source_required else True
    n_ok = actual.n_min >= contract.S.n if source_required else True
    r_ok = actual.r_min >= contract.S.r if source_required else True

    hard_T_ok = True
    if contract.B == 1:
        hard_T_ok = (
            actual.T_hard_verified and actual.T_seconds is not None
            and actual.T_seconds >= contract.T_seconds
        )
    hard_t_ok = True
    if contract.S.b == 1:
        hard_t_ok = (
            actual.t_hard_verified and actual.t_seconds is not None
            and actual.t_seconds >= contract.S.t_seconds
        )

    d_ok = actual.D_s >= contract.D_s
    # L is an implementation mode for D, not a universal task stop gate.
    # If D is off there is nothing to isolate. If D is on, mismatch remains
    # visible but only blocks delivery when the U0/contract explicitly says so.
    l_target_met = actual.L_e is not None and actual.L_e == contract.L_e
    if contract.D_s == 0:
        l_ok = True
    elif contract.L_mismatch_blocks_delivery:
        l_ok = l_target_met
    else:
        l_ok = actual.L_e is not None

    return MechanicalStopCheck(
        N_ok=actual.N >= contract.N,
        R_ok=actual.R >= contract.R,
        source_instance_ok=source_instance_ok,
        n_ok=n_ok,
        r_ok=r_ok,
        hard_T_ok=hard_T_ok,
        hard_t_ok=hard_t_ok,
        D_ok=d_ok,
        L_ok=l_ok,
        L_target_met=l_target_met,
    )
