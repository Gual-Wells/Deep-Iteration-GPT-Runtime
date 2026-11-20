"""Task-scoped aggregate usage, with explicit denominators and billing states.

Only selected native aggregate events are projected. Message bodies, reasoning
content, credentials and arbitrary provider payloads are never retained. This
module does not call a model, discover other chats, or convert credits into a
subscription allowance. Account changes and task attribution remain distinct.
"""
from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Mapping
import uuid

FORMAT = 'digr-codex-usage-1'
PRICING_SOURCE = 'https://learn.chatgpt.com/docs/pricing'
# Public credit rates are a relative-work proxy, NOT a subscription conversion.
# No effort multiplier: actual output already includes the measured reasoning.
PROXY_RATES = {
    'gpt-6.2-astra': (200, 10, 1000), 'gpt-6-astra': (250, 25, 1250),
    'gpt-6.2-sol': (50, 2.5, 250), 'gpt-6.1-sol': (50, 2.5, 250),
    'gpt-6.1-terra': (25, 1.25, 125), 'gpt-6-sol': (50, 5, 250),
    'gpt-6-luna': (2.5, .25, 12.5), 'gpt-5.6-sol': (100, 10, 500),
    'gpt-5.6-terra': (50, 5, 300), 'gpt-5.6-luna': (5, .5, 30),
}
_NATIVE_TYPES = {'session_meta', 'turn_context', 'token_usage_record', 'event_msg'}
_METHODS = {'thread/tokenUsage/updated', 'account/rateLimits/updated', 'model/rerouted'}
_LABELS = {'model': ('model',), 'effort': ('effort', 'reasoning_effort', 'reasoningEffort'),
           'speed': ('speed', 'service_tier', 'serviceTier')}
_LABEL_SCOPE = 'thread_and_turn'
_TOKENS = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
           'output_tokens', 'reasoning_output_tokens', 'total_tokens')
_PREFIX = r'^\s*\{(?:(?:\s*"timestamp"\s*:\s*"[^"]*"|\s*"ordinal"\s*:\s*\d+|\s*"jsonrpc"\s*:\s*"[^"]*")\s*,)*'
_TOP = re.compile(_PREFIX + r'\s*"type"\s*:\s*"([^"]+)"')
_METHOD = re.compile(_PREFIX + r'\s*"method"\s*:\s*"([^"]+)"')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _time(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError('usage timestamps must be ISO strings with a timezone')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('usage timestamps require a timezone')
    return parsed.astimezone(timezone.utc).isoformat()


def _key(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _number(value: Any) -> float | None:
    return float(value) if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError(f'usage object required: {path}')
    return value


def _folder(root: Path) -> Path:
    root = Path(root).resolve()
    if not (root / 'session.json').is_file():
        raise ValueError('usage root must be an existing DIGR task')
    path = root / 'usage'
    if path.is_symlink():
        raise ValueError('usage directory must belong to the selected task')
    return path


def _ledger(root: Path) -> dict:
    path = _folder(root) / 'observations.json'
    if not path.exists():
        return {'format': FORMAT, 'events': {}, 'observations': {}, 'snapshots': {},
                'imports': {}, 'notices': [], 'source_gaps': {}}
    value = _read(path)
    if value.get('format') != FORMAT:
        raise ValueError('unsupported usage observations')
    value.setdefault('observations', dict(value['events']))
    value.setdefault('source_gaps', {})
    return value


@contextmanager
def _writer(root: Path):
    folder = _folder(root)
    folder.mkdir(exist_ok=True)
    lock = folder / '.writer.lock'
    # A short projection transaction, never held across network or model work.
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, str(os.getpid()).encode('ascii'))
        yield folder
    finally:
        os.close(descriptor)
        lock.unlink()


def _save(folder: Path, data: Mapping[str, Any]) -> None:
    pending = folder / ('observations.new-' + uuid.uuid4().hex)
    try:
        pending.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                      indent=2, allow_nan=False) + '\n', encoding='utf-8')
        pending.replace(folder / 'observations.json')
    finally:
        pending.unlink(missing_ok=True)


def normalize_tokens(raw: Mapping[str, Any], *, reasoning_in_output: bool = True) -> dict:
    """Project overlapping token categories once; reject contradictory totals."""
    aliases = {
        'input_tokens': ('input_tokens', 'inputTokens', 'prompt_tokens'),
        'cached_input_tokens': ('cached_input_tokens', 'cachedInputTokens'),
        'cache_write_input_tokens': ('cache_write_input_tokens', 'cacheWriteInputTokens'),
        'output_tokens': ('output_tokens', 'outputTokens', 'completion_tokens'),
        'reasoning_output_tokens': ('reasoning_output_tokens', 'reasoningOutputTokens'),
        'total_tokens': ('total_tokens', 'totalTokens'),
    }
    result = {}
    for target, names in aliases.items():
        supplied = next((raw[name] for name in names if name in raw), None)
        if supplied is not None and (type(supplied) is not int or supplied < 0):
            raise ValueError('token counts must be nonnegative integers')
        result[target] = supplied
    for target, nested, key in (
        ('cached_input_tokens', 'prompt_tokens_details', 'cached_tokens'),
        ('reasoning_output_tokens', 'completion_tokens_details', 'reasoning_tokens'),
    ):
        if result[target] is None and isinstance(raw.get(nested), Mapping):
            supplied = raw[nested].get(key)
            if supplied is not None:
                if type(supplied) is not int or supplied < 0:
                    raise ValueError('nested token counts must be nonnegative integers')
                result[target] = supplied
    if result['input_tokens'] is None or result['output_tokens'] is None:
        raise ValueError('aggregate input and output token counts are required')
    cached = result['cached_input_tokens']
    reasoning = result['reasoning_output_tokens']
    if cached is not None and cached > result['input_tokens']:
        raise ValueError('cached input is a subset of input')
    if not reasoning_in_output:
        if reasoning is None:
            raise ValueError('separate reasoning output requires its aggregate count')
        result['output_tokens'] += reasoning
    elif reasoning is not None and reasoning > result['output_tokens']:
        raise ValueError('reasoning output is a subset of output')
    result['reported_total_tokens'] = result['total_tokens']
    result['total_tokens'] = result['input_tokens'] + result['output_tokens']
    result['reasoning_in_output'] = True
    result['cached_in_input'] = True
    return result


def _rate_rows(raw: Mapping[str, Any], timestamp: str, *, account: str,
               boundary: str = 'observed') -> list[dict]:
    # Prefer the multi-bucket view; never add its backward-compatible alias.
    container = raw.get('result', raw.get('params', raw))
    by_id = container.get('rateLimitsByLimitId', container.get('rate_limits_by_limit_id'))
    if isinstance(by_id, Mapping):
        buckets = [(key, value) for key, value in by_id.items() if isinstance(value, Mapping)]
    else:
        bucket = container.get('rateLimits', container.get('rate_limits', container))
        buckets = [(bucket.get('limitId', bucket.get('limit_id', 'unknown')), bucket)] if isinstance(bucket, Mapping) else []
    result = []
    for identity, bucket in buckets:
        plan = bucket.get('planType', bucket.get('plan_type', container.get('planType')))
        for slot in ('primary', 'secondary'):
            window = bucket.get(slot)
            if not isinstance(window, Mapping):
                continue
            used = _number(window.get('usedPercent', window.get('used_percent')))
            minutes = _number(window.get('windowDurationMins', window.get('window_minutes')))
            reset = _number(window.get('resetsAt', window.get('resets_at')))
            if used is None or used > 100 or minutes is None or minutes <= 0:
                continue
            result.append({'at': timestamp, 'account': account,
                'limit_id': str(bucket.get('limitId', bucket.get('limit_id', identity))),
                'limit_name': _text(bucket.get('limitName', bucket.get('limit_name'))),
                'plan_type': _text(plan), 'window_minutes': minutes, 'slot': slot,
                'used_percent': used, 'resets_at': reset, 'boundary': boundary})
    return result


