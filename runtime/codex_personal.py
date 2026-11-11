"""Private source-bound personal context and explicit, minimal role views.

No model calls, automatic mastery, personality diagnosis or authenticated identity.
"""
from __future__ import annotations
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import uuid
from runtime.codex_personal_sources import extract, clean, representation_digest

SCHEMA = 1
KINDS = {'goal', 'preference', 'fact', 'claim', 'self_report', 'observation',
         'knowledge_evidence', 'resource', 'inference', 'unknown'}
ORIGINS = {'user_message', 'user_material', 'project_artifact', 'reference', 'simulation', 'learner_observation'}
AUDIENCES = {'self': {'self', 'scene_author', 'actor', 'public'},
             'scene_author': {'scene_author', 'actor', 'public'}, 'actor': {'actor', 'public'}, 'public': {'public'}}
KEY = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def text(value, name):
    need(isinstance(value, str) and value.strip(), name + ' must be nonempty text')
    return value


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _write(path, value):
    temp = path.with_name(path.name + '.new-' + uuid.uuid4().hex)
    with temp.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
    temp.replace(path)


def _seal(value):
    value = deepcopy(value); value.pop('integrity_sha256', None)
    value['integrity_sha256'] = digest(value)
    return value


def load(root):
    state = json.loads((Path(root) / 'profile.json').read_text(encoding='utf-8-sig'))
    need(state.get('schema_version') == SCHEMA, 'unsupported personal context schema')
    need(_seal(state)['integrity_sha256'] == state.get('integrity_sha256'), 'personal snapshot was changed outside a recorded operation')
    return state


def initialize(root, *, name='Personal Context', binding=None):
    root = Path(root).resolve(); need(not root.exists(), 'new personal context root must not exist')
    root.mkdir(parents=True)
    state = {'schema_version': SCHEMA, 'profile_id': uuid.uuid4().hex, 'name': name, 'revision': 0,
             'binding': binding or {}, 'sources': {}, 'source_heads': {}, 'entries': {}, 'history': [], 'receipts': {},
             'limits': 'Private selected material; source statements and operator classifications are not authenticated truth or learner mastery.'}
    _write(root / 'profile.json', _seal(state))
    return {'root': root.as_posix(), 'profile_id': state['profile_id'], 'revision': 0}


@contextmanager
def _lock(root):
    path = Path(root) / '.writer.lock'; token = uuid.uuid4().hex
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('writer lock exists; inspect the recorded process before recovery') from None
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump({'pid': os.getpid(), 'token': token}, f)
    try:
        yield
    finally:
        if path.exists() and json.loads(path.read_text())['token'] == token:
            path.unlink()


def _mutate(root, payload, revision, operation_id, change):
    root = Path(root); need(isinstance(operation_id, str) and KEY.fullmatch(operation_id), 'invalid operation id')
    request_hash = digest(payload)
    with _lock(root):
        state = load(root); old = state['receipts'].get(operation_id)
        if old:
            need(old['request_sha256'] == request_hash, 'operation id reused with different input')
            return {**old, 'retried': True}
        need(type(revision) is int and revision == state['revision'], 'revision conflict')
        result = change(state)
        state['revision'] += 1
        receipt = {'operation_id': operation_id, 'request_sha256': request_hash,
                   'revision': state['revision'], **result}
        state['receipts'][operation_id] = receipt
        _write(root / 'profile.json', _seal(state))
        return receipt


def _locator(root, path):
    root = Path(root).resolve(); path = Path(path).resolve()
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()


def _path(root, locator):
    p = Path(locator)
    return p if p.is_absolute() else Path(root) / p


