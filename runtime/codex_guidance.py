"""Source-bound public guidance; receipts do not certify semantic compliance."""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import closing
from hashlib import sha256
from pathlib import Path
import re
import sqlite3


def enabled(p_run: str) -> bool:
    match = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)@[a-f0-9]{40}', p_run)
    return bool(match and tuple(map(int, match.groups())) >= (0, 18, 0))


def input_ref(lifecycle: Mapping) -> dict:
    from .codex_lifecycle import content_message
    return _message_ref(content_message(lifecycle))


def _message_ref(source: Mapping) -> dict:
    return {'message_id': source['id'], 'sha256': source['source']['sha256'],
            'source_ref': source['source']['source_ref']}


def _legacy_identity(root: Path, session: Mapping, attempt: Mapping,
                     supplied: Mapping) -> dict:
    """Explicitly adopt a pre-0.18 source using its existing pre-call claim.

    Never write an identity into an old paid request. The independent local
    wallet row must already bind this session UUID and the actual request.
    This is source consistency, not authentication of a provider or operator.
    """
    from . import codex_wallet
    adoption = supplied.get('legacy_task_adoption')
    version = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)@[a-f0-9]{40}', session['P_run'])
    if (not version or not (0, 16, 0) <= tuple(map(int, version.groups())) < (0, 18, 0)
            or not isinstance(session.get('task_uuid'), str)
            or not re.fullmatch(r'[a-f0-9]{32}', session['task_uuid'])
            or not isinstance(adoption, Mapping)
            or adoption.get('basis') != 'PRECALL_WALLET_CLAIM'):
        raise ValueError('legacy guidance needs explicit adoption of an existing pre-call task UUID wallet claim')
    claim = attempt.get('wallet_claim')
    expected = codex_wallet.claim_id(root, session, attempt['exchange_id'])
    if (not isinstance(claim, Mapping) or claim.get('format') != codex_wallet.FORMAT
            or claim.get('claim_id') != expected or adoption.get('claim_id') != expected
            or claim.get('request_sha256') != attempt['request_sha256']):
        raise ValueError('legacy guidance wallet claim belongs to a different task UUID or request')
    ledger = codex_wallet.ledger_path()
    if Path(claim.get('ledger_path', '')).resolve() != ledger or not ledger.is_file():
        raise ValueError('legacy guidance requires its existing configured wallet ledger')
    try:
        with closing(sqlite3.connect(ledger.as_uri() + '?mode=ro', uri=True)) as db:
            row = db.execute('SELECT task_id,exchange_id,request_sha256,wallet_id,state FROM claims WHERE claim_id=?',
                             (expected,)).fetchone()
    except sqlite3.Error as error:
        raise ValueError('legacy guidance wallet source unavailable: ' + type(error).__name__) from None
    if (row is None or row[:4] != (codex_wallet.task_id(root, session), attempt['exchange_id'],
                                   attempt['request_sha256'], claim.get('wallet_id'))
            or row[4] not in {'COMMITTED', 'KNOWN'}):
        raise ValueError('legacy guidance has no committed same-task wallet source for this request')
    return {'basis': 'PRECALL_WALLET_CLAIM', 'claim_id': expected}