def _safe_lines(path: Path):
    """Skip content-bearing record types before decoding their JSON payloads."""
    with path.open(encoding='utf-8-sig') as stream:
        for line in stream:
            top = _TOP.match(line)
            method = _METHOD.match(line)
            if top and top[1] in _NATIVE_TYPES:
                if top[1] == 'event_msg' and not re.search(
                    r'"payload"\s*:\s*\{\s*"type"\s*:\s*"(?:token_count|token_usage_record)"', line):
                    continue
            elif not (method and method[1] in _METHODS):
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue  # A live file may end in an incomplete aggregate row.
            if isinstance(event, dict):
                yield event


def _counter_range(cumulative: Mapping[str, Any] | None, tokens: Mapping[str, Any]) -> tuple[int | None, int | None]:
    if not isinstance(cumulative, Mapping):
        return None, None
    end = cumulative.get('total_tokens', cumulative.get('totalTokens'))
    if type(end) is not int or end < tokens['total_tokens']:
        return None, None
    return end - tokens['total_tokens'], end


def _left_ranges(start: int, end: int, covered: list[tuple[int, int]]) -> list[tuple[int, int]]:
    remaining = [(start, end)]
    for left, right in covered:
        parts = []
        for a, b in remaining:
            if right <= a or left >= b:
                parts.append((a, b))
            else:
                if a < left:
                    parts.append((a, left))
                if right < b:
                    parts.append((right, b))
        remaining = parts
    return remaining


def _native_id(payload: Mapping[str, Any], field: str) -> str | None:
    return _text(payload.get(field + '_id')) or _text(payload.get(field + 'Id'))


def _labels(payload: Mapping[str, Any]) -> dict:
    return {key: next((payload[name] for name in aliases if _text(payload.get(name))), None)
            for key, aliases in _LABELS.items()}


def _metadata(payload: Mapping[str, Any], context: Mapping[str, Any],
              caller: Mapping[str, str | None]) -> tuple[dict, dict]:
    actual = _labels(payload)
    result, sources = {}, {}
    for key in _LABELS:
        if actual[key] is not None:
            result[key], sources[key] = actual[key], {'rank': 4, 'basis': 'response_payload'}
        elif context.get(key) is not None:
            result[key], sources[key] = context[key], context['metadata_sources'][key]
        else:
            result[key] = caller[key]
            sources[key] = {'rank': 1, 'basis': 'caller_fill'} if caller[key] else {'rank': 0, 'basis': 'unavailable'}
    return result, sources


def _limits(value: Any) -> list[str] | None:
    return sorted(set(value)) if isinstance(value, list) and all(isinstance(item, str) and item for item in value) else None


def _metadata_candidates(row: dict, key: str) -> list[dict]:
    prior = row.get('metadata_candidates', {}).get(key)
    if prior is not None:
        return prior
    value = row.get(key)
    source = row.get('metadata_sources', {}).get(key, {})
    return ([{'value': value, 'rank': source.get('rank', 2),
              'basis': source.get('basis', 'legacy_attribution')}] if value is not None else [])


def _merge_observation(old: dict | None, row: dict, notices: list[str]) -> dict:
    if old is None:
        ids = row.get('metered_limit_ids')
        row.setdefault('metered_limit_candidates', ([{'ids': ids,
            'rank': row.get('metered_limit_source', {}).get('rank', 2)}] if ids is not None else []))
        return row
    if old['tokens'] != row['tokens']:
        raise ValueError('conflicting usage for one native aggregate; investigate instead of double counting')
    merged = {**old, **row}
    merged['actors'] = sorted(set(old.get('actors', [old['actor']]) + row.get('actors', [row['actor']])))
    merged['metadata_sources'] = dict(row['metadata_sources'])
    candidates, conflicts = {}, []
    scoped_reimport = old.get('label_scope') != _LABEL_SCOPE and row.get('label_scope') == _LABEL_SCOPE
    for key in (*_LABELS, 'account'):
        values = list(_metadata_candidates(old, key))
        if scoped_reimport and key in _LABELS:
            # The legacy rolling context could attach another turn's labels.
            # Keep only an identifiable payload value; recover any other
            # evidence by replaying the original, selected native records.
            prior_source = old.get('metadata_sources', {}).get(key, {})
            values = ([{'value': old[key], 'rank': 4, 'basis': 'response_payload'}]
                      if prior_source.get('basis') == 'response_payload' and old.get(key) is not None else [])
        for item in _metadata_candidates(row, key):
            if item not in values:
                values.append(item)
        candidates[key] = values
        if values:
            rank = max(item['rank'] for item in values)
            strongest = [item for item in values if item['rank'] == rank]
            actual = {item['value'] for item in strongest}
            merged[key] = next(iter(actual)) if len(actual) == 1 else None
            merged['metadata_sources'][key] = {'rank': rank, 'basis':
                strongest[-1].get('basis', 'legacy_attribution') if len(actual) == 1 else 'conflicting_observations'}
            if old.get(key) != merged[key]:
                notices.append('later metadata corrected or suspended an earlier ' + key + ' attribution')
            if len(actual) != 1:
                conflicts.append(key)
                notices.append('contradictory equally strong ' + key + ' metadata; attribution is unknown')
    merged['metadata_candidates'] = candidates
    merged['metadata_conflicts'] = conflicts
    eligibility = list(old.get('metered_limit_candidates', []))
    for source in (old, row):
        ids = source.get('metered_limit_ids')
        source_candidates = source.get('metered_limit_candidates', [])
        if not source_candidates and ids is not None:
            source_candidates = [{'ids': ids, 'rank': source.get('metered_limit_source', {}).get('rank', 2)}]
        for candidate in source_candidates:
            if candidate not in eligibility:
                eligibility.append(candidate)
    merged['metered_limit_candidates'] = eligibility
    if eligibility:
        strongest = max(candidate['rank'] for candidate in eligibility)
        alternatives = {tuple(candidate['ids']) for candidate in eligibility if candidate['rank'] == strongest}
        merged['metered_limit_conflict'] = len(alternatives) != 1
        merged['metered_limit_ids'] = list(next(iter(alternatives))) if len(alternatives) == 1 else None
        if merged['metered_limit_conflict']:
            notices.append('conflicting metered-bucket eligibility; pp allocation is unavailable')
    return merged