def register_source(root, path, *, origin, selectors=None, pages=None, items=None,
                    lineage=None, make_current=False, expected_revision, operation_id):
    need(origin in ORIGINS, 'unknown source origin')
    need(lineage is None or (isinstance(lineage, str) and KEY.fullmatch(lineage)), 'invalid logical source lineage')
    indexed = extract(path, selectors=selectors, pages=pages, items=items)
    payload = {'locator': _locator(root, path), 'origin': origin, 'index': indexed,
               'lineage': lineage, 'make_current': bool(make_current)}
    def change(state):
        # Equal words can be a learner statement or an invented scene. Do not
        # merge these source identities merely because the bytes coincide.
        sid = 'src-' + digest({'sha256': indexed['sha256'], 'origin': origin,
                               'format': indexed['format'], 'lineage': lineage})[:24]
        previous = state['sources'].get(sid)
        if previous:
            need(previous['origin'] == origin and previous['sha256'] == indexed['sha256'], 'source origin/identity conflict')
            for uid, value in indexed['units'].items():
                need(uid not in previous['units'] or previous['units'][uid] == value, 'source unit changed')
                previous['units'][uid] = value
            previous['read_scopes'].append(indexed['read_scope'])
            previous['representations'].append({'sha256': indexed['representation_sha256'],
                                                'unit_ids': list(indexed['units']), 'scope': indexed['read_scope']})
            previous['representation_sha256'] = representation_digest(previous['units'])
            if payload['locator'] not in previous['locators']:
                previous['locators'].append(payload['locator'])
        else:
            state['sources'][sid] = {**deepcopy(indexed), 'id': sid, 'origin': origin,
                                      'lineage': lineage,
                                      'locators': [payload['locator']], 'read_scopes': [indexed['read_scope']],
                                      'representations': [{'sha256': indexed['representation_sha256'],
                                                           'unit_ids': list(indexed['units']), 'scope': indexed['read_scope']}]}
        heads = state.setdefault('source_heads', {})
        if lineage and (lineage not in heads or make_current):
            if lineage in heads and heads[lineage] != sid:
                state['history'].append({'source_head': lineage, 'previous': heads[lineage],
                                         'replacement': sid, 'at_revision': state['revision'] + 1})
            heads[lineage] = sid
        return {'source_id': sid, 'indexed_units': len(indexed['units']), 'origin': origin,
                'read_scope': indexed['read_scope'], 'learner_evidence_added': 0}
    return _mutate(root, payload, expected_revision, operation_id, change)


def source_status(root, source):
    if source.get('withdrawn'):
        return {'status': 'WITHDRAWN', 'reason': source['withdrawn']['reason'],
                'scope': 'Explicitly excluded from new use; historical records are retained.'}
    observations = []
    for number, locator in enumerate(source['locators']):
        p = _path(root, locator)
        if not p.is_file():
            observations.append({'locator': locator, 'primary': number == 0, 'status': 'MISSING'}); continue
        h = sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        observations.append({'locator': locator, 'primary': number == 0,
                             'status': 'CURRENT' if h.hexdigest() == source['sha256'] else 'CHANGED'})
    primary = observations[0]
    return {'status': primary['status'], 'locator': primary['locator'], 'sha256': source['sha256'],
            'locations': observations, 'historical_snapshot_available': any(x['status'] == 'CURRENT' for x in observations[1:]),
            'scope': 'Primary source bytes; historical copies do not establish present personal truth.'}


def relocate_source(root, source_id, path, *, expected_revision, operation_id):
    """Explicitly choose a new primary location for the same immutable version."""
    path = Path(path).resolve(strict=True)
    payload = {'source_id': source_id, 'locator': _locator(root, path)}
    def change(state):
        need(source_id in state['sources'], 'unknown source')
        s = state['sources'][source_id]
        probe = {**s, 'locators': [payload['locator']]}
        need(source_status(root, probe)['status'] == 'CURRENT', 'relocation needs identical source bytes')
        state['history'].append({'source_location': source_id, 'previous': s['locators'][0],
                                 'replacement': payload['locator'], 'at_revision': state['revision'] + 1})
        s['locators'] = [payload['locator']] + [x for x in s['locators'] if x != payload['locator']]
        return {'source_id': source_id, 'primary_locator': payload['locator']}
    return _mutate(root, payload, expected_revision, operation_id, change)


