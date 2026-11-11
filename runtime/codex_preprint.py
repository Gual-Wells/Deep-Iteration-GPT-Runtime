"""English-Spoken-Preprint: explicit fictional state and native-agent I/O.

No model calls, scheduler, natural-language truth checker or learner diagnosis.
World decisions, character perceptions and authored inner speech are separate.
"""
from __future__ import annotations
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import uuid

SCHEMA = 2
KEY = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,100}$')


def need(condition, message):
    if not condition:raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):return sha256(canonical(value)).hexdigest()


def text(value, name):
    need(isinstance(value, str) and value.strip(), name+' must be nonempty text')
    return value


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def _write(path, value):
    path=Path(path);temp=path.with_name(path.name+'.new-'+uuid.uuid4().hex)
    with temp.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    temp.replace(path)


def _sealed(value):
    value=deepcopy(value);value.pop('integrity_sha256',None)
    value['integrity_sha256']=digest(value);return value


def load(root):
    state=read(Path(root)/'preprint.json');need(type(state.get('schema_version')) is int and state['schema_version'] in {1,SCHEMA},'unsupported preprint schema')
    actual=deepcopy(state);actual.pop('integrity_sha256',None)
    need(digest(actual)==state.get('integrity_sha256'),'preprint snapshot changed outside a recorded operation')
    return state


@contextmanager
def _lock(root):
    path=Path(root)/'.writer.lock';token=uuid.uuid4().hex
    try:fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise ValueError('writer lock exists; inspect its process before recovery') from None
    with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump({'pid':os.getpid(),'token':token},f)
    try:yield
    finally:
        if path.exists() and read(path).get('token')==token:path.unlink()


def initialize(root, spec):
    root=Path(root).resolve();need(not root.exists(),'new preprint root must not exist')
    need(isinstance(spec,dict),'spec must be an object')
    for key in ('id','title','public_scene'):text(spec.get(key),key)
    need(KEY.fullmatch(spec['id']),'invalid preprint id')
    actors=spec.get('actors');need(isinstance(actors,list) and len(actors)>=2,'at least two independent characters required')
    seen=set()
    for actor in actors:
        aid=actor.get('id');need(isinstance(aid,str) and KEY.fullmatch(aid) and aid not in seen,'invalid/duplicate actor id')
        seen.add(aid)
        for key in ('name','outward','inner'):need(actor.get(key),'each character needs name, outward and inner companion material')
    directors=spec.get('directors',[])
    need(isinstance(directors,list),'directors must be a list')
    need(all(isinstance(d,dict) and isinstance(d.get('id'),str) and KEY.fullmatch(d['id']) for d in directors),'invalid director')
    need(len({d['id'] for d in directors})==len(directors),'duplicate director id')
    need(isinstance(spec.get('initial_state',{}),dict),'initial_state must be an object')
    need(isinstance(spec.get('sources',[]),list),'sources must be a list')
    from runtime import codex_preprint_context, codex_preprint_learning
    codex_preprint_context.validate_spec(spec)
    codex_preprint_learning.validate_spec(spec)
    state={'schema_version':SCHEMA,'revision':0,'spec':deepcopy(spec),'spec_sha256':digest(spec),
        'world':deepcopy(spec.get('initial_state',{})),'events':[],
        'language':[],'learner_evidence':[],
        'receipts':{},'status':'DRAFT',
        'limits':'operator-authored fictional facts and source attributions; no semantic or host authentication'}
    root.mkdir(parents=True);_write(root/'preprint.json',_sealed(state))
    return {'root':root.as_posix(),'id':spec['id'],'revision':0,'status':'DRAFT','schema_version':SCHEMA}


def requires_current_schema(state):
    spec=state['spec']
    return (any(k in spec for k in ('learning_contract','world_rules','frozen_world_keys','perturbation_defs')) or
            any(any(k in a for k in ('personal_context','working_profile','materials')) for a in spec['actors']) or
            any(state.get(k) for k in ('learning_cases','learning_lessons','series_relations','perturbations')))


def upgrade_source(root, *, expected_revision, operation_id):
    """Explicit format migration; historical reads never rewrite their source."""
    def change(state):
        previous=state['schema_version'];state['schema_version']=SCHEMA
        return {'schema_migration':{'from':previous,'to':SCHEMA},'scope':'Format and writer boundary; no learning evidence or dialogue changes.'}
    return _mutate(root,{'upgrade_source_schema':SCHEMA},expected_revision,operation_id,change)