def _reconcile_observations(observations: list[dict]) -> tuple[dict, list[str]]:
    """Union counter coverage; exact records replace only proved aliases.

    A partial exact projection does not stand for an entire turn. Scalar
    residuals preserve total-token conservation when category splits cannot be
    identified from overlapping evidence.
    """
    result, notices = {}, []
    domains = defaultdict(list)
    for row in observations:
        domains[(row.get('account'), row['thread_id'], row.get('counter_epoch', 0))].append(row)
    for rows in domains.values():
        exact = [row for row in rows if row['basis'] == 'native_response_aggregate']
        fallback = [row for row in rows if row['basis'] != 'native_response_aggregate']
        covered, accepted = [], []
        for row in exact:
            start, end = row.get('counter_start'), row.get('counter_end')
            if start is None or end is None:
                if fallback:
                    notices.append('exact response without cumulative coverage retained as non-additive evidence; alias overlap unresolved')
                    continue
            else:
                if sum(b - a for a, b in _left_ranges(start, end, covered)) != end - start:
                    notices.append('distinct response records have overlapping counter coverage; cumulative attribution is unresolved')
                covered.append((start, end))
                accepted.append(row)
            result[row['event_id']] = row
        for row in sorted(fallback, key=lambda item: (item.get('counter_start') or 0, item['at'], item['event_id'])):
            start, end = row.get('counter_start'), row.get('counter_end')
            if start is None or end is None:
                if exact:
                    notices.append('unplaced legacy aggregate retained as non-additive evidence; exact overlap unknown')
                else:
                    result[row['event_id']] = row
                continue
            remaining = _left_ranges(start, end, covered)
            count = sum(b - a for a, b in remaining)
            if not count:
                continue
            selected = row
            if count != row['tokens']['total_tokens']:
                # Subtract category vectors only when entire, disjoint observed
                # records account for all removed coverage. Otherwise only the
                # scalar remainder is identifiable; do not invent its mix.
                overlaps = [item for item in accepted if item.get('counter_start') is not None
                            and start <= item['counter_start'] and item['counter_end'] <= end]
                removed = sum(item['tokens']['total_tokens'] for item in overlaps)
                residual = None
                if removed == row['tokens']['total_tokens'] - count:
                    vector = {}
                    for key in _TOKENS:
                        values = [item['tokens'][key] for item in overlaps]
                        vector[key] = row['tokens'][key] - sum(values) if row['tokens'][key] is not None and all(value is not None for value in values) else None
                    try:
                        residual = normalize_tokens({key: value for key, value in vector.items() if value is not None})
                    except ValueError:
                        pass
                if residual is None:
                    residual = {key: None for key in _TOKENS}
                    residual.update(total_tokens=count, reported_total_tokens=None,
                                    reasoning_in_output=True, cached_in_input=True)
                selected = {**row, 'event_id': 'residual:' + _key([row['event_id'], remaining]),
                            'basis': 'native_cumulative_residual', 'tokens': residual,
                            'coverage_ranges': remaining, 'metadata_sources': dict(row['metadata_sources'])}
                for key in _LABELS:
                    if row.get('metadata_coverage', {}).get(key) is not True or any(
                        item.get(key) is not None and item[key] != row.get(key)
                        and item['counter_start'] < end and start < item['counter_end']
                        for item in accepted
                    ):
                        selected[key] = None
                        selected['metadata_sources'][key] = {'rank': 0, 'basis': 'interval_identity_unresolved'}
                if any(selected[key] is None and row.get(key) is not None for key in _LABELS):
                    notices.append('residual model/effort/speed identity lacks whole-interval evidence; affected fields are unknown')
                notices.append('partial exact coverage reconciled; unmatched cumulative residual retained')
            result[selected['event_id']] = selected
            covered.extend(remaining)
            accepted.append(selected)
    return result, sorted(set(notices))