def public_receipt(root: Path, supplied: Mapping, *, current: bool = True) -> dict:
    """Verify an actual complete formal Claude exchange, never a caller's quote."""
    from .codex_consult import DEFAULT_MODEL, _load
    from .codex_lifecycle import require_active
    from .codex_session import _session
    root, session = _session(root)
    lifecycle = require_active(root)
    if not isinstance(supplied, Mapping):
        raise ValueError('guidance needs exchange_id and the actual public_sha256')
    exchange_id = supplied.get('exchange_id')
    if not isinstance(exchange_id, str) or not exchange_id:
        raise ValueError('guidance must identify a real exchange')
    directory, attempt, request = _load(root, exchange_id)
    legacy = None
    if enabled(session['P_run']):
        identity = {'kind': 'HASHED_REQUEST_TASK_UUID', 'task_uuid': session['task_uuid']}
    else:
        legacy = _legacy_identity(root, session, attempt, supplied)
        identity = {'kind': 'EXPLICIT_LEGACY_PRECALL_WALLET_CLAIM',
                    'task_uuid': session['task_uuid'], 'claim_id': legacy['claim_id']}
    if (attempt.get('participation_role') != 'consult_guidance'
            or request.get('model') != DEFAULT_MODEL
            or attempt.get('response_model') != DEFAULT_MODEL
            or attempt.get('transport_status') != 'RESPONDED'
            or attempt.get('public_status') != 'COMPLETE'
            or attempt.get('finish_reason') != 'stop'
            or attempt.get('http_status') != 200):
        raise ValueError('guidance requires a complete actual formal Claude public return')
    public = (directory / 'public.md').read_bytes()
    actual_hash = sha256(public).hexdigest()
    if (not public.strip() or supplied.get('public_sha256') != actual_hash
            or attempt.get('public_sha256') != actual_hash):
        raise ValueError('guidance public body/hash does not match the actual return')
    expected = input_ref(lifecycle)
    if current and attempt.get('input_ref') != expected:
        raise ValueError('new material interpretation needs guidance bound to the current input')
    receipt = {'exchange_id': exchange_id, 'public_sha256': actual_hash,
            'request_sha256': attempt['request_sha256'],
            'task_request_sha256': session['request_sha256'], 'P_run': session['P_run'],
            'task_identity': identity,
            'input_ref': attempt['input_ref'], 'model': attempt['response_model'],
            'participation_role': 'consult_guidance',
            'scope': 'verified public source and order; not semantic approval, user consent, or host-thinking attestation'}
    if legacy is not None:
        receipt['legacy_task_adoption'] = legacy
    return receipt


def covered_revision(root: Path, session: Mapping, supplied: Mapping | None,
                     *, previous: Mapping | None, brief: Mapping) -> dict | None:
    """Bind a reviewable coverage claim to actual sources, not a prose parser.

    These three categories apply a decision already supplied by the user,
    established facts, or a uniquely locked execution. There is intentionally
    no model-preference or 'pure engineering' exemption. Exact quotes/hashes
    establish what was selected; the operator still owns their true meaning.
    """
    if supplied is None:
        return None
    from .codex_foundation import BRIEF_FIELDS, _digest
    from .codex_collaboration import layered_policy
    from .codex_lifecycle import require_active
    if not enabled(session['P_run']):
        raise ValueError('covered revisions require the new task pin; old pins are not migrated')
    lifecycle = require_active(root)
    if (not isinstance(supplied, Mapping) or not previous
            or previous.get('status') != 'CONFIRMED' or not previous.get('confirmation')):
        raise ValueError('covered revision needs a current confirmed foundation; it cannot revive old authority')
    kind = supplied.get('kind')
    if kind not in {'DIRECT_USER_DECISION', 'ESTABLISHED_FACT', 'LOCKED_EXECUTION'}:
        raise ValueError('covered revision must identify a direct user decision, established fact, or locked execution')
    changed = sorted(key for key in BRIEF_FIELDS if previous['brief'].get(key) != brief.get(key))
    if (not changed or supplied.get('changed_fields') != changed
            or supplied.get('previous_brief_sha256') != previous['brief_sha256']
            or supplied.get('input_ref') != input_ref(lifecycle)):
        raise ValueError('covered revision must bind all actual changed fields, the preceding brief, and current input')
    if supplied.get('no_new_substantive_prior') is not True or supplied.get('no_new_user_choice') is not True:
        raise ValueError('new substantive priors or user choices require their actual current guidance/decision')
    message = lifecycle['current_message']
    if (layered_policy(session['P_run']) and kind == 'DIRECT_USER_DECISION'
            and (message.get('handling') or {}).get('action') == 'budget' and changed != ['resources']):
        raise ValueError('a budget-only reply can cover resource limits only')
    reason = supplied.get('reason')
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('covered revision needs the actual applicability reason')
    receipt = None
    quote = supplied.get('guidance_quote')
    if not layered_policy(session['P_run']) or previous.get('guidance_required'):
        receipt = public_receipt(root, previous.get('guidance'), current=False)
        directory = root / 'consult' / 'exchanges' / receipt['exchange_id']
        if not isinstance(quote, str) or not quote.strip() or quote not in (directory / 'public.md').read_text(encoding='utf-8'):
            raise ValueError('covered revision must quote the actual complete guidance rule it applies')
    elif quote is not None:
        raise ValueError('the prior decision has no formal guidance to quote')
    sources = supplied.get('sources')
    if not isinstance(sources, list) or not sources:
        raise ValueError('covered revision needs its actual decision/fact sources')
    selected = []
    for source in sources:
        if not isinstance(source, Mapping):
            raise ValueError('coverage source must identify selected actual bytes')
        source_quote = source.get('quote')
        if not isinstance(source_quote, str) or not source_quote.strip():
            raise ValueError('coverage source needs an exact relevant quote')
        if kind == 'DIRECT_USER_DECISION':
            if source.get('kind') != 'CURRENT_USER_INPUT' or source_quote not in message['source']['text']:
                raise ValueError('direct user decision must quote the actual current user input')
            selected.append({'kind': 'CURRENT_USER_INPUT', 'input_ref': _message_ref(message), 'quote': source_quote})
        else:
            if source.get('kind') != 'ACTUAL_ARTIFACT' or not isinstance(source.get('path'), str) or not source['path'].strip():
                raise ValueError('established fact/locked execution needs an actual selected artifact')
            path = Path(source['path']).resolve()
            raw = path.read_bytes()
            if sha256(raw).hexdigest() != source.get('sha256') or source_quote not in raw.decode('utf-8-sig'):
                raise ValueError('coverage artifact hash/quote does not match selected bytes')
            selected.append({'kind': 'ACTUAL_ARTIFACT', 'path': path.as_posix(),
                             'sha256': source['sha256'], 'quote': source_quote})
    return {'kind': kind, 'input_ref': input_ref(lifecycle), 'changed_fields': changed,
            'previous_brief_sha256': previous['brief_sha256'], 'brief_sha256': _digest(brief),
            'guidance': receipt, 'guidance_quote': quote, 'sources': selected, 'reason': reason,
            'no_new_substantive_prior': True, 'no_new_user_choice': True,
            'scope': 'operator-declared applicability; exact source/order checks do not certify meaning or truth'}