def _actor(state, aid):
    actor=next((a for a in state['spec']['actors'] if a['id']==aid),None)
    need(actor is not None,'unknown character');return actor


def _audience(value, state):
    need(isinstance(value,list) and value,'explicit nonempty audience required')
    valid={'public','creator',*(a['id'] for a in state['spec']['actors'])}
    need(all(isinstance(a,str) and a in valid for a in value),'unknown audience')
    return value


def _event_view(event, aid, channel):
    """Do not reveal unseen causes, global revisions or sequence-number gaps."""
    kind=event['kind'];public='public' in event.get('audience',[]) or aid in event.get('audience',[])
    if kind in {'speech','action'} and public:
        view={'id':event['id'],'kind':kind,'actor':event.get('actor'),'text':event['text']}
        if event.get('actor')==aid and event.get('material_results'):
            view['own_material_results']=deepcopy(event['material_results'])
        return view
    if kind in {'world','perturbation'}:
        perceptions=[p['text'] for p in event.get('percepts',[]) if 'public' in p['to'] or aid in p['to']]
        if perceptions:return {'id':event['id'],'kind':'observation','percepts':perceptions}
    if kind in {'inner','inner_reply'} and event.get('actor')==aid:
        return {'id':event['id'],'kind':'companion_message','text':event['text'],
            'from_channel':'inner' if kind=='inner' else 'outward',
            'authored_by_self':(kind=='inner')==(channel=='inner')}
    return None


def actor_packet(root, aid, channel='outward'):
    need(channel in {'outward','inner'},'character channel must be outward or inner')
    state=load(root);actor=_actor(state,aid)
    view={'character':{'id':aid,'name':actor['name']},'channel':channel,
        'identity':'fictional outward participant' if channel=='outward' else 'fictional private inner companion; not model hidden reasoning',
        'persona':deepcopy(actor[channel]),'own_background':deepcopy(actor.get('own_background',[])),
        'scene':state['spec']['public_scene'],
        'cast':[{'id':a['id'],'name':a['name'],'public_role':a.get('public_role','')} for a in state['spec']['actors']],
        'observed':[p for e in state['events'] if (p:=_event_view(e,aid,channel)) is not None],
        'instruction':'Use only this view. Another character claim is not certified world truth. Choose your own response, including silence or refusal.'}
    from runtime.codex_preprint_context import actor_additions
    view.update(actor_additions(state,aid,channel))
    return {'packet_sha256':digest(view),'view':view}


def director_packet(root, director_id):
    state=load(root);director=next((d for d in state['spec'].get('directors',[]) if d['id']==director_id),None)
    need(director is not None,'unknown world director')
    public_events=[]
    for event in state['events']:
        if event['kind'] in {'speech','action'} and 'public' in event.get('audience',[]):
            public_events.append({'id':event['id'],'kind':event['kind'],'actor':event['actor'],'text':event['text']})
        elif (event['kind']=='world' and event['decision']=='apply') or event['kind']=='perturbation':
            percepts=[item['text'] for item in event.get('percepts',[]) if 'public' in item['to']]
            if percepts:public_events.append({'id':event['id'],'kind':'observation','percepts':percepts})
    view={'director':deepcopy(director),'scene':state['spec']['public_scene'],
        'world':deepcopy(state['world']),
        'public_events':public_events,
        'instruction':'Propose or refrain. Affect situations and perceived events, not another participant private mind. Do not write other characters dialogue.'}
    from runtime.codex_preprint_context import director_additions
    view.update(director_additions(state,director_id))
    return {'packet_sha256':digest(view),'view':view}


def _mutate(root, payload, expected_revision, operation_id, change):
    root=Path(root);need(isinstance(operation_id,str) and KEY.fullmatch(operation_id),'stable operation id required')
    request_hash=digest(payload)
    with _lock(root):
        state=load(root);previous=state['receipts'].get(operation_id)
        if previous:
            need(previous['request_sha256']==request_hash,'operation id reused with different content')
            return {**previous,'retried':True}
        need(type(expected_revision) is int and state['revision']==expected_revision,'revision conflict; reload actual state')
        result=change(state)
        if state['schema_version']==1 and requires_current_schema(state):
            state['schema_version']=SCHEMA
            result['schema_migration']={'from':1,'to':SCHEMA}
        state['revision']+=1
        receipt={'operation_id':operation_id,'request_sha256':request_hash,'revision':state['revision'],**result}
        state['receipts'][operation_id]=receipt
        _write(root/'preprint.json',_sealed(state));return receipt


