"""DIGRP paper work packages and independent, evidence-bound mail returns.

The native host reads, teaches, reviews and sends mail. These standard-library
operations preserve its source/mapping/artifact/receipt facts, not their truth.
Each paper has its own revision. Returning it never closes the parent DIGR run.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import time
from typing import Any

VERSION = '0.1.0'
PARTS = ('m1', 'm4', 'm2', 'm3', 'm5')
DISPOSITIONS = {'explained', 'context', 'non_content', 'unavailable'}


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + ' must be nonempty text')
    return value


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _read(path):
    value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('expected a JSON object: ' + str(path))
    return value


def _write(path, value):
    path = Path(path)
    temp = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    try:
        with temp.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


@contextmanager
def _lock(root):
    lock = Path(root) / '.paper-write.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError('paper writer is busy; inspect a stale lock before recovery') from error
    try:
        os.write(fd, json.dumps({'pid': os.getpid(), 'at_ns': time.time_ns()}).encode())
        os.close(fd); fd = None
        yield
    finally:
        if fd is not None:
            os.close(fd)
        lock.unlink()


def _file(root, value, kind='evidence'):
    path = Path(value)
    path = (Path(root) / path).resolve() if not path.is_absolute() else path.resolve()
    raw = path.read_bytes()
    if kind == 'pdf' and not raw.startswith(b'%PDF-'):
        raise ValueError('not a PDF: ' + str(path))
    return {'path': os.path.relpath(path, Path(root).resolve()).replace('\\', '/'),
            'filename': path.name, 'bytes': len(raw), 'sha256': sha256(raw).hexdigest(), 'kind': kind}


def _file_issues(root, item):
    try:
        now = _file(root, item['path'], item.get('kind', 'evidence'))
        return [] if (now['sha256'], now['bytes']) == (item['sha256'], item['bytes']) else [item['path'] + ': changed']
    except (OSError, ValueError):
        return [item['path'] + ': unavailable']


def _load(root):
    value = _read(Path(root) / 'paper.json')
    if value.get('format') != 'digrp-paper-1':
        raise ValueError('unsupported paper format')
    return value


def initialize(root, *, p_run, authorization, source_ref, recipient):
    root = Path(root).resolve(); root.mkdir(parents=True, exist_ok=True)
    if not re.fullmatch(r'[^@\s]+@[0-9a-f]{40}', p_run):
        raise ValueError('p_run needs a version and full immutable SHA')
    with _lock(root):
        if (root / 'batch.json').exists():
            raise ValueError('batch already exists')
        value = {'format': 'digrp-batch-1', 'addon_version': VERSION, 'P_run': p_run,
                 'authorization': _file(root, authorization),
                 'authorization_source_ref': _text(source_ref, 'actual user source_ref'),
                 'recipient': _text(recipient, 'authorized resolved recipient'),
                 'papers': {}, 'parent_lifecycle_unchanged': True}
        _write(root / 'batch.json', value)
    return value


def add_paper(batch, *, paper_id, title, line, owner, parameters):
    batch = Path(batch).resolve()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', paper_id):
        raise ValueError('paper_id must be lowercase letters, numbers and hyphens')
    if not re.fullmatch(r'M[0-9]{2,}', line):
        raise ValueError('line must identify a complete M mainline')
    for key in ('N', 'R', 'D', 'V'):
        if type(parameters.get(key)) is not int or parameters[key] < 0:
            raise ValueError('complete mainline parameters required: ' + key)
    if parameters.get('L') != 3 or any(key not in parameters for key in ('T', 'B', 'S')):
        raise ValueError('each paper needs its own complete DIGR configuration, L3')
    if not isinstance(parameters['S'], dict) or set(parameters['S']) != {'n', 't', 'r', 'b'}:
        raise ValueError('complete S configuration required per paper')
    for key in ('n', 'r'):
        if type(parameters['S'][key]) is not int or parameters['S'][key] < 0:
            raise ValueError('source counts must be nonnegative integers')
    if parameters['B'] not in (0, 1) or parameters['S']['b'] not in (0, 1):
        raise ValueError('B/b must preserve the actual binary time policy')
    with _lock(batch):
        index = _read(batch / 'batch.json')
        if paper_id in index['papers'] or any(p['line'] == line for p in index['papers'].values()):
            raise ValueError('paper ID and M line must be unique within the batch')
        root = batch / 'papers' / paper_id
        root.mkdir(parents=True, exist_ok=False)
        value = {'format': 'digrp-paper-1', 'addon_version': VERSION, 'revision': 0,
                 'paper_id': paper_id, 'title': _text(title, 'title'), 'line': line,
                 'owner': _text(owner, 'actual owner'), 'parameters': deepcopy(parameters),
                 'P_run': index['P_run'], 'recipient': index['recipient'],
                 'authorization_source_ref': index['authorization_source_ref'],
                 'sources': {}, 'mapping': None,
                 'candidate': None, 'deliveries': [], 'returns': [], 'cursor': None, 'operations': {}}
        _write(root / 'paper.json', value)
        index['papers'][paper_id] = {'path': 'papers/' + paper_id, 'line': line}
        _write(batch / 'batch.json', index)
    return {'paper_root': root.as_posix(), 'revision': 0, 'line': line}


def _mutate(root, expected_revision, operation_id, action, payload, update):
    root = Path(root).resolve(); _text(operation_id, 'operation_id')
    fingerprint = _digest({'action': action, 'payload': payload})
    with _lock(root):
        value = _load(root)
        previous = value['operations'].get(operation_id)
        if previous:
            if previous['fingerprint'] != fingerprint:
                raise ValueError('operation ID reused for different content')
            return {**previous['result'], 'idempotent_replay': True}
        if type(expected_revision) is not int or value['revision'] != expected_revision:
            raise ValueError('paper revision conflict; reread this paper before reconciling')
        update(value)
        value['revision'] += 1
        result = {'paper_id': value['paper_id'], 'revision': value['revision'], 'action': action}
        value['operations'][operation_id] = {'fingerprint': fingerprint, 'result': result}
        _write(root / 'paper.json', value)
    return result


def register_source(root, payload, **revision):
    source_id = _text(payload.get('id'), 'source id')
    observed = _file(root, payload['path'], 'source')
    pages = payload.get('pages')
    if type(pages) is not int or pages < 1:
        raise ValueError('physical page count must be a positive integer')
    path = (Path(root) / observed['path']).resolve()
    if path.suffix.lower() == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError as error:
            raise ValueError('PDF page verification needs the configured Python with pypdf') from error
        if len(PdfReader(path).pages) != pages:
            raise ValueError('physical page count does not match PDF')
    def update(value):
        if source_id in value['sources']:
            raise ValueError('source ID is immutable; add a new version ID instead')
        value['sources'][source_id] = {**observed, 'pages': pages,
            'identity': _text(payload.get('identity'), 'source/version identity')}
    return _mutate(root, action='source', payload={**payload, 'observed': observed}, update=update, **revision)


def _anchor(value, anchor):
    if not isinstance(anchor, dict) or anchor.get('source') not in value['sources']:
        raise ValueError('anchor needs a registered source')
    if type(anchor.get('page')) is not int or not 1 <= anchor['page'] <= value['sources'][anchor['source']]['pages']:
        raise ValueError('anchor physical page outside its own source version')
    _text(anchor.get('label'), 'anchor label')


def map_paper(root, payload, **revision):
    def update(value):
        if set(payload.get('parts', {})) != set(PARTS):
            raise ValueError('reader order must be m1, m4, m2, m3, m5')
        for heading in payload['parts'].values():
            _text(heading, 'reader part heading')
        ids = {}
        for group in ('assumptions', 'claims', 'chains', 'experiments', 'coverage'):
            rows = payload.get(group)
            if not isinstance(rows, list):
                raise ValueError('mapping needs ' + group)
            ids[group] = set()
            for row in rows:
                item_id = _text(row.get('id'), group + ' id')
                if item_id in ids[group]:
                    raise ValueError('duplicate ' + group + ' id')
                ids[group].add(item_id)
                _anchor(value, row.get('anchor'))
                _text(row.get('location'), 'actual guide location')
                if group == 'coverage' and row.get('disposition') not in DISPOSITIONS:
                    raise ValueError('coverage needs an explicit disposition')
        for row in payload['claims']:
            _text(row.get('basis'), 'claim evidence nature')
            for group in ('assumptions', 'chains', 'experiments'):
                if not set(row.get(group, [])).issubset(ids[group]):
                    raise ValueError('claim points at an unknown ' + group)
        for chain in payload['chains']:
            for field in ('purpose', 'prerequisites', 'source_vs_supplement', 'result', 'unresolved'):
                if field not in chain:
                    raise ValueError('chain must preserve ' + field)
        value['mapping'] = deepcopy(payload)
    return _mutate(root, action='map', payload=payload, update=update, **revision)


def _candidate_issues(root, value):
    issues = []
    for source in value['sources'].values():
        issues.extend(_file_issues(root, source))
    candidate = value['candidate']
    if candidate:
        if candidate['mapping_digest'] != _digest(value['mapping']):
            issues.append('mapping changed after candidate review')
        for file in candidate['files']:
            issues.extend(_file_issues(root, file))
        for delivery in value['deliveries']:
            if delivery['candidate_id'] == candidate['id']:
                for evidence in delivery['evidence']:
                    issues.extend(_file_issues(root, evidence))
        for returned in value['returns']:
            if returned['candidate_id'] == candidate['id']:
                issues.extend(_file_issues(root, returned['body']))
    return issues


def prepare_candidate(root, payload, **revision):
    def update(value):
        if not value['mapping'] or not value['mapping']['coverage']:
            raise ValueError('source-to-guide mapping with original coverage required')
        issues = _candidate_issues(root, {**value, 'candidate': None})
        if issues:
            raise ValueError('source changed/unavailable: ' + '; '.join(issues))
        markdown = _file(root, payload['markdown'], 'markdown')
        text = (Path(root) / markdown['path']).read_text(encoding='utf-8-sig')
        heading_order = {}
        for position, line in enumerate(text.splitlines()):
            if line.startswith('#'):
                heading_order.setdefault(re.sub(r'^#+\s*', '', line).strip(), position)
        headings = set(heading_order)
        locations = list(value['mapping']['parts'].values())
        for group in ('assumptions', 'claims', 'chains', 'experiments', 'coverage'):
            locations.extend(row['location'] for row in value['mapping'][group])
        if any(location not in headings for location in locations):
            raise ValueError('mapping location is absent from Markdown headings')
        positions = [heading_order[value['mapping']['parts'][part]] for part in PARTS]
        if positions != sorted(positions) or len(set(positions)) != len(PARTS):
            raise ValueError('guide parts must actually appear in reader order m1, m4, m2, m3, m5')
        pdfs = [_file(root, name, 'pdf') for name in payload['pdfs']]
        if not pdfs or len({p['filename'] for p in pdfs}) != len(pdfs):
            raise ValueError('one or more uniquely named PDF volumes required')
        files = [markdown, *pdfs, _file(root, payload['qa'], 'qa'), _file(root, payload['review'], 'review')]
        for match in re.finditer(r'!\[[^\]]*\]\(([^)]+)\)', text):
            target = match.group(1).strip().strip('<>')
            if re.match(r'https?://', target):
                raise ValueError('delivery images must be local, actually embedded assets')
            asset = (Path(root) / markdown['path']).parent / target
            files.append(_file(root, asset, 'image'))
        qa = _read(Path(root) / payload['qa'])
        if (qa.get('pages', 0) < 1 or qa.get('rendered_pages') != qa.get('pages') or
                any(qa.get(k) != [] for k in ('formula_errors', 'overflow', 'missing_images'))):
            raise ValueError('actual rendered PDF QA must include page coverage and resolved layout/image errors')
        review = (Path(root) / payload['review']).read_text(encoding='utf-8-sig')
        _text(review, 'native content and final-page review')
        candidate = {'mapping_digest': _digest(value['mapping']), 'files': files,
                     'responsibility_report': deepcopy(payload.get('responsibility_report', {}))}
        for key in ('N', 'R', 'D', 'V'):
            actual = candidate['responsibility_report'].get(key)
            if type(actual) is not int or actual < value['parameters'][key]:
                raise ValueError('native responsibility report incomplete for this paper: ' + key)
        candidate['id'] = _digest(candidate)
        value['candidate'] = candidate
    return _mutate(root, action='candidate', payload=payload, update=update, **revision)


def record_delivery(root, payload, **revision):
    def update(value):
        candidate = value['candidate']
        if not candidate or _candidate_issues(root, value):
            raise ValueError('mail receipt cannot refer to a missing or stale candidate')
        if payload.get('candidate_id') != candidate['id']:
            raise ValueError('receipt must identify the exact reviewed candidate')
        message_id = _text(payload.get('message_id'), 'actual Gmail message_id')
        if 'SENT' not in payload.get('label_ids', []):
            raise ValueError('read-back SENT label required')
        recipient = _text(payload.get('recipient'), 'observed recipient')
        if recipient.casefold() != value['recipient'].casefold():
            raise ValueError('read-back recipient differs from the authorized destination')
        if payload.get('authorization_source_ref') != value['authorization_source_ref']:
            raise ValueError('mail authorization reference differs from the actual batch decision')
        pdfs = {file['filename']: file for file in candidate['files'] if file['kind'] == 'pdf'}
        attachments = payload.get('attachments')
        if not isinstance(attachments, list) or not attachments:
            raise ValueError('read-back attachment facts required')
        for attachment in attachments:
            expected = pdfs.get(attachment.get('filename'))
            if not expected or attachment.get('bytes') != expected['bytes']:
                raise ValueError('read-back attachment name/size differs from final PDF')
        evidence = [_file(root, payload[key], key) for key in ('send_evidence', 'readback_evidence')]
        value['deliveries'].append({'candidate_id': candidate['id'], 'message_id': message_id,
            'recipient': recipient, 'attachments': deepcopy(attachments), 'evidence': evidence,
            'authorization_source_ref': payload['authorization_source_ref'],
            'observation_scope': 'operator-selected Gmail send/readback facts; no open/read or learning claim'})
    return _mutate(root, action='delivery', payload=payload, update=update, **revision)


def _unresolved_delivery(value):
    cursor = value.get('cursor') or {}
    pending = cursor.get('pending_delivery')
    if not isinstance(pending, dict) or pending.get('outcome') != 'uncertain':
        return None
    candidate_id = pending.get('candidate_id')
    volumes = pending.get('volumes', [])
    receipts = [r for r in value['deliveries'] if r['candidate_id'] == candidate_id]
    observed = {(a['filename'], a['bytes']) for r in receipts for a in r['attachments']}
    remaining = [v['filename'] for v in volumes if (v['filename'], v['bytes']) not in observed]
    # Legacy unbound intent cannot be silently resolved against another edition.
    if candidate_id and volumes and not remaining:
        return None
    return {**pending, 'remaining': remaining or pending.get('pdf_names', []),
            'basis': cursor.get('basis')}



def inspect(root):
    root = Path(root).resolve(); value = _load(root)
    issues = _candidate_issues(root, value)
    candidate = value['candidate']; status = 'DRAFT'
    receipts = [r for r in value['deliveries']
                if candidate and r['candidate_id'] == candidate['id']]
    volumes = []
    if candidate:
        for file in candidate['files']:
            if file['kind'] != 'pdf':
                continue
            messages = [r['message_id'] for r in receipts
                        if any(a['filename'] == file['filename'] and
                               a['bytes'] == file['bytes'] for a in r['attachments'])]
            volumes.append({**file, 'message_ids': messages,
                            'sent_verified': bool(messages) and not issues})
    remaining = [v['filename'] for v in volumes if not v['sent_verified']]
    if issues:
        status = 'STALE_OR_UNAVAILABLE'
    elif candidate:
        status = 'READY'
        if volumes and not remaining:
            status = 'SENT_VERIFIED'
            if any(r['candidate_id'] == candidate['id'] for r in value['returns']):
                status = 'RETURNED'

    # A checkpoint is an explicit saved next step. Later mutations preserve
    # its reading context but supersede its action, so an old cursor cannot
    # re-send an already verified volume or undo a completed paper return.
    checkpoint_revision = max((o['result']['revision']
        for o in value['operations'].values()
        if o['result']['action'] == 'checkpoint'), default=-1)
    cursor_current = bool(value['cursor']) and checkpoint_revision == value['revision']
    unresolved_delivery = _unresolved_delivery(value)
    pending_saved_step = (cursor_current or bool(unresolved_delivery)) and not issues
    next_action = {
        'DRAFT': 'complete source-bound guide and native review',
        'READY': 'send only remaining PDF volumes through authorized Gmail, then read back: ' + ', '.join(remaining),
        'SENT_VERIFIED': 'record this paper return; parent DIGR task stays open',
        'RETURNED': 'this paper returned; continue other papers/common work',
        'STALE_OR_UNAVAILABLE': 'inspect changed source/artifact; do not reuse an old mail receipt'
    }[status]
    if unresolved_delivery and not issues:
        next_action = ('reconcile uncertain Gmail send ' + unresolved_delivery['attempt_id'] +
            ' for ' + ', '.join(unresolved_delivery['remaining']) +
            '; do not resend before checking SENT')
    elif cursor_current and not issues:
        next_action = value['cursor']['next_action']
    return {'paper_id': value['paper_id'], 'line': value['line'], 'revision': value['revision'],
        'status': status, 'issues': issues, 'candidate_id': candidate['id'] if candidate else None,
        'cursor': value['cursor'], 'cursor_current': cursor_current,
        'pending_saved_step': pending_saved_step, 'mapping': value['mapping'],
        'unresolved_delivery_attempt': unresolved_delivery,
        'delivery_progress': {'volumes': volumes, 'verified_count': len(volumes) - len(remaining),
                              'volume_count': len(volumes), 'remaining': remaining},
        'next_action': next_action,
        'fact_scope': 'file and operator records; not proof correctness, authenticated consent or learning'}


def return_paper(root, payload, **revision):
    body = _file(root, payload['body'], 'paper_return')
    def update(value):
        status = inspect(root)
        if status['status'] != 'SENT_VERIFIED' or status.get('unresolved_delivery_attempt'):
            raise ValueError('paper return requires complete current Gmail attachment verification')
        value['returns'].append({'candidate_id': value['candidate']['id'], 'body': body,
                                'parent_lifecycle_unchanged': True, 'at_ns': time.time_ns()})
    return _mutate(root, action='paper_return', payload={**payload, 'body_file': body}, update=update, **revision)


def checkpoint(root, payload, **revision):
    def update(value):
        if payload.get('anchor'):
            _anchor(value, payload['anchor'])
        for field in ('position', 'next_action', 'basis'):
            _text(payload.get(field), field)
        saved = deepcopy(payload)
        prior = (value.get('cursor') or {}).get('pending_delivery')
        if 'pending_delivery' not in saved and isinstance(prior, dict) and prior.get('outcome') == 'uncertain':
            saved['pending_delivery'] = deepcopy(prior)
        pending = saved.get('pending_delivery')
        if pending is not None:
            if not isinstance(pending, dict) or pending.get('outcome') not in ('uncertain', 'resolved'):
                raise ValueError('pending delivery needs uncertain/resolved outcome')
            _text(pending.get('attempt_id'), 'stable Gmail send attempt ID')
            if pending['outcome'] == 'uncertain':
                candidate = value['candidate']
                candidate_id = pending.get('candidate_id') or (candidate or {}).get('id')
                if candidate and candidate_id == candidate['id']:
                    files = [f for f in candidate['files'] if f['kind'] == 'pdf']
                elif isinstance(prior, dict) and candidate_id == prior.get('candidate_id'):
                    files = prior.get('volumes', [])
                else:
                    raise ValueError('uncertain send must bind a current or retained candidate')
                names = pending.get('pdf_names')
                if not isinstance(names, list) or not names or not set(names).issubset({f['filename'] for f in files}):
                    raise ValueError('uncertain send must identify its selected PDF volumes')
                pending['candidate_id'] = candidate_id
                pending['volumes'] = [deepcopy(f) for f in files if f['filename'] in names]
        value['cursor'] = saved
    return _mutate(root, action='checkpoint', payload=payload, update=update, **revision)


def summarize(batch):
    batch = Path(batch).resolve(); index = _read(batch / 'batch.json')
    papers = [inspect(batch / paper['path']) for paper in index['papers'].values()]
    complete = bool(papers) and all(paper['status'] == 'RETURNED' and
        not paper['pending_saved_step'] for paper in papers)
    return {'P_run': index['P_run'], 'papers': papers, 'all_papers_returned': complete,
            'pending_saved_steps': [p['paper_id'] for p in papers if p['pending_saved_step']],
            'next_action': 'complete common work and use the parent DIGR RETURN' if complete else 'continue pending saved steps and unfinished papers',
            'parent_lifecycle_unchanged': True}


def acquire_addon(base, *, fetch=None, output=None):
    """Continue a genuinely acquired execution pin; never resolve a new HEAD.

    Like the core continuation helper, saved bytes alone do not satisfy the
    next raw user invocation's live acquisition obligation.
    """
    from .codex_transport import CodexRepositoryTransport, REPOSITORY
    from .protocol_pin import raw_file_url, validate_repo_path
    from .repository_transport import normalize_pinned_file_bytes
    if base.stage != 'execution':
        raise ValueError('read the complete pinned core execution protocol before DIGRP')
    declaration = base.manifest.get('paper_addon')
    if not isinstance(declaration, dict):
        raise ValueError('this immutable core pin does not declare DIGRP')
    transport = CodexRepositoryTransport(fetch)
    files = {}
    def get(path, digest):
        path = validate_repo_path(path)
        if not path.startswith(('paper/', '.agents/skills/digr-paper/')):
            raise ValueError('unexpected DIGRP protocol member path')
        raw = transport._get(raw_file_url(*REPOSITORY.split('/'), base.sha, path), 'DIGRP ' + path)
        data = normalize_pinned_file_bytes(raw, path); data.decode('utf-8')
        if sha256(data).hexdigest() != digest:
            raise ValueError('DIGRP pinned member hash mismatch: ' + path)
        files[path] = data
        return data
    manifest_raw = get(declaration['manifest'], declaration['sha256'])
    manifest = json.loads(manifest_raw)
    if manifest.get('version') != declaration.get('version'):
        raise ValueError('DIGRP declaration/manifest version mismatch')
    members = manifest.get('file_sha256')
    if not isinstance(members, dict) or manifest.get('protocol') != 'digrp-codex-1':
        raise ValueError('unsupported DIGRP protocol manifest')
    required = {manifest.get('version_path'), manifest.get('entrypoint'), manifest.get('skill')}
    if not required.issubset(members) or None in required:
        raise ValueError('DIGRP manifest misses its version, entrypoint or skill')
    for path, digest in members.items():
        get(path, digest)
    if files[manifest['version_path']].decode('utf-8').strip() != manifest['version']:
        raise ValueError('DIGRP manifest/VERSION mismatch')
    record = {'format': 'digrp-acquisition-1', 'version': manifest['version'],
        'P_run': base.version + '@' + base.sha, 'sha': base.sha,
        'files': {path: sha256(raw).hexdigest() for path, raw in files.items()},
        'observations': transport.observations, 'new_live_ref_resolution': False,
        'continuation_of_core_pin': True, 'run_started': False}
    if output is not None:
        output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=False)
        for path, raw in files.items():
            target = output / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        _write(output / 'acquisition.json', record)
    return record


def refresh_addon(root):
    """Explicit source-maintenance action; not live acquisition or installation."""
    root = Path(root).resolve()
    version = (root / 'paper/VERSION').read_text(encoding='utf-8').strip()
    if version != VERSION:
        raise ValueError('paper source/tool version mismatch')
    paths = ('paper/VERSION', 'paper/PROTOCOL.md', 'paper/DATA.md',
             '.agents/skills/digr-paper/SKILL.md', '.agents/skills/digr-paper/agents/openai.yaml')
    manifest = {'name': 'DIGRP Paper Reading', 'version': version, 'protocol': 'digrp-codex-1',
        'version_path': 'paper/VERSION', 'entrypoint': 'paper/PROTOCOL.md',
        'skill': '.agents/skills/digr-paper/SKILL.md', 'reader_order': list(PARTS),
        'file_sha256': {path: sha256((root / path).read_bytes()).hexdigest() for path in paths}}
    _write(root / 'paper/manifest.json', manifest)
    core = _read(root / 'codex/manifest.json')
    core['paper_addon'] = {'manifest': 'paper/manifest.json', 'version': version,
                         'sha256': sha256((root / 'paper/manifest.json').read_bytes()).hexdigest()}
    _write(root / 'codex/manifest.json', core)
    return {'version': version, 'members': len(paths), 'live_acquisition_performed': False,
            'core_hash_refresh_required': True}
