"""Canonical compact DIGR 5.0.0-Berta1 proof renderer.

Hard actual duration is visible only when the ProofData itself carries a true
hard-verification fact.  This prevents callers from smuggling an observed but
unverified number into a hard proof.  The visible canonical line contains only
target/actual values and policies; verification facts remain internal.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import math
from .validation import (
    require_binary,
    require_bool,
    require_finite_nonnegative_number,
    require_isolation_level,
    require_nonnegative_int,
)

_SUB = str.maketrans('0123456789-', '₀₁₂₃₄₅₆₇₈₉₋')

def subscript_int(value: int) -> str:
    require_nonnegative_int('subscript value', value)
    return str(value).translate(_SUB)


def _format_whole_seconds(seconds: int) -> str:
    if seconds >= 3600 and seconds % 3600 == 0:
        return f'{seconds // 3600}h'
    if seconds >= 60 and seconds % 60 == 0:
        return f'{seconds // 60}min'
    if seconds >= 60:
        m, s = divmod(seconds, 60)
        return f'{m}m{s:02d}s'
    return f'{seconds}s'


def format_target_duration(seconds: float) -> str:
    value = require_finite_nonnegative_number('target duration', seconds)
    if value.is_integer():
        return _format_whole_seconds(int(value))
    txt = format(Decimal(str(value)).normalize(), 'f')
    return f'{txt}s'


def format_actual_duration(seconds: float | None) -> str:
    if seconds is None:
        return '?'
    value = require_finite_nonnegative_number('actual duration', seconds)
    return _format_whole_seconds(math.floor(value))


def format_duration(seconds: float | None) -> str:
    return format_actual_duration(seconds)


@dataclass(frozen=True)
class ProofData:
    N_target: int
    N_actual: int
    T_target_seconds: float
    T_actual_seconds: float | None
    R_target: int
    R_actual: int
    B: int
    S_count: int
    n_target: int
    n_actual: int
    t_target_seconds: float
    t_actual_seconds: float | None
    r_target: int
    r_actual: int
    b: int
    D_target: int
    D_actual: int
    L_target: int
    L_actual: int | None
    T_hard_verified: bool
    t_hard_verified: bool
    D_actual_seconds: float = 0.0
    D_time_verified: bool = True
    V_target: int = 0
    V_actual: int = 0
    V_actual_seconds: float = 0.0
    V_time_verified: bool = True

    def __post_init__(self):
        for name in (
            'N_target','N_actual','R_target','R_actual','S_count','n_target',
            'n_actual','r_target','r_actual','D_target','D_actual','V_target','V_actual'
        ):
            require_nonnegative_int(name, getattr(self, name))
        require_finite_nonnegative_number('T_target_seconds', self.T_target_seconds)
        require_finite_nonnegative_number('t_target_seconds', self.t_target_seconds)
        if self.T_actual_seconds is not None:
            require_finite_nonnegative_number('T_actual_seconds', self.T_actual_seconds)
        if self.t_actual_seconds is not None:
            require_finite_nonnegative_number('t_actual_seconds', self.t_actual_seconds)
        require_binary('B', self.B)
        require_binary('b', self.b)
        require_isolation_level('L_target', self.L_target)
        if self.L_actual is not None:
            require_isolation_level('L_actual', self.L_actual)
        require_bool('T_hard_verified', self.T_hard_verified)
        require_bool('t_hard_verified', self.t_hard_verified)
        require_finite_nonnegative_number('D_actual_seconds',self.D_actual_seconds)
        require_finite_nonnegative_number('V_actual_seconds',self.V_actual_seconds)
        require_bool('D_time_verified',self.D_time_verified)
        require_bool('V_time_verified',self.V_time_verified)

    @property
    def visible_T_actual(self) -> float | None:
        if self.B == 1 and not self.T_hard_verified:
            return None
        return self.T_actual_seconds

    @property
    def visible_t_actual(self) -> float | None:
        if self.b == 1 and not self.t_hard_verified:
            return None
        return self.t_actual_seconds

    def to_dict(self) -> dict:
        """Return the closed internal proof-data shape.

        Verification facts are serialized for machine validation but never
        printed into the canonical user-facing proof line.
        """
        return {
            'main': {
                'N_target': self.N_target, 'N_actual': self.N_actual,
                'T_target_seconds': self.T_target_seconds,
                'T_actual_seconds': self.T_actual_seconds,
                'T_hard_verified': self.T_hard_verified,
                'R_target': self.R_target, 'R_actual': self.R_actual, 'B': self.B,
            },
            'source': {
                'count': self.S_count, 'n_target': self.n_target, 'n_actual': self.n_actual,
                't_target_seconds': self.t_target_seconds,
                't_actual_seconds': self.t_actual_seconds,
                't_hard_verified': self.t_hard_verified,
                'r_target': self.r_target, 'r_actual': self.r_actual, 'b': self.b,
            },
            'dictator': {'target': self.D_target, 'actual': self.D_actual},
            'isolation': {'target': self.L_target, 'actual': self.L_actual},
        }

    def to_dict_berta(self)->dict:
        d=self.to_dict()
        d['dictator']={**d['dictator'],'actual_seconds':self.D_actual_seconds,'time_verified':self.D_time_verified}
        d['viewpoint']={'target':self.V_target,'actual':self.V_actual,'actual_seconds':self.V_actual_seconds,'time_verified':self.V_time_verified}
        return d

    def render(self) -> str:
        l_actual = '?' if self.L_actual is None else str(self.L_actual)
        return (
            f'DIGR（{self.N_target}/{self.N_actual}，'
            f'{format_target_duration(self.T_target_seconds)}/{format_actual_duration(self.visible_T_actual)}，'
            f'{self.R_target}/{self.R_actual}，{self.B}，'
            f'S{subscript_int(self.S_count)}（{self.n_target}/{self.n_actual}，'
            f'{format_target_duration(self.t_target_seconds)}/{format_actual_duration(self.visible_t_actual)}，'
            f'{self.r_target}/{self.r_actual}，{self.b}），'
            f'D（{self.D_target}）/D（{self.D_actual}），'
            f'L（{self.L_target}）/L（{l_actual}））'
        )

    def render_berta(self)->str:
        """Canonical Berta proof with the accepted T/D/V time grouping."""
        l_actual='?' if self.L_actual is None else str(self.L_actual)
        return (
            f'DIGR（{self.N_target}/{self.N_actual}，'
            f'{format_target_duration(self.T_target_seconds)}/{format_actual_duration(self.visible_T_actual)}'
            f'（+{format_actual_duration(self.D_actual_seconds)}，+{format_actual_duration(self.V_actual_seconds)}），'
            f'{self.R_target}/{self.R_actual}，{self.B}，'
            f'S{subscript_int(self.S_count)}（{self.n_target}/{self.n_actual}，'
            f'{format_target_duration(self.t_target_seconds)}/{format_actual_duration(self.visible_t_actual)}，'
            f'{self.r_target}/{self.r_actual}，{self.b}），'
            f'D（{self.D_target}）/D（{self.D_actual}），'
            f'V（{self.V_target}）/V（{self.V_actual}），'
            f'L（{self.L_target}）/L（{l_actual}））'
        )


def proof_data_from_contract_actuals(contract, actual):
    """Build canonical proof data from frozen contract + derived live actuals."""
    from .effective_contract import EffectiveContract
    from .stop_checks import ContractActuals
    if not isinstance(contract, EffectiveContract):
        raise TypeError('contract must be EffectiveContract')
    if not isinstance(actual, ContractActuals):
        raise TypeError('actual must be ContractActuals')
    return ProofData(
        N_target=contract.N, N_actual=actual.N,
        T_target_seconds=contract.T_seconds, T_actual_seconds=actual.T_seconds,
        R_target=contract.R, R_actual=actual.R, B=contract.B,
        S_count=actual.S_count, n_target=contract.S.n, n_actual=actual.n_min,
        t_target_seconds=contract.S.t_seconds, t_actual_seconds=actual.t_seconds,
        r_target=contract.S.r, r_actual=actual.r_min, b=contract.S.b,
        D_target=contract.D_s, D_actual=actual.D_s,
        L_target=contract.L_e, L_actual=actual.L_e,
        T_hard_verified=actual.T_hard_verified, t_hard_verified=actual.t_hard_verified,
        D_actual_seconds=actual.D_actual_seconds,D_time_verified=actual.D_time_verified,
        V_target=contract.V_o,V_actual=actual.V_o,
        V_actual_seconds=actual.V_actual_seconds,V_time_verified=actual.V_time_verified,
    )


def render_canonical_proof(contract,actual,*,delivery_status:str,delivery_verified:bool)->str:
    """Render the canonical line only for a verified stable delivery.

    ``ProofData.render`` remains a pure legacy formatter for compatibility.
    New runtime code must enter through this gate so a plausible-looking line
    cannot be emitted for FINALIZING, INCOMPLETE, or hash-drifted output.
    """
    from .stop_checks import check_mechanical_minima
    if delivery_status!='DELIVERED':
        raise RuntimeError('canonical proof requires DELIVERED status')
    if delivery_verified is not True:
        raise RuntimeError('canonical proof requires verified delivery artifacts')
    stop=check_mechanical_minima(contract,actual)
    if not stop.minima_satisfied:
        raise RuntimeError('canonical proof forbidden while delivery minima are unmet')
    return proof_data_from_contract_actuals(contract,actual).render_berta()