def append_event(root, payload, *, expected_revision, operation_id):
    """Commit an attributed result, never infer world effects from a speech."""
    need(isinstance(payload,dict),'event input must be an object')
    def change(state):
        kind=payload.get('kind');need(kind in {'speech','action','inner','inner_reply','world','perturbation','note'},'invalid event kind')
        event=deepcopy(payload);text(event.get('source_ref'),'actual source reference')
        event['id']='e-'+uuid.uuid4().hex[:16]
        event['recorded_at']=datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        event['time_basis']='ledger commit time, not hidden thought or speech latency'
        aid=event.get('actor')
        if kind in {'speech','action','inner','inner_reply'}:
            _actor(state,aid);text(event.get('text'),'actual utterance/action/fictional inner message')
            channel='inner' if kind=='inner' else 'outward'
            need(payload.get('packet_sha256')==actor_packet(root,aid,channel)['packet_sha256'],'stale character view; deliver new observations before another submission')
            text(event.get('executor'),'actual attributed native context')
            if kind in {'inner','inner_reply'}:event['audience']=['creator']
            else:event['audience']=_audience(event.get('audience',['public']),state)
            need('changes' not in event,'speech/action attribution does not certify world effects; use an explicit world decision')
            if event.get('reads'):
                need(kind in {'speech','action'},'physical material access belongs to outward action')
                from runtime.codex_preprint_context import apply_material_reads
                apply_material_reads(state,event)
        elif kind=='world':
            need(event.get('decision') in {'apply','retain','decline'},'record the actual world decision')
            text(event.get('proposal'),'world proposal');text(event.get('reason'),'world handling reason')
            event['audience']=['creator']
            changes=event.get('changes',{});need(isinstance(changes,dict),'world changes must be an object')
            from runtime.codex_preprint_context import validate_world
            validate_world(state,event,root)
            for p in event.get('percepts',[]):text(p.get('text'),'perceived event');_audience(p.get('to'),state)
            if event['decision']=='apply':state['world'].update(deepcopy(changes))
            else:
                need(not event.get('percepts'),'unapplied proposals cannot be delivered as experienced events')
                need(not changes,'unapplied proposals cannot change world state')
        elif kind=='perturbation':
            from runtime.codex_preprint_context import apply_perturbation
            apply_perturbation(state,event,root)
        else:event['audience']=['creator']
        state['events'].append(event)
        return {'event_id':event['id'],'kind':kind,'semantic_certification':False}
    return _mutate(root,payload,expected_revision,operation_id,change)


def annotate(root,payload,*,expected_revision,operation_id):
    def change(state):
        resources=payload.get('resources');need(isinstance(resources,list),'resources must be a list')
        by_id={e['id']:e for e in state['events']}
        for item in resources:
            event=by_id.get(item.get('event_id'));need(event is not None and event['kind']=='speech','language source must be a real submitted utterance')
            need(text(item.get('surface'),'actual language span') in event['text'],'language span absent from its source utterance')
            for field in ('meaning','function','register','frequency_status'):text(item.get(field),field)
            need('learner_mastery' not in item,'work language resources do not create learner mastery')
        threads=payload.get('listening_threads',[]);need(isinstance(threads,list),'listening threads must be a list')
        for thread in threads:
            for field in ('id','label','text'):text(thread.get(field),field)
            ids=thread.get('event_ids');need(isinstance(ids,list) and ids,'thread needs actual public utterances')
            need(all(i in by_id and by_id[i]['kind']=='speech' and 'public' in by_id[i].get('audience',[]) for i in ids),'listening thread refers to a non-public utterance')
            need('learner_mastery' not in thread,'listening resources do not create learner mastery')
        state['language'].extend(deepcopy(resources))
        state.setdefault('listening_threads',[]).extend(deepcopy(threads))
        return {'resources_added':len(resources),'threads_added':len(threads),'learner_evidence_added':0}
    return _mutate(root,payload,expected_revision,operation_id,change)