def collect_usage(root: Path, rollout: Path, *, actor: str, start: str | None = None,
                  end: str | None = None, turn_ids: list[str] | None = None,
                  token_baseline: Mapping[str, Any] | None = None,
                  model: str | None = None, effort: str | None = None,
                  speed: str | None = None, account: str = 'current-account',
                  limit_ids: list[str] | None = None) -> dict:
    """Import only a named file and task boundary; reimports deduplicate events.

    A turn filter or timestamp boundary is mandatory: a chat can contain many
    tasks. Explicit model/effort/speed fill missing host metadata only. A supplied
    token baseline is a thread cumulative aggregate at/before the boundary.
    """
    if not actor or not (start or turn_ids or token_baseline):
        raise ValueError('actor and a task start/turn/token baseline are required')
    start, end = _time(start) if start else None, _time(end) if end else None
    if start and end and end < start:
        raise ValueError('usage end precedes start')
    wanted = set(turn_ids or [])
    thread = None
    caller = {'model': model, 'effort': effort, 'speed': speed}
    active_turns, contexts, turn_epochs = {}, {}, {}
    native, fallback, rates, notices, selected_times, gaps = [], [], [], [], [], []
    source_id = _key(str(Path(rollout).resolve()))
    baseline_raw = token_baseline.get('total_token_usage', token_baseline) if token_baseline else None
    baseline_tokens = normalize_tokens(baseline_raw) if baseline_raw else None
    baseline_total = baseline_tokens['total_tokens'] if baseline_tokens else None
    previous_by_thread, previous_by_turn = {}, {}
    counters = {}
    unbound_responses = {}
    revisions_by_thread = defaultdict(lambda: dict.fromkeys(_LABELS, 0))
    revisions_by_turn = defaultdict(lambda: dict.fromkeys(_LABELS, 0))
    derived_start = None

    def counter_epoch(scope, aggregate, late):
        thread_id, turn_id = scope
        if late:
            # A delayed old-turn alias is still in that turn's coverage
            # epoch. It cannot reset the live thread's cumulative counter.
            return turn_epochs[scope]
        total = aggregate.get('total_tokens', aggregate.get('totalTokens')) if isinstance(aggregate, Mapping) else None
        prior = counters.get(thread_id)
        epoch = prior[1] if prior else 0
        if type(total) is int:
            if prior and total < prior[0]:
                epoch += 1
                notices.append('native cumulative counter decreased; a separate coverage epoch was opened')
            counters[thread_id] = (total, epoch)
            if turn_id:
                turn_epochs[scope] = epoch
        return epoch

    safe_events = sorted(_safe_lines(Path(rollout)), key=lambda item:
                         item.get('timestamp', item.get('params', {}).get('timestamp', '')))
    # In a single-thread export, legacy context and count rows often omit
    # thread_id. An export with several explicit threads cannot fill it this way.
    threads = set()
    for event in safe_events:
        payload = event.get('payload', event.get('params', {}))
        if isinstance(payload, Mapping):
            explicit = _text(payload.get('id')) if event.get('type') == 'session_meta' else _native_id(payload, 'thread')
            if explicit:
                threads.add(explicit)
    inferred_thread = next(iter(threads)) if len(threads) == 1 else None
    for event in safe_events:
        kind = event.get('type', event.get('method'))
        payload = event.get('payload', event.get('params', {}))
        if not isinstance(payload, Mapping):
            continue
        if kind == 'session_meta':
            thread = _text(payload.get('id')) or thread
            continue
        at = event.get('timestamp', payload.get('timestamp'))
        if not at:
            notices.append('undated native notification skipped; attach an observed timestamp before importing')
            continue
        at = _time(at)
        active_thread = _native_id(payload, 'thread') or thread or inferred_thread
        active_turn = active_turns.get(active_thread)
        explicit_turn = _native_id(payload, 'turn')
        thread_revisions = revisions_by_thread[active_thread]
        if kind == 'turn_context':
            revised = _labels(payload) if explicit_turn else dict.fromkeys(_LABELS)
            prior_context = contexts.get((active_thread, active_turn), {})
            for key in _LABELS:
                if revised[key] != prior_context.get(key):
                    thread_revisions[key] += 1
            active_turns[active_thread] = explicit_turn
            if explicit_turn:
                scope = active_thread, explicit_turn
                prior_turn_context = contexts.get(scope, {})
                for key in _LABELS:
                    if revised[key] != prior_turn_context.get(key):
                        revisions_by_turn[scope][key] += 1
                contexts[scope] = {**revised, 'metadata_sources': {
                    key: {'rank': 2, 'basis': 'turn_context'} for key in _LABELS}}
                turn_epochs.setdefault(scope, counters.get(active_thread, (None, 0))[1])
                if explicit_turn in wanted and derived_start is None:
                    derived_start = at
            continue
        turn = explicit_turn or active_turn
        scope = active_thread, turn
        context = contexts.get(scope, {})
        late = bool(explicit_turn and active_turn and turn != active_turn and scope in turn_epochs)
        turn_revisions = revisions_by_turn[scope]
        selected = (not start or at >= start) and (not end or at <= end) and (not wanted or turn in wanted)
        if selected:
            selected_times.append(at)
        if kind == 'model/rerouted':
            actual_model = _text(payload.get('toModel')) or _text(payload.get('to_model'))
            if turn and actual_model:
                if actual_model != context.get('model'):
                    turn_revisions['model'] += 1
                    if not late:
                        thread_revisions['model'] += 1
                contexts[scope] = {**context, 'model': actual_model, 'metadata_sources': {
                    **context.get('metadata_sources', {}), 'model': {'rank': 3, 'basis': 'service_reroute'}}}
            continue
        if kind == 'event_msg' and payload.get('type') == 'token_usage_record':
            kind = 'token_usage_record'
        if kind == 'token_usage_record':
            cumulative = payload.get('thread_token_usage')
            epoch = counter_epoch(scope, cumulative, late)
            if baseline_total is not None:
                count = cumulative.get('total_tokens', cumulative.get('totalTokens')) if isinstance(cumulative, Mapping) else None
                if type(count) is not int or count <= baseline_total:
                    selected = False
            try:
                tokens = normalize_tokens(payload.get('usage', {}))
            except ValueError:
                notices.append('a contradictory or incomplete native token record was excluded')
                continue
            metadata, metadata_sources = _metadata(payload, context, caller)
            for key in _LABELS:
                if metadata_sources[key]['basis'] == 'response_payload' and metadata[key] != context.get(key):
                    turn_revisions[key] += 1
                    if not late:
                        thread_revisions[key] += 1
            if not selected:
                continue
            response = _native_id(payload, 'response')
            identity = [active_thread, response] if response else [active_thread, turn, at, tokens]
            low, high = _counter_range(cumulative, tokens)
            row = {'event_id': 'response:' + _key(identity), 'at': at,
                   'thread_id': active_thread, 'turn_id': turn, 'actor': actor,
                   **metadata, 'metadata_sources': metadata_sources, 'label_scope': _LABEL_SCOPE,
                   'counter_start': low, 'counter_end': high, 'counter_epoch': epoch,
                   'metered_limit_ids': _limits(payload.get('metered_limit_ids', payload.get('meteredLimitIds'))),
                   'metered_limit_source': {'rank': 3, 'basis': 'response_payload'},
                   'tokens': tokens, 'basis': 'native_response_aggregate'}
            if inferred_thread and active_thread == inferred_thread:
                unbound_responses[row['event_id']] = 'response:' + _key([None, *identity[1:]])
            native.append(row)
        elif kind in ('event_msg', 'thread/tokenUsage/updated'):
            info = payload.get('info', payload.get('tokenUsage', payload.get('token_usage')))
            if not isinstance(info, Mapping):
                info = {}
            cumulative_raw = info.get('total_token_usage', info.get('total'))
            last_raw = info.get('last_token_usage', info.get('last'))
            current = None
            epoch = counter_epoch(scope, cumulative_raw, late)
            previous_info = previous_by_turn.get(scope) if late else previous_by_thread.get(active_thread)
            previous = previous_info['tokens'] if previous_info and previous_info['epoch'] == epoch else baseline_tokens
            if previous_info and previous_info['epoch'] != epoch:
                previous_info = None
                previous = None
            context_labels, context_sources = _metadata({}, context, caller)
            try:
                if isinstance(cumulative_raw, Mapping):
                    current = normalize_tokens(cumulative_raw)
                    if baseline_total is not None and current['total_tokens'] <= baseline_total:
                        selected = False
                last = normalize_tokens(last_raw, reasoning_in_output=info.get('last_usage_includes_reasoning', True)) if isinstance(last_raw, Mapping) else None
                delta = None
                basis = None
                task_attribution = 'selected_turn' if wanted else 'completion_timestamp_assumption'
                if selected and current and previous:
                    fields = {key: current[key] - previous[key] if current[key] is not None and previous[key] is not None else None for key in _TOKENS}
                    if all(value is None or value >= 0 for value in fields.values()):
                        delta = normalize_tokens({key: value for key, value in fields.items() if value is not None})
                        basis = 'native_cumulative_difference'
                        boundary = start or derived_start
                        crosses = previous_info and ((boundary and previous_info['at'] < boundary <= at)
                            or (wanted and previous_info['turn_id'] not in wanted))
                        if crosses and delta['total_tokens']:
                            full_count = delta['total_tokens']
                            delta = last if last and last['total_tokens'] <= full_count else None
                            basis = 'native_last_boundary_assumption'
                            task_attribution = 'last_response_completion_after_boundary_assumption'
                            gaps.append({'reason': 'task boundary crosses cumulative observation interval',
                                'thread_id': active_thread, 'counter_epoch': epoch,
                                'counter_end': current['total_tokens'],
                                'start_at': previous_info['at'], 'end_at': at,
                                'interval_tokens': full_count, 'included_last_tokens': delta['total_tokens'] if delta else None,
                                'unattributed_interval_tokens': full_count - (delta['total_tokens'] if delta else 0),
                                'scope': 'last response may itself straddle the boundary; no exact task attribution'})
                            notices.append('task boundary crosses cumulative coverage; only a labelled last-response assumption is additive, remaining tokens are an attribution gap')
                    else:
                        notices.append('native cumulative counter decreased; no subtraction across the boundary')
                elif selected and last:
                    delta = last
                    basis = 'native_last_aggregate'
                if selected and delta and delta['total_tokens']:
                    low, high = _counter_range(cumulative_raw, delta)
                    metadata, metadata_sources = dict(context_labels), dict(context_sources)
                    # Same-turn coverage follows only that turn's observations.
                    # Cross-turn coverage also needs a stable active thread span.
                    revision_key = 'turn_revisions' if turn and previous_info and previous_info['turn_id'] == turn else 'thread_revisions'
                    revisions = turn_revisions if revision_key == 'turn_revisions' else thread_revisions
                    metadata_coverage = {key: bool(previous_info and metadata[key] is not None
                        and previous_info['labels'][key] == metadata[key]
                        and previous_info[revision_key][key] == revisions[key])
                        for key in _LABELS}
                    if basis == 'native_cumulative_difference':
                        for key in _LABELS:
                            if not metadata_coverage[key]:
                                metadata[key] = None
                                metadata_sources[key] = {'rank': 0, 'basis': 'interval_identity_unresolved'}
                        if any(not metadata_coverage[key] and context.get(key) is not None for key in _LABELS):
                            notices.append('cumulative interval crosses or lacks metadata coverage; affected model/effort/speed attribution is unknown')
                    fallback.append({'event_id': 'cumulative:' + _key([active_thread, epoch, low, high, basis]) if cumulative_raw else 'last:' + _key([active_thread, turn, at, delta]),
                        'at': at, 'thread_id': active_thread, 'turn_id': turn,
                        'actor': actor, **metadata, 'metadata_sources': metadata_sources, 'label_scope': _LABEL_SCOPE,
                        'metadata_coverage': metadata_coverage,
                        'counter_start': low, 'counter_end': high, 'counter_epoch': epoch,
                        'interval_start_at': previous_info['at'] if previous_info else None,
                        'task_attribution': task_attribution, 'tokens': delta, 'basis': basis})
            except ValueError:
                notices.append('an invalid native cumulative token record was excluded')
            if current and (baseline_total is None or current['total_tokens'] >= baseline_total):
                info = {'tokens': current, 'at': at, 'turn_id': turn, 'epoch': epoch,
                        'labels': context_labels, 'turn_revisions': dict(turn_revisions),
                        'thread_revisions': dict(thread_revisions)}
                if not late or not previous or current['total_tokens'] >= previous['total_tokens']:
                    previous_by_turn[scope] = info
                if not late:
                    previous_by_thread[active_thread] = info
            if payload.get('rate_limits') is not None:
                rates.extend(_rate_rows(payload['rate_limits'], at, account=account))
        elif kind == 'account/rateLimits/updated':
            rates.extend(_rate_rows(payload, at, account=account))
    actual_start = start or derived_start
    if token_baseline and not actual_start and not wanted:
        # Token-only baselines identify a cumulative counter, not an account-time
        # boundary. Account observations still remain visibly partial.
        notices.append('token baseline has no timestamp; account task boundary is unknown')
    actual_end = end or (max(selected_times, default=None) if wanted else None)
    selected_rates = [row for row in rates if (not actual_start or row['at'] >= actual_start) and (not actual_end or row['at'] <= actual_end)]
    # The nearest prior snapshot is a boundary observation, not usage to add.
    prior = {}
    if actual_start:
        for row in rates:
            if row['at'] < actual_start:
                prior[(row['account'], row['limit_id'], row['window_minutes'])] = row
        for row in prior.values():
            selected_rates.append({**row, 'boundary': 'sampled_before_task'})
    for row in native + fallback:
        row['thread_id'] = row['thread_id'] or 'source:' + source_id
        row['source_id'] = source_id
        row['account'] = account
        row['metadata_sources']['account'] = {'rank': 1 if account == 'current-account' else 2, 'basis': 'caller_account_scope'}
        if row.get('metered_limit_ids') is None:
            row['metered_limit_ids'] = _limits(limit_ids)
            row['metered_limit_source'] = {'rank': 1, 'basis': 'caller_bucket_eligibility'}
    # A complete per-response record assigned to the selected turn can resolve
    # a last-only boundary alias. A genuinely unmatched cross-boundary residual
    # remains a gap; the completion timestamp alone never resolves it.
    unresolved = []
    for gap in gaps:
        high, amount = gap.get('counter_end'), gap.get('included_last_tokens')
        exact_ranges = [(row['counter_start'], row['counter_end']) for row in native
                        if row['thread_id'] == (gap['thread_id'] or 'source:' + source_id)
                        and row.get('counter_epoch') == gap['counter_epoch']
                        and row.get('counter_start') is not None and row['turn_id'] in wanted]
        proven = wanted and amount is not None and high is not None and not _left_ranges(high - amount, high, exact_ranges)
        if gap['unattributed_interval_tokens'] or not proven:
            unresolved.append(gap)
    gaps = unresolved
    boundary_notice = 'task boundary crosses cumulative coverage; only a labelled last-response assumption is additive, remaining tokens are an attribution gap'
    if not gaps:
        notices = [notice for notice in notices if notice != boundary_notice]
    projected = native + fallback
    source = {'actor': actor, 'source': str(Path(rollout).resolve()), 'start': actual_start,
              'end': end, 'turn_ids': sorted(wanted), 'account': account,
              'thread_ids': sorted({row['thread_id'] for row in projected if row['thread_id']}),
              'observed_through': max((row['at'] for row in projected), default=None)}
    with _writer(root) as folder:
        ledger = _ledger(root)
        before = len(ledger['events'])
        selection_id = _key([source['source'], start, sorted(wanted), baseline_tokens, account])
        ledger['observations'] = {key: row for key, row in ledger['observations'].items()
                                  if not (row.get('selection_id') == selection_id and row['basis'] != 'native_response_aggregate')
                                  and not (row.get('source_id') == source_id and 'selection_id' not in row)}
        for row in projected:
            row['selection_id'] = selection_id
            unbound_id = unbound_responses.get(row['event_id'])
            unbound = ledger['observations'].get(unbound_id)
            if (unbound and unbound.get('source_id') == source_id
                    and unbound['thread_id'] in {'source:' + source_id, row['thread_id']}):
                # An append may disclose the export's thread for the first
                # time. Give the previously unbound response the same identity.
                row = _merge_observation(ledger['observations'].pop(unbound_id), row, notices)
            ledger['observations'][row['event_id']] = _merge_observation(ledger['observations'].get(row['event_id']), row, notices)
        if inferred_thread:
            for row in ledger['observations'].values():
                if row.get('source_id') == source_id and row['thread_id'] == 'source:' + source_id:
                    row['thread_id'] = inferred_thread
        ledger['events'], reconciliation_notices = _reconcile_observations(list(ledger['observations'].values()))
        notices.extend(reconciliation_notices)
        ledger['source_gaps'][selection_id] = gaps
        for row in selected_rates:
            ledger['snapshots'][_key([row['account'], row['limit_id'], row['window_minutes'], row['at'], row['used_percent'], row['resets_at']])] = row
        ledger['imports'][_key([source['source'], actor, start, sorted(wanted)])] = source
        ledger['notices'] = sorted(set([notice for notice in ledger['notices'] + notices if notice != boundary_notice]
                                      + ([boundary_notice] if any(ledger['source_gaps'].values()) else [])))
        ledger['updated_at'] = _now()
        _save(folder, ledger)
    return {'format': FORMAT, 'new_events': len(ledger['events']) - before,
            'events_total': len(ledger['events']), 'source': source,
            'projection': str(folder / 'observations.json'), 'notices': notices}


