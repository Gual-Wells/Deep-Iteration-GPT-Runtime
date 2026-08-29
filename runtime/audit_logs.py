"""User-facing, local-only Berta audit-log materialization."""
from __future__ import annotations
import json
from typing import Any

LOG_NAMES=('N','T','R','B','S','D','V','L')

def _line(kind:str,event:str,details:dict[str,Any])->dict[str,Any]:
    return {'schema_version':1,'parameter':kind,'event':event,'details':details}

def materialize_audit_logs(run,actual)->dict[str,dict[str,Any]]:
    """Write TOTAL and independent parameter logs without any UI/bridge."""
    logs={name:[] for name in LOG_NAMES}
    contract=run.contract
    logs['T'].append(_line('T','CLOCK_SUMMARY',{
        'T_target_seconds':contract.T_seconds,'T_actual_seconds':actual.T_seconds,
        't_actual_seconds':actual.t_seconds,'D_actual_seconds':actual.D_actual_seconds,
        'V_actual_seconds':actual.V_actual_seconds,'clock_states':['MAIN','SOURCE','D_EXCLUSIVE','V_EXCLUSIVE','META','IDLE'],
    }))
    logs['B'].append(_line('B','POLICY',{'B':contract.B,'T_hard_verified':actual.T_hard_verified,'b':contract.S.b,'t_hard_verified':actual.t_hard_verified}))
    for event in run.events.events:
        row=_line('N' if event.kind.value=='MAIN_EVOLUTION' else 'R' if event.kind.value=='MAIN_REENTRY' else 'S',event.kind.value,event.to_dict())
        logs[row['parameter']].append(row)
    for source in run.sources.states:
        logs['S'].append(_line('S','WORKSPACE',source.to_dict()))
    for item in run.dictator.items:
        logs['D'].append(_line('D',item.status,item.to_dict()))
    logs['D'].append(_line('D','TIME',{'target':contract.D_s,'actual':actual.D_s,'actual_seconds':actual.D_actual_seconds,'time_verified':actual.D_time_verified}))
    for item in run.viewpoints.states:
        # V's compact result is user-facing semantic output, not private
        # chain-of-thought. Keep it beside behavior/finding evidence just as D
        # keeps its recorded outcomes.
        logs['V'].append(_line('V',item.status,item.to_dict()))
    logs['V'].append(_line('V','TIME',{'target':contract.V_o,'actual':actual.V_o,'actual_seconds':actual.V_actual_seconds,'time_verified':actual.V_time_verified}))
    logs['L'].append(_line('L','ISOLATION',{'target':contract.L_e,'actual':actual.L_e,'mismatch_blocks_delivery':contract.L_mismatch_blocks_delivery}))
    # N/R zero-actual runs still get an explicit audit fact.
    for name,target,value in [('N',contract.N,actual.N),('R',contract.R,actual.R)]:
        logs[name].append(_line(name,'COUNT',{'target':target,'actual':value}))
    paths={}
    total=[]
    for name in LOG_NAMES:
        rel=f'logs/{name}.ndjson';payload=''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in logs[name]).encode('utf-8')
        digest=run.workspace.atomic_write_bytes(rel,payload);run.workspace.index_existing(rel,kind=f'audit-{name.lower()}',expected_digest=digest);paths[name]={'path':rel,'sha256':digest,'byte_length':len(payload)}
        total.extend(logs[name])
    rel='logs/TOTAL.ndjson';payload=''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in total).encode('utf-8')
    digest=run.workspace.atomic_write_bytes(rel,payload);run.workspace.index_existing(rel,kind='audit-total',expected_digest=digest);paths={'TOTAL':{'path':rel,'sha256':digest,'byte_length':len(payload)},**paths}
    return paths