def withdraw_source(root, source_id, *, reason, expected_revision, operation_id):
    text(reason, 'withdrawal reason')
    def change(state):
        need(source_id in state['sources'], 'unknown source')
        state['sources'][source_id]['withdrawn'] = {'reason': reason, 'at_revision': state['revision'] + 1}
        state['history'].append({'withdrawn_source': source_id, 'reason': reason,
                                 'at_revision': state['revision'] + 1})
        return {'source_id': source_id, 'status': 'WITHDRAWN',
                'scope': 'New views exclude this source; already exported books are not remotely erased.'}
    return _mutate(root, {'source_id': source_id, 'reason': reason}, expected_revision, operation_id, change)


def _entry_source_status(root, state, entry):
    s = state['sources'][entry['source_id']]
    status = source_status(root, s)
    lineage = s.get('lineage')
    if lineage and state.get('source_heads', {}).get(lineage) != s['id']:
        return {'status': 'SUPERSEDED_SOURCE', 'source_bytes': status}
    return status


def admit(root, entry, *, expected_revision, operation_id):
    need(isinstance(entry, dict), 'entry must be an object')
    eid = entry.get('id'); need(isinstance(eid, str) and KEY.fullmatch(eid), 'invalid entry id')
    kind = entry.get('kind'); need(kind in KINDS, 'invalid entry kind')
    for key in ('statement', 'scope', 'as_of'):
        text(entry.get(key), key)
    sharing = entry.get('sharing', 'self'); need(sharing in AUDIENCES, 'invalid sharing scope')
    def change(state):
        value = deepcopy(entry); value['sharing'] = sharing
        sid = value.get('source_id')
        if kind != 'unknown' or sid:
            need(sid in state['sources'], 'entry source is missing')
            source = state['sources'][sid]
            need(source_status(root, source)['status'] == 'CURRENT', 'entry source is unavailable or changed')
            uid = value.get('unit_id'); need(uid in source['units'], 'entry source unit is missing')
            quote = clean(text(value.get('quote'), 'exact source quote'))
            need(quote in source['units'][uid]['text'], 'quote is absent from selected source unit')
            value['quote'] = quote
            value['source_sha256'] = source['sha256']
            value['unit_sha256'] = source['units'][uid]['text_sha256']
            if source['origin'] in {'reference', 'simulation'}:
                need(kind in {'resource', 'unknown'}, 'reference or simulation cannot become personal experience/knowledge evidence')
            if kind == 'knowledge_evidence':
                need(source['origin'] in {'learner_observation', 'user_message'}, 'knowledge evidence needs an actual learner observation or self-report source')
                text(value.get('evidence_scope'), 'observed evidence scope')
        else:
            text(value.get('reason'), 'reason for unknown')
        previous = state['entries'].get(eid)
        if previous:
            need(value.get('replaces_sha256') == previous['entry_sha256'], 'replacement requires the actual earlier entry hash')
            state['history'].append({'entry': previous, 'replaced_at_revision': state['revision'] + 1})
        value.pop('entry_sha256', None)
        value['entry_sha256'] = digest(value)
        state['entries'][eid] = value
        return {'entry_id': eid, 'kind': kind, 'entry_sha256': value['entry_sha256'],
                'learner_evidence_added': 1 if kind == 'knowledge_evidence' else 0,
                'semantic_certification': False}
    return _mutate(root, entry, expected_revision, operation_id, change)


