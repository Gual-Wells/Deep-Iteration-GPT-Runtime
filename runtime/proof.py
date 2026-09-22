"""Canonical compact DIGR 5.0.0-alpha.7 proof renderer.

L is intentionally absent from public proof.  For hard timing, an actual value
is visible only when both clock verification and semantic-time coverage are
complete.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import math
from .validation import require_binary, require_bool, require_finite_nonnegative_number, require_nonnegative_int

_SUB=str.maketrans('0123456789-','₀₁₂₃₄₅₆₇₈₉₋')

def subscript_int(value:int)->str:
    require_nonnegative_int('subscript value',value);return str(value).translate(_SUB)

def _format_whole_seconds(seconds:int)->str:
    if seconds>=3600 and seconds%3600==0:return f'{seconds//3600}h'
    if seconds>=60 and seconds%60==0:return f'{seconds//60}min'
    if seconds>=60:
        m,s=divmod(seconds,60);return f'{m}m{s:02d}s'
    return f'{seconds}s'

def format_target_duration(seconds:float)->str:
    value=require_finite_nonnegative_number('target duration',seconds)
    if value.is_integer():return _format_whole_seconds(int(value))
    return f"{format(Decimal(str(value)).normalize(),'f')}s"

def format_actual_duration(seconds:float|None)->str:
    if seconds is None:return '?'
    value=require_finite_nonnegative_number('actual duration',seconds)
    return _format_whole_seconds(math.floor(value))

def format_duration(seconds:float|None)->str:return format_actual_duration(seconds)


@dataclass(frozen=True)
class ProofData:
    N_target:int;N_actual:int
    T_target_seconds:float;T_actual_seconds:float|None
    R_target:int;R_actual:int;B:int
    S_count:int;n_target:int;n_actual:int
    t_target_seconds:float;t_actual_seconds:float|None
    r_target:int;r_actual:int;b:int
    D_target:int;D_actual:int
    T_hard_verified:bool;t_hard_verified:bool
    T_coverage_complete:bool;t_coverage_complete:bool

    def __post_init__(self):
        for name in ('N_target','N_actual','R_target','R_actual','S_count','n_target','n_actual','r_target','r_actual','D_target','D_actual'):
            require_nonnegative_int(name,getattr(self,name))
        require_finite_nonnegative_number('T_target_seconds',self.T_target_seconds)
        require_finite_nonnegative_number('t_target_seconds',self.t_target_seconds)
        if self.T_actual_seconds is not None:require_finite_nonnegative_number('T_actual_seconds',self.T_actual_seconds)
        if self.t_actual_seconds is not None:require_finite_nonnegative_number('t_actual_seconds',self.t_actual_seconds)
        require_binary('B',self.B);require_binary('b',self.b)
        for name in ('T_hard_verified','t_hard_verified','T_coverage_complete','t_coverage_complete'):
            require_bool(name,getattr(self,name))

    @property
    def visible_T_actual(self):
        if self.B==1 and (not self.T_hard_verified or not self.T_coverage_complete):return None
        return self.T_actual_seconds

    @property
    def visible_t_actual(self):
        if self.b==1 and (not self.t_hard_verified or not self.t_coverage_complete):return None
        return self.t_actual_seconds

    def to_dict(self)->dict:
        return {
            'main':{
                'N_target':self.N_target,'N_actual':self.N_actual,
                'T_target_seconds':self.T_target_seconds,'T_actual_seconds':self.T_actual_seconds,
                'T_hard_verified':self.T_hard_verified,'T_coverage_complete':self.T_coverage_complete,
                'R_target':self.R_target,'R_actual':self.R_actual,'B':self.B,
            },
            'source':{
                'count':self.S_count,'n_target':self.n_target,'n_actual':self.n_actual,
                't_target_seconds':self.t_target_seconds,'t_actual_seconds':self.t_actual_seconds,
                't_hard_verified':self.t_hard_verified,'t_coverage_complete':self.t_coverage_complete,
                'r_target':self.r_target,'r_actual':self.r_actual,'b':self.b,
            },
            'dictator':{'target':self.D_target,'actual':self.D_actual},
        }

    def render(self)->str:
        return (
            f'DIGR（{self.N_target}/{self.N_actual}，'
            f'{format_target_duration(self.T_target_seconds)}/{format_actual_duration(self.visible_T_actual)}，'
            f'{self.R_target}/{self.R_actual}，{self.B}，'
            f'S{subscript_int(self.S_count)}（{self.n_target}/{self.n_actual}，'
            f'{format_target_duration(self.t_target_seconds)}/{format_actual_duration(self.visible_t_actual)}，'
            f'{self.r_target}/{self.r_actual}，{self.b}），'
            f'D（{self.D_target}）/D（{self.D_actual}））'
        )


def proof_data_from_contract_actuals(contract,actual):
    from .effective_contract import EffectiveContract
    from .stop_checks import ContractActuals
    if not isinstance(contract,EffectiveContract):raise TypeError('contract must be EffectiveContract')
    if not isinstance(actual,ContractActuals):raise TypeError('actual must be ContractActuals')
    return ProofData(
        N_target=contract.N,N_actual=actual.N,
        T_target_seconds=contract.T_seconds,T_actual_seconds=actual.T_seconds,
        R_target=contract.R,R_actual=actual.R,B=contract.B,
        S_count=actual.S_count,n_target=contract.S.n,n_actual=actual.n_min,
        t_target_seconds=contract.S.t_seconds,t_actual_seconds=actual.t_seconds,
        r_target=contract.S.r,r_actual=actual.r_min,b=contract.S.b,
        D_target=contract.D_s,D_actual=actual.D_s,
        T_hard_verified=actual.T_hard_verified,t_hard_verified=actual.t_hard_verified,
        T_coverage_complete=actual.T_coverage_complete,t_coverage_complete=actual.t_coverage_complete,
    )
