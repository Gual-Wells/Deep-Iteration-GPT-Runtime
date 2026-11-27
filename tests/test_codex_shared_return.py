"""Exercise the new shared-journal -> session -> native response path."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from runtime.codex_return import (close_return, record_execution_error, response_body, return_status, seal_return)
from runtime.codex_session import activity, create_session, session_report, set_task_parameters
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
                     'verification_limits': '结论由给定前提与推论成立，只适用于原题界定的对象。',
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

    def test_argument_scope_uses_the_same_seal_body_close_path_without_empirical_gate(self):
        self.data['argument_scope'] = self.data.pop('verification_limits')
        self.save()
        sealed = seal_return(self.session, self.input)
        self.assertEqual(sealed['current_receipt'], 'READY_UNCLOSED')
        body = response_body(self.session)
        self.assertIn('## 论证与适用范围', body)
        self.assertNotIn('## 核验与限制', body)
        self.assertIn(self.data['argument_scope'], body)
        self.assertEqual(close_return(self.session, reason='reasoned explanation completed')['current_receipt'], 'CLOSED')

    def test_ordered_errors_survive_retry_and_refresh_the_current_return(self):
        self.session = self.base / 'ordered-session'
        create_session(self.session, request=self.request, p_run='1.9.0@' + 'a' * 40)
        set_task_parameters(self.session, parameters={'F': 0}, reasons={'F': 'This test has no source search'})
        with self.assertRaisesRegex(ValueError, 'schema 3'):
            seal_return(self.session, self.input)
        self.data['schema_version'] = 3
        self.data['argument_scope'] = self.data.pop('verification_limits')
        self.save()
        seal_return(self.session, self.input)
        self.assertTrue(response_body(self.session).endswith('未记录执行报错。\n'))

        first = {'id': 'read-document', 'stage': '来源', 'problem': '资料读取失败 <first>',
                 'impact': '暂缺原件', 'status': 'OPEN', 'handling': '准备从同一版本重读'}
        second = {'id': 'validate-output', 'stage': '验证', 'problem': '交叉核对失败',
                  'impact': '影响 A | B', 'status': 'BLOCKED', 'handling': '等待证据'}
        item = self.base / 'incident.json'
        item.write_text(json.dumps(first, ensure_ascii=False), encoding='utf-8')
        cli = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/codex.py'),
                              'return', 'record-error', '--root', str(self.session), '--input', str(item)],
                             capture_output=True)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        record_execution_error(self.session, second)
        self.assertEqual(return_status(self.session)['current_receipt'], 'STALE')
        record_execution_error(self.session, {**first, 'status': 'RECOVERED', 'handling': '同一版本已重读'})
        with self.assertRaisesRegex(ValueError, 'different occurrence'):
            record_execution_error(self.session, {**first, 'problem': '另一事件'})
        self.assertTrue(seal_return(self.session, self.input)['can_close'])
        body = response_body(self.session)
        self.assertLess(body.index('## 参数'), body.index('## 执行报错'))
        self.assertIn('| 1 | 来源 | 资料读取失败 &lt;first&gt; | 暂缺原件 | 已恢复 | 同一版本已重读 |', body)
        self.assertIn('| 2 | 验证 | 交叉核对失败 | 影响 A &#124; B | 受阻 | 等待证据 |', body)
        record_execution_error(self.session, second)
        self.assertEqual(return_status(self.session)['current_receipt'], 'READY_UNCLOSED')
        self.assertEqual(close_return(self.session, reason='fixture records preserved')['current_receipt'], 'CLOSED')

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
        # Fixed fixture boundaries avoid depending on Windows wall-clock ticks.
        with patch('runtime.codex_visits.time.time_ns', side_effect=[1_000_000_000, 2_000_000_000, 3_000_000_000]):
            self.visit('BEGIN', category='SOURCE')
            self.visit('END')
            self.visit('BEGIN', actor_id='interrupted')
        report = session_report(self.session)
        self.assertEqual(report['timing']['t_ns'], 1_000_000_000)
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
