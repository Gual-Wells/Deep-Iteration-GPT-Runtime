"""Task-scoped Gmail file outbox; the native connector performs the transfer.

The durable SENDING transition precedes the side effect. Its replay never grants
another send. An interrupted sender remains uncertain until actual readback or
positive non-send evidence reconciles it. These are operator evidence records,
not authentication of the host, an exactly-once transport, or remote-read proof.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from email.utils import getaddresses
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import time
import uuid

FORMAT = 'digr-file-delivery-1'
POLICY_FORMAT = 'digr-delivery-policy-1'
REGISTRY_FORMAT = 'digr-delivery-targets-1'
DEFAULT_TARGET = 'gmail'
_SLUG = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}')
_HASH = re.compile(r'[0-9a-f]{64}')
_UNRESOLVED = {'SENDING', 'UNCERTAIN'}
_TARGET_FIELDS = {'channel', 'account', 'recipient', 'transport', 'target_kind',
                  'aliases', 'binding_status', 'capability_status', 'evidence_refs',
                  'account_kind', 'evidence_adapter'}


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(label + ' must be nonempty, trimmed text')
    if '\r' in value or '\n' in value:
        raise ValueError(label + ' must be a single line')
    return value


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _read(path):
    value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('expected a JSON object: ' + str(path))
    return value


def _single_mailbox(value, label):
    _text(value, label)
    addresses = getaddresses([value])
    if len(addresses) != 1 or not re.fullmatch(r'[^\s@,;<>]+@[^\s@,;<>]+', addresses[0][1]):
        raise ValueError(label + ' must identify exactly one mailbox')
    return addresses[0][1].casefold()


def resolve_policy(selection, registry=None):
    """Resolve a parser selection once, without guessing or changing accounts.

    registry is a private JSON path or mapping. Only nonsecret endpoint data is
    supported; executable adapters, tokens, and arbitrary profile fields fail.
    No-X local selection neither requires nor reads a registry.
    """
    if not isinstance(selection, dict) or set(selection) != {'mode', 'target', 'explicit'}:
        raise ValueError('delivery_selection needs exactly mode, target, explicit')
    if type(selection['explicit']) is not bool:
        raise ValueError('delivery selection explicit must be boolean')
    mode, target = selection['mode'], selection['target']
    if mode == 'local':
        if target is not None or selection['explicit']:
            raise ValueError('local delivery selection cannot arm an external target')
        policy = {'format': POLICY_FORMAT, **selection, 'channel': None, 'account': None,
                  'recipient': None, 'transport': None, 'target_kind': None}
    elif mode == 'external':
        if not selection['explicit']:
            raise ValueError('external delivery requires an explicit X selection')
        if target is not None and (not isinstance(target, str) or not _SLUG.fullmatch(target)):
            raise ValueError('invalid delivery target slug')
        if registry is None:
            raise ValueError('selected external target has no private registry')
        registered = _read(registry) if isinstance(registry, (str, Path)) else deepcopy(registry)
        if not isinstance(registered, dict) or registered.get('format', REGISTRY_FORMAT) != REGISTRY_FORMAT:
            raise ValueError('unsupported delivery target registry format')
        if set(registered) - {'format', 'targets'} or not isinstance(registered.get('targets'), dict):
            raise ValueError('registry supports only a targets object and format')
        targets, aliases = {}, {}
        for name, profile in registered['targets'].items():
            if not isinstance(name, str) or not _SLUG.fullmatch(name):
                raise ValueError('invalid registered target slug')
            canonical = name.casefold()
            if canonical in targets:
                raise ValueError('case-insensitive duplicate registered target')
            if not isinstance(profile, dict) or set(profile) - _TARGET_FIELDS:
                raise ValueError('target supports endpoint facts only; no credentials or command plugins')
            for key in ('channel', 'account', 'recipient', 'transport', 'target_kind'):
                _text(profile.get(key), 'target ' + key)
            channel = profile['channel'].casefold()
            if channel != 'gmail':
                raise ValueError('unsupported delivery channel; this version supports Gmail only')
            if profile['transport'] != 'native-connector' or profile['target_kind'] != 'self_mailbox':
                raise ValueError('Gmail delivery requires the native connector and self mailbox')
            account = _single_mailbox(profile['account'], 'Gmail account')
            recipient = _single_mailbox(profile['recipient'], 'Gmail recipient')
            if account != recipient:
                raise ValueError('self mailbox account and recipient differ')
            binding = profile.get('binding_status', 'identity_unverified')
            if binding not in {'bound', 'identity_unverified'}:
                raise ValueError('binding_status must be bound or identity_unverified')
            # Keep passive origin fields so existing Gmail policy hashes remain
            # readable. They neither add transports nor grant sender authority.
            for field in ('capability_status', 'account_kind'):
                if field in profile:
                    _text(profile[field], 'historical ' + field)
            for field in ('aliases', 'evidence_refs'):
                if not isinstance(profile.get(field, []), list):
                    raise ValueError(field + ' must be a list')
                for item in profile.get(field, []):
                    _text(item, field)
            profile['channel'] = channel
            profile['binding_status'] = binding
            if profile.get('evidence_adapter', 'gmail-api') != 'gmail-api':
                raise ValueError('unsupported evidence adapter; native Gmail readback is required')
            profile['evidence_adapter'] = 'gmail-api'
            targets[canonical] = profile
            for alias in [name, *profile.get('aliases', [])]:
                if not _SLUG.fullmatch(alias):
                    raise ValueError('target alias must have target slug syntax')
                folded = alias.casefold()
                if folded in aliases and aliases[folded] != canonical:
                    raise ValueError('ambiguous case-insensitive target alias')
                aliases[folded] = canonical
        requested = (target or DEFAULT_TARGET).casefold()
        if requested not in aliases:
            raise ValueError('unknown or unconfigured delivery target: ' + requested)
        canonical = aliases[requested]
        profile = {key: value for key, value in targets[canonical].items() if key != 'aliases'}
        policy = {'format': POLICY_FORMAT, 'mode': 'external', 'target': canonical,
                  'explicit': True, **profile}
    else:
        raise ValueError('delivery selection mode must be local or external')
    policy['policy_id'] = _digest(policy)
    return policy


def validate_policy(policy):
    """Validate an already frozen policy; never re-resolve it from a registry."""
    if not isinstance(policy, dict) or policy.get('format') != POLICY_FORMAT:
        raise ValueError('unsupported delivery policy snapshot')
    original = deepcopy(policy); identity = original.pop('policy_id', None)
    if identity != _digest(original):
        raise ValueError('delivery policy snapshot changed')
    if policy.get('mode') == 'local':
        expected = resolve_policy({'mode': 'local', 'target': None, 'explicit': False})
    elif policy.get('mode') == 'external':
        target = policy.get('target')
        profile = {key: value for key, value in policy.items() if key in _TARGET_FIELDS}
        expected = resolve_policy({'mode': 'external', 'target': target, 'explicit': True},
            {'format': REGISTRY_FORMAT, 'targets': {target: profile}})
    else:
        raise ValueError('invalid delivery policy mode')
    if expected != policy:
        raise ValueError('invalid frozen delivery policy fields')
    return deepcopy(policy)


def snapshot_files(root, files):
    """Read selected actual files; supplied descriptors must still match bytes."""
    if not isinstance(files, list):
        raise ValueError('files must be an explicit list of selected files')
    root = Path(root).resolve()
    snapshots, names, paths = [], set(), set()
    for item in files:
        supplied = item if isinstance(item, dict) else None
        raw_path = supplied.get('path') if supplied is not None else item
        if not isinstance(raw_path, (str, Path)) or not str(raw_path):
            raise ValueError('selected file needs an actual path')
        path = Path(raw_path)
        path = path.resolve() if path.is_absolute() else (root / path).resolve()
        if not path.is_file():
            raise ValueError('selected file is unavailable: ' + str(path))
        raw = path.read_bytes()
        observed = {'path': os.path.relpath(path, root).replace('\\', '/'),
                    'filename': path.name, 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
        if supplied is not None:
            for field in ('filename', 'bytes', 'sha256'):
                if field in supplied and supplied[field] != observed[field]:
                    raise ValueError('selected file snapshot changed: ' + path.name)
        if observed['filename'].casefold() in names or str(path).casefold() in paths:
            raise ValueError('duplicate selected path or ambiguous attachment filename')
        names.add(observed['filename'].casefold()); paths.add(str(path).casefold())
        snapshots.append(observed)
    return snapshots


def _descriptors(files):
    if not isinstance(files, list) or not files:
        raise ValueError('receipt verification needs selected file descriptors')
    names = set()
    for item in files:
        if not isinstance(item, dict):
            raise ValueError('invalid selected file descriptor')
        name = _text(item.get('filename'), 'selected filename')
        if type(item.get('bytes')) is not int or item['bytes'] < 0 or not _HASH.fullmatch(str(item.get('sha256', ''))):
            raise ValueError('selected file descriptor needs exact bytes and local sha256')
        if name.casefold() in names:
            raise ValueError('ambiguous selected attachment filenames')
        names.add(name.casefold())
    return {item['filename']: item for item in files}


def _same_identity(policy, observed):
    if not isinstance(observed, dict) or observed.get('account_confirmed') is not True or observed.get('recipient_confirmed') is not True:
        raise ValueError('fresh current-account and destination identity observations are required')
    for field in ('account', 'recipient'):
        actual, expected = observed.get(field), policy[field]
        actual = _single_mailbox(actual, 'observed ' + field)
        expected = _single_mailbox(expected, 'configured ' + field)
        if actual != expected:
            raise ValueError('observed ' + field + ' differs from the frozen target')


def _gmail_message(result):
    if not isinstance(result, dict):
        raise ValueError('actual Gmail readback result required')
    result = result.get('structuredContent', result)
    if not isinstance(result, dict):
        raise ValueError('invalid Gmail structuredContent')
    # Some native hosts wrap the API Message as message; neither wrapper is a
    # replacement for the API's payload.headers/parts attachment facts.
    result = result.get('message', result)
    if not isinstance(result, dict) or not isinstance(result.get('payload'), dict):
        raise ValueError('Gmail readback needs the actual MIME payload')
    return result


def _gmail_facts(policy, receipt):
    message = _gmail_message(receipt.get('readback_result'))
    message_id = _text(message.get('id'), 'actual Gmail message ID')
    if receipt.get('message_id') not in (None, message_id):
        raise ValueError('Gmail message ID differs from actual readback')
    if 'labelIds' in message and 'label_ids' in message and message['labelIds'] != message['label_ids']:
        raise ValueError('conflicting Gmail native/API label fields')
    if 'SENT' not in message.get('labelIds', message.get('label_ids', [])):
        raise ValueError('Gmail readback must have the SENT label')
    headers = {}
    for header in message['payload'].get('headers', []):
        if not isinstance(header, dict):
            raise ValueError('invalid Gmail MIME header')
        name = _text(header.get('name'), 'MIME header name').casefold()
        if name in {'from', 'to', 'cc', 'bcc'}:
            raw_value = header.get('value')
            if not isinstance(raw_value, str):
                raise ValueError('invalid Gmail recipient/sender header')
            unfolded = re.sub(r'\r?\n[ \t]+', ' ', raw_value).strip()
            if unfolded:
                headers.setdefault(name, []).append(_text(unfolded, 'MIME header value'))
    to = [address for _, address in getaddresses(headers.get('to', [])) if address]
    extra = [address for _, address in getaddresses(headers.get('cc', []) + headers.get('bcc', [])) if address]
    if len(to) != 1 or extra or _single_mailbox(to[0], 'Gmail To') != _single_mailbox(policy['recipient'], 'configured recipient'):
        raise ValueError('Gmail readback has a different or additional recipient')
    senders = [address for _, address in getaddresses(headers.get('from', [])) if address]
    if len(senders) != 1 or _single_mailbox(senders[0], 'Gmail From') != _single_mailbox(policy['account'], 'configured account'):
        raise ValueError('Gmail From differs from the frozen account')
    attachments = []
    def visit(part):
        if not isinstance(part, dict):
            raise ValueError('invalid Gmail MIME part')
        if part.get('filename'):
            body = part.get('body')
            if body is None:
                body = {}
            if not isinstance(body, dict):
                raise ValueError('invalid Gmail attachment body')
            attachments.append({'filename': part['filename'], 'bytes': body.get('size'),
                                'transfer_complete': True})
        children = part.get('parts')
        if children is None:
            children = []
        if not isinstance(children, list):
            raise ValueError('Gmail MIME parts must be a list or null')
        for child in children:
            visit(child)
    visit(message['payload'])
    return message_id, attachments


def verify_receipt(policy, files, receipt, *, candidate_id=None, attempt_id=None):
    """Validate native Gmail metadata; local hashes bind the selected files.

    MIME part byte counts are metadata, not remote-byte hashes or recipient-read
    evidence. reconcile() also binds the actual saved native evidence files.
    """
    policy = validate_policy(policy)
    if policy['mode'] != 'external':
        raise ValueError('local selection cannot have an external receipt')
    expected = _descriptors(files)
    if not isinstance(receipt, dict):
        raise ValueError('receipt must be an object')
    for field in ('target', 'channel', 'account', 'recipient', 'transport'):
        actual, selected = receipt.get(field), policy[field]
        if field in ('account', 'recipient'):
            actual = _single_mailbox(actual, 'receipt ' + field)
            selected = _single_mailbox(selected, 'configured ' + field)
        if actual != selected:
            raise ValueError('receipt ' + field + ' differs from the frozen policy')
    for field, wanted in (('candidate_id', candidate_id), ('attempt_id', attempt_id)):
        _text(receipt.get(field), 'receipt ' + field)
        if wanted is not None and receipt[field] != wanted:
            raise ValueError('receipt does not bind the exact ' + field)
    _same_identity(policy, receipt.get('identity'))
    for field in ('identity_evidence', 'send_evidence', 'readback_evidence'):
        _text(receipt.get(field), field)
    readback = receipt.get('readback')
    if not isinstance(readback, dict) or readback.get('completed') is not True or readback.get('attempt_correlated') is not True:
        raise ValueError('completed readback must be correlated with this actual attempt')
    kind = receipt.get('evidence_kind')
    if kind != policy.get('evidence_adapter'):
        raise ValueError('receipt evidence kind differs from the frozen evidence adapter')
    if kind != 'gmail-api':
        raise ValueError('unsupported receipt evidence kind')
    message_id, attachments = _gmail_facts(policy, receipt)
    strength = 'api-attachment-metadata'
    if not isinstance(attachments, list) or len(attachments) != len(expected):
        raise ValueError('readback attachment count differs from selected files')
    observed, names = [], set()
    for item in attachments:
        if not isinstance(item, dict) or item.get('filename') not in expected:
            raise ValueError('readback attachment filename differs from selected files')
        name = item['filename']
        if name in names or item.get('transfer_complete') is not True:
            raise ValueError('duplicate attachment or incomplete transfer')
        names.add(name); local = expected[name]
        normalized = {'filename': name, 'local_bytes': local['bytes'], 'local_sha256': local['sha256'],
                      'transfer_complete': True, 'remote_bytes': None, 'remote_sha256': None}
        if item.get('bytes') is not None:
            if type(item['bytes']) is not int or item['bytes'] != local['bytes']:
                raise ValueError('readback attachment bytes differ from selected files')
            normalized.update(remote_bytes=item['bytes'], exact_remote_bytes=True)
        else:
            raise ValueError('Gmail attachment part body.size is required; message sizeEstimate is not attachment bytes')
        observed.append(normalized)
    return {'candidate_id': receipt['candidate_id'], 'attempt_id': receipt['attempt_id'],
            'policy_id': policy['policy_id'], 'target': policy['target'], 'channel': policy['channel'],
            'account': policy['account'], 'recipient': policy['recipient'], 'message_id': message_id,
            'evidence_kind': kind, 'evidence_strength': strength, 'attachments': observed,
            'scope': 'host-selected send and readback observations; no remote open/read claim'}


def _empty():
    return {'format': FORMAT, 'revision': 0, 'deliveries': {}, 'operations': {}}


def _load(root):
    path = Path(root) / 'delivery.json'
    value = _read(path) if path.exists() else _empty()
    if value.get('format') != FORMAT:
        raise ValueError('unsupported delivery ledger format; preserve historical pin semantics')
    return value


def _write(root, value):
    path = Path(root) / 'delivery.json'
    temp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
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
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    path = root / '.delivery-write.lock'
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError('delivery writer is busy; inspect a stale lock before recovery') from error
    try:
        os.write(descriptor, json.dumps({'pid': os.getpid(), 'at_ns': time.time_ns()}).encode())
        os.close(descriptor); descriptor = None
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        path.unlink()


def policy_lock(root):
    """Serialize an explicit task policy-change check+save with send reserves.

    Lifecycle callers reload their task state inside this context. STOP and new
    input fences need not wait for it; the native host still honors those fences.
    """
    return _lock(Path(root).resolve())


def _mutate(root, action, payload, update, *, operation_id, expected_revision=None, guard=None):
    root = Path(root).resolve(); _text(operation_id, 'operation_id')
    fingerprint = _digest({'action': action, 'payload': payload})
    with _lock(root):
        value = _load(root)
        previous = value['operations'].get(operation_id)
        if previous:
            if previous['fingerprint'] != fingerprint:
                raise ValueError('operation ID reused for different delivery content')
            # Replayed bookkeeping is never a second permission for an effect.
            return {**deepcopy(previous['result']), 'idempotent_replay': True, 'send_allowed': False}
        if expected_revision is not None and (type(expected_revision) is not int or expected_revision != value['revision']):
            raise ValueError('delivery revision conflict; inspect before reconciling')
        result = update(value)
        if guard is not None:
            guard()
        value['revision'] += 1
        result.update(revision=value['revision'], action=action)
        value['operations'][operation_id] = {'fingerprint': fingerprint, 'result': deepcopy(result)}
        _write(root, value)
        if guard is not None:
            # A concurrent STOP/pending input is allowed to fence execution
            # without waiting for this lock. Keep SENDING but return no grant.
            guard()
    return result


def _endpoint(policy):
    endpoint = {key: policy[key] for key in ('channel', 'account', 'recipient', 'target_kind')}
    endpoint.update(account=_single_mailbox(endpoint['account'], 'account'),
                    recipient=_single_mailbox(endpoint['recipient'], 'recipient'))
    return endpoint


def _effect_key(candidate_id, policy, files):
    # Paths, aliases, authorization wording and explicit syntax cannot create a
    # second effect for the same candidate, endpoint and attachment selection.
    identities = sorted(({key: item[key] for key in ('filename', 'bytes', 'sha256')} for item in files), key=lambda row: row['filename'])
    return _digest({'candidate_id': candidate_id, 'endpoint': _endpoint(policy), 'files': identities})


def _reject_overlap(value, candidate_id, policy, files, exclude=None):
    identities = {(item['filename'], item['bytes'], item['sha256']) for item in files}
    for other in value['deliveries'].values():
        if (other['id'] == exclude or other['candidate_id'] != candidate_id or
                _endpoint(other['policy']) != _endpoint(policy) or
                other['status'] not in _UNRESOLVED | {'SENT_VERIFIED'}):
            continue
        other_files = {(item['filename'], item['bytes'], item['sha256']) for item in other['files']}
        if identities & other_files:
            raise ValueError('overlap with an uncertain or verified delivery; reconcile its exact attempt instead of repackaging files')


def _current_evidence(delivery):
    if not delivery['attempts']:
        return []
    attempt = delivery['attempts'][-1]
    if delivery['status'] in {'SENT_VERIFIED', 'NOT_SENT'}:
        outcome = 'sent' if delivery['status'] == 'SENT_VERIFIED' else 'not_sent'
        latest = next((item for item in reversed(attempt['observations']) if item['outcome'] == outcome), None)
        return list(latest['evidence'].values()) if latest else [attempt['identity_evidence']]
    return [attempt['identity_evidence'], *attempt.get('identity_sources', {}).values(),
            *(item for observation in attempt['observations'] for item in observation['evidence'].values())]


def _delivery_issues(root, delivery, *, history=False):
    issues = []
    try:
        validate_policy(delivery['policy']); snapshot_files(root, delivery['files'])
    except (OSError, ValueError) as error:
        issues.append(str(error))
    selected = _current_evidence(delivery)
    if history:
        selected = [item for attempt in delivery['attempts'] for item in
            [attempt['identity_evidence'], *attempt.get('identity_sources', {}).values(),
             *(file for observation in attempt['observations'] for file in observation['evidence'].values())]]
    for item in selected:
        try:
            snapshot_files(root, [item])
        except (OSError, ValueError) as error:
            issues.append(str(error))
    return issues


def _task_policy(root, policy, *, active=True, production=False):
    if not (Path(root) / 'session.json').exists():
        return None
    from .codex_session import task_delivery_policy
    current = task_delivery_policy(Path(root))
    if current is None:
        raise ValueError('legacy pinned task has no X delivery contract; use its original tools')
    if validate_policy(current) != policy:
        raise ValueError('supplied delivery policy differs from the current task selection')
    if active:
        from .codex_lifecycle import require_active
        lifecycle = require_active(Path(root))
        if validate_policy(lifecycle.get('delivery_policy', current)) != policy:
            raise ValueError('task delivery authority changed during policy observation')
    if production:
        from .codex_foundation import require_foundation_ready
        require_foundation_ready(Path(root))
    return {'lifecycle_revision': lifecycle['revision'], 'message_id': lifecycle['message_id'],
            'handled_message_id': lifecycle['handled_message_id'], 'policy_id': policy['policy_id'],
            'foundation_sha256': sha256((Path(root) / 'foundation.json').read_bytes()).hexdigest() if production else None}


def prepare(root, payload, **revision):
    """Freeze exact candidate/files/target; this function never grants a send."""
    policy = validate_policy(payload.get('policy'))
    _task_policy(root, policy)
    if policy['mode'] == 'local':
        return {'status': 'LOCAL_ONLY', 'send_allowed': False, 'delivery_id': None}
    if payload.get('files') == []:
        return {'status': 'NO_FILES', 'send_allowed': False, 'delivery_id': None}
    files = snapshot_files(root, payload.get('files'))
    candidate = _text(payload.get('candidate_id'), 'exact candidate_id')
    authorization = _text(payload.get('authorization_source_ref'), 'actual authorization source reference')
    effect = _effect_key(candidate, policy, files)
    frozen = {'candidate_id': candidate, 'policy': policy, 'files': files,
              'authorization_source_ref': authorization}
    def update(value):
        for delivery in value['deliveries'].values():
            if delivery['effect_key'] == effect:
                return {'delivery_id': delivery['id'], 'status': delivery['status'],
                        'send_allowed': False, 'existing_delivery': True}
        _reject_overlap(value, candidate, policy, files)
        delivery_id = _digest(frozen)
        value['deliveries'][delivery_id] = {'id': delivery_id, **deepcopy(frozen),
            'effect_key': effect, 'status': 'PREPARED', 'attempts': [], 'created_at_ns': time.time_ns()}
        return {'delivery_id': delivery_id, 'status': 'PREPARED', 'send_allowed': False}
    return _mutate(root, 'prepare', frozen, update, **revision)


def _delivery(value, payload):
    delivery_id = _text(payload.get('delivery_id'), 'delivery_id')
    if delivery_id not in value['deliveries']:
        raise ValueError('unknown task-scoped delivery_id')
    return value['deliveries'][delivery_id]


def _evidence(root, path):
    if not isinstance(path, str):
        raise ValueError('actual local evidence path required')
    return snapshot_files(root, [path])[0]


def _evidence_document(root, snapshot):
    raw = (Path(root) / snapshot['path']).read_bytes()
    if sha256(raw).hexdigest() != snapshot['sha256']:
        raise ValueError('evidence changed while binding its observations')
    try:
        document = json.loads(raw.decode('utf-8-sig'))
    except (UnicodeError, ValueError) as error:
        raise ValueError('evidence needs saved JSON observations or actual native results') from error
    if not isinstance(document, dict):
        raise ValueError('saved evidence observation must be a JSON object')
    return document


def _bind_observation(document, expected, key, label):
    observed = document.get(key, document)
    if not isinstance(observed, dict) or any(observed.get(field) != wanted for field, wanted in expected.items()):
        raise ValueError('saved ' + label + ' evidence differs from supplied observations')


def _source_evidence(root, document, prefix):
    paths = document.get('source_evidence', [])
    if not isinstance(paths, list) or any(not isinstance(item, str) or not item for item in paths):
        raise ValueError('source_evidence must list actual local source paths')
    return {prefix + '_source_' + str(index): _evidence(root, path) for index, path in enumerate(paths, 1)}


def _receipt_evidence(root, receipt, policy):
    evidence = {key: _evidence(root, receipt.get(key)) for key in ('identity_evidence', 'send_evidence', 'readback_evidence')}
    documents = {key: _evidence_document(root, snapshot) for key, snapshot in evidence.items()}
    _bind_observation(documents['identity_evidence'], receipt['identity'], 'identity', 'identity')
    back = documents['readback_evidence']
    stored = back.get('readback_result', back)
    if _gmail_message(stored) != _gmail_message(receipt.get('readback_result')):
        raise ValueError('saved Gmail MIME readback differs from supplied native result')
    sent = documents['send_evidence']
    native = sent.get('send_result', sent)
    native = native.get('structuredContent', native) if isinstance(native, dict) else native
    native = native.get('message', native) if isinstance(native, dict) else native
    native_id = native.get('id') if isinstance(native, dict) else None
    if native_id is not None:
        if native_id != _gmail_message(receipt['readback_result'])['id']:
            raise ValueError('saved Gmail send and readback message IDs differ')
    else:
        required = {key: receipt[key] for key in ('candidate_id', 'attempt_id', 'target', 'account', 'recipient')}
        _bind_observation(sent, required, 'send_observation', 'send')
        observed = sent.get('send_observation', sent)
        if observed.get('outcome') not in {'submitted', 'uncertain'}:
            raise ValueError('saved send observation must record submitted or uncertain outcome')
        _text(observed.get('basis'), 'actual saved send observation basis')
    for key, document in documents.items():
        evidence.update(_source_evidence(root, document, key))
    return evidence


def mark_sending(root, payload, **revision):
    """Persist the uncertain-effect boundary, then grant one native-host send.

    The host must await success and act only on send_allowed:true. A replay or
    restart cannot obtain another grant. This cannot stop a host ignoring it.
    """
    observed = _evidence(root, payload.get('identity_evidence'))
    identity_document = _evidence_document(root, observed)
    _bind_observation(identity_document, payload.get('identity', {}), 'identity', 'identity')
    source_evidence = _source_evidence(root, identity_document, 'identity')
    frozen = {**deepcopy(payload), 'identity_snapshot': observed, 'source_evidence': source_evidence}
    authority = {}
    def update(value):
        delivery = _delivery(value, payload)
        if delivery['status'] in _UNRESOLVED:
            raise ValueError('uncertain external effect; reconcile before any retry')
        if delivery['status'] == 'SENT_VERIFIED':
            raise ValueError('delivery already verified; another send is not permitted')
        policy = validate_policy(delivery['policy'])
        authority['policy'] = policy
        authority['snapshot'] = _task_policy(root, policy, production=True)
        if policy.get('evidence_adapter') != 'gmail-api':
            raise ValueError('selected evidence adapter is unavailable; no native send grant')
        _reject_overlap(value, delivery['candidate_id'], policy, delivery['files'], exclude=delivery['id'])
        _same_identity(policy, payload.get('identity'))
        # Registry observations are historical. Fresh native account proof
        # supplements the same frozen endpoint without changing its identity.
        basis = payload['identity'].get('binding_basis')
        if basis not in {'stable-identifiers', 'native-self-entry'}:
            raise ValueError('fresh binding_basis must establish this exact Gmail account and self mailbox')
        issues = _delivery_issues(root, delivery)
        if issues:
            raise ValueError('delivery snapshot or prior evidence changed: ' + '; '.join(issues))
        attempt_id = _digest({'delivery_id': delivery['id'], 'number': len(delivery['attempts']) + 1})
        delivery['attempts'].append({'id': attempt_id, 'outcome': 'uncertain',
            'started_at_ns': time.time_ns(), 'identity': deepcopy(payload['identity']),
            'identity_evidence': observed, 'identity_sources': source_evidence,
            'authority': deepcopy(authority['snapshot']), 'observations': []})
        delivery['status'] = 'SENDING'
        return {'delivery_id': delivery['id'], 'attempt_id': attempt_id, 'status': 'SENDING',
                'send_allowed': True, 'files': deepcopy(delivery['files']), 'policy': deepcopy(policy)}
    def guard():
        if _task_policy(root, authority['policy'], production=True) != authority['snapshot']:
            raise ValueError('task delivery authority changed before returning the send reservation')
        snapshot_files(root, [observed, *source_evidence.values()])
    return _mutate(root, 'mark-sending', frozen, update, guard=guard, **revision)


def reconcile(root, payload, **revision):
    """Record sent, positively not-sent, or still-uncertain host evidence.

    Not finding a message in a search is not positive non-send evidence. A
    confirmed rejection/cancellation before submission can release the retry.
    """
    outcome = payload.get('outcome')
    if outcome not in {'sent', 'not_sent', 'uncertain'}:
        raise ValueError('reconciliation outcome must be sent, not_sent or uncertain')
    frozen = deepcopy(payload)
    if outcome == 'sent':
        receipt = payload.get('receipt')
        if not isinstance(receipt, dict):
            raise ValueError('sent reconciliation requires an actual receipt')
        selected = _delivery(_load(root), payload)
        evidence = _receipt_evidence(root, receipt, selected['policy'])
    else:
        evidence = {'outcome_evidence': _evidence(root, payload.get('evidence_path'))}
        document = _evidence_document(root, evidence['outcome_evidence'])
        _bind_observation(document, payload.get('evidence', {}), 'evidence', 'outcome')
        evidence.update(_source_evidence(root, document, 'outcome'))
    frozen['evidence_snapshots'] = evidence
    def update(value):
        delivery = _delivery(value, payload)
        if not delivery['attempts']:
            raise ValueError('no pre-send reservation exists for this delivery')
        attempt = delivery['attempts'][-1]
        if payload.get('attempt_id') != attempt['id']:
            raise ValueError('reconciliation must identify the exact current attempt')
        if outcome == 'sent':
            normalized = verify_receipt(delivery['policy'], delivery['files'], payload['receipt'],
                candidate_id=delivery['candidate_id'], attempt_id=attempt['id'])
            actual_evidence = _receipt_evidence(root, payload['receipt'], delivery['policy'])
            if actual_evidence != evidence:
                raise ValueError('receipt evidence changed before reconciliation commit')
            if delivery['status'] == 'SENT_VERIFIED':
                if normalized != attempt.get('receipt'):
                    raise ValueError('different receipt for an already verified send; inspect possible duplicate')
                proof_refresh = True
            elif delivery['status'] not in _UNRESOLVED:
                raise ValueError('sent receipt conflicts with the recorded attempt outcome')
            else:
                proof_refresh = False
            attempt.update(outcome='sent', receipt=normalized)
            delivery['status'] = 'SENT_VERIFIED'
        else:
            if delivery['status'] not in _UNRESOLVED:
                raise ValueError('only an unresolved attempt may be reconciled')
            observation = payload.get('evidence')
            if not isinstance(observation, dict):
                raise ValueError('reconciliation needs actual observed evidence facts')
            for field, expected in (('candidate_id', delivery['candidate_id']), ('target', delivery['policy']['target']),
                                    ('account', delivery['policy']['account']), ('recipient', delivery['policy']['recipient']),
                                    ('attempt_id', attempt['id'])):
                if observation.get(field) != expected:
                    raise ValueError('outcome evidence does not bind the exact ' + field)
            _text(observation.get('basis'), 'actual outcome observation basis')
            if outcome == 'not_sent':
                if observation.get('disposition') not in {'rejected-before-submit', 'cancelled-before-submit', 'provider-confirmed-not-accepted'}:
                    raise ValueError('positive non-send evidence required; search absence is insufficient')
                attempt['outcome'] = 'not_sent'; delivery['status'] = 'NOT_SENT'
            else:
                delivery['status'] = 'UNCERTAIN'
        attempt['observations'].append({'outcome': outcome, 'at_ns': time.time_ns(),
            'facts': deepcopy(payload.get('evidence')), 'evidence': deepcopy(actual_evidence if outcome == 'sent' else evidence)})
        return {'delivery_id': delivery['id'], 'attempt_id': attempt['id'], 'status': delivery['status'], 'send_allowed': False,
                **({'existing_receipt': True, 'proof_refreshed': True} if outcome == 'sent' and proof_refresh else {})}
    return _mutate(root, 'reconcile', frozen, update, **revision)


def inspect(root):
    """Return full immutable selections and evidence, including stale histories."""
    value = _load(Path(root).resolve())
    deliveries, unresolved = [], []
    for stored in value['deliveries'].values():
        delivery = deepcopy(stored); issues = _delivery_issues(root, delivery)
        history_issues = _delivery_issues(root, delivery, history=True)
        delivery.update(issues=issues, send_allowed=False,
            history_issues=history_issues,
            identity_digest=_digest({key: stored[key] for key in ('id', 'candidate_id', 'files', 'policy', 'authorization_source_ref')}),
            receipt_digest=_digest(stored['attempts'][-1]['receipt']) if stored['status'] == 'SENT_VERIFIED' else None,
            current_proof=deepcopy(_current_evidence(stored)),
            unresolved=stored['status'] in _UNRESOLVED,
            retry_allowed=stored['status'] == 'NOT_SENT' and not issues,
            recorded_status=stored['status'])
        if issues:
            delivery['status'] = 'STALE_OR_UNAVAILABLE'
        if delivery['unresolved']:
            unresolved.append(delivery['id'])
        deliveries.append(delivery)
    return {'format': FORMAT, 'revision': value['revision'], 'deliveries': deliveries,
            'unresolved_delivery_ids': unresolved, 'send_allowed': False,
            'status': 'UNCERTAIN' if unresolved else 'NO_DELIVERIES' if not deliveries else 'RECORDED',
            'fact_scope': 'local snapshots and host-selected evidence; no authenticated delivery or recipient-read proof'}


def completion_status(root, files, policy=None, *, candidate_id=None):
    """Check only selected final artifacts against complete verified deliveries.

    Other candidates' files cannot satisfy these bytes. Any unresolved attempt
    involving these same artifacts remains visible, including an earlier target.
    Unrelated artifact histories do not block this artifact-specific result.
    """
    root = Path(root).resolve()
    if policy is None and (root / 'session.json').exists():
        from .codex_session import task_delivery_policy
        policy = task_delivery_policy(root)
        if policy is None:
            raise ValueError('legacy pinned task has no X delivery completion contract')
    policy = validate_policy(policy) if policy is not None else None
    if policy is not None and policy['mode'] == 'local':
        return {'ready': True, 'status': 'LOCAL_ONLY', 'send_allowed': False,
                'verified_delivery_ids': [], 'missing_files': [], 'unresolved_delivery_ids': []}
    selected = snapshot_files(root, files)
    if not selected:
        return {'ready': True, 'status': 'NO_FILES', 'send_allowed': False,
                'verified_delivery_ids': [], 'missing_files': [], 'unresolved_delivery_ids': []}
    identity = lambda item: (item['filename'], item['bytes'], item['sha256'])
    wanted = {identity(item) for item in selected}
    verified, covered, unresolved, issues = [], set(), [], []
    for delivery in inspect(root)['deliveries']:
        actual = {identity(item) for item in delivery['files']}
        if not (wanted & actual) or (candidate_id is not None and candidate_id != delivery['candidate_id']):
            continue
        if delivery['unresolved']:
            unresolved.append(delivery['id'])
        if policy is not None and delivery['policy'] != policy:
            continue
        # A partly overlapping message with unrelated extra attachments cannot
        # satisfy an exact final selection, even if one filename happens to fit.
        if actual - wanted:
            continue
        if delivery['issues']:
            issues.extend(delivery['issues'])
        elif delivery['recorded_status'] == 'SENT_VERIFIED':
            verified.append(delivery['id']); covered.update(actual)
    missing = [item['filename'] for item in selected if identity(item) not in covered]
    return {'ready': not missing and not unresolved and not issues,
            'status': 'VERIFIED' if not missing and not unresolved and not issues else 'UNCERTAIN' if unresolved else 'DELIVERY_REQUIRED',
            'send_allowed': False, 'verified_delivery_ids': verified, 'missing_files': missing,
            'unresolved_delivery_ids': unresolved, 'issues': sorted(set(issues))}
