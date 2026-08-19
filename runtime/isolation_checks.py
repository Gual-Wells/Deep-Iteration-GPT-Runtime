"""Mechanical evidence and receipts for DIGR D isolation levels (Alpha 2).

Capability, requested target, and actual implementation are deliberately
separate.  A host that can support L3 does not thereby claim that a particular
intervention actually ran at L3.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from typing import Any
from .validation import require_bool,require_isolation_level,require_nonempty_text

@dataclass(frozen=True)
class IsolationFacts:
    semantic_firewall:bool
    separate_llm_history:bool=False
    controlled_telemetry_only:bool=False
    latent_d_state_hidden_from_main:bool=False
    application_state_isolated_or_filtered:bool=False
    independent_agent_identity:bool=False
    independent_instructions:bool=False
    independent_execution_loop:bool=False
    independent_tool_execution:bool=False
    def __post_init__(self):
        for n in self.__dataclass_fields__:require_bool(n,getattr(self,n))
    @property
    def L1(self):return self.semantic_firewall
    @property
    def L2(self):return all((self.L1,self.separate_llm_history,self.controlled_telemetry_only,self.latent_d_state_hidden_from_main,self.application_state_isolated_or_filtered))
    @property
    def L3(self):return all((self.L2,self.independent_agent_identity,self.independent_instructions,self.independent_execution_loop,self.independent_tool_execution))
    @property
    def max_claimable_level(self)->int|None:
        return 3 if self.L3 else (2 if self.L2 else (1 if self.L1 else None))
    def to_dict(self):d=asdict(self);d['max_claimable_level']=self.max_claimable_level;return d
    @classmethod
    def from_dict(cls,d):return cls(*(d[k] for k in ('semantic_firewall','separate_llm_history','controlled_telemetry_only','latent_d_state_hidden_from_main','application_state_isolated_or_filtered','independent_agent_identity','independent_instructions','independent_execution_loop','independent_tool_execution')))

@dataclass(frozen=True)
class IsolationReceipt:
    receipt_id:str
    L_target:int
    L_cap:int|None
    L_actual:int|None
    facts:IsolationFacts
    input_packet_ref:str|None=None
    output_packet_ref:str|None=None
    mode:str='exclusive'
    def __post_init__(self):
        object.__setattr__(self,'receipt_id',require_nonempty_text('receipt_id',self.receipt_id));require_isolation_level('L_target',self.L_target)
        if self.L_cap is not None:require_isolation_level('L_cap',self.L_cap)
        if self.L_actual is not None:require_isolation_level('L_actual',self.L_actual)
        if not isinstance(self.facts,IsolationFacts):raise TypeError('facts must be IsolationFacts')
        if self.L_cap!=self.facts.max_claimable_level:raise ValueError('L_cap must equal evidence-backed capability')
        expected=min(self.L_target,self.L_cap) if self.L_cap is not None else None
        if self.L_actual!=expected:raise ValueError('L_actual must be the actually selected target bounded by capability')
        for n in ('input_packet_ref','output_packet_ref'):
            v=getattr(self,n)
            if v is not None:object.__setattr__(self,n,require_nonempty_text(n,v))
        if self.mode not in ('exclusive','background'):raise ValueError('mode must be exclusive/background')
        if self.L_actual is not None and self.L_actual >= 2 and self.input_packet_ref is None:
            raise ValueError('L2/L3 actual isolation requires a controlled Input Packet artifact before D execution')
        if self.mode=='background' and self.L_actual not in (2,3):
            raise ValueError('background D requires actual isolated context L2 or L3')
    @property
    def target_met(self):return self.L_actual==self.L_target
    def to_dict(self)->dict[str,Any]:
        return {'receipt_id':self.receipt_id,'L_target':self.L_target,'L_cap':self.L_cap,'L_actual':self.L_actual,'facts':self.facts.to_dict(),'input_packet_ref':self.input_packet_ref,'output_packet_ref':self.output_packet_ref,'mode':self.mode,'target_met':self.target_met}
    @classmethod
    def from_dict(cls,d):return cls(d['receipt_id'],d['L_target'],d.get('L_cap'),d.get('L_actual'),IsolationFacts.from_dict(d['facts']),d.get('input_packet_ref'),d.get('output_packet_ref'),d.get('mode','exclusive'))

def make_isolation_receipt(receipt_id:str,target:int,facts:IsolationFacts,*,input_packet_ref:str|None=None,output_packet_ref:str|None=None,mode:str='exclusive')->IsolationReceipt:
    require_isolation_level('target',target)
    if not isinstance(facts,IsolationFacts):raise TypeError('facts must be IsolationFacts')
    cap=facts.max_claimable_level;actual=min(target,cap) if cap is not None else None
    return IsolationReceipt(receipt_id,target,cap,actual,facts,input_packet_ref,output_packet_ref,mode)

def level_is_supported(target:int,facts:IsolationFacts)->bool:
    require_isolation_level('target',target)
    if not isinstance(facts,IsolationFacts):raise TypeError('facts must be IsolationFacts')
    return facts.max_claimable_level is not None and facts.max_claimable_level>=target
