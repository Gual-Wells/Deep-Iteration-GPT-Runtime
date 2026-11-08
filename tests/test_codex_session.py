from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from runtime.codex_session import (
    activity, capture_clock, create_line, create_session, derive_activity,
    line_packet, session_report, set_line_parameters,
    summarize_activity, update_line, windows_process_anchor,
)

ROOT = Path(__file__).resolve().parents[1]
MINUTE = 60_000_000_000
PIN = '0.5.1@11631eec1cbf3397a2b4d6d7cc24190188c0d2d6'


def parameters(**updates):
    values = {'N': 12, 'T': '45min', 'R': 4, 'B': 0,
              'S': {'n': 3, 't': '20min', 'r': 1, 'b': 0}, 'D': 3, 'V': 3, 'L': 3}
    values.update(updates)
    return values


def stamp(minute, domain='constructed-A'):
    return {'provider': 'constructed-test-fixture', 'domain': domain,
            'monotonic_ns': minute * MINUTE if domain is not None else None,
            'wall_ns': minute * MINUTE, 'clock_basis': 'constructed-not-observed'}


def event(action, minute, state=None, *, domain='constructed-A'):
    value = {'action': action, 'at': stamp(minute, domain)}
    if state is not None:
        value['state'] = state
    if action in ('end', 'checkpoint'):
        value['declared_continuity'] = True
    return value


