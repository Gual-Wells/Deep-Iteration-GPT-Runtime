from email.message import Message
import io
import json
import unittest

from runtime.codex_public_stream import read_public_response


SECRET = 'PRIVATE_KEY_SENTINEL'
HIDDEN = 'HIDDEN_REASONING_SENTINEL'


def frame(value):
    return ('data: ' + json.dumps(value, ensure_ascii=False) + '\r\n\r\n').encode('utf-8')


class Response(io.BytesIO):
    def __init__(self, raw, streaming=True):
        super().__init__(raw)
        self.headers = Message()
        self.headers['Content-Type'] = 'text/event-stream; charset=utf-8' if streaming else 'application/json'


class PublicStreamTests(unittest.TestCase):
    def test_public_callback_precedes_terminal_read_and_usage_is_not_second_answer(self):
        seen = []
        chunks = [frame({'id': 'gen-real', 'model': 'anthropic/claude-sonnet-5.5',
                         'choices': [{'index': 0, 'delta': {'content': '第一段。\n', 'reasoning': HIDDEN}}]}),
                  frame({'choices': [{'index': 0, 'delta': {'content': '第二段。'}, 'finish_reason': 'stop'}]}),
                  frame({'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}],
                         'usage': {'cost': .01, 'completion_tokens_details': {'reasoning_tokens': 5, 'private': HIDDEN}}}),
                  b'data: [DONE]\n\n']
        class LiveResponse(Response):
            def __init__(self):
                super().__init__(b'')
                self.current = io.BytesIO(chunks.pop(0))
            def readline(self):
                line = self.current.readline()
                if not line and chunks:
                    self_test.assertTrue(seen, 'Public text must be delivered before the next chunk is read')
                    self.current = io.BytesIO(chunks.pop(0))
                    line = self.current.readline()
                return line
        self_test = self
        result = read_public_response(LiveResponse(), secret=SECRET, on_delta=seen.append)
        self.assertEqual(seen, ['第一段。\n', '第二段。'])
        self.assertTrue(result['stream_ended'])
        self.assertEqual(result['usage']['cost'], .01)
        self.assertNotIn(HIDDEN, json.dumps(result))

    def test_truncated_stream_preserves_text_and_is_not_complete(self):
        seen = []
        raw = b': OPENROUTER PROCESSING\r\n\r\n' + frame({'choices': [{'delta': {'content': '已收到的原文'}, 'finish_reason': 'stop'}]})
        result = read_public_response(Response(raw), secret=SECRET, on_delta=seen.append)
        self.assertEqual(seen, ['已收到的原文'])
        self.assertFalse(result['stream_ended'])

    def test_secret_split_across_chunks_is_redacted_before_each_callback(self):
        seen = []
        raw = b''.join(frame({'choices': [{'delta': {'content': text}}]}) for text in ['公开 ', SECRET[:7], SECRET[7:], ' 结束']) + b'data: [DONE]\n\n'
        result = read_public_response(Response(raw), secret=SECRET, on_delta=seen.append)
        self.assertEqual(''.join(seen), '公开 [REDACTED] 结束')
        self.assertNotIn(SECRET, json.dumps(seen))
        self.assertTrue(result['public_redacted'])

    def test_json_fallback_and_provider_error_keep_only_public_allowlist(self):
        seen = []
        value = {'model': 'actual', 'choices': [{'message': {'content': '公开', 'reasoning': HIDDEN}, 'finish_reason': 'error'}],
                 'error': {'code': 502, 'message': HIDDEN}, 'private': HIDDEN}
        result = read_public_response(Response(json.dumps(value).encode(), streaming=False), secret=SECRET, on_delta=seen.append)
        self.assertFalse(result['actual_streamed'])
        self.assertEqual(seen, ['公开'])
        self.assertEqual(result['error'], {'code': 502})
        self.assertNotIn(HIDDEN, json.dumps(result))


if __name__ == '__main__':
    unittest.main()
