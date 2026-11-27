"""DIGRP paper work packages and independent, evidence-bound mail returns.

The native host reads, teaches, reviews and sends mail. These file operations
preserve its source/mapping/artifact/receipt facts, not their truth.
Each paper has its own revision. Returning it never closes the parent DIGR run.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
import math
import os
from pathlib import Path
import re
import time
from typing import Any

VERSION = '0.6.3'
CORE_MINIMUMS = {
    '0.3.0': (0, 9, 0), '0.4.0': (0, 10, 0), '0.5.0': (0, 11, 0),
    '0.5.1': (0, 11, 1), '0.5.2': (0, 12, 0), '0.5.3': (0, 12, 1),
    '0.5.4': (0, 13, 0), '0.6.0': (0, 14, 0), '0.6.1': (1, 0, 0),
    '0.6.2': (1, 1, 0), VERSION: (1, 9, 0),
}
SINGLE_PDF_CONTRACT = 'single-pdf-one-message'
X_PDF_CONTRACT = 'single-pdf-x-files'
LEGACY_CONTRACT = 'legacy-multiple-volumes'
# Named physical sheets, measured after /UserUnit and /Rotate. The tolerance
# only accommodates rounding of PDF point values, not arbitrary page shapes.
PAGE_PROFILES = {'A4': (210 * 72 / 25.4, 297 * 72 / 25.4),
                 'A5': (148 * 72 / 25.4, 210 * 72 / 25.4),
                 'Letter': (612.0, 792.0)}
PAGE_TOLERANCE_PT = 1.0
PARTS = ('m1', 'm4', 'm2', 'm3', 'm5')
DISPOSITIONS = {'explained', 'context', 'non_content', 'unavailable'}
NATIVE_MAPPING_CONTRACT = 'source-bound-native-v1'
NATIVE_AUTHORING_CONTRACT = 'sonnet-native-v1'


def addon_version_for(core_version: tuple[int, ...]) -> str:
    return next((addon for addon, minimum in reversed(CORE_MINIMUMS.items())
                 if core_version >= minimum), '0.2.0')


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


def initialize(root, *, p_run, authorization, source_ref, recipient=None, task_root=None):
    root = Path(root).resolve(); root.mkdir(parents=True, exist_ok=True)
    if not re.fullmatch(r'[^@\s]+@[0-9a-f]{40}', p_run):
        raise ValueError('p_run needs a version and full immutable SHA')
    version = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)@.+', p_run)
    core_version = tuple(map(int, version.groups())) if version else ()
    uses_x = core_version >= CORE_MINIMUMS['0.3.0']
    uses_consult = core_version >= CORE_MINIMUMS['0.4.0']
    uses_native = core_version >= CORE_MINIMUMS['0.5.0']
    addon_version = addon_version_for(core_version)
    policy = None
    if uses_x:
        from .codex_session import _session, task_delivery_policy
        if task_root is None or recipient is not None:
            raise ValueError('new DIGRP uses --task-root X policy, not the legacy --recipient option')
        task_root, parent = _session(Path(task_root))
        if parent['P_run'] != p_run:
            raise ValueError('paper batch and parent task must use the same immutable P_run')
        policy = task_delivery_policy(task_root)
        if policy is None:
            raise ValueError('parent task has no X file-delivery contract')
        recipient = policy.get('recipient')
    elif task_root is not None:
        raise ValueError('legacy paper batches keep their original delivery semantics')
    else:
        recipient = _text(recipient, 'authorized resolved recipient')
    with _lock(root):
        if (root / 'batch.json').exists():
            raise ValueError('batch already exists')
        value = {'format': 'digrp-batch-1',
                 'addon_version': addon_version, 'P_run': p_run,
                 'authorization': _file(root, authorization),
                 'authorization_source_ref': _text(source_ref, 'actual user source_ref'),
                 'recipient': recipient,
                 'papers': {}, 'parent_lifecycle_unchanged': True}
        if uses_x:
            value.update(task_root=task_root.as_posix(), delivery_policy=policy)
        if uses_consult:
            value.update(consult_enabled=True, mapping_contract='integrated-functions-v1')
        if uses_native:
            value.update(authoring_contract=NATIVE_AUTHORING_CONTRACT,
                         mapping_contract=NATIVE_MAPPING_CONTRACT)
        _write(root / 'batch.json', value)
    if uses_consult:
        # A user-selected paper addon can be entered inside a native DIGR task.
        # Preserve its initial mode and record the actual addon scope instead
        # of pretending the task originally used the DIGRP prefix.
        from .codex_session import _write_json
        task_root, parent = _session(task_root)
        scopes = list(parent.get('consult_addons', []))
        scope = {'addon': 'paper', 'version': addon_version, 'batch': root.as_posix(),
                 'authorization_source_ref': source_ref}
        if uses_native:
            scope['authoring_contract'] = NATIVE_AUTHORING_CONTRACT
        scopes.append(scope)
        parent['consult_addons'] = scopes
        _write_json(task_root / 'session.json', parent)
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
        value = {'format': 'digrp-paper-1', 'addon_version': index['addon_version'], 'revision': 0,
                 'paper_id': paper_id, 'title': _text(title, 'title'), 'line': line,
                 'owner': _text(owner, 'actual owner'), 'parameters': deepcopy(parameters),
                 'P_run': index['P_run'], 'recipient': index['recipient'],
                 'authorization_source_ref': index['authorization_source_ref'],
                 'sources': {}, 'mapping': None,
                 'candidate': None, 'deliveries': [], 'returns': [], 'cursor': None, 'operations': {}}
        if 'delivery_policy' in index:
            from .codex_session import task_delivery_policy
            value.update(task_root=index['task_root'],
                         delivery_policy=task_delivery_policy(Path(index['task_root'])))
        if index.get('consult_enabled'):
            value.update(consult_enabled=True,
                         mapping_contract=index.get('mapping_contract', 'integrated-functions-v1'))
        if index.get('authoring_contract') == NATIVE_AUTHORING_CONTRACT:
            value.update(authoring_contract=NATIVE_AUTHORING_CONTRACT, batch_root=batch.as_posix())
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


def _part_locations(mapping, integrated=False):
    locations = []
    for part in PARTS:
        supplied = mapping['parts'][part]
        if isinstance(supplied, str):
            supplied = [supplied]
        elif not integrated or not isinstance(supplied, list) or not supplied:
            raise ValueError('each function needs an actual nonempty manuscript location')
        locations.extend(_text(location, 'reader part heading') for location in supplied)
    return locations


def map_paper(root, payload, **revision):
    def update(value):
        if value.get('mapping_contract') == NATIVE_MAPPING_CONTRACT:
            if payload.get('mapping_contract') != NATIVE_MAPPING_CONTRACT:
                raise ValueError('new paper mapping needs its source-bound-native-v1 contract')
            if 'parts' in payload:
                raise ValueError('source-bound native papers do not use the legacy parts framework')
            rows = payload.get('coverage')
            if not isinstance(rows, list) or not rows:
                raise ValueError('native mapping needs actual original-source coverage')
            ids = set()
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError('each coverage row must be an original-source object')
                item_id = _text(row.get('id'), 'coverage id')
                if item_id in ids:
                    raise ValueError('duplicate coverage id')
                ids.add(item_id)
                _anchor(value, row.get('anchor'))
                _text(row.get('location'), 'actual guide location')
                if row.get('disposition') not in DISPOSITIONS:
                    raise ValueError('coverage needs an explicit disposition')
            value['mapping'] = deepcopy(payload)
            return
        if set(payload.get('parts', {})) != set(PARTS):
            raise ValueError('reader order must be m1, m4, m2, m3, m5')
        integrated = bool(value.get('consult_enabled'))
        declared = payload.get('mapping_contract')
        if declared is not None and (not integrated or declared != 'integrated-functions-v1'):
            raise ValueError('integrated function locations require the new paper 0.4 contract')
        _part_locations(payload, integrated)
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


def _authoring_scope(root, value):
    return {'paper_root': Path(root).resolve().as_posix(),
            'batch_root': Path(value['batch_root']).resolve().as_posix(),
            'paper_id': value['paper_id'], 'line': value['line'],
            'addon_version': value['addon_version'],
            'authoring_contract': value['authoring_contract'], 'P_run': value['P_run'],
            'authorization_source_ref': value['authorization_source_ref']}


def _native_consultation(root, value, supplied):
    """Bind this paper's observed public authoring, independent of billing updates."""
    if not isinstance(supplied, dict):
        raise ValueError('native paper candidate needs an actual scoped paper collaborator exchange')
    exchange_id = _text(supplied.get('exchange_id'), 'actual Sonnet exchange_id')
    from .codex_consult import inspect_exchange
    observed = inspect_exchange(Path(value['task_root']), exchange_id)
    attempt = observed['exchange']
    if attempt.get('public_status') != 'COMPLETE' or observed.get('public_integrity') != 'MATCH':
        raise ValueError('paper authoring needs the actual COMPLETE, unchanged public output')
    model_identity = observed.get('paper_model_identity')
    if not isinstance(model_identity, dict) or model_identity.get('status') != 'CONFIRMED':
        raise ValueError('paper authoring model identity is unconfirmed; actual request and response needed')
    expected = _authoring_scope(root, value)
    scope = attempt.get('authoring_scope')
    if not isinstance(scope, dict) or any(scope.get(key) != item for key, item in expected.items()):
        raise ValueError('Sonnet exchange authoring scope differs from this paper')
    from . import codex_collaboration, codex_production
    production = attempt.get('production')
    comparison = codex_collaboration.peer_collaboration(value['P_run'])
    stages = {'candidate', 'arbitration'} if comparison else {'arbitration'}
    if codex_production.enabled(value['P_run']) and (not production or production['stage'] not in stages):
        raise ValueError('A Stable paper candidate needs its actual scoped production exchange')
    guidance = _file(root, observed['public_path'], 'consult_guidance')
    if guidance['sha256'] != attempt.get('public_sha256'):
        raise ValueError('Sonnet public output changed while preparing the paper candidate')
    _text((Path(root) / guidance['path']).read_text(encoding='utf-8-sig'), 'actual Sonnet public work')
    source = {'exchange_id': exchange_id, 'guidance': guidance, 'authoring_scope': expected,
              'model_identity': {key: model_identity[key]
                                 for key in ('status', 'requested_model', 'response_model')},
              'scope': _text(supplied.get('scope'), 'actual applicable authoring scope')}
    if production is not None:
        source['production_id'] = production['production_id']
        if comparison:
            source['production_stage'] = production['stage']
    return source


