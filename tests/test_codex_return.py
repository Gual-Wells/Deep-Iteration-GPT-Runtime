from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from runtime.codex_lifecycle import handle_message, ingest_message, load_lifecycle
from runtime.codex_return import close_return, return_status, seal_return
from runtime.codex_session import activity, create_line, create_session

ROOT = Path(__file__).resolve().parents[1]
PIN = '0.8.0@' + 'a' * 40  # A constructed test pin, never an acquisition claim.


class ReturnTests(unittest.TestCase):
    def setUp(self):
        cache = (ROOT / '.cache').resolve()
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='codex-return-test-', dir=cache)
        self.base = Path(self.temp.name).resolve()
        if not self.base.is_relative_to(cache) or not self.base.name.startswith('codex-return-test-'):
            raise RuntimeError('refusing cleanup outside this test cache')
        self.addCleanup(self.temp.cleanup)
        self.request = self.base / 'request.txt'
        self.request.write_text('DIGR：解释给定结论并返回有范围的研究结果。\n', encoding='utf-8')
        self.session = self.base / 'session'
        create_session(self.session, request=self.request, p_run=PIN)
        self.input = self.base / 'return.json'
        self.data = {
            'schema_version': 1, 'result': '这是可直接阅读的解释结果，无需另做软件。',
            'scope': '仅对给定材料作解释；本测试不声明整任务历史。',
            'evidence': '依据与反例在这份解释中；无外部实证声明。',
            'limits': '没有真实读者实验。',
            'time_and_responsibilities': '没有可信完整时间；N/R/D/V实际数量未认证。',
            'artifacts': [], 'decisions': [], 'unhandled': ['独立语义判断仍由模型负责。'],
            'sources': [],
        }
        self.save()

    def save(self):
        self.input.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')

    def timeline(self, mode='recorded'):
        return {'schema_version': 1, 'mode': mode, 'title': '明确标识的测试fixture',
                'axis_domain': 'constructed-fixture-domain', 'origin': '2026-11-10T12:00:00+00:00',
                'protocol_pin': PIN, 'notice': '只测试缺时渲染，时间和事实均为测试数据。',
                'tracks': [{'id': 'M01', 'kind': 'M', 'label': '测试作用域', 'segments': []}],
                'events': [{'id': 'unknown', 'track': 'M01', 'kind': 'note', 'at': None,
                            'label': '时间未记录的公开事实', 'source_ref': str(self.input)}],
                'links': [], 'highlights': [{'label': '事实仍可读，时刻保持未知。', 'events': ['unknown']}]}

    def test_explanation_only_seals_and_closes_without_self_staleness(self):
        sealed = seal_return(self.session, self.input)
        self.assertEqual(sealed['current_receipt'], 'READY_UNCLOSED')
        folder = Path(sealed['receipt']).parent
        self.assertIn(self.data['result'], (folder / 'RETURN.md').read_text(encoding='utf-8'))
        self.assertIn('不从活动钟', (folder / 'details.html').read_text(encoding='utf-8'))
        self.assertFalse((folder / 'pipeline.svg').exists())
        closed = close_return(self.session, reason='解释结果已返回，限制仍明确保留。')
        self.assertEqual(closed['current_receipt'], 'CLOSED')
        self.assertEqual(closed['lifecycle_status'], 'CLOSED')
        self.assertEqual(return_status(self.session)['current_receipt'], 'CLOSED')
        self.assertFalse(closed['semantic_certification'])
        self.assertIn('独立语义判断', (folder / 'RETURN.md').read_text(encoding='utf-8'))
        state = load_lifecycle(self.session)
        self.assertEqual(state['closure']['result_ref']['path'], Path(sealed['receipt']).as_posix())
        self.assertFalse((self.session / 'return-state.json').exists())
        self.assertEqual(close_return(self.session, reason='重复核验')['current_receipt'], 'CLOSED')

    def test_changed_artifact_source_input_and_generated_view_are_not_current(self):
        artifact, source = self.base / 'result.txt', self.base / 'source.txt'
        artifact.write_text('初稿', encoding='utf-8')
        source.write_text('原始依据', encoding='utf-8')
        self.data['artifacts'] = [{'label': '成品', 'path': artifact.name}]
        self.data['sources'] = [source.name]
        self.save()
        for target in (artifact, source, self.input):
            sealed = seal_return(self.session, self.input)
            previous = target.read_bytes()
            target.write_bytes(previous + b'\n')
            self.assertEqual(return_status(self.session)['current_receipt'], 'STALE')
            with self.assertRaisesRegex(ValueError, 'current sealed return'):
                close_return(self.session, reason='不能沿用旧快照')
            self.assertEqual(load_lifecycle(self.session)['status'], 'ACTIVE')
            target.write_bytes(previous)
        sealed = seal_return(self.session, self.input)
        view = Path(sealed['receipt']).parent / 'RETURN.md'
        view.write_text('修改后的旧返回', encoding='utf-8')
        self.assertEqual(return_status(self.session)['current_receipt'], 'STALE')

    def test_resealing_before_close_selects_a_new_snapshot(self):
        one = seal_return(self.session, self.input)
        two = seal_return(self.session, self.input)
        self.assertNotEqual(one['receipt'], two['receipt'])
        self.assertEqual(two['current_receipt'], 'READY_UNCLOSED')
        closed = close_return(self.session, reason='当前结果')
        self.assertEqual(closed['receipt'], two['receipt'])

    def test_missing_time_has_a_real_fallback_and_illustration_is_rejected(self):
        self.data['timeline'] = self.timeline()
        self.save()
        sealed = seal_return(self.session, self.input)
        folder = Path(sealed['receipt']).parent
        self.assertIn('时间未定位', (folder / 'pipeline.svg').read_text(encoding='utf-8'))
        self.assertIn('时间未记录的公开事实', (folder / 'details.html').read_text(encoding='utf-8'))
        self.data['timeline']['mode'] = 'illustration'
        self.save()
        with self.assertRaisesRegex(ValueError, 'illustration'):
            seal_return(self.session, self.input)
        self.assertEqual(return_status(self.session)['current_receipt'], 'STALE')

    def test_selected_timeline_file_is_bound_and_pin_must_match(self):
        timeline = self.base / 'facts.json'
        timeline.write_text(json.dumps(self.timeline()), encoding='utf-8')
        self.data['timeline'] = timeline.name
        self.save()
        seal_return(self.session, self.input)
        timeline.write_text(json.dumps(self.timeline()) + '\n', encoding='utf-8')
        self.assertEqual(return_status(self.session)['current_receipt'], 'STALE')
        bad = self.timeline()
        bad['protocol_pin'] = '0.8.0@' + 'b' * 40
        timeline.write_text(json.dumps(bad), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'P_run'):
            seal_return(self.session, self.input)

    def test_open_clock_must_end_before_seal_and_close_does_not_mutate_it(self):
        activity(self.session, 'COMMON', 'begin', state='SOURCE', scope='FOUNDATION')
        with self.assertRaisesRegex(ValueError, 'open managed activity'):
            seal_return(self.session, self.input)
        activity(self.session, 'COMMON', 'end', continued=True)
        clock = self.session / 'common/activity.jsonl'
        previous = clock.read_bytes()
        seal_return(self.session, self.input)
        self.assertEqual(close_return(self.session, reason='完成')['current_receipt'], 'CLOSED')
        self.assertEqual(clock.read_bytes(), previous)

    def test_later_message_or_line_and_clock_changes_invalidate_selected_return(self):
        seal_return(self.session, self.input)
        activity(self.session, 'COMMON', 'begin', state='SOURCE', scope='FOUNDATION')
        activity(self.session, 'COMMON', 'end', continued=True)
        self.assertEqual(return_status(self.session)['current_receipt'], 'STALE')
        seal_return(self.session, self.input)
        message = self.base / 'message.txt'
        message.write_text('补充：请说明限制。', encoding='utf-8')
        pending = ingest_message(self.session, source=message, source_ref='实际消息测试fixture')
        pending_return = return_status(self.session)
        self.assertFalse(pending_return['can_close'])
        self.assertTrue(any('pending' in reason for reason in pending_return['cannot_close']))
        with self.assertRaisesRegex(ValueError, 'pending'):
            seal_return(self.session, self.input)
        handle_message(self.session, message_id=pending['message_id'], action='continue', reason='同任务补充，已有结果需复核')
        self.assertEqual(return_status(self.session)['current_receipt'], 'STALE')
        seal_return(self.session, self.input)
        create_line(self.session, 'M01', parameters={'N': 2, 'T': 0, 'R': 1, 'B': 0,
                    'S': {'n': 0, 't': 0, 'r': 0, 'b': 0}, 'D': 0, 'V': 0, 'L': 3})
        self.assertEqual(return_status(self.session)['current_receipt'], 'STALE')

    def test_tool_implementation_change_invalidates_and_paused_state_cannot_close(self):
        renderer = self.base / 'selected-renderer.py'
        renderer.write_text('# selected tool implementation', encoding='utf-8')
        with patch('runtime.codex_return._tool_paths', return_value={renderer}):
            sealed = seal_return(self.session, self.input)
            receipt = json.loads(Path(sealed['receipt']).read_text(encoding='utf-8'))
            self.assertEqual(receipt['tool_state'][str(renderer)]['resolved_path'], str(renderer.resolve()))
            renderer.write_text('# same-version tool changed', encoding='utf-8')
            self.assertEqual(return_status(self.session)['current_receipt'], 'STALE')
        seal_return(self.session, self.input)
        message = self.base / 'pause.txt'
        message.write_text('暂停。', encoding='utf-8')
        pending = ingest_message(self.session, source=message, source_ref='实际暂停测试fixture')
        handle_message(self.session, message_id=pending['message_id'], action='pause', reason='用户要求暂停')
        paused = return_status(self.session)
        self.assertEqual(paused['current_receipt'], 'READY_UNCLOSED')
        self.assertFalse(paused['can_close'])
        self.assertTrue(any('PAUSED' in reason for reason in paused['cannot_close']))
        with self.assertRaisesRegex(ValueError, 'PAUSED'):
            close_return(self.session, reason='不能忽略暂停')

    def test_ordinary_chat_after_close_does_not_invalidate_finished_result(self):
        seal_return(self.session, self.input)
        close_return(self.session, reason='原任务已返回')
        message = self.base / 'thanks.txt'
        message.write_text('谢谢，另问一个普通问题。', encoding='utf-8')
        pending = ingest_message(self.session, source=message, source_ref='普通新轮次测试fixture')
        self.assertTrue(any('pending' in reason for reason in return_status(self.session)['cannot_close']))
        handle_message(self.session, message_id=pending['message_id'], action='ordinary', reason='未改变原完成对象')
        self.assertEqual(return_status(self.session)['current_receipt'], 'CLOSED')

    def _link(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=True)
            return 'symlink'
        except OSError:
            if os.name != 'nt':
                self.skipTest('directory symlinks unavailable')
            result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)],
                                    capture_output=True, check=False)
            if result.returncode:
                self.skipTest('neither directory symlinks nor task-local junctions available')
            return 'junction'

    def test_source_and_artifact_alias_retargeting_with_identical_bytes_is_stale(self):
        one, two = self.base / 'one', self.base / 'two'
        one.mkdir(); two.mkdir()
        for directory in (one, two):
            (directory / 'same.txt').write_bytes(b'exactly identical bytes')
        alias = self.base / 'selected'
        for field in ('sources', 'artifacts'):
            kind = self._link(alias, one)
            self.data['sources'] = ['selected/same.txt'] if field == 'sources' else []
            self.data['artifacts'] = [{'label': '当前成品', 'path': 'selected/same.txt'}] if field == 'artifacts' else []
            self.save()
            seal_return(self.session, self.input)
            os.rmdir(alias) if kind == 'junction' else alias.unlink()
            kind = self._link(alias, two)
            stale = return_status(self.session)
            self.assertEqual(stale['current_receipt'], 'STALE')
            self.assertTrue(any('redirected' in issue for issue in stale['issues']))
            os.rmdir(alias) if kind == 'junction' else alias.unlink()

    def test_stop_precedes_packaging_and_legacy_is_not_upgraded(self):
        activity(self.session, 'COMMON', 'begin', state='SOURCE', scope='FOUNDATION')
        stopped = close_return(self.session, reason='测试用户真实停止分支', outcome='STOPPED')
        self.assertEqual(stopped['lifecycle_status'], 'STOPPED')
        self.assertEqual(stopped['current_receipt'], 'MISSING')
        self.assertFalse((self.session / 'current-return.json').exists())
        legacy = self.base / 'legacy'
        create_session(legacy, request=self.request, p_run='0.5.1@' + 'a' * 40)
        self.assertEqual(seal_return(legacy, self.input)['lifecycle_status'], 'LEGACY_UNMANAGED')
        with self.assertRaisesRegex(ValueError, 'legacy session'):
            close_return(legacy, reason='不应静默升级')
        self.assertFalse((legacy / 'lifecycle.json').exists())

    def test_missing_snapshot_and_mutable_control_inputs_do_not_claim_normal_close(self):
        with self.assertRaisesRegex(ValueError, 'current sealed return'):
            close_return(self.session, reason='无返回不能正常终结')
        self.data['sources'] = ['session/lifecycle.json']
        self.save()
        with self.assertRaisesRegex(ValueError, 'control files'):
            seal_return(self.session, self.input)

    def test_matching_bytes_are_not_semantic_approval_and_cli_checks_actual_state(self):
        self.data['result'] = '这个文本故意没有回答真实题目；机制不能认证语义。'
        self.save()
        self.assertFalse(seal_return(self.session, self.input)['semantic_certification'])
        command = [sys.executable, '-B', str(ROOT / 'tools/codex_return.py'), 'status', '--root', str(self.session)]
        ready = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(ready.returncode, 0, ready.stderr)
        self.assertEqual(json.loads(ready.stdout)['current_receipt'], 'READY_UNCLOSED')
        self.input.write_text('{}', encoding='utf-8')
        stale = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(stale.returncode, 2)
        self.assertEqual(json.loads(stale.stdout)['current_receipt'], 'STALE')


if __name__ == '__main__':
    unittest.main()