class SessionTests(unittest.TestCase):
    def setUp(self):
        cache = (ROOT / '.cache').resolve()
        cache.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='codex-session-test-', dir=cache)
        self.root = Path(self.temporary.name).resolve()
        if not self.root.is_relative_to(cache) or not self.root.name.startswith('codex-session-test-'):
            raise RuntimeError('refusing cleanup outside the intended task cache')
        self.addCleanup(self.temporary.cleanup)
        self.request = self.root / 'request.txt'
        self.request.write_bytes(b'\xef\xbb\xbf' + '保留原页，将给定材料组装成可阅读文件。\r\n'.encode('utf-8'))
        self.decisions = self.root / 'DECISIONS.md'
        self.decisions.write_text('用户已定：先交英文原文。\n', encoding='utf-8')
        self.session = self.root / 'session'
        create_session(self.session, request=self.request, p_run=PIN, decisions=self.decisions)

    def line(self, line_id='M01', **kwargs):
        return create_line(self.session, line_id, parameters=parameters(), **kwargs)

    def test_literal_request_pin_and_existing_session_survive(self):
        self.assertEqual((self.session / 'REQUEST.txt').read_bytes(), self.request.read_bytes())
        self.assertEqual(session_report(self.session)['session']['M_target'], 1)
        original = (self.session / 'session.json').read_bytes()
        with self.assertRaises(FileExistsError):
            create_session(self.session, request=self.request, p_run=PIN)
        self.assertEqual((self.session / 'session.json').read_bytes(), original)
        self.request.write_text('外部输入后来被改写。', encoding='utf-8')
        self.line()
        packet = line_packet(self.session, 'M01')
        self.assertIn('保留原页', packet)
        self.assertNotIn('外部输入后来被改写', packet)
        self.assertEqual(session_report(self.session)['session']['P_run'], PIN)
        (self.session / 'REQUEST.txt').write_text('静默替换U0。', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'frozen'):
            session_report(self.session)

    def test_complete_individual_parameters_preserve_explicit_input_and_reasons(self):
        other_session = self.root / 'different-session'
        explicit = {'M': 2, 'N': 18, 'T': '120min', 'S': {'t': '45min'}}
        create_session(other_session, request=self.request, p_run=PIN, explicit_parameters=explicit)
        one = create_line(other_session, 'M01', parameters=parameters(N=20, T='120min'),
                          parameter_reasons={'N': '独立路线需要更深资料工作。'})
        two = create_line(other_session, 'M02', parameters=parameters(N=24, T=7200),
                          parameter_reasons={'N': '本线需重做接口路线。', 'T': 'API值以秒表示同一目标。'})
        report = session_report(other_session)
        self.assertEqual(report['session']['explicit_parameters'], explicit)
        self.assertEqual(report['session']['M_target'], 2)
        self.assertEqual(one['parameters']['N'], 20)
        self.assertEqual(two['parameters']['N'], 24)
        self.assertEqual(two['parameters']['T'], 7200)
        self.assertIn('独立路线', one['explicit_parameter_differences'][0]['reason'])
        self.assertEqual(report['registered_line_count'], 2)
        self.assertIsNone(report['effective_M_count'])
        self.assertEqual(one['responsibility_status'], 'UNVERIFIED')
        self.assertIsNone(one['owner'])

    def test_invalid_parameters_fail_before_preparing_a_line(self):
        for changes in ({'L': 2}, {'N': True}, {'T': '45'}, {'B': 2}, {'T': float('inf')}, {'T': -1}):
            with self.subTest(changes=changes), self.assertRaises((TypeError, ValueError)):
                create_line(self.session, 'M01', parameters=parameters(**changes))
        incomplete = parameters()
        del incomplete['V']
        with self.assertRaisesRegex(ValueError, 'complete'):
            create_line(self.session, 'M01', parameters=incomplete)
        self.assertFalse((self.session / 'lines' / 'M01').exists())
        with self.assertRaises(ValueError):
            create_line(self.session, '../escape', parameters=parameters())

    def test_parameter_adjustment_retains_previous_target_without_counting_progress(self):
        self.line()
        package = set_line_parameters(self.session, 'M01', parameters=parameters(N=16),
                                      reasons={'N': '新增关键证据改变了研究范围。'})
        self.assertEqual(package['parameters']['N'], 16)
        self.assertEqual(package['parameter_changes'][0]['changes'][0]['explicit'], 12)
        self.assertEqual(package['content_status'], 'PREPARED')
        self.assertEqual(package['responsibility_status'], 'UNVERIFIED')
        with self.assertRaisesRegex(ValueError, 'reduced'):
            set_line_parameters(self.session, 'M01', parameters=parameters(), reasons={'N': '想快点结束。'})

    def test_actual_user_revision_can_lower_target_and_keeps_its_reference(self):
        self.line()
        revision = '用户补充原话：本项收窄为只验证恢复行为，N改为4，R改为1。'
        package = set_line_parameters(self.session, 'M01', parameters=parameters(N=4, R=1),
                                      reasons={'N': '用户明确收窄范围。', 'R': '同一条用户修订。'},
                                      user_revision=revision)
        self.assertEqual(package['parameters']['N'], 4)
        self.assertEqual(package['parameters']['R'], 1)
        self.assertEqual(package['parameter_changes'][0]['user_revision'], revision)
        self.assertEqual(package['parameter_changes'][0]['changes'][0]['explicit'], 12)
        self.assertEqual(package['responsibility_status'], 'UNVERIFIED')
        with self.assertRaisesRegex(ValueError, 'reduced'):
            set_line_parameters(self.session, 'M01', parameters=parameters(N=3, R=1),
                                reasons={'N': '自主减少仍不允许。'})

    def test_resume_gets_latest_correction_own_artifact_and_unhandled_work(self):
        existing = self.root / 'existing-work.md'
        notes = '# 已有研究\n\n## 原页路线\n小样缺依赖页，先对照原件。\n'
        existing.write_text(notes, encoding='utf-8')
        self.line(work=existing)
        other = self.line('M02')
        Path(other['work']).write_text('# M02私有研究\n不应出现在M01包内。\n', encoding='utf-8')
        # An unrelated damaged clock stream must not prevent M01 resumption.
        (self.session / 'lines' / 'M02' / 'activity.jsonl').write_text('{partial', encoding='utf-8')
        candidate = self.root / 'reader.pdf'
        candidate.write_bytes(b'%PDF-1.7\n\xff\x00binary-output')
        update_line(self.session, 'M01', candidate=candidate, content_status='CANDIDATE',
                    responsibility_status='IN_PROGRESS', next_action='补依赖页并打开小样。',
                    unhandled=['D01关于跨页公式的返回仍待处理。'], owner='native-agent-reference')
        self.decisions.write_text('用户最新纠正：目录保留原页码。\n', encoding='utf-8')
        packet = line_packet(self.session, 'M01', topic='原页路线')
        for expected in ('保留原页', '目录保留原页码', 'reader.pdf', '跨页公式', '补依赖页'):
            self.assertIn(expected, packet)
        self.assertNotIn('不应出现在M01包内', packet)
        self.assertNotIn('binary-output', packet)
        self.assertEqual(existing.read_text(encoding='utf-8'), notes)
        candidate.write_bytes(b'%PDF-1.7\nchanged')
        self.assertIn('旧状态与评审不能自动覆盖当前文件', line_packet(self.session, 'M01'))

    def test_directory_candidate_is_an_entrypoint_not_recursive_certification(self):
        self.line()
        folder = self.root / 'actual-product'
        folder.mkdir()
        update_line(self.session, 'M01', candidate=folder, content_status='DRAFT',
                    responsibility_status='IN_PROGRESS', next_action='运行真实用户路径。')
        packet = line_packet(self.session, 'M01')
        self.assertIn('entrypoint only', packet)
        self.assertIn(folder.as_posix(), packet)

    def test_context_budget_does_not_silently_truncate_original_or_corrections(self):
        package = self.line()
        original = Path(package['work']).read_bytes()
        with self.assertRaises(ValueError):
            line_packet(self.session, 'M01', max_chars=100)
        self.assertEqual(Path(package['work']).read_bytes(), original)

    def test_current_user_correction_follows_old_plan_without_promoting_model_proposals(self):
        work = self.root / 'old-work.md'
        old_action = '下一步修改当前实现、重做全书并部署。'
        original = ('# 旧工作笔记\n\n## 当前关键问题\n怎样重做当前实现？\n\n'
                    '## 当前产物与可继续的位置\n当前产品应改版。\n\n'
                    '## 值得继续的工作\n' + old_action + '\n')
        work.write_text(original, encoding='utf-8')
        self.line(work=work)
        correction = '用户原话：这轮只导出指定历史版本，不能变成修补当前版。'
        proposal = 'Main未获确认的提议：之后可以另做网站。'
        self.decisions.write_text(correction + '\n\n' + proposal + '\n', encoding='utf-8')
        packet = line_packet(self.session, 'M01')
        self.assertIn('保留原页', packet)
        self.assertIn(old_action, packet)
        self.assertIn(proposal, packet)
        self.assertGreater(packet.index(correction), packet.rindex(old_action))
        self.assertEqual(packet.count(correction), 1)
        self.assertIn('不能把模型建议', packet)
        self.assertIn('不因旧记录写成', packet)
        self.assertEqual(work.read_text(encoding='utf-8'), original)

    def test_unified_cli_preserves_individual_targets_recovery_and_common_time(self):
        cli = [sys.executable, '-B', str(ROOT / 'tools' / 'codex.py')]

        def call(*args, expected=0):
            result = subprocess.run([*cli, *map(str, args)], cwd=ROOT, capture_output=True,
                                    text=True, encoding='utf-8')
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            return result.stdout if expected == 0 else result.stderr

        folder = self.root / 'cli-session'
        explicit = self.root / 'explicit.json'
        explicit.write_text(json.dumps({'M': 2, 'N': 12, 'R': 4}), encoding='utf-8')
        params = self.root / 'params.json'
        params.write_text(json.dumps(parameters()), encoding='utf-8')
        anchor_args = ('--anchor-pid', os.getpid()) if sys.platform == 'win32' else ()
        call('task', 'create', '--out', folder, '--request', self.request, '--p-run', PIN,
             '--decisions', self.decisions, '--explicit', explicit, *anchor_args)
        call('line', 'create', '--root', folder, '--id', 'M01', '--parameters', params)
        params.write_text(json.dumps(parameters(N=16)), encoding='utf-8')
        call('line', 'create', '--root', folder, '--id', 'M02', '--parameters', params)
        call('clock', 'begin', '--root', folder, '--owner', 'M01', '--state', 'MAIN')
        candidate = self.root / 'actual-export.txt'
        candidate.write_bytes(b'preserved historical bytes\r\n')
        status = self.root / 'status.json'
        status.write_text(json.dumps({'candidate': candidate.name, 'content_status': 'SAMPLE_EXPORTED',
            'responsibility_status': 'FULL_M_NOT_VERIFIED', 'next_action': 'Open the preserved export',
            'unhandled': ['actual independent Main responsibilities are outside the CLI exercise']}), encoding='utf-8')
        call('line', 'update', '--root', folder, '--id', 'M01', '--input', status)
        call('clock', 'checkpoint', '--root', folder, '--owner', 'M01', '--continued')
        call('clock', 'begin', '--root', folder, '--owner', 'M02', '--state', 'SOURCE')
        call('line', 'packet', '--root', folder, '--id', 'M02')
        call('clock', 'end', '--root', folder, '--owner', 'M02', '--continued')
        call('clock', 'begin', '--root', folder, '--owner', 'COMMON', '--state', 'MAIN')
        before = json.loads(call('task', 'report', '--root', folder))
        call('clock', 'end', '--root', folder, '--owner', 'COMMON', '--continued')
        self.assertEqual(before['registered_line_count'], 2)
        self.assertIsNone(before['effective_M_count'])
        self.assertEqual(before['line_packages']['M02']['parameters']['N'], 16)
        revision = '用户修订原话：只导出指定历史版本，本线N改4、R改1。'
        self.decisions.write_text(revision + '\nMain提议另做网站，尚未确认。\n', encoding='utf-8')
        params.write_text(json.dumps(parameters(N=4, R=1)), encoding='utf-8')
        call('line', 'parameters', '--root', folder, '--id', 'M01', '--parameters', params,
             '--user-revision', revision)
        params.write_text(json.dumps(parameters(N=3, R=1)), encoding='utf-8')
        self.assertIn('reduced', call('line', 'parameters', '--root', folder, '--id', 'M01',
                                     '--parameters', params, expected=2))
        call('clock', 'recover', '--root', folder, '--owner', 'M01', '--reason', 'previous CLI tail was not closed')
        call('clock', 'begin', '--root', folder, '--owner', 'M01', '--state', 'SOURCE')
        packet = call('line', 'packet', '--root', folder, '--id', 'M01')
        call('clock', 'end', '--root', folder, '--owner', 'M01', '--continued')
        self.assertIn(revision, packet)
        report = json.loads(call('clock', 'report', '--root', folder))
        self.assertEqual(report, json.loads(call('task', 'report', '--root', folder)))
        self.assertEqual(report['session']['explicit_parameters'], {'M': 2, 'N': 12, 'R': 4})
        self.assertEqual(report['line_packages']['M01']['parameters']['N'], 4)
        self.assertEqual(report['line_packages']['M01']['parameter_changes'][-1]['user_revision'], revision)
        self.assertTrue(report['timing']['has_recorded_gaps'])
        self.assertIn('COMMON', report['timing']['lines'])
        if sys.platform == 'win32' or sys.platform.startswith('linux'):
            self.assertGreater(report['timing']['lines']['M01']['known_union_ns']['T_ns'], 0)
            total = report['timing']['global_known_union_ns']['T_ns']
            sum_of_parts = sum(item['known_union_ns']['T_ns'] for item in report['timing']['lines'].values())
            self.assertLessEqual(total, sum_of_parts)

        if sys.platform == 'win32':
            child = subprocess.Popen([sys.executable, '-B', '-c', 'import sys; sys.stdin.read()'], stdin=subprocess.PIPE)
            try:
                call('clock', 'anchor', '--root', folder, '--pid', child.pid,
                     '--reason', 'explicit alternate live process for the CLI domain comparison')
                call('clock', 'begin', '--root', folder, '--owner', 'M02', '--state', 'MAIN')
                call('line', 'packet', '--root', folder, '--id', 'M02')
                call('clock', 'end', '--root', folder, '--owner', 'M02', '--continued')
                domains = json.loads(call('clock', 'report', '--root', folder))['timing']
                self.assertIsNone(domains['global_known_union_ns'])
                self.assertEqual(len(domains['global_known_by_clock_domain']), 2)
                self.assertIsNone(domains['lines']['M02']['known_union_ns'])
            finally:
                child.stdin.close()
                child.wait(timeout=10)

    def test_open_tail_recovery_keeps_only_explicitly_closed_prefix(self):
        self.line()
        with patch('runtime.codex_session.capture_clock', side_effect=[stamp(0), stamp(4), stamp(10), stamp(12), stamp(14)]):
            activity(self.session, 'M01', 'begin', state='SOURCE')
            activity(self.session, 'M01', 'checkpoint', continued=True)
            before = session_report(self.session)['timing']['lines']['M01']
            self.assertEqual(before['known_union_ns']['T_ns'], 4 * MINUTE)
            self.assertEqual(before['gaps'][0]['reason'], 'unclosed-tail-not-counted')
            activity(self.session, 'M01', 'recover', reason='实际发生中断，旧尾段未知。')
            activity(self.session, 'M01', 'begin', state='MAIN')
            activity(self.session, 'M01', 'end', continued=True)
        after = session_report(self.session)['timing']
        self.assertEqual(after['lines']['M01']['known_union_ns'], {'T_ns': 6 * MINUTE, 't_ns': 4 * MINUTE})
        self.assertEqual(after['gaps'][0]['start']['monotonic_ns'], 4 * MINUTE)
        self.assertEqual(after['gaps'][0]['end']['monotonic_ns'], 10 * MINUTE)
        self.assertEqual(after['gaps'][0]['reason'], '实际发生中断，旧尾段未知。')

    def test_new_cli_call_cannot_implicitly_end_or_restart_activity(self):
        self.line()
        activity(self.session, 'M01', 'begin', state='MAIN')
        path = self.session / 'lines' / 'M01' / 'activity.jsonl'
        original = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'continuity'):
            activity(self.session, 'M01', 'end')
        with self.assertRaisesRegex(ValueError, 'recover'):
            activity(self.session, 'M01', 'begin', state='SOURCE')
        self.assertEqual(path.read_bytes(), original)
        self.assertIsNone(session_report(self.session)['timing']['global_known_union_ns'])

    def test_clock_unavailable_does_not_block_candidate_production(self):
        self.line()
        with patch('runtime.codex_session.capture_clock', side_effect=[stamp(0, None), stamp(4, None)]):
            activity(self.session, 'M01', 'begin', state='MAIN')
            activity(self.session, 'M01', 'end', continued=True)
        candidate = self.root / 'result.txt'
        candidate.write_text('实际可用的产物仍能保存与接续。', encoding='utf-8')
        update_line(self.session, 'M01', candidate=candidate, content_status='CANDIDATE',
                    responsibility_status='IN_PROGRESS', next_action='打开检查成品。')
        report = session_report(self.session)
        self.assertIsNone(report['timing']['global_known_union_ns'])
        self.assertEqual(report['timing']['gaps'][0]['reason'], 'clock-domain-or-boundary-unverifiable')
        self.assertIn(candidate.as_posix(), line_packet(self.session, 'M01'))

    def test_partial_activity_report_preserves_packages_but_never_infers_whole_task_union(self):
        self.line()
        self.line('M02')
        one = self.session / 'lines' / 'M01' / 'activity.jsonl'
        two = self.session / 'lines' / 'M02' / 'activity.jsonl'
        common = self.session / 'common' / 'activity.jsonl'
        one.write_text('\n'.join(json.dumps(item) for item in
                                 [event('begin', 0, 'SOURCE'), event('end', 5)]) + '\n', encoding='utf-8')
        original = ('\n'.join(json.dumps(item) for item in
                              [event('begin', 2, 'MAIN', domain='constructed-B'),
                               event('end', 6, domain='constructed-B')]) + '\n').encode('utf-8')
        two.write_bytes(original)
        common.write_text('\n'.join(json.dumps(item) for item in
                                    [event('begin', 6, 'MAIN'), event('end', 7)]) + '\n', encoding='utf-8')
        healthy = session_report(self.session)
        self.assertEqual(healthy['report_status'], 'READABLE')
        self.assertEqual(healthy['issues'], [])
        self.assertEqual(len(healthy['timing']['global_known_by_clock_domain']), 2)
        damaged = original + b'{"action":'
        two.write_bytes(damaged)
        report = session_report(self.session)
        self.assertEqual(report['report_status'], 'PARTIAL_READ')
        self.assertEqual(set(report['line_packages']), {'M01', 'M02'})
        self.assertEqual(report['registered_line_count'], 2)
        self.assertIsNone(report['effective_M_count'])
        self.assertEqual(report['issues'][0]['owner'], 'M02')
        self.assertEqual(report['issues'][0]['path'], two.as_posix())
        timing = report['timing']
        self.assertEqual(timing['unreadable_activity_owners'], ['M02'])
        self.assertIsNone(timing['global_known_union_ns'])
        self.assertIsNone(timing['single_comparable_domain'])
        self.assertTrue(timing['available_single_comparable_domain'])
        self.assertEqual(timing['available_global_known_union_ns'], {'T_ns': 6 * MINUTE, 't_ns': 5 * MINUTE})
        self.assertEqual(timing['lines']['M01']['known_union_ns'], {'T_ns': 5 * MINUTE, 't_ns': 5 * MINUTE})
        self.assertEqual(timing['lines']['COMMON']['known_union_ns'], {'T_ns': MINUTE, 't_ns': 0})
        self.assertEqual(timing['lines']['M02']['recording_status'], 'UNREADABLE')
        self.assertIsNone(timing['lines']['M02']['known_union_ns'])
        self.assertIsNone(timing['lines']['M02']['closed_interval_count'])
        self.assertEqual(two.read_bytes(), damaged)
        with self.assertRaises(ValueError):
            activity(self.session, 'M02', 'recover', reason='must not auto-repair a broken log')
        self.assertEqual(two.read_bytes(), damaged)
        # Explicit restoration of a known test backup is separate from the
        # read-only reporter and proves its corruption handling wrote nothing.
        two.write_bytes(original)
        restored = session_report(self.session)
        self.assertEqual(restored, healthy)

    def test_unreadable_common_activity_is_unknown_and_not_credited_to_an_m(self):
        self.line()
        one = self.session / 'lines' / 'M01' / 'activity.jsonl'
        one.write_text('\n'.join(json.dumps(item) for item in
                                 [event('begin', 0, 'SOURCE'), event('end', 3)]) + '\n', encoding='utf-8')
        (self.session / 'common' / 'activity.jsonl').write_text('{partial', encoding='utf-8')
        report = session_report(self.session)
        timing = report['timing']
        self.assertEqual(report['report_status'], 'PARTIAL_READ')
        self.assertEqual(timing['unreadable_activity_owners'], ['COMMON'])
        self.assertEqual(timing['lines']['M01']['known_union_ns'], {'T_ns': 3 * MINUTE, 't_ns': 3 * MINUTE})
        self.assertEqual(timing['lines']['COMMON']['recording_status'], 'UNREADABLE')
        self.assertIsNone(timing['global_known_union_ns'])
        self.assertEqual(timing['available_global_known_union_ns'], {'T_ns': 3 * MINUTE, 't_ns': 3 * MINUTE})

    def test_semantically_broken_and_nonfinite_activity_stay_local_issues(self):
        self.line()
        self.line('M02')
        log = self.session / 'lines' / 'M02' / 'activity.jsonl'
        for raw in (json.dumps(event('end', 3)), '{"action":"begin","state":"MAIN","at":4}',
                    '{"action":"begin","state":"MAIN","at":{"wall_ns":NaN}}'):
            with self.subTest(raw=raw):
                log.write_text(raw + '\n', encoding='utf-8')
                report = session_report(self.session)
                self.assertEqual(report['report_status'], 'PARTIAL_READ')
                self.assertEqual(report['timing']['unreadable_activity_owners'], ['M02'])
                self.assertEqual(report['registered_line_count'], 2)
                self.assertIsNone(report['timing']['global_known_union_ns'])
                json.dumps(report, allow_nan=False)
                self.assertEqual(log.read_text(encoding='utf-8'), raw + '\n')

    def test_partial_activity_read_does_not_hide_task_or_package_identity_failure(self):
        self.line()
        self.line('M02')
        log = self.session / 'lines' / 'M02' / 'activity.jsonl'
        log.write_text('{partial', encoding='utf-8')
        path = self.session / 'lines' / 'M02' / 'line.json'
        original = path.read_bytes()
        path.write_text('{broken package', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'line package is unreadable'):
            session_report(self.session)
        package = json.loads(original.decode('utf-8'))
        package['line_id'] = 'M99'
        path.write_text(json.dumps(package), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            session_report(self.session)
        path.write_bytes(original)
        (self.session / 'REQUEST.txt').write_text('incorrectly substituted original request', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'frozen'):
            session_report(self.session)


class ActivityArithmeticTests(unittest.TestCase):
    def test_parallel_union_common_and_real_gap_are_distinct(self):
        facts = summarize_activity({
            'M01': [event('begin', 0, 'SOURCE'), event('end', 4), event('begin', 4, 'MAIN'),
                    event('checkpoint', 10), event('recover', 12), event('begin', 12, 'SOURCE'), event('end', 18)],
            'M02': [event('begin', 3, 'MAIN'), event('end', 6), event('begin', 6, 'SOURCE'), event('end', 14),
                    event('begin', 18, 'MAIN'), event('end', 20)],
            'COMMON': [event('begin', 20, 'SOURCE'), event('end', 22)],
        })
        self.assertEqual(facts['lines']['M01']['known_union_ns'], {'T_ns': 16 * MINUTE, 't_ns': 10 * MINUTE})
        self.assertEqual(facts['lines']['M02']['known_union_ns'], {'T_ns': 13 * MINUTE, 't_ns': 8 * MINUTE})
        self.assertEqual(facts['global_known_union_ns'], {'T_ns': 22 * MINUTE, 't_ns': 18 * MINUTE})
        self.assertTrue(facts['has_recorded_gaps'])
        self.assertEqual(len(facts['gaps']), 1)
        self.assertEqual(facts['gaps'][0]['owner'], 'M01')

    def test_multiple_clock_domains_do_not_turn_into_a_false_total(self):
        facts = summarize_activity({
            'M01': [event('begin', 0, 'MAIN'), event('end', 4),
                    event('begin', 5, 'MAIN', domain='constructed-B'), event('end', 7, domain='constructed-B')],
            'M02': [event('begin', 1, 'SOURCE'), event('end', 3)],
        })
        self.assertIsNone(facts['global_known_union_ns'])
        self.assertIsNone(facts['lines']['M01']['known_union_ns'])
        self.assertEqual(len(facts['global_known_by_clock_domain']), 2)
        self.assertFalse(facts['single_comparable_domain'])

    def test_nonformal_activities_and_unknown_tail_are_not_credited(self):
        facts = summarize_activity({'M01': [event('begin', 0, 'MAIN'), event('end', 2),
                                            event('begin', 2, 'V_EXCLUSIVE'), event('end', 20),
                                            event('begin', 20, 'IDLE'), event('end', 30),
                                            event('begin', 30, 'SOURCE')]})
        self.assertEqual(facts['lines']['M01']['known_union_ns'], {'T_ns': 2 * MINUTE, 't_ns': 0})
        self.assertEqual(facts['gaps'][0]['reason'], 'unclosed-tail-not-counted')

    def test_domain_change_or_backward_clock_becomes_gap(self):
        changed = derive_activity([event('begin', 1, 'MAIN'), event('end', 5, domain='constructed-B')])
        backwards = derive_activity([event('begin', 5, 'MAIN'), event('end', 1)])
        for facts in (changed, backwards):
            self.assertFalse(facts['spans'])
            self.assertEqual(facts['gaps'][0]['reason'], 'clock-domain-or-boundary-unverifiable')


class RealClockTests(unittest.TestCase):
    def test_actual_same_process_clock(self):
        first, second = capture_clock(), capture_clock()
        if first['domain'] is None or second['domain'] is None:
            self.skipTest('clock identity unavailable in this environment')
        self.assertEqual(first['domain'], second['domain'])
        self.assertGreaterEqual(second['monotonic_ns'], first['monotonic_ns'])
        self.assertTrue(first['clock_basis'].startswith('tool-observed/'))

    @unittest.skipUnless(sys.platform == 'win32', 'Windows live-process anchor')
    def test_actual_short_lived_processes_share_explicit_live_anchor(self):
        anchor = windows_process_anchor(os.getpid())
        code = ('import json,sys; from runtime.codex_session import capture_clock; '
                'print(json.dumps(capture_clock(json.loads(sys.argv[1]))))')
        command = [sys.executable, '-B', '-c', code, json.dumps(anchor)]
        first = json.loads(subprocess.check_output(command, cwd=ROOT, text=True, encoding='utf-8'))
        second = json.loads(subprocess.check_output(command, cwd=ROOT, text=True, encoding='utf-8'))
        self.assertIsNotNone(first['domain'])
        self.assertEqual(first['domain'], second['domain'])
        self.assertGreaterEqual(second['monotonic_ns'], first['monotonic_ns'])
        mismatch = capture_clock({**anchor, 'creation_100ns': anchor['creation_100ns'] + 1})
        self.assertIsNone(mismatch['domain'])

    @unittest.skipUnless(sys.platform == 'win32', 'Windows live-process anchor')
    def test_actual_dead_anchor_is_unknown(self):
        child = subprocess.Popen([sys.executable, '-B', '-c', 'import sys; sys.stdin.read()'], stdin=subprocess.PIPE)
        try:
            anchor = windows_process_anchor(child.pid)
            child.stdin.close()
            child.wait(timeout=10)
            missing = capture_clock(anchor)
            self.assertIsNone(missing['domain'])
            self.assertEqual(missing['clock_basis'], 'unavailable')
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)


if __name__ == '__main__':
    unittest.main()
