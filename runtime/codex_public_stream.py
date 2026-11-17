"""Read public chat content incrementally without retaining private fields."""
from __future__ import annotations

import json
from typing import Callable, Mapping


class _PublicRedactor:
    def __init__(self, secret: str):
        self.secret, self.pending, self.changed = secret, '', False

    def feed(self, text: str, *, final: bool = False) -> str:
        self.pending += text
        replaced = self.pending.replace(self.secret, '[REDACTED]') if self.secret else self.pending
        self.changed |= replaced != self.pending
        keep = 0
        if not final and self.secret:
            for length in range(1, min(len(replaced), len(self.secret) - 1) + 1):
                if replaced.endswith(self.secret[:length]):
                    keep = length
        result = replaced[:-keep] if keep else replaced
        self.pending = replaced[-keep:] if keep else ''
        return result


def _sse_data(response):
    fields = []
    while True:
        raw = response.readline()
        if not raw:
            if fields:
                yield '\n'.join(fields)
            return
        line = raw.decode('utf-8').rstrip('\r\n')
        if not line:
            if fields:
                yield '\n'.join(fields)
                fields = []
        elif line.startswith('data:'):
            value = line[5:]
            fields.append(value[1:] if value.startswith(' ') else value)


def read_public_response(response, *, secret: str, on_delta: Callable[[str], None]) -> dict:
    """Relay only public content; return an aggregate suitable for cost/identity.

    JSON fallbacks are identified as non-streaming. EOF without [DONE] does
    not complete an SSE answer, even if an earlier frame said finish=stop.
    The caller owns persistence, visible forwarding and interruption handling.
    """
    streamed = 'text/event-stream' in response.headers.get('Content-Type', '').lower()
    result = {'choices': [{'message': {'content': ''}, 'finish_reason': None}],
              'actual_streamed': streamed, 'stream_ended': not streamed}
    parts, redactor = [], _PublicRedactor(secret)

    def emit(text, *, final=False):
        safe = redactor.feed(text, final=final)
        if safe:
            parts.append(safe)
            on_delta(safe)

    def consume(data):
        if not isinstance(data, Mapping):
            raise ValueError('nonobject public response')
        for field in ('id', 'model', 'provider'):
            if isinstance(data.get(field), str):
                result[field] = data[field].replace(secret, '[REDACTED]') if secret else data[field]
        if isinstance(data.get('usage'), Mapping):
            # The runtime's existing usage allowlist selects aggregate numbers.
            source = data['usage']
            usage = {key: source[key] for key in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'cost')
                     if type(source.get(key)) in (int, float)}
            for field in ('prompt_tokens_details', 'completion_tokens_details'):
                nested = source.get(field)
                if isinstance(nested, Mapping):
                    usage[field] = {key: nested[key] for key in ('reasoning_tokens', 'cached_tokens', 'cache_write_tokens')
                                    if type(nested.get(key)) in (int, float)}
            result['usage'] = usage
        error = data.get('error')
        if isinstance(error, Mapping):
            code = error.get('code')
            result['error'] = {'code': code if type(code) is int else None}
        choices = data.get('choices')
        choice = next((item for item in choices if isinstance(item, Mapping) and item.get('index', 0) == 0), {}) if isinstance(choices, list) else {}
        finish = choice.get('finish_reason')
        if isinstance(finish, str):
            result['choices'][0]['finish_reason'] = finish.replace(secret, '[REDACTED]') if secret else finish
        message = choice.get('delta' if streamed else 'message')
        if isinstance(message, Mapping) and isinstance(message.get('content'), str):
            emit(message['content'])

    if streamed:
        for payload in _sse_data(response):
            if payload.strip() == '[DONE]':
                result['stream_ended'] = True
                break
            consume(json.loads(payload))
    else:
        consume(json.loads(response.read()))
    emit('', final=True)
    result['choices'][0]['message']['content'] = ''.join(parts)
    result['public_redacted'] = redactor.changed
    return result
