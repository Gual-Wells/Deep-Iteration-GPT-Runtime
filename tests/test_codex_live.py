import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from runtime.codex_live import ParagraphRelay, emit_work, pending, acknowledge
from runtime.codex_session import create_session


class LiveRelayTests(unittest.TestCase):
    def test_interleaved_streams_preserve_exact_original_text(self):
        received = []
        relay = ParagraphRelay(received.append, max_chars=128, latency_seconds=10)
        originals = {'a': '原文第一段。\n\n' + '真实公开内容' * 100 + '\n末行', 'b': '另一成员\n保留换行\n\n后半段。'}
        for index in range(max(map(len, originals.values()))):
            for exchange, body in originals.items():
                if index < len(body):
                    relay.feed({'event': 'public_delta', 'exchange_id': exchange, 'text': body[index], 'sequence': index})
        relay.flush()
        for exchange, original in originals.items():
            self.assertEqual(''.join(e['text'] for e in received if e.get('exchange_id') == exchange), original)
        self.assertLess(len(received), 30)

    def test_short_partial_is_visible_before_model_finish(self):
        seen = threading.Event()
        values = []
        def emit(value):
            values.append(value)
            seen.set()
        relay = ParagraphRelay(emit, latency_seconds=.05)
        relay.feed({'event': 'public_delta', 'exchange_id': 'a', 'text': '已经到达但尚未结束。', 'sequence': 1})
        self.assertTrue(seen.wait(1))
        relay.feed({'event': 'finished', 'exchange_id': 'a', 'public_status': 'PARTIAL', 'arbitrary_private': 'NEVER_FORWARD'})
        self.assertEqual(values[0]['text'], '已经到达但尚未结束。')
        self.assertNotIn('NEVER_FORWARD', json.dumps(values))
        relay.flush()

    def test_non_claude_collaborator_is_not_labelled_claude(self):
        values = []
        relay = ParagraphRelay(values.append)
        relay.feed({'event': 'public_delta', 'exchange_id': 'other-model', 'requested_model': 'other/vendor-model', 'text': 'Public text.\n\n'})
        relay.flush()
        self.assertIn('other/vendor-model', values[0]['display_text'])
        self.assertNotIn('Claude', values[0]['display_text'])

    def test_cursor_does_not_skip_unacknowledged_batches(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            request = base / 'request.txt'
            request.write_text('DIGR: synthetic live relay fixture', encoding='utf-8')
            root = base / 'task'
            create_session(root, request=request, p_run='0.16.0@' + 'd' * 40)
            path = root / 'consult/exchanges/ex/public.events.jsonl'
            path.parent.mkdir(parents=True)
            original = '完整正文' * 1000
            path.write_bytes((json.dumps({'event': 'public_delta', 'exchange_id': 'ex', 'text': original}) + '\n').encode('utf-8'))
            one = pending(root, reader='host', exchange_id='ex', max_chars=512)
            repeated = pending(root, reader='host', exchange_id='ex', max_chars=512)
            self.assertEqual(one['segments'], repeated['segments'])
            self.assertEqual(one['delivery_id'], repeated['delivery_id'])
            with self.assertRaises(ValueError):
                acknowledge(root, one['delivery_id'], evidence_ref='')
            pieces = []
            while True:
                current = pending(root, reader='host', exchange_id='ex', max_chars=512)
                pieces.extend(part['text'] for part in current['segments'] if part['public_original'])
                if current.get('delivery_id'):
                    result = acknowledge(root, current['delivery_id'], evidence_ref='synthetic actual host commentary marker')
                    self.assertEqual(result['visibility'], 'HOST_REPORTED_DISPLAYED')
                if not current['remaining']:
                    break
            self.assertEqual(''.join(pieces), original)
            self.assertFalse(pending(root, reader='host', exchange_id='ex')['segments'])

    def test_changed_partial_history_cannot_be_acknowledged(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp);request = base / 'request.txt';request.write_text('DIGR: fixture', encoding='utf-8')
            root = base / 'task';create_session(root, request=request, p_run='0.16.0@' + 'd' * 40)
            path = root / 'consult/exchanges/ex/public.events.jsonl';path.parent.mkdir(parents=True)
            row = {'event': 'public_delta', 'exchange_id': 'ex', 'text': 'original' * 1000}
            path.write_bytes((json.dumps(row) + '\n').encode())
            batch = pending(root, reader='host', exchange_id='ex', max_chars=256)
            row['text'] = 'changed' * 1000
            path.write_bytes((json.dumps(row) + '\n').encode())
            with self.assertRaisesRegex(ValueError, 'source changed'):
                acknowledge(root, batch['delivery_id'], evidence_ref='synthetic marker')

    def test_work_identity_stages_and_missing_start_are_not_fabricated(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp);request = base / 'request.txt';request.write_text('DIGR: fixture', encoding='utf-8')
            root = base / 'task';create_session(root, request=request, p_run='0.16.0@' + 'd' * 40)
            event = emit_work(root, actor='D-real', kind='D', unit='01', stage='RETURN',
                text='Independent actual contribution', operation_id='returned', source_ref='synthetic actual artifact')
            self.assertTrue(event['missing_start'])
            again = emit_work(root, actor='D-real', kind='D', unit='01', stage='RETURN',
                text='Independent actual contribution', operation_id='returned', source_ref='synthetic actual artifact')
            self.assertEqual(event, again)
            shown = pending(root, reader='host')
            self.assertIn('D01', shown['display_text'])
            self.assertIn('↩ 返回', shown['display_text'])
            self.assertEqual(shown['visibility'], 'PENDING_HOST_DISPLAY')

    def test_stable_dispatch_keeps_roles_and_stream_text_at_host_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            request = base / 'request.txt'
            request.write_text('DIGR: fixture', encoding='utf-8')
            root = base / 'task'
            create_session(root, request=request, p_run='1.0.0@' + 'a' * 40)
            identity = dict(kind='D', unit='D05', line='M01')
            emit_work(root, actor='D05', stage='START', text='开始工作。', operation_id='start', **identity)
            emit_work(root, actor='D05', stage='RETURN', text='第一段。\n\n第二段。', operation_id='return',
                      source_ref='synthetic return', return_mode='quote', **identity)
            emit_work(root, actor='Main', stage='HANDLED', text='处理所得。', operation_id='handling',
                      source_ref='synthetic handling', **identity)
            native = pending(root, reader='commentary')['display_text']
            self.assertIn('M01·D05**\n**↩ 返回｜逐字引文**\n\n> 第一段。\n> \n> 第二段。', native)
            self.assertIn('M01·D05·Main**\n**◆ 主线处理**\n\n处理所得。', native)

            stream = root / 'consult/exchanges/ex/public.events.jsonl'
            stream.parent.mkdir(parents=True)
            original = '保留原文。\r\n  缩进。\n\n尾行'
            value = {'event': 'public_delta', 'exchange_id': 'ex', 'member_id': 'writer', 'text': original}
            stream.write_bytes((json.dumps(value, ensure_ascii=False) + '\n').encode('utf-8'))
            args = [sys.executable, '-B', str(Path(__file__).resolve().parents[1] / 'tools/codex.py'),
                    'live', 'read', '--root', str(root), '--reader', 'commentary', '--exchange-id', 'ex',
                    '--format', 'commentary', '--catch-up']
            header, _, rendered = subprocess.check_output(args).decode('utf-8').partition('\n')
            receipt = json.loads(header)
            self.assertEqual(receipt['visibility'], 'PENDING_HOST_DISPLAY')
            self.assertEqual(rendered.count(original), 1)
            self.assertIn('**补转｜从同一记录恢复**', rendered)
            self.assertIn('writer / ex', rendered)
            self.assertTrue(rendered.endswith(original))
            saved = acknowledge(root, receipt['delivery_id'], evidence_ref='synthetic host publication')
            self.assertEqual(saved['segments'][0]['text'], original)
            self.assertFalse(pending(root, reader='commentary', exchange_id='ex')['segments'])


if __name__ == '__main__':
    unittest.main()
