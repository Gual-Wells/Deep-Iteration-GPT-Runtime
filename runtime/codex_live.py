"""Lossless public relay and host-reported commentary delivery cursors.

No hidden content, inferred UI success, synthesized past progress or model calls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
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
STABLE_KINDS = {'INIT': '⚙️', 'ARBITRATION': '🟥'}
_PUBLIC_EVENTS = {'public_delta', 'connected', 'finished'}
_PUBLIC_FIELDS = ('event', 'exchange_id', 'member_id', 'sequence', 'at', 'text',
                  'transport_status', 'public_status', 'billing_status', 'known_cost_usd', 'http_status')


def stable_live(p_run: str) -> bool:
    version = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)@[0-9a-f]{40}', p_run)
    return bool(version and tuple(map(int, version.groups())) >= (1, 0, 0))


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


def _external_label(item, *, member=None, model_label='', production_stage=None):
    exchange = item.get('exchange_id')
    member = item.get('member_id') or member
    identity = ' / '.join(dict.fromkeys(name for name in (member, exchange) if name)) or 'Consult'
    if production_stage in ('candidate', 'arbitration'):
        label = 'Claude 候选' if production_stage == 'candidate' else 'Claude 终裁'
        identity = label + ' / ' + identity
    if item['event'] in {'public_delta', 'public_text'}:
        return '**外部协作者 / ' + identity + model_label + '｜公开正文片段**'
    stage = '**▶ 已连接**' if item['event'] == 'connected' else '**■ 交换状态**'
    return '**宿主 / ' + identity + '**\n' + stage


def _model_label(requested, observed=None):
    if isinstance(observed, str) and observed:
        return ' / 服务标识 ' + ' '.join(observed.splitlines())
    if isinstance(requested, str) and requested:
        return ' / 请求 ' + ' '.join(requested.splitlines()) + '（身份待核）'
    return ''


def _external_status(item):
    if item['event'] == 'connected':
        return '收到服务连接响应' + (f'（HTTP {item["http_status"]}）' if 'http_status' in item else '') + '。'
    body = {'COMPLETE': '公开正文完整', 'PARTIAL': '已取得部分正文，续文未确认',
            'ABSENT': '未取得公开正文'}.get(item.get('public_status'), '公开正文状态未知')
    transport = {'RESPONDED': '已返回', 'OUTCOME_UNKNOWN': '结果未确认'}.get(item.get('transport_status'), '未确认')
    billing = {'KNOWN': '已知', 'UNKNOWN': '待对账', 'NOT_ATTEMPTED': '未发出'}.get(item.get('billing_status'))
    cost = item.get('known_cost_usd')
    if billing == '已知' and type(cost) in (int, float):
        billing = f'{cost} 美元'
    return f'传输{transport}。{body}。' + (f'费用{billing}。' if billing else '')


class ParagraphRelay:
    """Coalesce actual public deltas by exchange without rewriting their text."""
    def __init__(self, emit, *, max_chars=1600, latency_seconds=.5, stable=False):
        if max_chars < 64 or latency_seconds <= 0:
            raise ValueError('relay bounds must be positive and readable')
        self.emit, self.max_chars, self.latency = emit, max_chars, latency_seconds
        self.stable = stable
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
        event = {'event': 'public_text', 'exchange_id': key[0], 'member_id': key[1],
                 'text': text, 'first_sequence': state['first'], 'last_sequence': state['last'],
                 'public_status': 'PARTIAL',
                 'source': 'actual external public text; requested model identity is not yet confirmation'}
        label = (_external_label(event, model_label=_model_label(state.get('model')),
                                 production_stage=state.get('production_stage')) if self.stable else
                 '**外部协作者 / ' + (key[1] or key[0] or 'Consult')
                 + (' / 请求 ' + state['model'] + '（身份待核）' if state.get('model') else '')
                 + '｜正文增量（尚未收齐）**')
        event['display_text'] = label + '\n\n' + text
        self.emit(event)
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
                state['production_stage'] = event.get('production_stage')
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
                if self.stable and event.get('event') not in _PUBLIC_EVENTS:
                    return
                fields = _PUBLIC_FIELDS if self.stable else ('event', 'exchange_id', 'member_id', 'sequence',
                    'at', 'http_status', 'transport_status', 'public_status', 'billing_status', 'known_cost_usd')
                status = {field: event[field] for field in fields if field in event and field != 'text'}
                if self.stable:
                    status['display_text'] = _external_label(
                        status, production_stage=event.get('production_stage')) + '\n\n' + _external_status(status)
                else:
                    status['display_text'] = '**宿主状态｜' + str(event.get('event')) + '**\n\n' + json.dumps(status, ensure_ascii=False)
                self.emit(status)

    def flush(self):
        with self.lock:
            for key in self.buffers:
                self._flush(key)


def emit_work(root: Path, *, actor: str, kind: str, unit: str, stage: str,
              text: str, operation_id: str, source_ref: str = '', topic: str = '',
              line: str = '', return_mode: str = '') -> dict:
    from .codex_session import _session
    from .codex_lifecycle import require_active
    from .codex_visits import _locked
    root, session = _session(root)
    stable = stable_live(session['P_run'])
    if not stable:
        require_active(root)
        if line or return_mode:
            raise ValueError('line and return mode require a 1.x or later task pin')
    _id(actor); _id(unit); _id(operation_id)
    if (kind not in KINDS and not (stable and kind in STABLE_KINDS)
            or stage not in STAGES or not isinstance(text, str) or not text.strip()):
        raise ValueError('actual work kind, stage and public summary text required')
    if stage in {'RETURN', 'HANDLED'} and (not isinstance(source_ref, str) or not source_ref.strip()):
        raise ValueError('returned contribution and actual handling require a source reference')
    path = root / 'live' / 'work.events.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(topic, str) or '\n' in topic or len(topic) > 200:
        raise ValueError('topic must be one short public problem title')
    record = {'actor': actor, 'kind': kind, 'unit': unit, 'stage': stage, 'topic': topic,
              'text': text, 'operation_id': operation_id, 'source_ref': source_ref}
    if stable:
        if line:
            _id(line)
        if return_mode and (stage != 'RETURN' or return_mode not in {'quote', 'summary'}):
            raise ValueError('native return mode must be quote or summary on an actual return')
        record.update(line=line, return_mode=(return_mode or 'summary') if stage == 'RETURN' else '')
    with _locked(path, create=True) as descriptor:
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
        if stable:
            scope = _work_scope(record)
            started = any(item['stage'] == 'START' and _work_scope(item) == scope for item in previous)
        else:
            started = any(item['stage'] == 'START' and (item['actor'], item['kind'], item['unit']) == (actor, kind, unit)
                          for item in previous)
        record.update(at=_now(), P_run=session['P_run'],
                      missing_start=not started and stage != 'START' and kind != 'INIT',
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
    return [{field: row[field] for field in _PUBLIC_FIELDS if field in row}
            for row in events if row.get('event') in _PUBLIC_EVENTS]


def _public_text(item, stable):
    if 'kind' in item:
        return item['text']
    if item['event'] == 'public_delta':
        return item['text']
    if stable:
        return _external_status(item)
    return '宿主连接/结束状态：' + json.dumps({k: v for k, v in item.items() if k != 'text'}, ensure_ascii=False)


def _unit_label(item):
    kind, unit = item['kind'], item['unit']
    if kind == 'INIT':
        return {'COMPLETE': '[DIGR INIT OK]', 'BLOCKED': '[DIGR INIT BLOCKED]'}.get(item['stage'], 'DIGR INIT')
    if kind == 'ARBITRATION':
        return '仲裁' if unit == kind else '仲裁·' + unit
    if kind in {'U0', 'SIDECAR'}:
        return kind if unit == kind else kind + '·' + unit
    return unit if unit.startswith(kind) else kind + unit


def _work_scope(item):
    kind = item['kind']
    unit = _unit_label(item)
    # V reentry and the Main's handling keep the independent work's identity.
    if kind == 'V':
        unit = unit.partition('.')[0]
    actor = None if kind in {'D', 'V'} else item['actor']
    return item.get('line', ''), kind, unit, actor


def _work_label(item, stable):
    actor, kind = item['actor'], item['kind']
    stage = STAGES[item['stage']]
    topic = '｜' + item['topic'] if item.get('topic') else ''
    if not stable:
        return f"{ICONS[kind]} **{actor} · {kind}{item['unit']}{topic}**\n**{stage}**"
    unit = _unit_label(item)
    line = item.get('line')
    role = '·'.join(dict.fromkeys(part for part in (line, unit, actor) if part))
    if item['stage'] == 'RETURN':
        stage += '｜' + ('逐字引文' if item.get('return_mode') == 'quote' else '概括')
    if item.get('missing_start'):
        stage += '｜开始边界缺记录'
    icon = ICONS.get(kind) or STABLE_KINDS[kind]
    return f'{icon} **{role}{topic}**\n**{stage}**'


def _text_limit(text, offset, budget, quote):
    """Count the quote markers in the display bound while retaining the raw slice."""
    if not quote:
        return min(len(text) - offset, budget)
    remaining = budget - 2  # Opening '> ' before the first line.
    count = 0
    for character in text[offset:offset + remaining]:
        remaining -= 3 if character == '\n' else 1
        if remaining < 0:
            break
        count += 1
    return count


def _json(path):
    return json.loads(codex_io.read_bytes(path).decode('utf-8'))


def _cursor(path):
    return _json(path) if path.exists() else {'index': 0, 'offset': 0}


def pending(root: Path, *, reader: str, exchange_id: str | None = None,
            max_chars: int = 8000, catch_up: bool = False) -> dict:
    from .codex_session import _session
    from .codex_visits import _locked
    root, session = _session(root)
    stable = stable_live(session['P_run'])
    if catch_up and not stable:
        raise ValueError('catch-up display requires a 1.x or later task pin')
    _id(reader)
    if type(max_chars) is not int or not 256 <= max_chars <= 64000:
        raise ValueError('display batch must be 256 to 64000 characters')
    source = 'work' if exchange_id is None else 'public-' + _id(exchange_id)
    cursor_path = root / 'live/cursors' / (reader + '.' + source + '.json')
    cursor = _cursor(cursor_path)
    items = _items(root, exchange_id)
    model_label, member, production_stage = '', None, None
    if exchange_id is not None:
        request_path = root / 'consult/exchanges' / exchange_id / 'request.json'
        attempt_path = request_path.with_name('attempt.json')
        requested = _json(request_path).get('model') if request_path.is_file() else None
        attempt = _json(attempt_path) if attempt_path.is_file() else {}
        observed = attempt.get('response_model')
        if stable:
            model_label = _model_label(requested, observed)
            member = (attempt.get('council_scope') or {}).get('member_id')
            production_stage = (attempt.get('production') or {}).get('stage')
        else:
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
    catch_up_notice = '**补转｜从同一记录恢复**\n\n' if catch_up else ''
    left -= len(catch_up_notice)
    while index < len(items) and (stable or left > 128):
        item = items[index]
        public_original = item.get('event') == 'public_delta'
        quote = stable and item.get('stage') == 'RETURN'
        if 'kind' in item:
            label = _work_label(item, stable)
        elif stable:
            label = _external_label(item, member=member, model_label=model_label, production_stage=production_stage)
        else:
            label = ('**外部协作者 / ' + (item.get('member_id') or item.get('exchange_id') or 'Consult')
                     + model_label + '**' if public_original else '**宿主状态**')
        label += '（续）' if offset else ''
        start_index, start_offset = index, offset
        budget = left - len(label) - 8
        if stable and budget < (5 if quote else 1):
            if segments:
                break
            raise ValueError('commentary header exceeds the display batch; increase --max-chars')
        budget = max(1, budget)
        pieces = []
        while index < len(items) and budget:
            current = items[index]
            if index != start_index and not (
                public_original and current.get('event') == 'public_delta'
                and current.get('exchange_id') == item.get('exchange_id')
                and current.get('member_id') == item.get('member_id')
            ):
                break
            full = _public_text(current, stable)
            if offset > len(full):
                raise ValueError('partial public history changed')
            take = _text_limit(full, offset, budget, quote)
            pieces.append(full[offset:offset + take])
            budget -= take
            offset += take
            if offset < len(full):
                break
            index, offset = index + 1, 0
        text = ''.join(pieces)
        segments.append({'index': start_index, 'offset': start_offset, 'end_index': index,
                         'end_offset': offset, 'text': text, 'public_original': public_original,
                         'source_ref': item.get('source_ref'), 'actor': item.get('actor'), 'stage': item.get('stage')})
        body = '> ' + text.replace('\n', '\n> ') if quote else text
        displays.append(label + '\n\n' + body)
        left -= len(label) + len(body) + 8
    to = {'index': index, 'offset': offset, 'prefix_sha256': sha256(_bytes(items[:index])).hexdigest(),
          'partial_sha256': sha256(_bytes(items[index])).hexdigest() if offset else None}
    result = {'reader': reader, 'source': source, 'from': cursor, 'to': to, 'segments': segments,
              'display_text': catch_up_notice + '\n\n'.join(displays) if displays else '', 'remaining': index < len(items),
              'visibility': 'PENDING_HOST_DISPLAY',
              'scope': 'read does not mark user-visible delivery; host must post commentary then acknowledge'}
    if segments:
        result['delivery_id'] = sha256(_bytes(result)).hexdigest()[:32]
        result['exchange_id'] = exchange_id
        delivery = root / 'live/deliveries' / (result['delivery_id'] + '.json')
        if stable:
            cursor_path.parent.mkdir(parents=True, exist_ok=True)
            with _locked(cursor_path.with_suffix('.lock'), create=True):
                if delivery.exists():
                    return _json(delivery)
                _write(delivery, result)
        else:
            _write(delivery, result)
    return result


def acknowledge(root: Path, delivery_id: str, *, evidence_ref: str) -> dict:
    from .codex_session import _session
    from .codex_visits import _locked
    root, session = _session(root)
    stable = stable_live(session['P_run'])
    _id(delivery_id)
    if not isinstance(evidence_ref, str) or not evidence_ref.strip():
        raise ValueError('actual host commentary reference required; reading a file is not display')
    path = root / 'live/deliveries' / (delivery_id + '.json')
    value = _json(path)
    cursor_path = root / 'live/cursors' / (value['reader'] + '.' + value['source'] + '.json')
    cursor_path.parent.mkdir(parents=True, exist_ok=True)
    with _locked(cursor_path.with_suffix('.lock'), create=True):
        value = _json(path)
        current = _cursor(cursor_path)
        reported = value.get('visibility') == 'HOST_REPORTED_DISPLAYED'
        if reported and (not stable or current != value['from']):
            return value
        if current != value['from']:
            raise ValueError('stale display acknowledgement; do not move the reader cursor backwards')
        items = _items(root, value.get('exchange_id'))
        if sha256(_bytes(items[:value['to']['index']])).hexdigest() != value['to']['prefix_sha256']:
            raise ValueError('public source changed before acknowledgement')
        target = value['to']
        if target['offset'] and (target['index'] >= len(items) or sha256(_bytes(items[target['index']])).hexdigest() != target['partial_sha256']):
            raise ValueError('partial public source changed before acknowledgement')
        if not stable:
            _write(cursor_path, target)
        if not reported:
            value.update(visibility='HOST_REPORTED_DISPLAYED', evidence_ref=evidence_ref, acknowledged_at=_now(),
                         scope='host-reported actual commentary; helper cannot authenticate UI delivery')
            _write(path, value)
        if stable:
            # Retrying after a fault between the two writes resumes this actual receipt.
            _write(cursor_path, target)
    return value
