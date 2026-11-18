from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from runtime.codex_live import acknowledge, pending
from runtime.codex_session import create_session


class LiveBatchingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='live-batches-')
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        request = base / 'request.txt'
        request.write_text('DIGR: synthetic stream fixture', encoding='utf-8')
        self.task = base / 'task'
        create_session(self.task, request=request, p_run='0.17.0@' + 'a' * 40)
        self.exchange = self.task / 'consult/exchanges/ex'
        self.exchange.mkdir(parents=True)
        (self.exchange / 'request.json').write_text('{"model":"synthetic-collaborator"}', encoding='utf-8')
        self.stream = self.exchange / 'public.events.jsonl'

    def write(self, events):
        raw = ''.join(json.dumps(event, ensure_ascii=False) + '\n' for event in events)
        self.stream.write_bytes(raw.encode('utf-8'))

    def delta(self, member, text):
        return {'event': 'public_delta', 'exchange_id': 'ex', 'member_id': member, 'text': text}

    def pending(self, max_chars=5000, reader='host'):
        return pending(self.task, reader=reader, exchange_id='ex', max_chars=max_chars)

    def test_single_label_covers_small_deltas_and_cursor_keeps_raw_offsets(self):
        initial = ['片段\n'] * 1000
        large = '第二段🧪\n\n' * 900
        events = [
            {'event': 'connected', 'exchange_id': 'ex', 'transport_status': 'connected'},
            *(self.delta('writer-a', piece) for piece in initial),
            self.delta('writer-a', large),
            self.delta('writer-b', 'B first line\n  indentation'),
            self.delta('writer-b', 'B second line'),
            self.delta('writer-a', 'A 多行\n\n尾声'),
            {'event': 'finished', 'exchange_id': 'ex', 'public_status': 'PARTIAL'},
        ]
        self.write(events)
        original = ''.join(item.get('text', '') for item in events)
        first = self.pending()
        retry = self.pending()
        self.assertEqual(first, retry)
        segment, = [part for part in first['segments'] if part['public_original']]
        self.assertGreater(len(segment['text']), 4500)
        self.assertEqual(first['display_text'].count('synthetic-collaborator'), 1)
        self.assertLessEqual(len(first['display_text']), 5000)
        self.assertEqual((segment['index'], segment['offset']), (1, 0))
        self.assertEqual(segment['end_index'], first['to']['index'])
        self.assertGreater(segment['end_offset'], 0)
        self.assertEqual(segment['end_offset'], first['to']['offset'])
        self.assertTrue(first['to']['partial_sha256'])

        collected = []
        while True:
            batch = self.pending()
            for part in batch['segments']:
                if not part['public_original']:
                    continue
                start, end = part['index'], part['end_index']
                cursor = (start, part['offset'])
                last = (end, part['end_offset'])
                evidence = []
                while cursor < last:
                    index, offset = cursor
                    event = events[index]
                    self.assertEqual(event['member_id'], events[start]['member_id'])
                    limit = last[1] if index == end else len(event['text'])
                    evidence.append(event['text'][offset:limit])
                    cursor = index + 1, 0
                self.assertEqual(''.join(evidence), part['text'])
                collected.append(part['text'])
            acknowledge(self.task, batch['delivery_id'], evidence_ref='synthetic actual host commentary')
            if not batch['remaining']:
                self.assertEqual(batch['segments'][-1]['public_original'], False)
                self.assertIn('PARTIAL', batch['segments'][-1]['text'])
                break
        self.assertEqual(sha256(''.join(collected).encode('utf-8')).digest(), sha256(original.encode('utf-8')).digest())
        self.assertEqual(self.pending()['segments'], [])
        self.assertEqual(self.pending(reader='other')['from'], {'index': 0, 'offset': 0})

    def test_compact_ack_keeps_full_receipt_and_old_output(self):
        original = '公开原文🧪\n\n' * 4000
        self.write([self.delta('writer-a', original)])
        batch = self.pending(max_chars=32000)
        delivery_id = batch['delivery_id']
        args = [sys.executable, '-X', 'utf8', '-B',
                str(Path(__file__).resolve().parents[1] / 'tools/codex.py'), 'live', 'ack',
                '--root', str(self.task), '--delivery-id', delivery_id,
                '--evidence-ref', 'synthetic host display reference']
        compact = subprocess.check_output(args + ['--compact'], encoding='utf-8')
        full = subprocess.check_output(args, encoding='utf-8')
        saved = json.loads((self.task / 'live/deliveries' / (delivery_id + '.json')).read_text(encoding='utf-8'))
        compact_json = json.loads(compact)
        self.assertLess(len(compact.encode('utf-8')), 700)
        self.assertEqual(compact_json['visibility'], 'HOST_REPORTED_DISPLAYED')
        self.assertEqual(compact_json['to'], batch['to'])
        self.assertEqual(saved, json.loads(full))
        self.assertEqual(saved['segments'], batch['segments'])
        self.assertEqual(saved['display_text'], batch['display_text'])
        self.assertEqual(saved['evidence_ref'], 'synthetic host display reference')
        self.assertEqual(self.pending()['from'], batch['to'])


if __name__ == '__main__':
    unittest.main()