def record_rate_limits(root: Path, data: Mapping[str, Any], *, observed_at: str,
                       account: str = 'current-account', baseline: bool = False) -> dict:
    """Project a genuine rate-limit read result without retaining unrelated data."""
    rows = _rate_rows(data, _time(observed_at), account=account,
                      boundary='explicit_baseline' if baseline else 'observed')
    if not rows:
        raise ValueError('no supported account quota windows in the supplied observation')
    with _writer(root) as folder:
        ledger = _ledger(root)
        for row in rows:
            ledger['snapshots'][_key([row['account'], row['limit_id'], row['window_minutes'], row['at'], row['used_percent'], row['resets_at']])] = row
        _save(folder, ledger)
    return {'windows_recorded': len(rows)}


def _weight(event: dict, calibration: Mapping[str, Any] | None) -> tuple[float | None, list[str]]:
    model = event.get('model')
    raw = calibration.get(model) if calibration else PROXY_RATES.get(model)
    if isinstance(raw, Mapping):
        raw = (raw.get('input'), raw.get('cached_input'), raw.get('output'))
    if not isinstance(raw, (tuple, list)) or len(raw) != 3 or any(_number(value) is None for value in raw):
        return None, ['no weight for the actual model']
    tokens = event['tokens']
    if tokens['input_tokens'] is None or tokens['output_tokens'] is None:
        return None, ['partial overlap leaves only scalar residual tokens; category-weighted attribution is unavailable']
    cached = tokens['cached_input_tokens']
    if cached is None:
        return None, ['cached-input aggregate unavailable; measured total-token share remains usable']
    speed = event.get('speed')
    if 'speed' in event.get('metadata_conflicts', []):
        return None, ['actual speed metadata conflicts; measured total-token share remains usable']
    # Credit speed is only a proxy for this relative allocation. Public included
    # multipliers can differ, so it is never called subscription consumption.
    multiplier = {'standard': 1, 'default': 1, 'fast': 2, 'ultrafast': 6}.get(speed, 1)
    notices = [] if speed in ('standard', 'default', 'fast', 'ultrafast') else ['speed unavailable; Standard credit proxy assumed']
    return ((tokens['input_tokens'] - cached) * raw[0] + cached * raw[1]
            + tokens['output_tokens'] * raw[2]) * multiplier, notices