def _candidate_issues(root, value):
    issues = []
    for source in value['sources'].values():
        issues.extend(_file_issues(root, source))
    candidate = value['candidate']
    if candidate:
        if 'delivery_policy' in value and not any(r['candidate_id'] == candidate['id'] for r in value['returns']):
            from .codex_session import task_delivery_policy
            if task_delivery_policy(Path(value['task_root'])) != value['delivery_policy']:
                issues.append('task X choice changed; review a candidate under the current task policy')
        if candidate['mapping_digest'] != _digest(value['mapping']):
            issues.append('mapping changed after candidate review')
        if candidate.get('authoring_contract') == NATIVE_AUTHORING_CONTRACT:
            try:
                if _native_consultation(root, value, candidate.get('consultation')) != candidate.get('consultation'):
                    issues.append('selected paper authoring identity changed')
            except (OSError, ValueError, KeyError, TypeError) as error:
                issues.append('selected paper authoring unavailable: ' + str(error))
        for file in candidate['files']:
            issues.extend(_file_issues(root, file))
        for delivery in value['deliveries']:
            if delivery['candidate_id'] == candidate['id']:
                if 'delivery_policy' in value:
                    try:
                        entry = _paper_delivery_entry(value, delivery['delivery_id'])
                        if (entry['identity_digest'] != delivery['ledger_identity_digest'] or
                                entry['receipt_digest'] != delivery['ledger_receipt_digest']):
                            issues.append('selected per-paper delivery identity or receipt changed')
                    except (OSError, ValueError, KeyError) as error:
                        issues.append('selected per-paper delivery unavailable: ' + str(error))
                else:
                    for evidence in delivery['evidence']:
                        issues.extend(_file_issues(root, evidence))
        for returned in value['returns']:
            if returned['candidate_id'] == candidate['id']:
                issues.extend(_file_issues(root, returned['body']))
    return issues