def make_view(root, *, entry_ids, purpose, audience='scene_author', include_resources=False,
              book_id=None, role_id=None):
    text(purpose, 'view purpose'); need(audience in AUDIENCES, 'invalid view audience')
    need(isinstance(entry_ids, list) and bool(entry_ids) and len(entry_ids) == len(set(entry_ids)), 'select explicit unique entry ids')
    if audience == 'actor':
        need(isinstance(book_id, str) and KEY.fullmatch(book_id) and isinstance(role_id, str) and KEY.fullmatch(role_id),
             'actor view needs explicit book_id and role_id')
    state = load(root); selected = []; unavailable = []
    for eid in entry_ids:
        need(eid in state['entries'], 'unknown selected entry: ' + eid)
        entry = state['entries'][eid]
        need(entry['sharing'] in AUDIENCES[audience], 'entry is not shared with requested audience: ' + eid)
        need(include_resources or entry['kind'] != 'resource', 'resource is not actor knowledge; explicitly include reference material if needed')
        if entry.get('source_id'):
            status = _entry_source_status(root, state, entry)
            if status['status'] != 'CURRENT':
                unavailable.append({'entry_id': eid, 'source_status': status['status']}); continue
        item = deepcopy(entry)
        if entry.get('source_id'):
            s = state['sources'][entry['source_id']]
            item['source_binding'] = {'origin': s['origin'], 'format': s['format'], 'sha256': s['sha256'],
                                      'metadata': {k: s['metadata'][k] for k in ('title', 'creator') if k in s['metadata']},
                                      'location': s['units'][entry['unit_id']]['location'],
                                      'read_scopes': deepcopy(s['read_scopes']), 'lineage': s.get('lineage'),
                                      'currency': 'Explicit primary/logical-source selection; semantic relevance and present ability are not automatically checked.'}
        selected.append(item)
    view = {'schema_version': SCHEMA, 'profile_id': state['profile_id'], 'profile_revision': state['revision'],
            'purpose': purpose, 'audience': audience, 'book_id': book_id, 'role_id': role_id,
            'entries': selected, 'unavailable': unavailable,
            'requires_private_publication': any(e['sharing'] != 'public' for e in selected),
            'limits': 'Selected source-bound statements, not a complete person, predictive twin, role knowledge grant or learner mastery. No simulation write-back.'}
    return {'view': view, 'view_sha256': digest(view)}


def check_view(root, packet, *, book_id=None, role_id=None):
    view = packet['view']; need(digest(view) == packet.get('view_sha256'), 'view digest mismatch')
    state = load(root); need(view['profile_id'] == state['profile_id'], 'view belongs to another profile')
    need(book_id is None or view.get('book_id') == book_id, 'view belongs to another book')
    need(role_id is None or view.get('role_id') == role_id, 'view belongs to another role')
    issues = list(view.get('unavailable', []))
    for old in view['entries']:
        now = state['entries'].get(old['id'])
        if not now or now['entry_sha256'] != old['entry_sha256']:
            issues.append({'entry_id': old['id'], 'status': 'ENTRY_CHANGED'})
        elif now.get('source_id'):
            status = _entry_source_status(root, state, now)
            if status['status'] != 'CURRENT':
                issues.append({'entry_id': old['id'], 'status': status['status']})
    return {'status': 'CURRENT_SELECTED_ENTRIES' if not issues else 'STALE_OR_UNAVAILABLE',
            'issues': issues, 'scope': 'Selected entries and source bytes; not semantic truth or personal ability.'}


def validate_role_view(packet, *, book_id, role_id):
    """Check a frozen capsule without requiring a live profile to read a book."""
    view = packet.get('view')
    need(isinstance(view, dict) and digest(view) == packet.get('view_sha256'), 'role view digest mismatch')
    need(view.get('audience') == 'actor' and view.get('book_id') == book_id and view.get('role_id') == role_id,
         'role view belongs to another book, role or audience')
    need(not view.get('unavailable'), 'resolve unavailable personal sources before using this role view')
    need(isinstance(view.get('entries'), list), 'role view entries missing')
    return deepcopy(view)


def inspect(root):
    state = load(root)
    return {'profile_id': state['profile_id'], 'revision': state['revision'], 'sources': len(state['sources']),
            'entries_by_kind': {kind: sum(e['kind'] == kind for e in state['entries'].values()) for kind in sorted(KINDS)},
            'source_status': {sid: source_status(root, s) for sid, s in state['sources'].items()},
            'history_count': len(state['history']), 'scope': 'Private source and entry summary; no automatic mastery.'}
