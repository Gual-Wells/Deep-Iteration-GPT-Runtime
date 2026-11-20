"""Bind local support work to a Claude member's actual public request."""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Mapping

from . import codex_collaboration

ROUND_KIND = 'NATIVE_WORK_RETURN'
RETURN_SCOPE_KEYS = frozenset({'native_work_return_of', 'native_work_ids'})
RESEARCH_EFFORTS = frozenset({'high', 'xhigh', 'max'})
OUTCOMES = frozenset({'COMPLETE', 'UNAVAILABLE'})
_OPEN = '[[CODEX NATIVE WORK]]'
_CLOSE = '[[END CODEX NATIVE WORK]]'
_FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')

MEMBER_INSTRUCTION = (
    'Use your high-effort research for the attention, problem framing, strong alternatives, '
    'and judgment that materially improve this work. When evidence you could use requires '
    'Codex to retrieve originals, extract a window, calculate, compare, or run a bounded '
    'trial, ask the host to do that work. State the concrete deliverable and the judgment '
    'it would inform. Include the source window or check when it matters. Keep your useful '
    'public reasoning and place any actual requests at the end of your public answer as '
    'one standalone block outside quotations or code fences, with these two literal marker '
    'lines and one JSON array between them:\n' + _OPEN + '\n'
    '[{"work":"the concrete Codex work","informs":"the judgment this evidence would inform"}]\n'
    + _CLOSE + '\nThe host chooses the actual local operation within the user task. '
    'Only request work you want performed now. When the host returns the evidence in your '
    'public conversation, continue your own reasoning and explain how it affects your judgment.'
)


def requests_from_body(body: str) -> list[dict]:
    """Recognize an unquoted closing block; an invalid block creates no work."""
    lines = body.rstrip().split('\n')
    lines = [line.removesuffix('\r') for line in lines]
    if lines[-1] != _CLOSE or _OPEN not in lines:
        return []
    start = len(lines) - 1 - lines[::-1].index(_OPEN)
    fence = ''
    for line in lines[:start]:
        match = _FENCE.match(line)
        if match is None:
            continue
        marker, tail = match.groups()
        if not fence:
            fence = marker
        elif marker[0] == fence[0] and len(marker) >= len(fence) and not tail.strip():
            fence = ''
    if fence:
        return []
    try:
        raw = json.loads('\n'.join(lines[start + 1:-1]))
        if not isinstance(raw, list):
            return []
        requests = []
        seen = set()
        for item in raw:
            if not isinstance(item, dict) or set(item) != {'work', 'informs'}:
                return []
            pair = (item['work'], item['informs'])
            if any(not isinstance(value, str) or not value.strip() for value in pair):
                return []
            for value in pair:
                value.encode('utf-8')
            if pair not in seen:
                requests.append(item)
                seen.add(pair)
        return requests
    except (ValueError, RecursionError):
        return []


def observed_requests(attempt: Mapping, body: str | None) -> dict[str, dict]:
    """Use the same identity during discovery and later source verification."""
    if (body is None or attempt['participation_role'] != 'council_member'
            or attempt['transport_status'] != 'RESPONDED' or attempt['public_status'] != 'COMPLETE'
            or not codex_collaboration.CLAUDE_MODEL.search(
                attempt['collaboration_contract']['requested_model'])
            or (attempt.get('response_model') and not codex_collaboration.CLAUDE_MODEL.search(
                attempt['response_model']))):
        return {}
    if sha256(body.encode('utf-8')).hexdigest() != attempt['public_sha256']:
        raise ValueError('Native work source differs from the observed public output')
    source = {'scope': attempt['council_scope'], 'exchange_id': attempt['exchange_id'],
              'request_sha256': attempt['request_sha256'], 'public_sha256': attempt['public_sha256']}
    requests = {}
    for ordinal, request in enumerate(requests_from_body(body), start=1):
        key = f"{source['exchange_id']}/{source['public_sha256']}/{ordinal}"
        identity = 'work-' + sha256(key.encode('ascii')).hexdigest()[:32]
        requests[identity] = {'source': source, 'request': request}
    return requests


def open_requests(state: Mapping, member_id: str) -> dict[str, dict]:
    exchanges = state['members'][member_id]['exchanges']
    return {identity: item for identity, item in state.get('native_work', {}).items()
            if (exchanges and exchanges[-1] == item['source']['exchange_id']
                and item['source']['scope']['member_id'] == member_id
                and item['source']['scope']['cycle_id'] == state['cycle_id']
                and item['source']['scope']['input_version'] == state['input_version']
                and item.get('return_exchange_id') is None)}


def bound_returns(state: Mapping, scope: Mapping, exchange_id: str) -> dict[str, dict]:
    identities = scope['native_work_ids']
    if (not isinstance(identities, list) or not identities
            or not all(isinstance(identity, str) for identity in identities)
            or identities != sorted(set(identities))):
        raise ValueError('Native work return needs distinct recorded work identities')
    entries = {}
    for identity in identities:
        item = state.get('native_work', {}).get(identity)
        if (item is None or item['return_exchange_id'] != exchange_id or item['result'] is None
                or item['source']['exchange_id'] != scope['native_work_return_of']
                or any(item['source']['scope'][key] != scope[key] for key in
                       ('council_id', 'member_id', 'line_id', 'cycle_id', 'input_version', 'packet_sha256'))):
            raise ValueError('Native work results differ from the frozen member and source exchange')
        entries[identity] = item
    return entries


def verify_origin(entries: Mapping, attempt: Mapping, body: str | None) -> None:
    actual = observed_requests(attempt, body)
    for identity, item in entries.items():
        if actual.get(identity) != {'source': item['source'], 'request': item['request']}:
            raise ValueError('Native work request differs from the original public member output')