def _candidate_contract(candidate):
    # 0.1 candidates did not declare a contract. Reading them never upgrades
    # their artifact count or rewrites their already selected mail facts.
    return candidate.get('delivery_contract', LEGACY_CONTRACT) if candidate else SINGLE_PDF_CONTRACT


def _pdf_geometry(root, file, profile_name):
    if not isinstance(profile_name, str) or profile_name not in PAGE_PROFILES:
        raise ValueError('page_profile must be a supported named portrait sheet: ' + ', '.join(PAGE_PROFILES))
    try:
        from pypdf import PdfReader
        from pypdf.errors import PyPdfError
    except ImportError as error:
        raise ValueError('actual PDF geometry verification needs the configured Python with pypdf') from error
    raw = (Path(root) / file['path']).read_bytes()
    if sha256(raw).hexdigest() != file['sha256']:
        raise ValueError('PDF changed while preparing the candidate')
    try:
        reader = PdfReader(BytesIO(raw))
        sizes = []
        for page in reader.pages:
            unit = float(page.get('/UserUnit', 1))
            rotation = int(page.rotation or 0) % 360
            if not math.isfinite(unit) or unit <= 0 or rotation not in (0, 90, 180, 270):
                raise ValueError('invalid PDF page unit or rotation')
            boxes = []
            for box in (page.mediabox, page.cropbox):
                width, height = float(box.width) * unit, float(box.height) * unit
                if rotation in (90, 270):
                    width, height = height, width
                boxes.append((width, height))
            sizes.append(boxes)
    except (PyPdfError, ValueError, TypeError, KeyError, AttributeError) as error:
        raise ValueError('cannot verify actual PDF pages: ' + str(error)) from error
    if not sizes:
        raise ValueError('the complete PDF must contain at least one page')
    target = PAGE_PROFILES[profile_name]
    for number, boxes in enumerate(sizes, 1):
        for box_name, size in zip(('MediaBox', 'CropBox'), boxes):
            if any(not math.isfinite(x) or abs(x - wanted) > PAGE_TOLERANCE_PT
                   for x, wanted in zip(size, target)):
                raise ValueError(f'PDF page {number} {box_name} must be the standard portrait {profile_name} sheet')
    for box_index in (0, 1):
        for dimension in (0, 1):
            values = [boxes[box_index][dimension] for boxes in sizes]
            if max(values) - min(values) > PAGE_TOLERANCE_PT:
                raise ValueError('all complete-PDF pages must have uniform physical geometry')
    return {'profile': profile_name, 'pages': len(sizes), 'orientation': 'portrait',
            'width_pt': target[0], 'height_pt': target[1],
            'tolerance_pt': PAGE_TOLERANCE_PT, 'media_and_crop_boxes_checked': True}


