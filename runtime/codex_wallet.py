"""Short, durable reservations shared by every managed task and wallet.

The account alias is explicit configuration, never an API-key fingerprint.
Only participating local clients are covered; external usage remains a supplied
fact. A reservation survives a crash before an attempt record is committed.
"""
from __future__ import annotations

from contextlib import closing, contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import os
import math
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

FORMAT = 'digr-shared-wallet-1'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ledger_path() -> Path:
    home = os.environ.get('CODEX_HOME')
    if not home or not Path(home).is_absolute():
        raise ValueError('Shared wallet requires an explicit absolute CODEX_HOME; no per-task budget fallback')
    return Path(home).resolve() / 'digr-codex' / 'wallet-ledger.sqlite3'


def task_id(root: Path, session: Mapping[str, Any]) -> str:
    identity = session.get('task_uuid')
    if identity is not None:
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError('Frozen task UUID must be nonempty text')
        frozen = {'task_uuid': identity, 'P_run': session['P_run'], 'request_sha256': session['request_sha256']}
    else:
        # Legacy records have no UUID. Use only their frozen metadata; moving
        # or restoring a root must never manufacture a fresh spending identity.
        frozen = {key: session.get(key) for key in
                  ('P_run', 'request_sha256', 'created_wall_ns', 'request_origin')}
    return sha256(json.dumps(frozen, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def claim_id(root: Path, session: Mapping[str, Any], exchange_id: str) -> str:
    return sha256((task_id(root, session) + '\0' + exchange_id).encode('utf-8')).hexdigest()


@contextmanager
def _transaction(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        db = sqlite3.connect(path, timeout=15, isolation_level=None)
    except sqlite3.Error as error:
        raise ValueError('Shared wallet open failed: ' + type(error).__name__ + '; no local budget fallback') from None
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('BEGIN IMMEDIATE')
        db.execute('''CREATE TABLE IF NOT EXISTS claims (
            claim_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, wallet_id TEXT NOT NULL,
            exchange_id TEXT NOT NULL, request_sha256 TEXT NOT NULL,
            state TEXT NOT NULL, ceiling_usd REAL NOT NULL, known_cost_usd REAL,
            reserved_at TEXT NOT NULL, cost_observed_at TEXT, committed_at TEXT,
            account_authorization_ref TEXT)''')
        columns = {row['name'] for row in db.execute('PRAGMA table_info(claims)')}
        for name, declaration in (('cost_revision', 'INTEGER NOT NULL DEFAULT 0'),
                                  ('cost_first_observed_at', 'TEXT'), ('last_cost_checked_at', 'TEXT')):
            if name not in columns:
                db.execute('ALTER TABLE claims ADD COLUMN ' + name + ' ' + declaration)
        db.execute('''CREATE TABLE IF NOT EXISTS cost_events (
            claim_id TEXT NOT NULL, revision INTEGER NOT NULL, previous_cost_usd REAL NOT NULL,
            known_cost_usd REAL NOT NULL, delta_usd REAL NOT NULL, observed_at TEXT NOT NULL,
            PRIMARY KEY(claim_id, revision))''')
        db.execute('''CREATE TABLE IF NOT EXISTS snapshots (
            wallet_id TEXT NOT NULL, snapshot_id TEXT NOT NULL, body TEXT NOT NULL,
            first_recorded_at TEXT NOT NULL, PRIMARY KEY(wallet_id,snapshot_id))''')
        yield db
        db.execute('COMMIT')
    except sqlite3.Error as error:
        if db.in_transaction:
            db.execute('ROLLBACK')
        raise ValueError('Shared wallet transaction failed: ' + type(error).__name__ + '; no local budget fallback') from None
    except BaseException:
        if db.in_transaction:
            db.execute('ROLLBACK')
        raise
    finally:
        db.close()


def _totals(rows) -> dict:
    rows = list(rows)
    return {'known_cost_usd': sum(row['known_cost_usd'] for row in rows if row['state'] == 'KNOWN'),
            'unresolved_reserved_usd': sum(row['ceiling_usd'] for row in rows
                                          if row['state'] in {'RESERVED', 'COMMITTED'}),
            'unresolved_exchanges': [row['exchange_id'] for row in rows
                                     if row['state'] in {'RESERVED', 'COMMITTED'}]}


def _has_table(db, name: str) -> bool:
    return db is not None and db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _availability(db, task_rows, wallet_rows, wallet_id: str, budget: Mapping[str, Any], *,
                  save_snapshot: bool) -> dict:
    task_totals, wallet_totals = _totals(task_rows), _totals(wallet_rows)
    total = budget['budget_total_usd']
    task_available = (None if total is None else total - budget['outside_spent_usd']
                      - budget['outside_reserved_usd'] - task_totals['known_cost_usd']
                      - task_totals['unresolved_reserved_usd'])
    snapshot = budget.get('wallet_snapshot')
    covered = {}
    if snapshot is not None:
        if (not isinstance(snapshot, Mapping) or set(snapshot) != {'snapshot_id', 'wallet_id', 'covered_claims'}
                or not isinstance(snapshot['snapshot_id'], str) or not snapshot['snapshot_id'].strip()
                or snapshot['wallet_id'] != wallet_id or not isinstance(snapshot['covered_claims'], Mapping)):
            raise ValueError('Wallet snapshot needs its ID, matching wallet_id and confirmed covered claim revisions')
        normalized = {'wallet_remaining_usd': budget['wallet_remaining_usd'], **dict(snapshot)}
        body = json.dumps(normalized, sort_keys=True, separators=(',', ':'), allow_nan=False)
        previous = db.execute('SELECT body FROM snapshots WHERE wallet_id=? AND snapshot_id=?',
                              (wallet_id, snapshot['snapshot_id'])).fetchone() if _has_table(db, 'snapshots') else None
        if previous and previous['body'] != body:
            raise ValueError('An immutable wallet snapshot cannot change balance or confirmed coverage')
        current_claims = {row['claim_id']: row for row in wallet_rows}
        has_events = _has_table(db, 'cost_events')
        for identity_key, entry in snapshot['covered_claims'].items():
            if not isinstance(entry, Mapping) or set(entry) != {'cost_revision', 'covered_cost_usd'}:
                raise ValueError('Snapshot coverage must identify a cost revision and its confirmed covered amount')
            revision, amount = entry['cost_revision'], entry['covered_cost_usd']
            if (type(revision) is not int or revision < 1 or type(amount) not in (int, float)
                    or not math.isfinite(amount) or amount < 0 or identity_key not in current_claims):
                raise ValueError('Invalid wallet snapshot claim coverage')
            event = db.execute('SELECT known_cost_usd FROM cost_events WHERE claim_id=? AND revision=?',
                               (identity_key, revision)).fetchone() if has_events else None
            if event is None or amount > event['known_cost_usd'] + 1e-12:
                raise ValueError('Snapshot coverage is not bound to an actual observed cost revision')
            covered[identity_key] = float(amount)
        if save_snapshot and previous is None:
            db.execute('INSERT INTO snapshots VALUES (?,?,?,?)', (wallet_id, snapshot['snapshot_id'], body, _now()))
    # Recency is separate from coverage. Deduct unresolved holds and any cost
    # or revision delta not explicitly confirmed in the provider balance.
    uncovered = sum(max(row['known_cost_usd'] - covered.get(row['claim_id'], 0.0), 0.0)
                    for row in wallet_rows if row['state'] == 'KNOWN')
    available = (budget['wallet_remaining_usd'] - uncovered
                 - wallet_totals['unresolved_reserved_usd'] - budget['outside_reserved_usd'])
    account_available = None
    if 'account_budget_total_usd' in budget:
        account_ref = budget.get('account_authorization_ref')
        totals = _totals(row for row in wallet_rows if row['account_authorization_ref'] == account_ref)
        account_available = (budget['account_budget_total_usd'] - budget.get('account_outside_spent_usd', 0)
                             - budget.get('account_outside_reserved_usd', 0)
                             - totals['known_cost_usd'] - totals['unresolved_reserved_usd'])
    return {'task_available_before_usd': task_available, 'wallet_available_before_usd': available,
            'account_available_before_usd': account_available,
            'wallet_snapshot_id': snapshot['snapshot_id'] if snapshot is not None else None,
            'known_uncovered_usd': uncovered,
            'coverage_basis': 'explicit confirmed cost revisions' if snapshot is not None else 'no confirmed coverage; covered amount zero'}


def review_capacity(root: Path, session: Mapping[str, Any], *, wallet_id: str,
                    budgets: list[Mapping[str, Any]]) -> list[dict]:
    """Price preview reads one consistent ledger view without creating claims or schema."""
    path, task = ledger_path(), task_id(root, session)
    if not path.is_file():
        return [_availability(None, [], [], wallet_id, budget, save_snapshot=False) for budget in budgets]
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=15)) as db:
            db.row_factory = sqlite3.Row
            db.execute('BEGIN')
            has_claims = _has_table(db, 'claims')
            task_rows = list(db.execute('SELECT * FROM claims WHERE task_id=?', (task,))) if has_claims else []
            wallet_rows = list(db.execute('SELECT * FROM claims WHERE wallet_id=?', (wallet_id,))) if has_claims else []
            return [_availability(db, task_rows, wallet_rows, wallet_id, budget, save_snapshot=False)
                    for budget in budgets]
    except sqlite3.Error as error:
        raise ValueError('Shared wallet read failed: ' + type(error).__name__ + '; no local budget fallback') from None


def reserve(root: Path, session: Mapping[str, Any], *, exchange_id: str, request_sha256: str,
            wallet_id: str, budget: Mapping[str, Any]) -> dict:
    from .codex_collaboration import layered_policy
    if not isinstance(wallet_id, str) or not wallet_id.strip():
        raise ValueError('New DIGR submissions require an explicit shared wallet_id in the private config')
    if budget['budget_total_usd'] is None and not layered_policy(session['P_run']):
        raise ValueError('Wallet-only accounting requires the Stable task policy')
    path, task = ledger_path(), task_id(root, session)
    identity = claim_id(root, session, exchange_id)
    with _transaction(path) as db:
        if db.execute('SELECT 1 FROM claims WHERE claim_id=?', (identity,)).fetchone():
            raise ValueError('Shared wallet already claimed this exchange; inspect/recover without repeating inference')
        task_rows = list(db.execute('SELECT * FROM claims WHERE task_id=?', (task,)))
        wallet_rows = list(db.execute('SELECT * FROM claims WHERE wallet_id=?', (wallet_id,)))
        availability = _availability(db, task_rows, wallet_rows, wallet_id, budget, save_snapshot=True)
        account_ref = budget.get('account_authorization_ref')
        ceiling = budget['ceiling_usd']
        limits = [availability[key] for key in ('task_available_before_usd', 'wallet_available_before_usd',
                                                'account_available_before_usd') if availability[key] is not None]
        if ceiling > min(limits) + 1e-12:
            raise ValueError('Shared wallet reservation exceeds remaining task/account/wallet budget')
        db.execute('''INSERT INTO claims
            (claim_id,task_id,wallet_id,exchange_id,request_sha256,state,ceiling_usd,reserved_at,account_authorization_ref)
            VALUES (?,?,?,?,?,'RESERVED',?,?,?)''',
            (identity, task, wallet_id, exchange_id, request_sha256, ceiling, _now(), account_ref))
    return {'format': FORMAT, 'claim_id': identity, 'ledger_path': path.as_posix(),
            'wallet_id': wallet_id, 'request_sha256': request_sha256,
            **availability,
            'scope': 'atomic participating local clients; external wallet and authorization facts supplied separately'}


def update(receipt: Mapping[str, Any], *, state: str, cost: float | None = None,
           cost_observed_at: str | None = None) -> dict:
    if state not in {'COMMITTED', 'KNOWN', 'ABORTED'}:
        raise ValueError('Unknown shared wallet transition')
    if state == 'KNOWN' and (type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0
                            or not isinstance(cost_observed_at, str)):
        raise ValueError('Shared wallet settlement needs a finite observed cost and its timestamp')
    with _transaction(Path(receipt['ledger_path'])) as db:
        row = db.execute('SELECT * FROM claims WHERE claim_id=?', (receipt['claim_id'],)).fetchone()
        if not row or row['request_sha256'] != receipt['request_sha256']:
            raise ValueError('Shared wallet claim identity changed')
        if state == 'ABORTED' and row['state'] != 'RESERVED':
            raise ValueError('Only a proven unsent reservation can be released')
        if state == 'COMMITTED' and row['state'] != 'RESERVED':
            raise ValueError('Shared wallet claim has already passed its send boundary')
        if state == 'KNOWN' and row['state'] == 'ABORTED':
            raise ValueError('An unsent reservation cannot acquire a provider invoice')
        revision = row['cost_revision']
        first_observed = row['cost_first_observed_at']
        observed = row['cost_observed_at']
        if state == 'KNOWN':
            if row['state'] != 'KNOWN' or abs(row['known_cost_usd'] - cost) > 1e-12:
                revision += 1
                prior = row['known_cost_usd'] if row['state'] == 'KNOWN' else 0.0
                db.execute('INSERT INTO cost_events VALUES (?,?,?,?,?,?)',
                    (receipt['claim_id'], revision, prior, cost, cost - prior, cost_observed_at))
                observed = cost_observed_at
                first_observed = first_observed or observed
            elif revision == 0:
                # Preserve an earlier candidate's observation rather than
                # pretending its reread first incurred the original charge.
                revision = 1
                first_observed = observed
                db.execute('INSERT INTO cost_events VALUES (?,?,?,?,?,?)',
                           (receipt['claim_id'], revision, 0.0, cost, cost, observed))
            checked = _now()
        else:
            checked = row['last_cost_checked_at']
        db.execute('UPDATE claims SET state=?,known_cost_usd=?,cost_observed_at=?,committed_at=? WHERE claim_id=?',
                   (state, cost if state == 'KNOWN' else None,
                    observed if state == 'KNOWN' else None,
                    _now() if state == 'COMMITTED' else row['committed_at'], receipt['claim_id']))
        db.execute('UPDATE claims SET cost_revision=?,cost_first_observed_at=?,last_cost_checked_at=? WHERE claim_id=?',
                   (revision, first_observed, checked, receipt['claim_id']))
    return {'cost_revision': revision, 'cost_first_observed_at': first_observed,
            'cost_observed_at': observed, 'last_cost_checked_at': checked}


def inspect_task(root: Path, session: Mapping[str, Any]) -> dict:
    """Read canonical task claims once, without credentials or creating files."""
    try:
        path = ledger_path()
    except ValueError:
        return {'format': FORMAT, 'status': 'UNCONFIGURED', 'claims': []}
    if not path.is_file():
        return {'format': FORMAT, 'status': 'ABSENT', 'claims': []}
    try:
        db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=15)
    except sqlite3.Error as error:
        raise ValueError('Shared wallet open failed: ' + type(error).__name__ + '; no local budget fallback') from None
    db.row_factory = sqlite3.Row
    try:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='claims'").fetchone():
            # Another process may have created the file but not committed its
            # first schema/reservation yet. reserve() rechecks under its writer
            # transaction, so this read cannot authorize a conflicting spend.
            return {'format': FORMAT, 'status': 'ABSENT', 'claims': []}
        rows = list(db.execute('SELECT * FROM claims WHERE task_id=? ORDER BY reserved_at', (task_id(root, session),)))
        has_events = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cost_events'").fetchone()
        events = list(db.execute('''SELECT cost_events.* FROM cost_events JOIN claims USING(claim_id)
            WHERE claims.task_id=? ORDER BY cost_events.observed_at,cost_events.revision''',
            (task_id(root, session),))) if has_events else []
    except sqlite3.Error as error:
        raise ValueError('Shared wallet read failed: ' + type(error).__name__ + '; no local budget fallback') from None
    finally:
        db.close()
    claims = [{**dict(row), 'reserved_usd': row['ceiling_usd']
               if row['state'] in {'RESERVED', 'COMMITTED'} else 0.0} for row in rows]
    return {'format': FORMAT, 'status': 'READ', 'ledger_path': path.as_posix(),
            'claims': claims, 'cost_events': [dict(event) for event in events], 'totals': _totals(rows),
            'scope': 'canonical reservations include crashes before ATTEMPTED; not an external provider invoice'}