def _groups(events: list[dict], calibration: Mapping[str, Any] | None) -> tuple[list[dict], list[str]]:
    groups, notices = {}, []
    for event in events:
        identity = tuple(event.get(key) for key in ('model', 'effort', 'speed'))
        group = groups.setdefault(identity, {**dict(zip(('model', 'effort', 'speed'), identity)),
            'responses': 0, 'tokens': {key: 0 for key in _TOKENS}, 'weight': 0.0,
            'weight_available': True, 'actors': set()})
        group['responses'] += 1
        group['actors'].update(event.get('actors', [event['actor']]))
        for key in _TOKENS:
            value = event['tokens'][key]
            if value is None:
                group['tokens'][key] = None
            elif group['tokens'][key] is not None:
                group['tokens'][key] += value
        weight, notes = _weight(event, calibration)
        notices.extend(notes)
        if weight is None:
            group['weight_available'] = False
        else:
            group['weight'] += weight
    total_tokens = sum(group['tokens']['total_tokens'] for group in groups.values())
    weights_available = all(group['weight_available'] for group in groups.values())
    total_weight = sum(group['weight'] for group in groups.values()) if weights_available else None
    result = []
    for _, group in sorted(groups.items(), key=lambda item: tuple(value or '' for value in item[0])):
        group['actors'] = sorted(group['actors'])
        group['measured_token_share_percent'] = 100 * group['tokens']['total_tokens'] / total_tokens if total_tokens else None
        group['proxy_share_percent'] = 100 * group['weight'] / total_weight if total_weight else None
        if not group['weight_available']:
            group['weight'] = None
        result.append(group)
    return result, sorted(set(notices))


def _windows(snapshots: list[dict], events: list[dict], *, account_activity: str,
             calibration: Mapping[str, Any] | None) -> list[dict]:
    streams = defaultdict(list)
    for row in snapshots:
        # Slot names are UI positions, not stable quota identities.
        streams[(row['account'], row['limit_id'], row['window_minutes'])].append(row)
    result = []
    for identity, rows in sorted(streams.items()):
        rows.sort(key=lambda row: (row['at'], row['used_percent']))
        segments, active, reason = [], [], 'first_observation'
        def flush():
            if not active:
                return
            if all(row['boundary'] == 'sampled_before_task' for row in active):
                return  # A prior task's lone/retired bucket is not this task.
            first, last = active[0], active[-1]
            delta = last['used_percent'] - first['used_percent'] if len(active) > 1 else None
            matching_time = [event for event in events if first['at'] <= event['at'] <= last['at']]
            account_events = [event for event in matching_time if event.get('account') == identity[0]]
            unknown_account = [event for event in matching_time if event.get('account') is None]
            unknown_bucket = [event for event in account_events if event.get('metered_limit_ids') is None]
            covered = [event for event in account_events if event.get('metered_limit_ids') is not None
                       and identity[1] in event['metered_limit_ids']]
            shares, _ = _groups(covered, calibration)
            task_pp = delta if account_activity in ('exclusive', 'primary_task') and delta is not None and delta > 0 else None
            allocation_known = not (unknown_account or unknown_bucket)
            for group in shares:
                group['allocated_pp_approx'] = task_pp * group['proxy_share_percent'] / 100 if allocation_known and task_pp is not None and group['proxy_share_percent'] is not None else None
            segments.append({'account': identity[0], 'limit_id': identity[1],
                'window_minutes': identity[2], 'plan_type': first['plan_type'],
                'start_at': first['at'], 'end_at': last['at'],
                'start_used_percent': first['used_percent'], 'end_used_percent': last['used_percent'],
                'account_delta_pp': delta, 'boundary_basis': first['boundary'],
                'segment_reason': reason, 'observations': len(active),
                'task_interval_pp_approx': task_pp,
                'task_interval_pp_upper_bound': None,
                'group_allocation_scope': 'explicit account and metered bucket eligibility' if allocation_known else 'account or metered bucket eligibility unknown; no group pp allocation',
                'unassigned_account_records': len(unknown_account),
                'unassigned_bucket_records': len(unknown_bucket),
                'precision_and_posting': 'unknown; observed delta is not a strict consumption upper bound',
                'attribution': 'declared_exclusive_approximation' if account_activity == 'exclusive' else 'primary_task_assumption' if account_activity == 'primary_task' else 'concurrent_activity_unknown',
                'zero_reading': 'unchanged reading; below discernibility or not yet posted' if delta == 0 else None,
                'coverage': 'observed interval only; not a whole-task quota bound',
                'groups': shares})
        for row in rows:
            why = None
            if active:
                prev = active[-1]
                if row['plan_type'] != prev['plan_type']:
                    why = 'plan_changed'
                elif row['used_percent'] < prev['used_percent']:
                    why = 'usage_decreased_reset_or_adjustment'
                elif prev['resets_at'] is not None and datetime.fromisoformat(row['at']).timestamp() >= prev['resets_at']:
                    why = 'reset_boundary_crossed'
                elif row['resets_at'] is not None and prev['resets_at'] is not None and abs(row['resets_at'] - prev['resets_at']) > 60:
                    why = 'reset_marker_changed_unconfirmed'
            if why:
                flush()
                active, reason = [], why
            active.append(row)
        flush()
        result.extend(segments)
    return result


