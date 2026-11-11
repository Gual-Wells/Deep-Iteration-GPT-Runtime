"""Exercise the new shared-journal -> session -> native response path."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from runtime.codex_return import close_return, response_body, return_status, seal_return
from runtime.codex_session import activity, create_session, session_report
from runtime.codex_visits import append_visit

ROOT = Path(__file__).resolve().parents[1]
PIN = '0.8.1@' + 'a' * 40  # Constructed fixture; no live acquisition claim.


class SharedReturnTests(unittest.TestCase):
    def setUp(self):
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='shared-return-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.request = self.base / 'request.txt'
        self.request.write_text('DIGR：解释选定材料，直接返回报告正文。\n', encoding='utf-8')
        self.session = self.base / 'session'
        self.log = self.base / 'all-visits.jsonl'
        create_session(self.session, request=self.request, p_run=PIN,
                       visits_path=self.log, run_id='selected')
        self.input = self.base / 'return.json'
        self.data = {'schema_version': 2,
                     'result': '给定解释已经完整写在正文，原件仅为补充。',
                     'key_changes': '本次形成了有范围的结论；没有虚构前后性能变化。',
                     'work_process': '| 时间／记录范围 | 工作与后果 |\n| --- | --- |\n| 未记录 | 完成选定解释；不补造工时。 |',
                     'verification_limits': '未进行真实读者实验。',
                     'parameters': '测试夹具，不追认 N/R/D/V 或真实投入。',
                     'artifacts': [], 'sources': []}
        self.save()

    def save(self):
        self.input.write_text(json.dumps(self.data, ensure_ascii=False), encoding='utf-8')

    def visit(self, event, **kw):
        return append_visit(self.log, run_id=kw.pop('run_id', 'selected'),
                            actor_id=kw.pop('actor_id', 'worker'), event=event, **kw)

    def test_native_body_cli_and_close_without_html_report(self):
        status = seal_return(self.session, self.input)
        folder = Path(status['receipt']).parent
        body = response_body(self.session)
        self.assertEqual(body, (folder / 'RETURN.md').read_text(encoding='utf-8'))
        self.assertIn(self.data['result'], body)
        self.assertFalse((folder / 'details.html').exists())
        self.assertFalse((folder / 'pipeline.svg').exists())
        cli = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/codex.py'),
                              'return', 'body', '--root', str(self.session)],
                             capture_output=True)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertEqual(cli.stdout, body.encode('utf-8'))
        self.assertEqual(close_return(self.session, reason='fixture result selected')['current_receipt'], 'CLOSED')

    def test_unrelated_run_and_duplicate_replay_do_not_stale_selected_body(self):
        begin = self.visit('BEGIN', category='SOURCE')
        self.visit('END')
        seal_return(self.session, self.input)
        self.visit('BEGIN', run_id='different')
        self.visit('END', run_id='different')
        with self.log.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(begin) + '\n')
        self.assertEqual(return_status(self.session)['current_receipt'], 'READY_UNCLOSED')
        self.visit('BEGIN', actor_id='second')
        self.assertEqual(return_status(self.session)['current_receipt'], 'STALE')

    def test_missing_end_preserves_gap_without_invalidating_other_pairs_or_return(self):
        self.visit('BEGIN', category='SOURCE')
        self.visit('END')
        self.visit('BEGIN', actor_id='interrupted')
        report = session_report(self.session)
        self.assertGreater(report['timing']['t_ns'], 0)
        self.assertEqual(len(report['timing']['gaps']), 1)
        self.assertEqual(seal_return(self.session, self.input)['current_receipt'], 'READY_UNCLOSED')
        self.assertEqual(close_return(self.session, reason='unresolved gap explicitly retained')['current_receipt'], 'CLOSED')

    def test_legacy_clock_and_schema_cannot_silently_replace_new_path(self):
        with self.assertRaisesRegex(ValueError, 'shared visit'):
            activity(self.session, 'COMMON', 'begin', state='SOURCE', scope='FOUNDATION')
        self.data['schema_version'] = 1
        self.save()
        with self.assertRaisesRegex(ValueError, 'schema 2'):
            seal_return(self.session, self.input)
        legacy = self.base / 'legacy'
        with self.assertRaisesRegex(ValueError, 'keep old pins'):
            create_session(legacy, request=self.request, p_run='0.8.0@' + 'b' * 40,
                           visits_path=self.log, run_id='legacy')

    def test_cli_begin_end_and_foundation_scope_use_the_same_file(self):
        cli = [sys.executable, '-B', str(ROOT / 'tools/codex.py'), 'visits']
        begin = subprocess.run(cli + ['begin', '--root', str(self.session), '--actor', 'helper',
                                     '--phase', 'FOUNDATION', '--category', 'SOURCE'],
                               capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(begin.returncode, 0, begin.stderr)
        end = subprocess.run(cli + ['end', '--root', str(self.session), '--actor', 'helper',
                                   '--phase', 'FOUNDATION'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(end.returncode, 0, end.stderr)
        report = session_report(self.session)
        self.assertEqual(report['timing']['T_ns'], 0)
        self.assertGreater(report['foundation_timing']['t_ns'], 0)

    def test_body_changed_after_seal_is_not_the_selected_report(self):
        status = seal_return(self.session, self.input)
        Path(status['response_body']).write_text('a different document', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'current sealed return'):
            response_body(self.session)


if __name__ == '__main__':
    unittest.main()
