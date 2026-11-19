from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from runtime.codex_lifecycle import recover_session
from runtime.codex_profile import classify_invocation
from runtime.codex_session import create_line, create_session, line_packet, session_report, set_line_parameters
from tools.codex import main as codex


CALIBRATED_PIN = '1.1.1@' + 'a' * 40
HISTORICAL_PIN = '1.1.0@6792fe208058ca14f88cb902775203555843deea'
STANDARD = {'N': 2, 'T': 0, 'R': 1, 'B': 0, 'S': {'n': 0, 't': 0, 'r': 0, 'b': 0},
            'D': 0, 'V': 0, 'L': 3, 'M': 1}


def parameters(**updates):
    values = {'N': 8, 'T': '15min', 'R': 2, 'B': 0,
              'S': {'n': 2, 't': '5min', 'r': 1, 'b': 0}, 'D': 1, 'V': 1, 'L': 3}
    values.update(updates)
    return values


class CodexDepthCalibrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='codex-depth-calibration-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.request = self.root / 'request.txt'
        self.session = self.root / 'session'
        self.visits = self.root / 'visits.jsonl'

    def create(self, raw, *, pin=CALIBRATED_PIN, **kwargs):
        self.request.write_text(raw, encoding='utf-8')
        return create_session(self.session, request=self.request, p_run=pin, visits_path=self.visits, **kwargs)

    def cli(self, *args, expected=0):
        output = StringIO()
        error = StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            status = codex([str(arg) for arg in args])
        self.assertEqual(status, expected, error.getvalue())
        return json.loads(output.getvalue()) if expected == 0 else error.getvalue()

    def test_standard_alias_keeps_preference_separate_from_explicit_values_and_x(self):
        body = '  比较两条路线：保留任务原文\n(X=Other)'
        raw = '　DIGR（standard，N（7），S（n（2），t（5min）））（X＝Gmail）::' + body
        result = classify_invocation(raw, p_run=CALIBRATED_PIN)
        self.assertEqual(result['classification'], 'EXECUTING')
        self.assertEqual(result['task'], body)
        self.assertEqual(result['claude_selection'], 'ALLOW')
        self.assertEqual(result['delivery_selection'], {'mode': 'external', 'target': 'gmail', 'explicit': True})
        self.assertNotIn('depth_defaults', result)
        preference = result['depth_preferences']
        self.assertEqual(preference['preset'], 'Light')
        self.assertTrue(preference['preset_explicit'])
        self.assertEqual(preference['preference_baseline'], STANDARD)
        self.assertEqual(preference['explicit_overrides'], {'N': 7, 'S': {'n': 2, 't': '5min'}})
        self.assertEqual(preference['unparsed_tokens'], [])
        self.assertNotIn('parameters', preference)

    def test_default_and_positional_groups_have_no_named_overrides(self):
        for group in ('', '(16,60min,4,0,S(3,20min,2,0),3,3,3)'):
            with self.subTest(group=group):
                result = classify_invocation(f'DIGR{group}:研究实际任务', p_run=CALIBRATED_PIN)
                self.assertEqual(result['classification'], 'EXECUTING')
                self.assertEqual(result['execution_parameter_text'], group)
                preference = result['depth_preferences']
                self.assertEqual(preference['preset'], 'Default')
                self.assertFalse(preference['preset_explicit'])
                self.assertEqual(preference['preference_baseline'],
                                 {'N': 12, 'R': 4, 'B': 0, 'D': 3, 'V': 3, 'L': 3, 'M': 1})
                self.assertEqual(preference['explicit_overrides'], {})
                if group:
                    self.assertIn('60min', preference['unparsed_tokens'])
                    self.assertTrue(any('20min' in token for token in preference['unparsed_tokens']))
                else:
                    self.assertEqual(preference['unparsed_tokens'], [])

    def test_cli_persists_two_initial_lines_on_opposite_sides_of_one_preference(self):
        self.request.write_text('DIGR(More):比较不同的材料和执行路径', encoding='utf-8')
        invocation = self.cli('profile', 'classify', '--message-file', self.request, '--pin', CALIBRATED_PIN)
        session = self.cli('task', 'create', '--out', self.session, '--request', self.request,
                           '--p-run', CALIBRATED_PIN, '--visits', self.visits, '--m', '2')
        self.assertEqual(session['parameter_selection'], invocation['depth_preferences'])
        self.assertEqual(session['explicit_parameters'], {})
        self.assertEqual(session['M_target'], 2)
        self.assertEqual(session['parameter_selection']['preference_baseline'],
                         {'N': 18, 'R': 6, 'B': 0, 'D': 4, 'V': 4, 'L': 3, 'M': 1})
        with self.assertRaisesRegex(ValueError, 'L3'):
            create_line(self.session, 'M01', parameters=parameters(L=2))

        lower = parameters(N=5, R=1, D=0, V=0, T='8min')
        higher = parameters(N=21, R=7, D=5, V=6, T='35min')
        for line_id, effective, reason in (
            ('M01', lower, '关键事实已有来源，只需一次交叉核对。'),
            ('M02', higher, '竞争解释需要独立读源和比较多个例子。'),
        ):
            values = self.root / 'parameters.json'
            values.write_text(json.dumps(effective), encoding='utf-8')
            reasons = self.root / 'reasons.json'
            reasons.write_text(json.dumps({'N': reason}), encoding='utf-8')
            line = self.cli('line', 'create', '--root', self.session, '--id', line_id,
                            '--parameters', values, '--reasons', reasons)
            self.assertEqual(line['parameters'], effective)
            self.assertEqual(line['explicit_parameter_differences'], [])
            self.assertEqual(line['parameter_inference'],
                             {'basis': 'MAIN_SUPPLIED_INITIAL_PARAMETERS', 'reasons': {'N': reason}})

        with self.assertRaisesRegex(ValueError, 'cannot be silently reduced'):
            set_line_parameters(self.session, 'M01', parameters={**lower, 'N': 4}, reasons={})
        report = self.cli('task', 'report', '--root', self.session)
        self.assertEqual(report['line_packages']['M01']['parameters'], lower)
        self.assertEqual(report['line_packages']['M02']['parameters'], higher)

    def test_light_and_max_do_not_bound_initial_main_values(self):
        for tier, effective, task in (
            ('Light', parameters(N=0, R=0, D=0, V=0), '从已给的颜色值提取三个通道'),
            ('Max', parameters(N=31, R=11, D=8, V=7), '比较多个实现的恢复路径与并发反例'),
        ):
            with self.subTest(tier=tier):
                raw = f'DIGR({tier}):{task}'
                self.request.write_text(raw, encoding='utf-8')
                root = self.root / tier
                session = self.cli('task', 'create', '--out', root, '--request', self.request,
                                   '--p-run', CALIBRATED_PIN, '--visits', self.visits)
                self.assertEqual(session['parameter_selection']['preset'], tier)
                values = self.root / 'parameters.json'
                values.write_text(json.dumps(effective), encoding='utf-8')
                line = self.cli('line', 'create', '--root', root, '--id', 'M01', '--parameters', values)
                self.assertEqual(line['parameters'], effective)
                self.assertEqual(line['explicit_parameter_differences'], [])

    def test_main_target_inferred_after_task_creation_survives_recovery(self):
        raw = 'DIGR:比较互相独立的两个设计，最后给出取舍'
        self.request.write_text(raw, encoding='utf-8')
        initial = self.cli('task', 'create', '--out', self.session, '--request', self.request,
                           '--p-run', CALIBRATED_PIN, '--visits', self.visits)
        self.assertEqual(initial['M_target'], 1)
        session_file = self.session / 'session.json'
        original_session = session_file.read_bytes()

        reason = '两条设计可独立验证，最终必须对照兼容性和成本。'
        selected = self.cli('task', 'main-target', '--root', self.session, '--m', '2', '--reason', reason)
        self.assertEqual(selected['M_target'], 2)
        self.assertEqual(selected['M_target_reason'], reason)
        self.assertEqual(selected['explicit_parameters'], {})
        self.assertEqual(selected['parameter_selection'], initial['parameter_selection'])
        self.assertEqual(session_file.read_bytes(), original_session)

        create_line(self.session, 'M01', parameters=parameters())
        self.cli('task', 'recover', '--root', self.session, '--reason', '复开同一冻结任务')
        recovered = self.cli('task', 'report', '--root', self.session)
        self.assertEqual(recovered['session'], selected)
        packet = line_packet(self.session, 'M01')
        self.assertIn('"M_target": 2', packet)
        self.assertIn(f'"M_target_reason": "{reason}"', packet)

        from runtime.codex_return import _native_state
        sealed_facts = _native_state(self.session)
        self.assertEqual(sealed_facts['task']['M_target'], 2)
        self.assertEqual(sealed_facts['task']['M_target_reason'], reason)
        changed_reason = '第二条路线已经取得可独立检查的候选。'
        self.cli('task', 'main-target', '--root', self.session, '--m', '2', '--reason', changed_reason)
        self.assertEqual(_native_state(self.session)['task']['M_target_reason'], changed_reason)

    def test_session_merges_only_actual_explicit_input_and_detects_conflicts(self):
        header = '(More,M=2,N=7,S(n=2),S(r=1))'
        raw = f'DIGR{header}:研究实际任务'
        explicit_file = self.root / 'explicit.json'
        preview_args = ['profile', 'parameters', '--text', header, '--overrides', str(explicit_file)]

        explicit_file.write_text(json.dumps({'S': {'n': 3}}), encoding='utf-8')
        self.assertIn('original header: S.n', self.cli(*preview_args, expected=2))
        with self.assertRaisesRegex(ValueError, r'original header: S\.n'):
            self.create(raw, explicit_parameters={'S': {'n': 3}})
        with self.assertRaisesRegex(ValueError, 'original header: N'):
            self.create(raw, explicit_parameters={'N': 8})
        with self.assertRaisesRegex(ValueError, 'M target conflicts'):
            self.create(raw, m_target=1)
        self.assertFalse(self.session.exists())
        explicit = {'S': {'n': 2, 't': '5min'}}
        explicit_file.write_text(json.dumps(explicit), encoding='utf-8')
        preview = self.cli(*preview_args)
        session = self.create(raw, explicit_parameters=explicit)
        self.assertEqual(session['explicit_parameters'], {'M': 2, 'N': 7, 'S': {'n': 2, 't': '5min', 'r': 1}})
        self.assertEqual(preview['explicit_overrides'], session['explicit_parameters'])
        self.assertEqual(session['M_target'], 2)
        error = self.cli('task', 'main-target', '--root', self.session, '--m', '1',
                         '--reason', '尝试改变真实指定项', expected=2)
        self.assertIn('M target conflicts with explicit parameter record', error)
        line = create_line(self.session, 'M01', parameters=parameters(N=7))
        self.assertEqual(line['explicit_parameter_differences'], [])

    def test_booleans_cannot_replace_equal_integer_header_declarations(self):
        header = '(M=1,S(n=1))'
        self.request.write_text(f'DIGR{header}:核对显式字段', encoding='utf-8')
        explicit_file = self.root / 'explicit.json'
        for explicit, key in (({'M': True}, 'M'), ({'S': {'n': True}}, 'S.n')):
            with self.subTest(key=key):
                explicit_file.write_text(json.dumps(explicit), encoding='utf-8')
                error = self.cli('profile', 'parameters', '--text', header,
                                 '--overrides', explicit_file, expected=2)
                self.assertIn(f'original header: {key}', error)
                error = self.cli('task', 'create', '--out', self.session, '--request', self.request,
                                 '--p-run', CALIBRATED_PIN, '--visits', self.visits, '--m', '1',
                                 '--explicit', explicit_file, expected=2)
                self.assertIn(f'original header: {key}', error)
                self.assertFalse(self.session.exists())

    def test_invalid_header_never_arms_x_or_exposes_preferences(self):
        for group in ('(Less,L=2)(X)', '(Less,M=0)(X)', '(Less,B=2)(X)', '(Less,N=1,X=Gmail)'):
            with self.subTest(group=group):
                result = classify_invocation(f'DIGR{group}:研究实际任务', p_run=CALIBRATED_PIN)
                self.assertEqual(result['classification'], 'INVALID')
                self.assertEqual(result['delivery_selection']['mode'], 'local')
                self.assertIsNone(result.get('depth_preferences'))

    def test_frozen_1_1_0_pin_keeps_the_historical_selection_on_recovery(self):
        raw = 'DIGR(standard,N=7):旧版本任务'
        result = classify_invocation(raw, p_run=HISTORICAL_PIN)
        historical = {**STANDARD, 'N': 7}
        self.assertNotIn('depth_preferences', result)
        self.assertEqual(result['depth_defaults']['parameters'], historical)
        session = self.create(raw, pin=HISTORICAL_PIN)
        self.assertEqual(session['explicit_parameters'], historical)
        self.assertEqual(session['parameter_selection'], result['depth_defaults'])
        create_line(self.session, 'M01', parameters=parameters(N=7))
        recover_session(self.session, reason='Reopen frozen fixture')
        report = session_report(self.session)
        self.assertEqual(report['session'], session)
        line = report['line_packages']['M01']
        self.assertNotIn('parameter_inference', line)
        self.assertIn({'parameter': 'R', 'explicit': 1, 'effective': 2, 'reason': None},
                      line['explicit_parameter_differences'])


if __name__ == '__main__':
    unittest.main()
