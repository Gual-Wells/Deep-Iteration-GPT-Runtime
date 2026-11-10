"""Portable, creator-only copies of an ESP snapshot and its selected records.

Original history is never rewritten. References are selected from events, not
discovered by scanning directories. Selected records use <sha>.<format>.raw to
preserve original bytes, including line endings. Legacy schema-1 bare-extension
records remain readable. File bindings do not authenticate a host,
an independent agent, actual input delivery, authorship or semantic correctness.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import stat

from runtime import codex_preprint as core

SCHEMA = 1
MANIFEST = 'native-source-manifest.json'
_RECORD = re.compile(r'^records/([0-9a-f]{64})\.(json|txt|md)(?:\.raw)?$')
_EXTENSIONS = {'.json', '.txt', '.md'}
_LIMITS = ('Creator-only selected file archive, not a phone package. Native text and '
           'saved packet checks are file consistency checks. Executor strings are '
           'operator attribution, not authenticated independent identities or input delivery. '
           'Missing inputs are not reconstructed. No hostile filesystem-race guarantee; '
           'the manifest does not hash or authenticate itself.')


def _no_links(path):
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        core.need(not stat.S_ISLNK(info.st_mode) and not (
            getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)),
            'linked or reparse paths are not allowed: ' + str(part))


def _directory(value):
    path = Path(value).absolute()
    _no_links(path)
    core.need(path.is_dir(), 'directory is missing: ' + str(path))
    return path.resolve(strict=True)


def _bytes(path):
    _no_links(path)
    before = path.stat()
    core.need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
              'selected source must be a regular, unlinked file: ' + str(path))
    raw = path.read_bytes()
    _no_links(path)
    after = path.stat()
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')
    core.need(all(getattr(before, f) == getattr(after, f) for f in fields) and len(raw) == after.st_size,
              'selected file changed while reading: ' + str(path))
    return raw


def _source_file(base, ref):
    core.text(ref, 'selected source reference')
    relative = Path(ref)
    core.need('..' not in relative.parts and '\x00' not in ref and
              not (relative.anchor and not relative.is_absolute()),
              'ambiguous or traversing source reference: ' + ref)
    core.need(relative.is_absolute() or ':' not in ref,
              'source reference is not a supported file path: ' + ref)
    path = relative if relative.is_absolute() else base / relative
    core.need(path.is_relative_to(base), 'source reference is outside source_base: ' + ref)
    _no_links(path)
    core.need(path.suffix.lower() in _EXTENSIONS and path.name.lower() != 'pool.json',
              'only selected JSON/text native records are supported; PDFs and pools are excluded: ' + ref)
    core.need(path.is_file(), 'selected source file is missing: ' + ref)
    core.need(path.resolve(strict=True).is_relative_to(base),
              'source reference resolves outside source_base: ' + ref)
    return path


def _snapshot(root):
    root = _directory(root)
    raw = _bytes(root / 'preprint.json')
    state = core.load(root)
    core.need(json.loads(raw.decode('utf-8-sig')) == state,
              'source changed while reading archive snapshot; retry')
    return root, state, raw


def _binding(state, raw):
    return {'file': 'preprint.json', 'baseline_id': state['spec']['id'],
            'snapshot_sha256': state['integrity_sha256'],
            'source_file_sha256': sha256(raw).hexdigest()}


def _references(state):
    uses, missing, ids = {}, [], set()
    for event in state['events']:
        eid = core.text(event.get('id'), 'actual event id')
        core.need(eid not in ids, 'duplicate event id')
        ids.add(eid)
        for field in ('source_ref', 'input_ref'):
            ref = event.get(field)
            if field == 'input_ref' and ref is None:
                missing.append({'event_id': eid, 'kind': event['kind'],
                                'reason': 'input_ref not recorded; no input snapshot reconstructed'})
                continue
            core.text(ref, 'event ' + field)
            uses.setdefault(ref, []).append({'event_id': eid, 'field': field})
    return uses, missing


def _json(raw):
    return json.loads(raw.decode('utf-8-sig'))


def _record_format(record):
    name = record.get('path')
    match = _RECORD.fullmatch(name) if isinstance(name, str) else None
    core.need(match is not None and record.get('sha256') == match.group(1),
              'invalid content-addressed archive record path or digest')
    # New raw envelopes declare the format; old schema-1 names already did so.
    actual = match.group(2)
    declared = record.get('format', actual if not name.endswith('.raw') else None)
    core.need(declared == actual, 'archive record format differs from its path')
    return actual


def _historical_records(root, state):
    path = root / MANIFEST
    _no_links(path)
    if not path.exists():
        return {}, None
    raw = _bytes(path)
    manifest = _json(raw)
    core.need(isinstance(manifest, dict) and manifest.get('schema_version') == SCHEMA and
              manifest.get('kind') == 'english-spoken-preprint-native-sources',
              'unsupported local native source manifest')
    source = manifest.get('source')
    core.need(isinstance(source, dict) and source.get('baseline_id') == state['spec']['id'],
              'local source manifest belongs to a different baseline')
    records = manifest.get('records')
    core.need(isinstance(records, dict), 'invalid local source record mapping')
    # Appending makes the old snapshot binding stale. Validate only records
    # needed now, against their retained current event uses and actual bytes.
    return records, raw


def _historical_file(root, ref, record, current_uses):
    core.need(isinstance(record, dict), 'invalid historical source record for ' + ref)
    file_format = _record_format(record)
    core.need(file_format == Path(ref).suffix.lower()[1:],
              'historical record format differs from original reference')
    previous = record.get('uses')
    core.need(isinstance(previous, list) and previous and all(
        isinstance(use, dict) and set(use) == {'event_id', 'field'} and
        isinstance(use['event_id'], str) and use['field'] in ('source_ref', 'input_ref')
        for use in previous), 'invalid historical event/field uses for ' + ref)
    pairs = [(use['event_id'], use['field']) for use in previous]
    current = {(use['event_id'], use['field']) for use in current_uses}
    core.need(len(pairs) == len(set(pairs)) and set(pairs) <= current,
              'historical record uses are not retained in current events for ' + ref)
    path = root / record['path']
    data = _bytes(path)
    core.need(sha256(data).hexdigest() == record['sha256'],
              'historical record bytes changed: ' + record['path'])
    return path, file_format, data


def _checks(state, records, payloads):
    text_checked, packet_checked, text_unchecked = [], [], []
    for event in state['events']:
        eid = event['id']
        source = records[event['source_ref']]
        document = _json(payloads[source['path']]) if _record_format(source) == 'json' else None
        if isinstance(document, dict) and 'actual_native_return' in document:
            returned = document['actual_native_return']
            core.need(isinstance(returned, str) and returned == event.get('text'),
                      'actual_native_return text mismatch for event ' + eid)
            if 'executor' in document and 'executor' in event:
                core.need(document['executor'] == event['executor'],
                          'executor attribution mismatch for event ' + eid)
            text_checked.append(eid)
        else:
            text_unchecked.append(eid)
        ref = event.get('input_ref')
        if ref is not None:
            item = records[ref]
            packet = _json(payloads[item['path']]) if _record_format(item) == 'json' else None
            if isinstance(packet, dict) and ('view' in packet or 'packet_sha256' in packet):
                core.need(isinstance(packet.get('view'), dict) and
                          core.digest(packet['view']) == packet.get('packet_sha256'),
                          'saved input packet digest mismatch for event ' + eid)
                if 'packet_sha256' in event:
                    core.need(packet['packet_sha256'] == event['packet_sha256'],
                              'saved input packet differs from event packet for ' + eid)
                packet_checked.append(eid)
    return {'native_return_text_checked': text_checked,
            'native_return_text_unchecked': text_unchecked,
            'saved_packet_checked': packet_checked}


def archive_sources(root, source_base, out):
    """Create a new creator archive; raise on unsupported/missing source records.

    Historical references first use selected, verified records in root's local
    manifest, even after its snapshot binding becomes stale through appending.
    New references resolve only against explicit source_base; absolute new paths
    must be inside it. No source directory, PDF or pool is copied.
    Preflight failures leave out absent; I/O failures may leave a partial new out.
    """
    out = Path(out).absolute()
    _no_links(out)
    core.need(not out.exists(), 'source archive output must be new; refusing overwrite')
    root, state, raw = _snapshot(root)
    uses, missing = _references(state)
    history, history_raw = _historical_records(root, state)
    base, reused = None, []
    records, payloads, selected = {}, {}, {}
    for ref, usage in uses.items():
        if ref in history:
            path, file_format, data = _historical_file(root, ref, history[ref], usage)
            reused.append(ref)
        else:
            if base is None:
                core.need(source_base is not None, 'new source references require explicit source_base')
                base = _directory(source_base)
            path = _source_file(base, ref)
            data = _bytes(path)
            file_format = path.suffix.lower()[1:]
        digest = sha256(data).hexdigest()
        target = 'records/' + digest + '.' + file_format + '.raw'
        records[ref] = {'path': target, 'sha256': digest,
                        'format': file_format, 'uses': usage}
        payloads[target] = data
        selected[ref] = (path, data)
    _checks(state, records, payloads)
    core.need(_bytes(root / 'preprint.json') == raw,
              'source snapshot changed while selecting archive records; retry')
    if history_raw is not None:
        core.need(_bytes(root / MANIFEST) == history_raw,
                  'local source manifest changed while selecting archive records; retry')
    for ref, (path, data) in selected.items():
        core.need(_bytes(path) == data,
                  'selected source changed while preparing archive: ' + ref)
    manifest = {'schema_version': SCHEMA, 'kind': 'english-spoken-preprint-native-sources',
                'source': _binding(state, raw), 'records': records,
                'missing_inputs': missing, 'limits': _LIMITS}
    out.mkdir(parents=True)
    (out / 'records').mkdir()
    files = {'preprint.json': raw, **payloads,
             MANIFEST: (json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')}
    for name, data in files.items():
        with (out / name).open('xb') as handle:
            handle.write(data)
    result = audit_sources(out)
    core.need(result['valid'], 'new source archive failed read-back: ' + '; '.join(result['errors']))
    return {'out': out.as_posix(), 'manifest': (out / MANIFEST).as_posix(),
            'reused_local_refs': reused, **result}


def _audit(out):
    out, state, raw = _snapshot(out)
    manifest = _json(_bytes(out / MANIFEST))
    core.need(manifest.get('schema_version') == SCHEMA and
              manifest.get('kind') == 'english-spoken-preprint-native-sources',
              'unsupported native source manifest')
    core.need(manifest.get('source') == _binding(state, raw), 'archived snapshot binding mismatch')
    uses, missing = _references(state)
    records = manifest.get('records')
    core.need(isinstance(records, dict) and records.keys() == uses.keys(),
              'archive reference coverage differs from snapshot')
    core.need(manifest.get('missing_inputs') == missing, 'missing-input declaration differs from snapshot')
    payloads = {}
    for ref, expected_uses in uses.items():
        record = records[ref]
        core.need(isinstance(record, dict) and record.get('uses') == expected_uses,
                  'archive event/field uses differ for reference ' + ref)
        core.need(_record_format(record) == Path(ref).suffix.lower()[1:],
                  'archive record format differs from original reference')
        name = record.get('path')
        data = _bytes(out / name)
        core.need(sha256(data).hexdigest() == record['sha256'], 'archived record bytes changed: ' + name)
        payloads[name] = data
    expected = {'preprint.json', MANIFEST, 'records'}
    core.need({p.name for p in out.iterdir()} == expected, 'unexpected source archive inventory')
    record_dir = _directory(out / 'records')
    core.need({p.name for p in record_dir.iterdir()} == {Path(n).name for n in payloads},
              'unexpected selected-record inventory')
    checks = _checks(state, records, payloads)
    return {'status': 'VALID_WITH_INPUT_GAPS' if missing else 'VALID', 'valid': True,
            'errors': [], 'source': manifest['source'], 'events': len(state['events']),
            'selected_refs': len(records), 'archived_files': len(payloads),
            'source_ref_uses': len(state['events']),
            'input_ref_uses': sum(e.get('input_ref') is not None for e in state['events']),
            'missing_inputs': missing, 'input_coverage_complete': not missing,
            **checks, 'identity_authenticated': False, 'limits': _LIMITS}


def audit_sources(out):
    """Audit only archive-local bytes; original paths are never dereferenced.

    VALID_WITH_INPUT_GAPS is deliberately different from complete input coverage.
    Invalid/missing files return INVALID_ARCHIVE with the first concrete error.
    """
    try:
        return _audit(out)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        return {'status': 'INVALID_ARCHIVE', 'valid': False, 'errors': [str(error)],
                'identity_authenticated': False}
