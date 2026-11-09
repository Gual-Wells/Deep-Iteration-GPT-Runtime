"""A private, source-bound knowledge pool; no model calls or mastery inference.

The snapshot is the authority. Receipts make a committed operation retryable;
frozen question items preserve what a historical answer actually referred to.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata
import uuid

SCHEMA = 2
RUNTIME_REPOSITORY = 'Gual-Wells/Deep-Iteration-GPT-Runtime'
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$')
SHA = re.compile(r'^[0-9a-f]{64}$')
EVIDENCE_KINDS = {'self_report', 'application_observation', 'needs_review',
                  'declined_check', 'legacy_unverified_claim'}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identifier(value):
    require(isinstance(value, str) and ID.fullmatch(value), 'invalid identifier')
    return value


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def seal(value):
    value = deepcopy(value)
    value.pop('integrity_sha256', None)
    value['integrity_sha256'] = digest(value)
    return value


def validate(value):
    require(isinstance(value, dict), 'pool must be an object')
    require(value.get('schema_version') == SCHEMA,
            'unsupported schema; import/migrate into a new pool, never guess')
    unsigned = dict(value)
    supplied = unsigned.pop('integrity_sha256', None)
    require(supplied == digest(unsigned), 'snapshot integrity mismatch')
    require(type(value.get('revision')) is int and value['revision'] >= 0,
            'invalid revision')
    for name in ('concepts', 'papers', 'occurrences', 'sessions', 'pool_members',
                 'explanations', 'evidence', 'receipts'):
        require(isinstance(value.get(name), dict), f'invalid {name}')
    for cid, c in value['concepts'].items():
        identifier(cid)
        core = {k: c[k] for k in ('id', 'label', 'definition', 'aliases', 'prerequisites')}
        require(c['content_sha256'] == digest(core), 'concept content mismatch')
        require(c['id'] == cid and set(c['prerequisites']) <= set(value['concepts']),
                'broken prerequisite reference')
    for oid, occurrence in value['occurrences'].items():
        require(oid == digest(occurrence), 'occurrence identity mismatch')
        require(occurrence['concept_id'] in value['concepts'], 'unknown concept')
        p = value['papers'].get(occurrence['paper_id'], {})
        require(occurrence['source_sha256'] in p.get('sources', {}), 'unknown source')
        source=p['sources'][occurrence['source_sha256']]
        require(occurrence['representation_sha256'] in source['representations'],
                'unknown source representation')
    require(set(value['pool_members']) <= set(value['occurrences']), 'broken pool member')
    for session in value['sessions'].values():
        questionnaire = session['questionnaire']
        require(session['questionnaire_sha256'] == digest(questionnaire),
                'questionnaire content mismatch')
        offered = {x['item_id'] for x in questionnaire['items']}
        require(set(session['selected_ids']) <= offered, 'selection outside offered set')
        for item in questionnaire['items']:
            require(set(item['occurrence_ids']) <= set(value['occurrences']),
                    'broken question occurrence')
    for oid, correction in value.get('use_corrections', {}).items():
        require(oid in value['occurrences'] and correction['replacement_id'] in value['occurrences'],
                'broken use correction reference')
        _correction_chain(value, oid)
    return value


def load(root: Path):
    return validate(read_json(Path(root) / 'pool.json'))


def _atomic(path: Path, value):
    raw = (json.dumps(seal(value), ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    fd, temporary = tempfile.mkstemp(prefix='.pool-', suffix='.json', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        validate(read_json(Path(temporary)))
        os.replace(temporary, path)
        require(path.read_bytes() == raw, 'snapshot read-back mismatch')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def _lock(root: Path):
    path = root / '.pool.lock'
    token = uuid.uuid4().hex
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError('pool is locked; inspect .pool.lock and its process before recovery') from exc
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump({'pid': os.getpid(), 'token': token, 'at': now()}, stream)
        yield
    finally:
        try:
            if read_json(path).get('token') == token:
                path.unlink()
        except FileNotFoundError:
            pass


def initialize(root: Path, *, runtime_pin: str, repository: str):
    root = Path(root).resolve()
    require(re.fullmatch(r'[^@\s]+@[0-9a-f]{40}', runtime_pin), 'invalid runtime pin')
    require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository), 'invalid repository')
    require(repository.casefold() != RUNTIME_REPOSITORY.casefold(),
            'personal data must not use the public runtime repository')
    root.mkdir(parents=True, exist_ok=True)
    with _lock(root):
        require(not (root / 'pool.json').exists(), 'pool already exists')
        pool = dict(schema_version=SCHEMA, revision=0, pool_id=uuid.uuid4().hex,
                    created_at=now(), updated_at=now(),
                    binding={'runtime_repository': RUNTIME_REPOSITORY,
                             'runtime_ref': 'codex/codex-host-adaptation',
                             'protocol_pin': runtime_pin,
                             'data_repository': repository, 'private_required': True},
                    concepts={}, papers={}, occurrences={}, sessions={}, pool_members={},
                    explanations={}, evidence={}, receipts={}, concept_history={}, use_corrections={}, active_session=None)
        _atomic(root / 'pool.json', pool)
    return load(root)


def mutate(root: Path, *, expected_revision: int, operation_id: str, action: str,
           payload: dict, operation):
    root = Path(root).resolve()
    identifier(operation_id)
    request_hash = digest({'action': action, 'payload': payload})
    with _lock(root):
        pool = load(root)
        receipt = pool['receipts'].get(operation_id)
        if receipt:
            require(receipt['request_sha256'] == request_hash,
                    'operation id reused with different content')
            return {'replayed': True, **receipt}
        require(pool['revision'] == expected_revision,
                f'revision conflict: expected {expected_revision}, current {pool["revision"]}')
        result = operation(pool)
        pool['revision'] += 1
        pool['updated_at'] = now()
        receipt = {'request_sha256': request_hash, 'action': action,
                   'revision': pool['revision'], 'result': result, 'recorded_at': now()}
        pool['receipts'][operation_id] = receipt
        _atomic(root / 'pool.json', pool)
        return {'replayed': False, **receipt}


def _normalized(text):
    text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text)).casefold()


def _source(root: Path, paper):
    file = Path(paper['file'])
    file = file if file.is_absolute() else root / file
    require(file.is_file(), 'source file missing')
    require(file_digest(file) == paper['source_sha256'], 'source SHA256 mismatch')
    if file.suffix.lower() == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError('PDF ingestion requires pypdf in the chosen Python runtime') from exc
        import pypdf
        reader = PdfReader(file)
        texts = [page.extract_text() or '' for page in reader.pages]
        extractor = 'pypdf/' + pypdf.__version__
    else:
        require(file.suffix.lower() in ('.txt', '.md'), 'supported source formats: PDF, TXT, MD')
        texts = [file.read_text(encoding='utf-8-sig')]
        extractor = 'utf-8-sig text/' + str(SCHEMA)
    require(len(texts) == paper['pages'], 'source page count mismatch')
    try:
        stored_file = file.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        stored_file = str(file.resolve())
    representation={'extractor':extractor,
                    'page_text_sha256':[hashlib.sha256(t.encode('utf-8')).hexdigest() for t in texts]}
    rep_id=digest(representation)
    return {'file':stored_file,'pages':len(texts),'active_representation_sha256':rep_id,
            'representations':{rep_id:representation}}, texts


def ingest(root: Path, analysis: dict, *, expected_revision: int, operation_id: str):
    """Commit native-Codex analysis, checking anchors; never infer concepts from PDF bytes."""
    root = Path(root).resolve()
    def apply(pool):
        paper = analysis['paper']
        pid = identifier(paper['id'])
        require(SHA.fullmatch(paper['source_sha256']), 'invalid source digest')
        source, texts = _source(root, paper)
        old = pool['papers'].get(pid)
        if old and old['active_source_sha256'] != paper['source_sha256']:
            require(analysis.get('new_source_version') is True,
                    'source version changed; explicitly retain the old version and create a new session')
        record = pool['papers'].setdefault(pid, {'id': pid, 'title': paper['title'], 'sources': {}})
        previous_source=record['sources'].get(paper['source_sha256'])
        if previous_source:
            source['representations']={**previous_source['representations'],**source['representations']}
        record['sources'][paper['source_sha256']] = source
        record['active_source_sha256'] = paper['source_sha256']
        for supplied in analysis['concepts']:
            c = {k: deepcopy(supplied.get(k, [] if k in ('aliases','prerequisites') else None))
                 for k in ('id','label','definition','aliases','prerequisites')}
            identifier(c['id'])
            require(c['label'] and c['definition'], 'empty concept content')
            require(all(isinstance(x,str) for x in c['aliases']+c['prerequisites']), 'invalid concept links')
            c['content_sha256'] = digest(c)
            previous = pool['concepts'].get(c['id'])
            require(previous is None or previous['content_sha256'] == c['content_sha256'],
                    'concept meaning changed; use a distinct id or an explicit reviewed migration')
            pool['concepts'][c['id']] = c
        require(all(set(c['prerequisites']) <= set(pool['concepts'])
                    for c in pool['concepts'].values()), 'unknown prerequisite')
        by_key = {}
        for item in analysis['occurrences']:
            key = identifier(item['key'])
            require(key not in by_key, 'duplicate occurrence key')
            cid = identifier(item['concept_id'])
            require(cid in pool['concepts'], 'occurrence concept missing')
            page = item['page']
            require(type(page) is int and 1 <= page <= len(texts), 'invalid source page')
            require(item.get('quote') and _normalized(item['quote']) in _normalized(texts[page-1]),
                    f'source quote not found: {key}')
            occurrence = {'paper_id': pid, 'source_sha256': paper['source_sha256'],
                          'representation_sha256':source['active_representation_sha256'],
                          'concept_id': cid, 'page': page, 'section': item.get('section',''),
                          'quote': item['quote'], 'usage': item['usage'],
                          'role': item.get('role',''), 'assumptions': item.get('assumptions',[]),
                          'claim_kind': item.get('claim_kind','author_usage'),
                          'concept_snapshot': deepcopy(pool['concepts'][cid])}
            require(occurrence['claim_kind'] in ('author_usage','author_claim','background_reference'),
                    'unknown claim kind')
            oid = digest(occurrence)
            pool['occurrences'][oid] = occurrence
            by_key[key] = oid
        questions=[]
        for q in analysis['questions']:
            iid = identifier(q['item_id'])
            require(iid not in {x['item_id'] for x in questions}, 'duplicate question item')
            refs = [by_key[k] for k in q['occurrence_keys']]
            require(refs, 'question without source context')
            questions.append({'item_id':iid,'group':q['group'],'label':q['label'],
                              'occurrence_ids':refs,
                              'offered_context':[deepcopy(pool['occurrences'][oid]) for oid in refs]})
        require(questions, 'empty questionnaire')
        session_id = identifier(analysis['session_id'])
        require(session_id not in pool['sessions'], 'session already exists')
        questionnaire={'paper_id':pid,'source_sha256':paper['source_sha256'],
                       'analysis_sha256':digest(analysis),'items':questions}
        pool['sessions'][session_id]={'id':session_id,'questionnaire':questionnaire,
            'questionnaire_sha256':digest(questionnaire),'selected_ids':[],
            'selection_record':None,'status':'awaiting_selection','created_at':now()}
        pool['active_session']=session_id
        return {'session_id':session_id,'questionnaire_sha256':digest(questionnaire),
                'offered':len(questions),'source_pages_checked':len(texts)}
    return mutate(root,expected_revision=expected_revision,operation_id=operation_id,
                  action='ingest',payload=analysis,operation=apply)


def _session(pool, payload):
    session = pool['sessions'].get(payload['session_id'])
    require(session is not None, 'session missing')
    require(payload.get('questionnaire_sha256') == session['questionnaire_sha256'],
            'questionnaire changed or response refers to another session')
    return session


def _pool_item(pool, session, item, reason):
    for oid in item['occurrence_ids']:
        member=pool['pool_members'].setdefault(oid,{'occurrence_id':oid,'added_at':now(),
                                                  'introductions':[]})
        entry={'session_id':session['id'],'questionnaire_sha256':session['questionnaire_sha256'],
               'item_snapshot':deepcopy(item),'reason':reason}
        if entry not in member['introductions']:member['introductions'].append(entry)


def _retire_cursor(session,reason):
    cursor=session.pop('continuation',None)
    if cursor:
        session.setdefault('continuation_history',[]).append(
            {'cursor':cursor,'retired_at':now(),'reason':reason})


def select(root: Path, payload: dict, *, expected_revision: int, operation_id: str):
    def apply(pool):
        session=_session(pool,payload)
        require(session['status']!='closed','session closed')
        require(payload.get('response_text') and payload.get('response_ref'),
                'selection needs actual user response text and location')
        chosen=payload['selected_ids']
        require(isinstance(chosen,list) and len(chosen)==len(set(chosen)), 'invalid selection')
        offered={i['item_id']:i for i in session['questionnaire']['items']}
        require(set(chosen)<=set(offered),'selected item was not offered')
        # Only items actually shown to this user can count as unselected.
        for iid,item in offered.items():
            if iid not in chosen:_pool_item(pool,session,item,'offered_not_selected; unassessed')
        _retire_cursor(session,'a new actual selection response superseded the prior continuation')
        session['selection_history']=session.get('selection_history',[])+[
            deepcopy(session['selection_record'])] if session['selection_record'] else []
        session['selected_ids']=list(chosen)
        session['selection_record']={'selected_ids':list(chosen),'response_text':payload['response_text'],
                                    'response_ref':payload['response_ref'],'recorded_at':now()}
        session['status']='learning' if chosen else 'selection_saved'
        return {'selected_ids':list(chosen),'unselected_added':len(offered)-len(chosen),
                'mastery_inferred':False}
    return mutate(root,expected_revision=expected_revision,operation_id=operation_id,
                  action='select',payload=payload,operation=apply)


def record(root: Path, payload: dict, *, expected_revision: int, operation_id: str, kind: str):
    def apply(pool):
        session=_session(pool,payload)
        items={i['item_id']:i for i in session['questionnaire']['items']}
        require(payload['item_id'] in items,'item not offered')
        require(payload.get('source_ref'),'record needs a real message/artifact location')
        entry=deepcopy(payload)
        offered_uses=items[payload['item_id']]['occurrence_ids']
        scope=payload.get('occurrence_ids',offered_uses)
        require(isinstance(scope,list) and scope and len(scope)==len(set(scope))
                and set(scope)<=set(offered_uses),'record scope outside the offered question')
        entry['occurrence_ids']=list(scope)
        entry['scope_basis']='explicit use subset' if 'occurrence_ids' in payload else 'operator attributed the whole offered item'
        entry['recorded_at']=now()
        entry['record_basis']='operator-supplied observation; not authenticated or semantically certified by CLI'
        if kind=='explanation':
            require(payload.get('delivered') is True and payload.get('text'),
                    'prepared material is not a delivered explanation')
            require(payload['item_id'] in session['selected_ids'], 'item was not requested')
            entry['text_sha256']=hashlib.sha256(payload['text'].encode()).hexdigest()
            pool['explanations'][operation_id]=entry
        else:
            require(payload.get('kind') in EVIDENCE_KINDS,'unknown evidence kind')
            require(payload.get('statement') and payload.get('ability') and payload.get('representation'),
                    'evidence needs statement, concrete ability and representation')
            # A response/observation is kept as scoped evidence, not a global mastery rank.
            pool['evidence'][operation_id]=entry
        return {'item_id':payload['item_id'],'recorded':kind,'mastery_inferred':False}
    require(kind in ('explanation','evidence'),'invalid record kind')
    return mutate(root,expected_revision=expected_revision,operation_id=operation_id,
                  action=kind,payload=payload,operation=apply)


def finish(root: Path,payload: dict,*,expected_revision: int,operation_id: str):
    def apply(pool):
        session=_session(pool,payload)
        require(payload.get('source_ref'),'closing needs the actual user instruction/reference')
        for item in session['questionnaire']['items']:
            if item['item_id'] in session['selected_ids']:
                _pool_item(pool,session,item,'session_closed; see separate learning evidence')
        _retire_cursor(session,'paper session closed')
        session['status']='closed';session['closed_at']=now();session['close_ref']=payload['source_ref']
        return {'closed':session['id'],'learning_inferred':False}
    return mutate(root,expected_revision=expected_revision,operation_id=operation_id,
                  action='finish',payload=payload,operation=apply)


def revise_concept(root: Path,payload: dict,*,expected_revision: int,operation_id: str):
    """An explicit correction creates a current definition; historical questions stay frozen."""
    def apply(pool):
        cid=identifier(payload['concept_id']);old=pool['concepts'].get(cid)
        require(old is not None,'concept missing')
        require(payload.get('expected_content_sha256')==old['content_sha256'],
                'concept revision conflict')
        require(payload.get('reason') and payload.get('source_ref'),'correction needs reason and source')
        core={k:deepcopy(payload['replacement'][k]) for k in ('id','label','definition','aliases','prerequisites')}
        require(core['id']==cid and core['label'] and core['definition'],'invalid replacement')
        require(set(core['prerequisites'])<=set(pool['concepts']),'unknown prerequisite')
        replacement={**core,'content_sha256':digest(core)}
        pool.setdefault('concept_history',{}).setdefault(cid,[]).append(
            {'previous':deepcopy(old),'reason':payload['reason'],'source_ref':payload['source_ref'],
             'recorded_at':now(),'replacement_sha256':replacement['content_sha256']})
        pool['concepts'][cid]=replacement
        return {'concept_id':cid,'content_sha256':replacement['content_sha256'],
                'historical_questions_rewritten':False,'evidence_reinterpreted':False}
    return mutate(root,expected_revision=expected_revision,operation_id=operation_id,
                  action='revise-concept',payload=payload,operation=apply)


def checkpoint(root: Path,payload: dict,*,expected_revision: int,operation_id: str):
    """Save an attributed explanation cursor, without changing a learning judgment."""
    def apply(pool):
        session=_session(pool,payload)
        require(session['status']!='closed','closed session cannot receive a current continuation')
        require(payload.get('source_ref') and payload.get('summary') and payload.get('next_action'),
                'checkpoint needs actual context reference, summary and next action')
        _retire_cursor(session,'a newer attributed continuation replaced this cursor')
        session['continuation']={key:deepcopy(payload[key]) for key in payload
                                 if key not in ('session_id','questionnaire_sha256')}
        session['continuation']['questionnaire_sha256']=session['questionnaire_sha256']
        session['continuation']['selection_sha256']=digest(session['selection_record'])
        session['continuation']['recorded_at']=now()
        session['continuation']['basis']='agent summary and separately attributed user words; not a mastery claim'
        return {'session_id':session['id'],'cursor_saved':True,'learning_inferred':False}
    return mutate(root,expected_revision=expected_revision,operation_id=operation_id,
                  action='checkpoint',payload=payload,operation=apply)


def _correction_chain(pool,oid):
    chain=[];seen=set();corrections=pool.get('use_corrections',{})
    while oid in corrections:
        require(oid not in seen,'cyclic use corrections')
        seen.add(oid);entry=corrections[oid];chain.append(entry);oid=entry['replacement_id']
    return oid,chain


def revise_use(root: Path,payload: dict,*,expected_revision: int,operation_id: str):
    """Correct a paper-local interpretation without rewriting its historical question."""
    root=Path(root).resolve()
    def apply(pool):
        oid=payload['occurrence_id'];old=pool['occurrences'].get(oid)
        require(old is not None,'occurrence missing')
        require(oid not in pool.get('use_corrections',{}),'use already corrected; read its current replacement')
        require(payload.get('reason') and payload.get('source_ref'),'use correction needs reason and source')
        allowed={'concept_id','page','section','quote','usage','role','assumptions','claim_kind','supporting_quotes'}
        replacement=payload['replacement']
        require(set(replacement)<=allowed,'cannot move a correction to a different paper/source')
        new=deepcopy(old);new.update(deepcopy(replacement))
        require(new['concept_id'] in pool['concepts'],'replacement concept missing')
        require(new.get('usage') and new['claim_kind'] in ('author_usage','author_claim','background_reference'),
                'invalid correction interpretation')
        paper=pool['papers'][old['paper_id']];known=paper['sources'][old['source_sha256']]
        source,texts=_source(root,{'file':known['file'],'source_sha256':old['source_sha256'],'pages':known['pages']})
        for anchor in [{'page':new['page'],'quote':new['quote']},*new.get('supporting_quotes',[])]:
            require(type(anchor['page']) is int and 1<=anchor['page']<=len(texts),'invalid correction page')
            require(anchor['quote'] and _normalized(anchor['quote']) in _normalized(texts[anchor['page']-1]),
                    'correction quote not found')
        known['representations'].update(source['representations'])
        new['representation_sha256']=source['active_representation_sha256']
        new['concept_snapshot']=deepcopy(pool['concepts'][new['concept_id']])
        new['correction_origin']={'occurrence_id':oid,'reason':payload['reason'],'source_ref':payload['source_ref']}
        new_id=digest(new);pool['occurrences'][new_id]=new
        correction={'replacement_id':new_id,'reason':payload['reason'],'source_ref':payload['source_ref'],'recorded_at':now()}
        pool.setdefault('use_corrections',{})[oid]=correction
        if oid in pool['pool_members']:
            pool['pool_members'][new_id]={'occurrence_id':new_id,'added_at':now(),
                'introductions':[{'correction_of':oid,**deepcopy(correction)}]}
        return {'original_id':oid,'replacement_id':new_id,'history_preserved':True,
                'learning_evidence_transferred':False}
    return mutate(root,expected_revision=expected_revision,operation_id=operation_id,
                  action='revise-use',payload=payload,operation=apply)


def _state(pool,item):
    ids=set(item['occurrence_ids'])
    explanations=[e for e in pool['explanations'].values() if ids.intersection(e['occurrence_ids'])]
    evidence=[e for e in pool['evidence'].values() if ids.intersection(e['occurrence_ids'])]
    explained={oid for e in explanations for oid in e['occurrence_ids']} & ids
    return {'status':('evidence_recorded_for_scoped_ability' if evidence else
                     'explained_not_assessed' if explained==ids else
                     'partially_explained_not_assessed' if explained else 'unassessed'),
            'explained_occurrence_ids':sorted(explained),
            'unexplained_occurrence_ids':sorted(ids-explained),
            'explanations':explanations,'evidence':evidence}


def resume(root: Path,session_id: str | None=None,*,related_limit: int=3,item_ids=None):
    require(type(related_limit) is int and related_limit>=0,'invalid related limit')
    pool=load(root);sid=session_id or pool['active_session']
    require(sid in pool['sessions'],'no current learning session')
    s=deepcopy(pool['sessions'][sid]);q=s['questionnaire']
    pid=q['paper_id'];active=pool['papers'][pid]['active_source_sha256']
    items=[]
    requested_filter=set(item_ids or [])
    offered_ids={item['item_id'] for item in q['items']}
    require(requested_filter<=offered_ids,'requested item filter was not offered')
    for item in q['items']:
        if requested_filter and item['item_id'] not in requested_filter:continue
        current=deepcopy(item)
        current['requested']=item['item_id'] in s['selected_ids']
        current['learning']=_state(pool,item)
        current['use_corrections']=[{'original_id':oid,'current_id':current_id,
            'history':chain,'current_occurrence':deepcopy(pool['occurrences'][current_id])}
            for oid in item['occurrence_ids'] for current_id,chain in [_correction_chain(pool,oid)] if chain]
        # Other occurrences are context to inspect, never automatic transfer credit.
        cids={pool['occurrences'][oid]['concept_id'] for oid in item['occurrence_ids']}
        related_ids=[oid for oid in pool['pool_members'] if pool['occurrences'][oid]['concept_id'] in cids
                     and oid not in item['occurrence_ids'] and oid not in pool.get('use_corrections',{})]
        shown=related_ids[-related_limit:] if related_limit else []
        current['related_pool_uses']=[{'occurrence_id':oid,**deepcopy(pool['occurrences'][oid])} for oid in shown]
        current['related_uses_total']=len(related_ids)
        current['related_uses_more_available']=len(related_ids)>len(shown)
        for related in current['related_pool_uses']:
            related['learning']=_state(pool,{'occurrence_ids':[related['occurrence_id']]})
        current['current_definition_differs']=any(
            o['concept_snapshot']['content_sha256']!=pool['concepts'][o['concept_id']]['content_sha256']
            for o in item['offered_context'])
        prerequisites=set()
        for o in item['offered_context']:prerequisites.update(o['concept_snapshot']['prerequisites'])
        current['prerequisite_context']=[deepcopy(pool['concepts'][cid]) for cid in sorted(prerequisites)]
        current['prerequisite_context_basis']='current optional background; not historical question wording or a mandatory gate'
        items.append(current)
    source=pool['papers'][pid]['sources'][q['source_sha256']]
    file=Path(source['file']);file=file if file.is_absolute() else Path(root)/file
    cursor=s.get('continuation')
    cursor_valid=(cursor and s['status']!='closed' and
                  cursor.get('questionnaire_sha256')==s['questionnaire_sha256'] and
                  cursor.get('selection_sha256')==digest(s['selection_record']))
    return {'schema_version':SCHEMA,'revision':pool['revision'],'binding':pool['binding'],
            'session_id':sid,'status':s['status'],'questionnaire_sha256':s['questionnaire_sha256'],
            'source_status':'current' if active==q['source_sha256'] else 'older_frozen_source',
            'source_available':file.is_file(),'source_bytes_match':file.is_file() and file_digest(file)==q['source_sha256'],
            'paper_id':pid,'source_sha256':q['source_sha256'],'items':items,
            'selection_record':s['selection_record'],'continuation':cursor if cursor_valid else None,
            'continuation_history':s.get('continuation_history',[]),
            'legacy_unbound_continuation':cursor if cursor and not cursor_valid else None,
            'next_action':('session closed; choose another paper or explicitly revisit a scoped question'
                if s['status']=='closed' else 'ask for one multi-selection response'
                if not s['selection_record'] else '本次未请求解释；可结束或明确改选'
                if not s['selected_ids'] else
                'continue requested explanations; use evidence only within its stated scope'),
            'interpretation':'unselected is not known; explained is not understood; past evidence is not permanent mastery'}


def current_card(root: Path,session_id: str | None=None):
    packet=resume(root,session_id,related_limit=0)
    wanted=[x for x in packet['items'] if x['requested']]
    cursor=packet['continuation']
    labels=', '.join(x['item_id']+' '+x['label'] for x in wanted) or (
        '本次明确未请求解释' if packet['selection_record'] is not None else '尚未收到本次多选')
    lines=[f'# 当前论文：{packet["paper_id"]}',
           f'会话：{packet["session_id"]} · 数据版本 {packet["revision"]} · {packet["status"]}',
           f'本次请求：{labels}',
           '续讲位置：'+(cursor['summary'] if cursor else '当前无有效续讲游标；历史记录已保留'
                         if packet['continuation_history'] or packet['legacy_unbound_continuation']
                         else '尚未记录授课或暂停位置'),
           '下一步：'+(packet['next_action'] if packet['status']=='closed' else cursor['next_action'] if cursor else packet['next_action']),
           '原件版本：'+('当前版本' if packet['source_status']=='current' else '历史冻结版本；当前论文另有新版'),
           '原件：'+('字节匹配' if packet['source_bytes_match'] else '缺失或变更，先取回原件'),
           '选择、已讲和有范围证据分别保留；本卡不表示长期掌握。']
    return '\n\n'.join(lines)+'\n'


def questionnaire_markdown(root: Path,session_id: str | None=None):
    packet=resume(root,session_id)
    lines=['# 这篇论文需要补哪些',
           '',f'session_id: {packet["session_id"]}',
           f'questionnaire_sha256: {packet["questionnaire_sha256"]}',
           f'expected_revision: {packet["revision"]}',
           '', '可以一次选多个；未选仅表示本次不请求解释。可勾选此文件，或一次回复多个编号。','']
    previous=None
    for item in packet['items']:
        if item['group']!=previous:lines += ['## '+item['group'],''];previous=item['group']
        mark='x' if item['requested'] else ' '
        refs=','.join(str(o['page']) for o in item['offered_context'])
        lines.append(f'- [{mark}] {item["item_id"]} | {item["label"]} | 原文PDF p{refs}')
    return '\n'.join(lines)+'\n'


def parse_selection_markdown(text: str):
    def field(name):
        match=re.search(r'^'+re.escape(name)+r':\s*(\S+)\s*$',text,re.M)
        require(match is not None,'questionnaire header missing: '+name)
        return match.group(1)
    selected=re.findall(r'^- \[[xX]\]\s+([A-Za-z0-9._-]+)\s*\|',text,re.M)
    return {'session_id':field('session_id'),'questionnaire_sha256':field('questionnaire_sha256'),
            'expected_revision':int(field('expected_revision')),'selected_ids':selected}


def check_sources(root: Path):
    root=Path(root).resolve();pool=load(root);results=[]
    for pid,paper in pool['papers'].items():
        for sha,source in paper['sources'].items():
            path=Path(source['file']);path=path if path.is_absolute() else root/path
            results.append({'paper_id':pid,'source_sha256':sha,'exists':path.is_file(),
                            'matches':path.is_file() and file_digest(path)==sha})
    return {'revision':pool['revision'],'sources':results,'ok':all(x['matches'] for x in results)}


def search(root: Path,query: str,limit: int=10,uses_limit: int=3):
    """Find candidate meanings before assigning a new ID; matching never merges them."""
    require(query.strip(),'empty search query')
    require(type(limit) is int and 1 <= limit <= 100,'limit must be 1..100')
    require(type(uses_limit) is int and 0<=uses_limit<=100,'uses limit must be 0..100')
    pool=load(root);needle=unicodedata.normalize('NFKC',query).casefold();matches=[]
    for cid,c in pool['concepts'].items():
        uses=[(oid,o) for oid,o in pool['occurrences'].items() if o['concept_id']==cid
              and oid not in pool.get('use_corrections',{})]
        fields=[cid,c['label'],c['definition'],*c['aliases']]
        fields += [str(o.get(name,'')) for _,o in uses for name in ('usage','role','quote')]
        if not any(needle in unicodedata.normalize('NFKC',text).casefold() for text in fields):continue
        shown_uses=uses[-uses_limit:] if uses_limit else []
        matches.append({'concept_id':cid,'label':c['label'],'definition':c['definition'],
                        'aliases':c['aliases'],'content_sha256':c['content_sha256'],
                        'uses_total':len(uses),'uses_more_available':len(uses)>len(shown_uses),
                        'uses':[{'occurrence_id':oid,'paper_id':o['paper_id'],'page':o['page'],
                                 'role':o['role'],'usage':o['usage'],
                                 'in_pool':oid in pool['pool_members']} for oid,o in shown_uses]})
    return {'revision':pool['revision'],'query':query,'total_matches':len(matches),
            'shown':matches[:limit],'more_available':len(matches)>limit,
            'interpretation':'candidate meanings, not automatic merges or mastery claims'}


def show_use(root: Path,occurrence_id: str):
    pool=load(root);require(occurrence_id in pool['occurrences'],'occurrence missing')
    current_id,chain=_correction_chain(pool,occurrence_id)
    return {'revision':pool['revision'],'occurrence_id':occurrence_id,
            'occurrence':pool['occurrences'][occurrence_id],
            'learning':_state(pool,{'occurrence_ids':[occurrence_id]}),
            'correction_history':chain,'current_id':current_id,
            'current_occurrence':pool['occurrences'][current_id],
            'pool_introductions':pool['pool_members'].get(occurrence_id)}


def migrate_legacy(root: Path,legacy: dict,*,expected_revision: int,operation_id: str):
    """Import an explicitly supplied flat prototype, retaining unsupported claims as data."""
    def apply(pool):
        require(not pool['concepts'] and not pool['sessions'],'legacy import requires an empty destination')
        require(legacy.get('schema_version')==1 and isinstance(legacy.get('concepts'),list),
                'supported legacy input is the documented v1 flat prototype only')
        pool['legacy_import']={'original':deepcopy(legacy),'sha256':digest(legacy),
                               'imported_at':now(),'status_claims':'unverified; no mastery promotion'}
        for old in legacy['concepts']:
            cid=identifier(old['concept_id'])
            core={'id':cid,'label':old.get('label') or old.get('names',{}).get('zh') or cid,
                  'definition':old.get('definition') or '旧记录未给定义；需要来源研究',
                  'aliases':old.get('aliases',[]),'prerequisites':old.get('prerequisite_ids',[])}
            pool['concepts'][cid]={**core,'content_sha256':digest(core)}
        return {'imported':len(legacy['concepts']),'original_preserved':True,'mastery_inferred':False}
    return mutate(root,expected_revision=expected_revision,operation_id=operation_id,
                  action='migrate-v1',payload=legacy,operation=apply)