def _claude_estimate(value: Mapping[str, Any]) -> tuple[float | None, str | None]:
    explicit = _number(value.get('estimated_cost_usd'))
    if explicit is not None:
        return explicit, 'explicit attempt estimate'
    usage, prices = value.get('usage'), value.get('budget_facts')
    if not isinstance(usage, Mapping) or not isinstance(prices, Mapping):
        return None, None
    input_count, output_count = _number(usage.get('prompt_tokens')), _number(usage.get('completion_tokens'))
    input_price = _number(prices.get('prompt_usd_per_million'))
    output_price = _number(prices.get('completion_usd_per_million'))
    fee = _number(prices.get('request_usd', 0))
    if None in (input_count, output_count, input_price, output_price, fee):
        return None, None
    return (input_count * input_price + output_count * output_price) / 1_000_000 + fee, 'actual aggregate tokens at supplied unit-price bounds; cache discounts unconfirmed'


def _claude_costs(root: Path) -> dict:
    from . import codex_collaboration

    rows, notices = [], []
    for path in sorted((root / 'consult' / 'exchanges').glob('*/attempt.json')):
        try:
            value = _read(path)
        except (OSError, ValueError):
            notices.append('an unreadable Consult attempt prevents complete cost coverage')
            continue
        status = value.get('billing_status', 'UNKNOWN')
        known = _number(value.get('known_cost_usd')) if status == 'KNOWN' else None
        estimate, estimate_basis = _claude_estimate(value) if status != 'KNOWN' else (None, None)
        reserve = _number(value.get('reserved_usd')) if status == 'UNKNOWN' else 0.0
        scope = value.get('council_scope')
        scope = scope if isinstance(scope, Mapping) else {}
        contract = value.get('collaboration_contract')
        contract = contract if isinstance(contract, Mapping) else {}
        # No request messages or public/hidden model content are read here.
        row = {'exchange_id': value.get('exchange_id', path.parent.name),
            'participation_role': value.get('participation_role', 'consult_guidance'),
            'member_id': scope.get('member_id'), 'cycle_id': scope.get('cycle_id'),
            'round_id': scope.get('round_id'),
            'model': value.get('response_model', contract.get('requested_model')),
            'transport_status': value.get('transport_status'), 'billing_status': status,
            'settled_usd': known if value.get('reconciled_at') else None,
            'observed_usd': known if not value.get('reconciled_at') else None,
            'estimated_usd': estimate, 'estimate_basis': estimate_basis, 'unresolved_reserved_usd': reserve,
            'generation_id': value.get('generation_id')}
        if scope.get('purpose') == codex_collaboration.FIRST_OPINION_PURPOSE:
            row.update(purpose=scope['purpose'], public_status=value.get('public_status'))
        production = value.get('production')
        if isinstance(production, Mapping):
            row.update(production_id=production.get('production_id'), production_stage=production.get('stage'))
        rows.append(row)
    wallet = {'status': 'UNAVAILABLE', 'claims': []}
    session = {}
    try:
        from .codex_wallet import inspect_task
        session = _read(root / 'session.json')
        wallet = inspect_task(root, session)
    except (ImportError, OSError, ValueError, KeyError, sqlite3.Error):
        notices.append('shared-wallet read unavailable; unresolved reservation coverage may be incomplete')
    indexed = {row['exchange_id']: row for row in rows}
    seen = set()
    for claim in wallet.get('claims', []):
        identity = claim.get('claim_id') or claim.get('exchange_id')
        if identity in seen:
            continue
        seen.add(identity)
        exchange = claim['exchange_id']
        row = indexed.get(exchange)
        if row is None:
            row = {'exchange_id': exchange, 'participation_role': 'unknown',
                   'member_id': None, 'cycle_id': None, 'round_id': None, 'model': None,
                   'transport_status': 'attempt_record_missing', 'billing_status': 'UNKNOWN',
                   'settled_usd': None, 'observed_usd': None, 'estimated_usd': None,
                   'estimate_basis': None, 'unresolved_reserved_usd': None, 'generation_id': None}
            indexed[exchange] = row
            rows.append(row)
        row['wallet_claim_state'] = claim['state']
        if claim['state'] == 'KNOWN':
            known = _number(claim.get('known_cost_usd'))
            if known is None:
                notices.append('a KNOWN wallet claim has no usable amount')
                continue
            if row['settled_usd'] is None or abs(row['settled_usd'] - known) > 1e-12:
                row['settled_usd'], row['observed_usd'] = None, known
            row.update(billing_status='KNOWN', estimated_usd=None, estimate_basis=None,
                       unresolved_reserved_usd=0.0)
        elif claim['state'] in ('RESERVED', 'COMMITTED'):
            row['unresolved_reserved_usd'] = _number(claim.get('reserved_usd', claim.get('ceiling_usd')))
            if row['billing_status'] != 'KNOWN':
                row['billing_status'] = 'UNKNOWN'
            else:
                notices.append('a known-cost exchange still holds a shared-wallet reservation; the hold is not another bill')
        elif claim['state'] == 'ABORTED':
            row['unresolved_reserved_usd'] = 0.0
            if row['billing_status'] != 'KNOWN':
                row['billing_status'] = 'NOT_ATTEMPTED'
    report = {'attempts': rows,
            'settled_usd': sum(row['settled_usd'] or 0 for row in rows),
            'observed_usd': sum(row['observed_usd'] or 0 for row in rows),
            'estimated_usd': sum(row['estimated_usd'] or 0 for row in rows),
            'unresolved_reserved_usd': sum(row['unresolved_reserved_usd'] or 0 for row in rows),
            'not_attempted': sum(row['billing_status'] == 'NOT_ATTEMPTED' for row in rows),
            'unknown_attempts': sum(row['billing_status'] == 'UNKNOWN' for row in rows),
            'unknown_unbounded_attempts': sum(row['billing_status'] == 'UNKNOWN' and row['unresolved_reserved_usd'] is None for row in rows),
            'shared_wallet_status': wallet.get('status'),
            'notices': notices,
            'scope': 'current task Consult attempts only; reservations are not incurred bills'}
    if codex_collaboration.first_opinion_policy(session.get('P_run', '')):
        claim = wallet.get('first_opinion_claim')
        initial = session.get('initial_invocation') or {}
        lifecycle_path = root / 'lifecycle.json'
        selection = initial.get('claude_selection')
        if lifecycle_path.is_file():
            try:
                selection = _read(lifecycle_path)['claude_policy']['mode']
            except (OSError, ValueError, KeyError):
                selection = None
        if claim is not None:
            reply = indexed[claim['exchange_id']]
            report['first_opinion'] = {
                'state': 'RESERVED' if claim['state'] == 'RESERVED' else 'CONSUMED',
                'exchange_id': claim['exchange_id'], 'wallet_status': claim['state'],
                'transport_status': reply['transport_status'], 'public_status': reply.get('public_status'),
                'billing_status': reply['billing_status'], 'settled_usd': reply['settled_usd'],
                'observed_usd': reply['observed_usd'], 'unresolved_reserved_usd': reply['unresolved_reserved_usd']}
        elif selection == codex_collaboration.COUNCIL_ONLY:
            report['first_opinion'] = {
                'state': 'UNUSED' if wallet.get('status') in {'READ', 'ABSENT'} else 'UNCONFIRMED'}
    return report