def prepare_candidate(root, payload, **revision):
    def update(value):
        if 'delivery_policy' in value:
            from .codex_session import task_delivery_policy
            current_policy = task_delivery_policy(Path(value['task_root']))
            if current_policy is None:
                raise ValueError('parent X task contract is unavailable')
            value['delivery_policy'] = current_policy
            value['recipient'] = current_policy.get('recipient')
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
        integrated = bool(value.get('consult_enabled'))
        native = value.get('mapping_contract') == NATIVE_MAPPING_CONTRACT
        if native:
            locations = [row['location'] for row in value['mapping']['coverage']]
        else:
            locations = _part_locations(value['mapping'], integrated)
            for group in ('assumptions', 'claims', 'chains', 'experiments', 'coverage'):
                locations.extend(row['location'] for row in value['mapping'][group])
        if any(location not in headings for location in locations):
            raise ValueError('mapping location is absent from Markdown headings')
        if not integrated and not native:
            positions = [heading_order[value['mapping']['parts'][part]] for part in PARTS]
            if positions != sorted(positions) or len(set(positions)) != len(PARTS):
                raise ValueError('guide parts must actually appear in reader order m1, m4, m2, m3, m5')
        if not isinstance(payload.get('pdfs'), list) or len(payload['pdfs']) != 1:
            raise ValueError('one complete PDF per paper is required; compress it or arrange alternative delivery, do not split volumes')
        pdfs = [_file(root, payload['pdfs'][0], 'pdf')]
        geometry = _pdf_geometry(root, pdfs[0], payload.get('page_profile', 'A4'))
        files = [markdown, *pdfs, _file(root, payload['qa'], 'qa'), _file(root, payload['review'], 'review')]
        consultation = None
        if native:
            consultation = _native_consultation(root, value, payload.get('consultation'))
            if 'production_id' in consultation:
                from .codex_production import require_applied
                exchange_field = ('candidate_exchange' if consultation.get('production_stage') == 'candidate'
                                  else 'arbitration_exchange')
                applied = require_applied(Path(value['task_root']), consultation['production_id'],
                                          **{exchange_field: consultation['exchange_id']})
                if (Path(applied['output']['path']) != (Path(root) / pdfs[0]['path']).resolve()
                        or applied['output']['sha256'] != pdfs[0]['sha256']):
                    raise ValueError('The selected final paper PDF does not match the applied production output')
            files.append(consultation['guidance'])
        elif integrated:
            supplied = payload.get('consultation')
            if not isinstance(supplied, dict):
                raise ValueError('new paper candidate needs actual Consult public guidance and applicable scope')
            guidance = _file(root, supplied['guidance'], 'consult_guidance')
            _text((Path(root) / guidance['path']).read_text(encoding='utf-8-sig'), 'actual Consult public guidance')
            consultation = {'guidance': guidance,
                'source_ref': _text(supplied.get('source_ref'), 'actual Consult exchange/source reference'),
                'scope': _text(supplied.get('scope'), 'actual applicable guidance scope')}
            files.append(guidance)
        for match in re.finditer(r'!\[[^\]]*\]\(([^)]+)\)', text):
            target = match.group(1).strip().strip('<>')
            if re.match(r'https?://', target):
                raise ValueError('delivery images must be local, actually embedded assets')
            asset = (Path(root) / markdown['path']).parent / target
            files.append(_file(root, asset, 'image'))
        qa = _read(Path(root) / payload['qa'])
        if qa.get('sha256') is not None:
            observed_hash = qa['sha256']
            if (not isinstance(observed_hash, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', observed_hash)
                    or observed_hash.lower() != pdfs[0]['sha256']):
                raise ValueError('QA PDF hash differs from the selected final complete PDF')
        if qa.get('status') == 'NEEDS_REVIEW':
            raise ValueError('selected final-PDF inspection still needs review; resolve it in documented final QA')
        if (qa.get('pages', 0) < 1 or qa.get('rendered_pages') != qa.get('pages') or
                any(qa.get(k) != [] for k in ('formula_errors', 'overflow', 'missing_images'))):
            raise ValueError('actual rendered PDF QA must include page coverage and resolved layout/image errors')
        if (type(qa.get('pages')) is not int or type(qa.get('rendered_pages')) is not int or
                qa['pages'] != geometry['pages']):
            raise ValueError('QA page count must match the actual complete PDF page count')
        review = (Path(root) / payload['review']).read_text(encoding='utf-8-sig')
        _text(review, 'native content and final-page review')
        candidate = {'addon_version': value.get('addon_version', '0.2.0'), 'delivery_contract':
                     X_PDF_CONTRACT if 'delivery_policy' in value else SINGLE_PDF_CONTRACT,
                     'pdf_geometry': geometry,
                     'mapping_digest': _digest(value['mapping']), 'files': files,
                     'responsibility_report': deepcopy(payload.get('responsibility_report', {}))}
        if 'delivery_policy' in value:
            candidate['delivery_policy_id'] = value['delivery_policy']['policy_id']
        if consultation is not None:
            candidate['consultation'] = consultation
        if native:
            candidate.update(authoring_contract=NATIVE_AUTHORING_CONTRACT,
                             mapping_contract=NATIVE_MAPPING_CONTRACT)
        for key in ('N', 'R', 'D', 'V'):
            actual = candidate['responsibility_report'].get(key)
            if type(actual) is not int or actual < value['parameters'][key]:
                raise ValueError('native responsibility report incomplete for this paper: ' + key)
        candidate['id'] = _digest(candidate)
        value['candidate'] = candidate
    return _mutate(root, action='candidate', payload=payload, update=update, **revision)


def _paper_delivery_entry(value, delivery_id):
    from .codex_delivery import inspect as inspect_delivery
    entries = inspect_delivery(value['task_root'])['deliveries']
    selected = next((entry for entry in entries if entry['id'] == delivery_id), None)
    if selected is None:
        raise ValueError('unknown parent-task delivery entry')
    if selected['status'] != 'SENT_VERIFIED' or selected['issues']:
        raise ValueError('parent-task delivery is not verified and current')
    return selected


def record_delivery(root, payload, **revision):
    def update(value):
        candidate = value['candidate']
        if not candidate or _candidate_issues(root, value):
            raise ValueError('mail receipt cannot refer to a missing or stale candidate')
        if 'delivery_policy' in value:
            if value['delivery_policy']['mode'] != 'external':
                raise ValueError('no-X paper has local file delivery; do not send or record external receipts')
            if payload.get('candidate_id') != candidate['id']:
                raise ValueError('receipt must identify the exact reviewed candidate')
            entry = _paper_delivery_entry(value, payload.get('delivery_id'))
            if entry['candidate_id'] != candidate['id'] or entry['policy'] != value['delivery_policy']:
                raise ValueError('verified delivery differs from this paper candidate or frozen X target')
            pdfs = [file for file in candidate['files'] if file['kind'] == 'pdf']
            expected = {(f['filename'], f['bytes'], f['sha256']) for f in pdfs}
            observed = {(f['filename'], f['bytes'], f['sha256']) for f in entry['files']}
            if len(entry['files']) != 1 or observed != expected:
                raise ValueError('this paper needs its one complete PDF in one delivery entry')
            if any(old['candidate_id'] == candidate['id'] and old.get('delivery_id') != entry['id']
                   for old in value['deliveries']):
                raise ValueError('this paper already has a different delivery; reconcile instead of duplicating')
            if any(old.get('delivery_id') == entry['id'] for old in value['deliveries']):
                return
            if entry['authorization_source_ref'] != value['authorization_source_ref']:
                raise ValueError('delivery authorization reference differs from the actual paper batch source')
            receipt = entry['attempts'][-1]['receipt']
            value['deliveries'].append({'candidate_id':candidate['id'], 'delivery_id':entry['id'],
                'ledger_identity_digest':entry['identity_digest'],
                'ledger_receipt_digest':entry['receipt_digest'], 'message_id':receipt.get('message_id'),
                'recipient':value['delivery_policy']['recipient'],
                'attachments':[{'filename':f['filename'],'bytes':f['bytes']} for f in pdfs],
                'evidence':[], 'proof_scope':'current proof in the parent-task ledger; older evidence remains history',
                'authorization_source_ref':entry['authorization_source_ref'],
                'evidence_strength':receipt['evidence_strength'],
                'observation_scope':receipt['scope']})
            return
        if _candidate_contract(candidate) != SINGLE_PDF_CONTRACT:
            raise ValueError('legacy candidate delivery history is read-only; review one current complete PDF before a new delivery')
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
        if _candidate_contract(candidate) == SINGLE_PDF_CONTRACT:
            if len(attachments) != 1:
                raise ValueError('one complete PDF attachment in one Gmail message is required')
            messages = {r['message_id'] for r in value['deliveries'] if r['candidate_id'] == candidate['id']}
            if messages - {message_id}:
                raise ValueError('this complete PDF already has a Gmail message; reconcile it instead of recording another send')
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
    contract = _candidate_contract(candidate)
    receipts = [r for r in value['deliveries']
                if candidate and r['candidate_id'] == candidate['id']]
    volumes = []
    if candidate:
        for file in candidate['files']:
            if file['kind'] != 'pdf':
                continue
            matches = [r for r in receipts if any(a['filename'] == file['filename'] and
                       a['bytes'] == file['bytes'] for a in r['attachments'])]
            messages = [r['message_id'] for r in matches if r.get('message_id') is not None]
            volumes.append({**file, 'message_ids': messages,
                            'delivery_ids':[r['delivery_id'] for r in matches if r.get('delivery_id')],
                            'sent_verified': bool(matches) and not issues})
    remaining = [v['filename'] for v in volumes if not v['sent_verified']]
    completion = None
    if candidate and 'delivery_policy' in value:
        from .codex_delivery import completion_status
        files = [(root / f['path']).as_posix() for f in candidate['files'] if f['kind'] == 'pdf']
        completion = completion_status(value['task_root'], files, value['delivery_policy'],
                                       candidate_id=candidate['id'])
    if issues:
        status = 'STALE_OR_UNAVAILABLE'
    elif candidate:
        status = 'READY'
        if volumes and not remaining:
            status = 'SENT_VERIFIED'
            if any(r['candidate_id'] == candidate['id'] for r in value['returns']):
                status = 'RETURNED'
        if completion is not None and value['delivery_policy']['mode'] == 'local':
            status = 'RETURNED' if any(r['candidate_id'] == candidate['id'] for r in value['returns']) else 'READY_LOCAL'
            remaining = []
        elif completion is not None and not completion['ready']:
            status = 'READY'

    # A checkpoint is an explicit saved next step. Later mutations preserve
    # its reading context but supersede its action, so an old cursor cannot
    # re-send an already verified volume or undo a completed paper return.
    checkpoint_revision = max((o['result']['revision']
        for o in value['operations'].values()
        if o['result']['action'] == 'checkpoint'), default=-1)
    cursor_current = bool(value['cursor']) and checkpoint_revision == value['revision']
    unresolved_delivery = _unresolved_delivery(value)
    if completion is not None and completion.get('unresolved_delivery_ids'):
        unresolved_delivery = {'delivery_ids':completion['unresolved_delivery_ids'],
                              'basis':'parent-task durable pre-send records'}
    pending_saved_step = (cursor_current or bool(unresolved_delivery)) and not issues
    next_action = {
        'DRAFT': 'complete source-bound guide and native review',
        'READY_LOCAL': 'return the complete PDF locally; X is absent, no external send is required or allowed',
        'READY': ('send the one complete PDF through authorized Gmail, then read back: '
                  if contract == SINGLE_PDF_CONTRACT else
                  'send only remaining PDF volumes through authorized Gmail, then read back: ') + ', '.join(remaining),
        'SENT_VERIFIED': 'record this paper return; parent DIGR task stays open',
        'RETURNED': 'this paper returned; continue other papers/common work',
        'STALE_OR_UNAVAILABLE': 'inspect changed source/artifact; do not reuse an old mail receipt'
    }[status]
    if completion is not None and status == 'READY':
        next_action = ('record the already verified parent-task delivery entry; do not resend'
                       if completion['ready'] else
                       'prepare/resume this exact complete PDF in the parent task delivery ledger, then use only the frozen X channel')
    if contract == LEGACY_CONTRACT and status in ('READY', 'SENT_VERIFIED'):
        next_action = 'read legacy delivery facts only; prepare one current complete PDF candidate before a new delivery or return'
    if unresolved_delivery and not issues and completion is not None:
        next_action = 'reconcile the parent-task uncertain delivery before retry or paper return; do not switch channels'
    elif unresolved_delivery and not issues:
        next_action = ('reconcile uncertain Gmail send ' + unresolved_delivery['attempt_id'] +
            ' for ' + ', '.join(unresolved_delivery['remaining']) +
            '; do not resend before checking SENT')
    elif cursor_current and not issues:
        next_action = value['cursor']['next_action']
    return {'paper_id': value['paper_id'], 'line': value['line'], 'revision': value['revision'],
        'status': status, 'issues': issues, 'candidate_id': candidate['id'] if candidate else None,
        'candidate_addon_version': candidate.get('addon_version', '0.1.0') if candidate else None,
        'delivery_contract': contract,
        'delivery_policy':value.get('delivery_policy'), 'delivery_completion':completion,
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
        if _candidate_contract(value['candidate']) not in (SINGLE_PDF_CONTRACT, X_PDF_CONTRACT):
            raise ValueError('legacy candidate return history is read-only; review one current complete PDF before a new return')
        status = inspect(root)
        if status['status'] not in ('SENT_VERIFIED','READY_LOCAL') or status.get('unresolved_delivery_attempt'):
            raise ValueError('paper return requires the complete local PDF or current selected-channel verification'
                             if 'delivery_policy' in value else
                             'paper return requires complete current Gmail attachment verification')
        value['returns'].append({'candidate_id': value['candidate']['id'], 'body': body,
                                'parent_lifecycle_unchanged': True, 'at_ns': time.time_ns()})
    return _mutate(root, action='paper_return', payload={**payload, 'body_file': body}, update=update, **revision)


def checkpoint(root, payload, **revision):
    def update(value):
        if 'delivery_policy' in value and payload.get('pending_delivery') is not None:
            raise ValueError('new X papers use the parent durable pre-send ledger, not a post-timeout Gmail checkpoint')
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
    version_parts = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)', manifest['version'])
    if not version_parts:
        raise ValueError('unsupported DIGRP protocol version')
    if tuple(map(int, version_parts.groups())) >= (0, 2, 0):
        required.add(manifest.get('pdf_design'))
    if not required.issubset(members) or None in required:
        raise ValueError('DIGRP manifest misses a required protocol member, including PDF design in 0.2+')
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
    paths = ('paper/VERSION', 'paper/PROTOCOL.md', 'paper/DATA.md', 'paper/PDF_DESIGN.md',
             '.agents/skills/digr-paper/SKILL.md', '.agents/skills/digr-paper/agents/openai.yaml')
    manifest = {'name': 'DIGR Paper Reading', 'version': version, 'protocol': 'digrp-codex-1',
        'version_path': 'paper/VERSION', 'entrypoint': 'paper/PROTOCOL.md',
        'pdf_design': 'paper/PDF_DESIGN.md',
        'skill': '.agents/skills/digr-paper/SKILL.md',
        'consult_enabled': True, 'authoring_contract': NATIVE_AUTHORING_CONTRACT,
        'mapping_contract': NATIVE_MAPPING_CONTRACT,
        'file_sha256': {path: sha256((root / path).read_bytes()).hexdigest() for path in paths}}
    _write(root / 'paper/manifest.json', manifest)
    core = _read(root / 'codex/manifest.json')
    core['paper_addon'] = {'manifest': 'paper/manifest.json', 'version': version,
                         'sha256': sha256((root / 'paper/manifest.json').read_bytes()).hexdigest()}
    _write(root / 'codex/manifest.json', core)
    return {'version': version, 'members': len(paths), 'live_acquisition_performed': False,
            'core_hash_refresh_required': True}