def for_proposal(root: Path, session: Mapping, supplied: Mapping | None,
                 *, previous: Mapping | None, material: bool,
                 covered_change: Mapping | None = None,
                 guidance_required: bool = False) -> dict | None:
    from .codex_collaboration import layered_policy
    from .codex_lifecycle import load_lifecycle
    if not enabled(session['P_run']):
        return None  # Immutable old pins retain their original entry semantics.
    lifecycle = load_lifecycle(root)
    if layered_policy(session['P_run']):
        if not guidance_required:
            return None
        if covered_change is not None:
            return covered_change['guidance']
        if supplied is None:
            # A draft may identify the concrete dependency before the source
            # has arrived. This never approves the dependent scope.
            retained = (previous or {}).get('guidance') if not material else None
            return public_receipt(root, retained, current=False) if retained else None
        if lifecycle.get('claude_policy', {}).get('mode') != 'ALLOW':
            raise ValueError('current task choice does not allow a new formal content-guidance decision')
        existing = (previous or {}).get('guidance')
        if previous and not material and (not existing or not isinstance(supplied, Mapping)
                or supplied.get('exchange_id') != existing['exchange_id']
                or supplied.get('public_sha256') != existing['public_sha256']):
            raise ValueError('changing the selected formal guidance needs a material revision')
        receipt = public_receipt(root, supplied, current=material or previous is None)
        if material and previous:
            versions = [previous, previous.get('accepted') or {}, *previous['history']]
            if any((revision.get('guidance') or {}).get('exchange_id') == receipt['exchange_id']
                   for revision in versions):
                raise ValueError('a new substantive prior needs new current guidance or a source-bound covered revision')
        return receipt
    if lifecycle.get('claude_policy', {}).get('mode') != 'ALLOW':
        return None
    if covered_change is not None:
        return covered_change['guidance']
    candidate = supplied or (previous or {}).get('guidance')
    receipt = public_receipt(root, candidate, current=material)
    if (material and previous and previous.get('guidance')
            and receipt['exchange_id'] == previous['guidance'].get('exchange_id')):
        raise ValueError('a new substantive prior needs a new current complete exchange; declare a source-bound covered revision for unchanged priors')
    return receipt
