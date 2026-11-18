"""Lossless public relay and host-reported commentary delivery cursors.

No hidden content, inferred UI success, synthesized past progress or model calls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import threading
import time
import uuid

from . import codex_io

_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}')
STAGES = {'START': '▶ 开始', 'PROGRESS': '⋯ 进展', 'REENTER': '↻ 再入',
          'RETURN': '↩ 返回', 'HANDLED': '◆ 主线处理', 'COMPLETE': '✓ 完成',
          'CLOSED': '■ 线路关闭', 'BLOCKED': '⏸ 受阻'}
KINDS = {'U0', 'N', 'R', 'D', 'V', 'S', 'M', 'SIDECAR'}
ICONS = {'U0': '🟦', 'N': '🟦', 'R': '🟪', 'D': '🟧', 'V': '🟩', 'S': '🟨', 'M': '🟥', 'SIDECAR': '🟦'}


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')


def _now():
    return datetime.now(timezone.utc).isoformat()


def _id(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError('safe nonempty identity required')
    return value


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex)
    temporary.write_bytes(_bytes(value) + b'\n')
    codex_io.replace(temporary, path)


def _lines(path, *, locked=False):
    if not path.exists():
        return []
    if locked:
        from .codex_visits import _locked
        import os
        with _locked(path, create=False) as descriptor:
            os.lseek(descriptor, 0, os.SEEK_SET)
            data = b''
            while chunk := os.read(descriptor, 65536):
                data += chunk
    else:
        data = codex_io.read_bytes(path)
    rows = []
    for raw in data.splitlines(keepends=True):
        if not raw.endswith(b'\n'):
            break  # Incomplete concurrent append is not acknowledged or skipped.
        rows.append(json.loads(raw))
    return rows


class ParagraphRelay:
    """Coalesce actual public deltas by exchange without rewriting their text."""
    def __init__(self, emit, *, max_chars=1600, latency_seconds=.5):
        if max_chars < 64 or latency_seconds <= 0:
            raise ValueError('relay bounds must be positive and readable')
        self.emit, self.max_chars, self.latency = emit, max_chars, latency_seconds
        self.buffers = {}
        self.lock = threading.RLock()

    def _flush(self, key, count=None):
        state = self.buffers[key]
        timer = state.get('timer')
        if timer is not None:
            timer.cancel()
            state['timer'] = None
        text = state['text'] if count is None else state['text'][:count]
        if not text:
            return
        self.emit({'event': 'public_text', 'exchange_id': key[0], 'member_id': key[1],
                   'text': text, 'first_sequence': state['first'], 'last_sequence': state['last'],
                   'public_status': 'PARTIAL',
                   'source': 'actual external public text; requested model identity is not yet confirmation',
                   'display_text': '**外部协作者 / ' + (key[1] or key[0] or 'Consult')
                       + (' / 请求 ' + state['model'] + '（身份待核）' if state.get('model') else '')
                       + '｜正文增量（尚未收齐）**\n\n' + text})
        state['text'] = state['text'][len(text):]
        state['at'] = time.monotonic()
        state['first'] = state['last']

    def feed(self, event):
        with self.lock:
            key = (event.get('exchange_id'), event.get('member_id'))
            if event.get('event') == 'public_delta':
                text = event.get('text')
                if not isinstance(text, str):
                    raise ValueError('public delta must be text')
                state = self.buffers.setdefault(key, {'text': '', 'at': time.monotonic(),
                    'first': event.get('sequence'), 'last': event.get('sequence'), 'timer': None})
                if isinstance(event.get('requested_model'), str):
                    state['model'] = event['requested_model']
                state['last'] = event.get('sequence')
                state['text'] += text
                while state['text']:
                    paragraph = state['text'].find('\n\n')
                    if paragraph >= 0 and paragraph + 2 <= self.max_chars:
                        self._flush(key, paragraph + 2)
                    elif len(state['text']) >= self.max_chars:
                        self._flush(key, self.max_chars)
                    elif time.monotonic() - state['at'] >= self.latency:
                        self._flush(key)
                    else:
                        break
                if state['text'] and state['timer'] is None:
                    def expire():
                        with self.lock:
                            self._flush(key)
                    timer = threading.Timer(self.latency, expire)
                    timer.daemon = True
                    state['timer'] = timer
                    timer.start()
            else:
                if key in self.buffers:
                    self._flush(key)
                # Only known public/connection metadata, never arbitrary response fields.
                status = {field: event[field] for field in ('event', 'exchange_id', 'member_id', 'sequence',
                    'at', 'http_status', 'transport_status', 'public_status', 'billing_status', 'known_cost_usd')
                    if field in event}
                status['display_text'] = '**宿主状态｜' + str(event.get('event')) + '**\n\n' + json.dumps(status, ensure_ascii=False)
                self.emit(status)

    def flush(self):
        with self.lock:
            for key in self.buffers:
                self._flush(key)


def emit_work(root: Path, *, actor: str, kind: str, unit: str, stage: str,
              text: str, operation_id: str, source_ref: str = '', topic: str = '') -> dict:
    from .codex_session import _session
    from .codex_lifecycle import require_active
    from .codex_visits import _locked
    root, session = _session(root)
    require_active(root)
    _id(actor); _id(unit); _id(operation_id)
    if kind not in KINDS or stage not in STAGES or not isinstance(text, str) or not text.strip():
        raise ValueError('actual work kind, stage and public summary text required')
    if stage in {'RETURN', 'HANDLED'} and not source_ref.strip():
        raise ValueError('returned contribution and actual handling require a source reference')
    path = root / 'live' / 'work.events.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(topic, str) or '\n' in topic or len(topic) > 200:
        raise ValueError('topic must be one short public problem title')
    record = {'actor': actor, 'kind': kind, 'unit': unit, 'stage': stage, 'topic': topic,
              'text': text, 'operation_id': operation_id, 'source_ref': source_ref}
    with _locked(path, create=True) as descriptor:
        import os
        os.lseek(descriptor, 0, os.SEEK_SET)
        saved = b''
        while chunk := os.read(descriptor, 65536):
            saved += chunk
        if saved and not saved.endswith(b'\n'):
            raise ValueError('interrupted work record needs explicit recovery; no silent append or fake history')
        previous = [json.loads(row) for row in saved.splitlines()]
        for item in previous:
            if item['operation_id'] == operation_id:
                if any(item[key] != value for key, value in record.items()):
                    raise ValueError('operation id already describes different actual work')
                return item
        starts = [item for item in previous if (item['actor'], item['kind'], item['unit']) == (actor, kind, unit)
                  and item['stage'] == 'START']
        record.update(at=_now(), P_run=session['P_run'],
                      missing_start=not starts and stage != 'START',
                      visibility='PENDING_HOST_DISPLAY')
        raw = _bytes(record) + b'\n'
        os.lseek(descriptor, 0, os.SEEK_END)
        while raw:
            written = os.write(descriptor, raw)
            raw = raw[written:]
    return record


def _items(root, exchange_id):
    if exchange_id is None:
        return _lines(root / 'live/work.events.jsonl', locked=True)
    _id(exchange_id)
    events = _lines(root / 'consult/exchanges' / exchange_id / 'public.events.jsonl')
    return [{field: row[field] for field in ('event', 'exchange_id', 'member_id', 'sequence', 'at', 'text',
             'transport_status', 'public_status', 'billing_status', 'known_cost_usd', 'http_status') if field in row}
            for row in events if row.get('event') in {'public_delta', 'connected', 'finished'}]


def _public_text(item):
    if 'kind' in item:
        return item['text']
    if item['event'] == 'public_delta':
        return item['text']
    return '宿主连接/结束状态：' + json.dumps({k: v for k, v in item.items() if k not in {'text'}}, ensure_ascii=False)


def pending(root: Path, *, reader: str, exchange_id: str | None = None, max_chars: int = 8000) -> dict:
    from .codex_session import _session
    root, _ = _session(root)
    _id(reader)
    if type(max_chars) is not int or not 256 <= max_chars <= 64000:
        raise ValueError('display batch must be 256 to 64000 characters')
    source = 'work' if exchange_id is None else 'public-' + _id(exchange_id)
    cursor_path = root / 'live/cursors' / (reader + '.' + source + '.json')
    cursor = json.loads(codex_io.read_bytes(cursor_path).decode('utf-8')) if cursor_path.exists() else {'index': 0, 'offset': 0}
    items = _items(root, exchange_id)
    model_label = ''
    if exchange_id is not None:
        request_path = root / 'consult/exchanges' / exchange_id / 'request.json'
        attempt_path = request_path.with_name('attempt.json')
        requested = json.loads(request_path.read_text('utf-8')).get('model') if request_path.is_file() else None
        observed = json.loads(attempt_path.read_text('utf-8')).get('response_model') if attempt_path.is_file() else None
        model_label = (' / 服务标识 ' + observed if isinstance(observed, str) else
                       ' / 请求 ' + requested + '（身份待核）' if isinstance(requested, str) else '')
    if cursor.get('prefix_sha256') and sha256(_bytes(items[:cursor['index']])).hexdigest() != cursor['prefix_sha256']:
        raise ValueError('acknowledged public history changed; do not silently skip or replay it')
    index, offset = cursor['index'], cursor['offset']
    if index > len(items):
        raise ValueError('public history was truncated')
    if offset and (index == len(items) or sha256(_bytes(items[index])).hexdigest() != cursor.get('partial_sha256')):
        raise ValueError('partially displayed public history changed')
    segments, displays, left = [], [], max_chars
    while index < len(items) and left > 128:
        item = items[index]
        full = _public_text(item)
        if offset > len(full):
            raise ValueError('partial public history changed')
        label = (ICONS[item['kind']] + ' **' + item['actor'] + ' · ' + item['kind'] + item['unit']
                 + ('｜' + item['topic'] if item.get('topic') else '') + '**\n**' + STAGES[item['stage']] + '**'
                 if 'kind' in item else '**外部协作者 / ' + (item.get('member_id') or item.get('exchange_id') or 'Consult') + model_label + '**'
                 if item['event'] == 'public_delta' else '**宿主状态**')
        label += '（续）' if offset else ''
        take = min(len(full) - offset, max(1, left - len(label) - 8))
        text = full[offset:offset + take]
        segments.append({'index': index, 'offset': offset, 'text': text,
                         'public_original': item.get('event') == 'public_delta',
                         'source_ref': item.get('source_ref'), 'actor': item.get('actor'), 'stage': item.get('stage')})
        displays.append(label + '\n\n' + text)
        left -= len(label) + len(text) + 8
        offset += take
        if offset == len(full):
            index, offset = index + 1, 0
    to = {'index': index, 'offset': offset, 'prefix_sha256': sha256(_bytes(items[:index])).hexdigest(),
          'partial_sha256': sha256(_bytes(items[index])).hexdigest() if offset else None}
    result = {'reader': reader, 'source': source, 'from': cursor, 'to': to, 'segments': segments,
              'display_text': '\n\n'.join(displays), 'remaining': index < len(items),
              'visibility': 'PENDING_HOST_DISPLAY',
              'scope': 'read does not mark user-visible delivery; host must post commentary then acknowledge'}
    if segments:
        result['delivery_id'] = sha256(_bytes(result)).hexdigest()[:32]
        result['exchange_id'] = exchange_id
        _write(root / 'live/deliveries' / (result['delivery_id'] + '.json'), result)
    return result


def acknowledge(root: Path, delivery_id: str, *, evidence_ref: str) -> dict:
    from .codex_session import _session
    from .codex_visits import _locked
    root, _ = _session(root)
    _id(delivery_id)
    if not isinstance(evidence_ref, str) or not evidence_ref.strip():
        raise ValueError('actual host commentary reference required; reading a file is not display')
    path = root / 'live/deliveries' / (delivery_id + '.json')
    value = json.loads(codex_io.read_bytes(path).decode('utf-8'))
    cursor_path = root / 'live/cursors' / (value['reader'] + '.' + value['source'] + '.json')
    cursor_path.parent.mkdir(parents=True, exist_ok=True)
    with _locked(cursor_path.with_suffix('.lock'), create=True):
        value = json.loads(codex_io.read_bytes(path).decode('utf-8'))
        if value.get('visibility') == 'HOST_REPORTED_DISPLAYED':
            return value
        current = json.loads(codex_io.read_bytes(cursor_path).decode('utf-8')) if cursor_path.exists() else {'index': 0, 'offset': 0}
        if current != value['from']:
            raise ValueError('stale display acknowledgement; do not move the reader cursor backwards')
        items = _items(root, value.get('exchange_id'))
        if sha256(_bytes(items[:value['to']['index']])).hexdigest() != value['to']['prefix_sha256']:
            raise ValueError('public source changed before acknowledgement')
        target = value['to']
        if target['offset'] and (target['index'] >= len(items) or sha256(_bytes(items[target['index']])).hexdigest() != target['partial_sha256']):
            raise ValueError('partial public source changed before acknowledgement')
        _write(cursor_path, value['to'])
        value.update(visibility='HOST_REPORTED_DISPLAYED', evidence_ref=evidence_ref, acknowledged_at=_now(),
                     scope='host-reported actual commentary; helper cannot authenticate UI delivery')
        _write(path, value)
    return value
