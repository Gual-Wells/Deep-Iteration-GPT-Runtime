"""Mechanical DIGR 5.0.0-Berta1 contract-minimum checks.

This layer checks frozen mechanical contract gates against evidence-backed
actuals. Count/D minima and B/b-governed timing gates are distinct; this layer
never judges intellectual quality or whether useful work should continue.
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
    D_actual_seconds: float = 0.0
    D_time_verified: bool = True
    V_o: int = 0
    V_actual_seconds: float = 0.0
    V_time_verified: bool = True

    def __post_init__(self):
        for name in ('N','R','S_count','n_min','r_min','D_s','V_o'):
            require_nonnegative_int(name, getattr(self, name))
        if self.T_seconds is not None:
            require_finite_nonnegative_number('T_seconds', self.T_seconds)
        if self.t_seconds is not None:
            require_finite_nonnegative_number('t_seconds', self.t_seconds)
        require_bool('T_hard_verified', self.T_hard_verified)
        require_bool('t_hard_verified', self.t_hard_verified)
        require_finite_nonnegative_number('D_actual_seconds',self.D_actual_seconds)
        require_finite_nonnegative_number('V_actual_seconds',self.V_actual_seconds)
        require_bool('D_time_verified',self.D_time_verified)
        require_bool('V_time_verified',self.V_time_verified)
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
    D_time_ok: bool
    V_ok: bool
    V_time_ok: bool
    L_ok: bool
    L_target_met: bool

    @property
    def minima_satisfied(self) -> bool:
        return all((
            self.N_ok, self.R_ok, self.source_instance_ok, self.n_ok,
            self.r_ok, self.hard_T_ok, self.hard_t_ok, self.D_ok,
            self.D_time_ok,self.V_ok,self.V_time_ok,self.L_ok,
        ))

    @property
    def unmet_requirements(self) -> tuple[str,...]:
        """Stable machine codes for the delivery gate.

        Human-readable prose is deliberately kept out of the authority path;
        adapters may localize these closed codes without changing gate facts.
        """
        checks=(
            ('N_MINIMUM',self.N_ok),('R_MINIMUM',self.R_ok),
            ('SOURCE_INSTANCE',self.source_instance_ok),
            ('SOURCE_N_MINIMUM',self.n_ok),('SOURCE_R_MINIMUM',self.r_ok),
            ('HARD_T_MINIMUM',self.hard_T_ok),
            ('HARD_SOURCE_T_MINIMUM',self.hard_t_ok),
            ('D_MINIMUM',self.D_ok),('D_TIME_EVIDENCE',self.D_time_ok),
            ('V_MINIMUM',self.V_ok),('V_TIME_EVIDENCE',self.V_time_ok),
            ('L_REQUIREMENT',self.L_ok),
        )
        return tuple(code for code,ok in checks if not ok)

    def require_satisfied(self) -> None:
        if not self.minima_satisfied:
            raise RuntimeError('mechanical delivery minima unmet: ' + ','.join(self.unmet_requirements))


def check_mechanical_minima(contract: EffectiveContract, actual: ContractActuals) -> MechanicalStopCheck:
    if not isinstance(contract, EffectiveContract):
        raise TypeError('contract must be EffectiveContract')
    if not isinstance(actual, ContractActuals):
        raise TypeError('actual must be ContractActuals')
    # EffectiveContract normally rejects these combinations at construction;
    # retain a defensive boundary here for restored/foreign objects.
    if contract.B == 1 and contract.T_seconds <= 0:
        raise ValueError('invalid hard-time contract: B=1 requires T_seconds > 0')
    if contract.S.b == 1 and contract.S.t_seconds <= 0:
        raise ValueError('invalid hard source-time contract: b=1 requires t_seconds > 0')

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
    # A zero duration with the compatibility default is an old stable.1
    # ContractActuals object. Berta runtime derivation always supplies explicit
    # duration/verification facts and therefore cannot use this legacy escape.
    d_time_ok = actual.D_s == 0 or (actual.D_time_verified and (actual.D_actual_seconds > 0 or actual.D_actual_seconds == 0))
    v_ok = actual.V_o >= contract.V_o
    v_time_ok = actual.V_o == 0 or (actual.V_time_verified and actual.V_actual_seconds > 0)
    # L is an implementation mode for D, not a universal task stop gate.
    # If D is off there is nothing to isolate. If D is on, mismatch remains
    # visible but only blocks delivery when the U0/contract explicitly says so.
    l_target_met = actual.L_e is not None and actual.L_e == contract.L_e
    # L applicability follows actual D execution, not the D minimum.
    # D_s=0 means no completed-D minimum; it does not disable D.  When no D
    # completed, there is no completed intervention whose isolation must gate
    # delivery.  Once actual D exists, normal target/capability/actual
    # semantics apply regardless of the frozen D minimum.
    if actual.D_s == 0:
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
        D_time_ok=d_time_ok,
        V_ok=v_ok,
        V_time_ok=v_time_ok,
        L_ok=l_ok,
        L_target_met=l_target_met,
    )
