"""Derived compact run brief for recovery/context re-entry.

The brief is a cache/index. Authoritative stores remain U0/contract/strategy/
candidate/source/D/completion/evidence and the clock/event journals.
"""
from __future__ import annotations
from hashlib import sha256
import json
from .workspace import RunWorkspace


def _digest(obj)->str:
    return sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def build_run_brief(run) -> dict:
    strategy = run.strategy.current if run.strategy.has_state else None
    candidate = run.candidates.current if run.candidates.has_state else None
    active_sources=[s.source_id for s in run.sources.open_states]
    gaps=[g.gap_id for g in run.completion.blocking_open]
    evidence=[x.evidence_id for x in run.evidence.items]
    latest_events=[e.event_id for e in run.events.events[-8:]]
    data={
        'schema_version':1,
        'run_id':run.run_id,
        'U0_sha256':run.U0.sha256 if run.U0 else None,
        'contract_present':run.contract is not None,
        'phase':run.phase.phase.value,
        'strategy_revision':strategy.revision if strategy else None,
        'candidate_revision':candidate.revision if candidate else None,
        'active_source_ids':active_sources,
        'D_completed':run.dictator.completed_count,
        'blocking_gap_ids':gaps,
        'key_evidence_refs':evidence[-24:],
        'latest_meaningful_event_refs':latest_events,
    }
    data['content_digest']=_digest(data)
    return data


def verify_run_brief(workspace: RunWorkspace, authoritative: dict) -> bool:
    d=workspace.read_json('state/run-brief.json')
    digest=d.pop('content_digest',None)
    if digest!=_digest(d): raise ValueError('run brief digest mismatch')
    for key,value in authoritative.items():
        if d.get(key)!=value: raise ValueError(f'run brief drift: {key}')
    return True