def usage_dependency_paths(root: Path) -> set[Path]:
    folder = _folder(root)
    return {path for path in (folder / 'observations.json', folder / 'config.json') if path.is_file()}


def usage_live_state(root: Path) -> dict:
    """Stable task-only claim projection for return staleness; no account scan."""
    return {'claude': _claude_costs(Path(root).resolve())}


def build_usage_report(root: Path, *, account_activity: str | None = None,
                       calibration: Mapping[str, Any] | None = None) -> dict:
    """Build from this task's saved observations and actual Consult ledger only."""
    root = Path(root).resolve()
    ledger = _ledger(root)
    config_path = _folder(root) / 'config.json'
    config = _read(config_path) if config_path.exists() else {}
    activity = account_activity or config.get('account_activity', 'unknown')
    if activity not in ('unknown', 'primary_task', 'exclusive'):
        raise ValueError('account_activity must be unknown, primary_task or exclusive')
    calibration = calibration if calibration is not None else config.get('calibration')
    events = list(ledger['events'].values())
    groups, notices = _groups(events, calibration)
    windows = _windows(list(ledger['snapshots'].values()), events,
                       account_activity=activity, calibration=calibration)
    return {'format': FORMAT, 'snapshot_at': _now(),
        'observed_through': max((event['at'] for event in events), default=None),
        'native': {'groups': groups, 'responses': len(events), 'imports': list(ledger['imports'].values()),
            'coverage_gaps': [gap for gaps in ledger['source_gaps'].values() for gap in gaps],
            'attribution_assumed_records': sum('assumption' in event.get('task_attribution', '') for event in events),
            'account_windows': windows, 'account_activity': activity,
            'weight_basis': 'caller calibration' if calibration else 'public credit-rate proxy; not included-subscription conversion',
            'weight_source': config.get('calibration_source') if calibration else PRICING_SOURCE,
            'weight_rates_observed_on': None if calibration else '2026-11-18',
            'denominators': {'measured_token_share_percent': 'imported task input + output tokens, counting cached/reasoning subsets once',
                'proxy_share_percent': 'relative weighted imported task usage; effort not multiplied again',
                'account_delta_pp': 'same account bucket and observed quota-window segment',
                'allocated_pp_approx': 'assumed task-attributable interval pp times within-interval proxy share'},
            'notices': sorted(set(ledger['notices'] + notices + ([] if events else ['no task-scoped native aggregate usage has been imported'])))},
        'claude': _claude_costs(root),
        'tail': 'Snapshot covers saved observations only; final reply, unimported agents and late billing may remain outside it.'}


def render_usage_markdown(report: Mapping[str, Any]) -> str:
    """A compact response-body fragment; all percentages keep their denominator."""
    native, claude = report['native'], report['claude']
    money = lambda value: '$' + format(value, '.6f').rstrip('0').rstrip('.')
    pct = lambda value: '未知' if value is None else format(value, '.1f').rstrip('0').rstrip('.') + '%'
    pp = lambda value: '未知' if value is None else format(value, '.1f').rstrip('0').rstrip('.') + 'pp'
    lines = ['用量快照：' + report['snapshot_at'], '',
        'Claude：已核对' + money(claude['settled_usd']) + '｜服务已报' + money(claude['observed_usd'])
        + '｜估算' + money(claude['estimated_usd']) + '｜未知预留≤' + money(claude['unresolved_reserved_usd']) + '。']
    if not claude['attempts']:
        lines[-1] += '本任务无已登记Claude尝试。'
    if claude.get('unknown_unbounded_attempts'):
        lines[-1] += '另有' + str(claude['unknown_unbounded_attempts']) + '项未决金额无可用预留上界。'
    opinion = claude.get('first_opinion')
    if opinion:
        use = {'UNUSED': '额度未使用', 'UNCONFIRMED': '额度使用状态待核对',
               'RESERVED': '已预留，发送意图待确认', 'CONSUMED': '一次额度已占用'}[opinion['state']]
        public = {'COMPLETE': '公开正文完整', 'PARTIAL': '已有部分公开正文',
                  'ABSENT': '当前没有公开正文'}.get(opinion.get('public_status'), '正文状态待核对')
        if opinion.get('exchange_id'):
            lines += ['', '首议 ' + opinion['exchange_id'] + '，' + use + '，' + public + '。']
        else:
            lines += ['', '本任务首议' + use + '。']
    lines += ['', '| Codex实际模型 / effort / speed | 已导入tokens占比 | 加权用量代理占比 |',
              '| --- | --- | --- |']
    for group in native['groups']:
        label = ' / '.join(str(group.get(key) or '未知') for key in ('model', 'effort', 'speed')).replace('|', '\\|')
        lines.append('| ' + label + ' | ' + pct(group['measured_token_share_percent']) + ' | ' + pct(group['proxy_share_percent']) + ' |')
    if not native['groups']:
        lines.append('| 未取得本任务结构化用量 | 未知 | 未知 |')
    for window in native['account_windows']:
        label = window['limit_id'] + ' ' + format(window['window_minutes'], 'g') + 'min'
        if window['plan_type']:
            label += ' (' + window['plan_type'] + ')'
        observed = pct(window['start_used_percent']) + '→' + pct(window['end_used_percent'])
        line = 'Codex账户 ' + label + '：' + observed + '（变化' + pp(window['account_delta_pp']) + '；' + window['start_at'] + ' 至 ' + window['end_at'] + '）。'
        if window['task_interval_pp_approx'] is not None:
            line += '本任务该观测段约' + pp(window['task_interval_pp_approx']) + '（' + window['attribution'] + '）。'
            for group in window['groups']:
                if group['allocated_pp_approx'] is not None:
                    line += ' ' + str(group['model'] or '未知') + '/' + str(group['effort'] or '未知') + '约' + pp(group['allocated_pp_approx']) + '；'
        elif window['task_interval_pp_upper_bound'] is not None:
            line += '并发消耗未知，本任务在此观测段为0–' + pp(window['task_interval_pp_upper_bound']) + '；不是全任务上界。'
        if window['zero_reading']:
            line += '读数未变化，低于可辨或尚未入账。'
        if window.get('unassigned_account_records') or window.get('unassigned_bucket_records'):
            line += '账户或计量桶归属尚未建立，各档pp分摊未知。'
        lines += ['', line]
    lines += ['', '份额只针对已导入的任务用量；加权列为' + native['weight_basis'] + '。',
              '覆盖截止：' + str(report['observed_through'] or '未知') + '；最终回复、未导入代理与迟到费用可能在快照之外。']
    if native['notices'] or claude['notices']:
        lines += ['说明：' + '；'.join(native['notices'] + claude['notices']) + '。']
    if native.get('coverage_gaps'):
        lines += ['任务边界存在' + str(len(native['coverage_gaps'])) + '项累计区间归因缺口；已导入last响应中的跨边界归属是假设，未决残差不冒充任务实测。']
    return '\n'.join(lines) + '\n'
