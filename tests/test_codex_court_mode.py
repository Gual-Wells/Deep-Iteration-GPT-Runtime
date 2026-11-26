"""Constructed source-bound calls, not live routing or judicial approval."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from runtime.codex_court import required
from runtime.codex_foundation import BRIEF_FIELDS, foundation_packet, propose_foundation
from runtime.codex_lifecycle import handle_message, ingest_message, load_lifecycle
from runtime.codex_presets import resolve_defaults
from runtime.codex_profile import classify_invocation
from runtime.codex_return import _native_state
from runtime.codex_session import create_session, set_task_parameters, task_parameters

REPO = Path(__file__).resolve().parents[1]
NEW = '1.6.0@' + 'a' * 40
OLD = '1.5.2@' + 'b' * 40


class CourtModeTests(unittest.TestCase):
    def setUp(self):
        cache = REPO / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='court-mode-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.next_id = 0

    def session(self, head='Less,F=0', pin=NEW, explicit=None):
        self.next_id += 1
        request = self.base / f'request-{self.next_id}.txt'
        request.write_text('DIGR(' + head + ')：Synthetic task.\n', encoding='utf-8')
        root = self.base / f'task-{self.next_id}'
        create_session(root, request=request, p_run=pin, explicit_parameters=explicit)
        return root

    def message(self, root, text, *, action='continue', **choices):
        self.next_id += 1
        source = self.base / f'message-{self.next_id}.txt'
        source.write_text(text, encoding='utf-8')
        message = ingest_message(root, source=source, source_ref='synthetic:' + source.name,
                                 route_pin=NEW if text.startswith('DIGR') else None)
        return handle_message(root, message_id=message['message_id'], action=action,
                              reason='Synthetic current source interpretation.', **choices)

    def test_all_tier_defaults_and_explicit_binary_overrides(self):
        for tier in ('Light', 'Less', 'Default', 'More', 'Max'):
            for choice in (None, 0, 1):
                head = tier + ('' if choice is None else f',C={choice}')
                with self.subTest(head=head):
                    root = self.session(head)
                    expected = int(tier == 'Max') if choice is None else choice
                    self.assertEqual(task_parameters(root)['parameters']['C'], expected)
                    self.assertEqual(required(root), bool(expected))
                    self.assertEqual(task_parameters(root)['input_explicit']['C'], choice is not None)
                    self.assertEqual(task_parameters(root)['parameters']['X'], 0)

    def test_documented_complete_named_call_preserves_every_parameter_and_task(self):
        call = ('DIGR(N=10,T=90min,R=3,B=0,S(n=2,t=25min,r=1,b=0),'
                'D=2,V=2,L=3,M=1,X=0,F=2,C=1)：任务：正文\n')
        parsed = classify_invocation(call, p_run=NEW)
        self.assertEqual(parsed['classification'], 'EXECUTING')
        self.assertEqual(parsed['task'], '任务：正文\n')
        self.assertEqual(parsed['depth_preferences']['unparsed_tokens'], [])
        self.assertEqual(parsed['depth_preferences']['explicit_overrides'], {
            'N': 10, 'T': '90min', 'R': 3, 'B': 0,
            'S': {'n': 2, 't': '25min', 'r': 1, 'b': 0},
            'D': 2, 'V': 2, 'L': 3, 'M': 1, 'X': 0, 'F': 2, 'C': 1})

    def test_binary_surface_variants_and_malformed_calls(self):
        for value in ('C=0', 'C(0)', 'C（0）', 'C＝0'):
            parsed = classify_invocation(f'DIGR（Max，{value}）：task', p_run=NEW)
            self.assertEqual(parsed['classification'], 'EXECUTING', value)
            self.assertEqual(parsed['depth_preferences']['explicit_overrides']['C'], 0)
        for value in ('C', 'C=', 'C()', 'C=2', 'C=-1', 'C(1.0)', 'C=True',
                      'C=0,C=0', 'C=1,C(0)', 'S(C=1)'):
            self.assertEqual(classify_invocation(f'DIGR({value}):task', p_run=NEW)['classification'],
                             'INVALID', value)
        for value in (True, False, -1, 2, '1'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_defaults(overrides={'C': value})

    def test_same_task_tier_changes_do_not_reset_current_choice(self):
        for initial, changed, expected in (('Less,C=1', 'Less', 1), ('Max,C=0', 'Max', 0)):
            root = self.session(initial)
            self.message(root, f'DIGR({changed})：只调整生产投入。')
            self.message(root, '请继续处理现有任务。', action='ordinary')
            self.assertEqual(task_parameters(root)['parameters']['C'], expected)
        root = self.session('Less')
        self.message(root, 'DIGR(Max)：仅加深生产投入。')
        self.assertFalse(required(root))

    def test_current_explicit_selection_history_and_return_binding(self):
        root = self.session('More,C=1,F=0')
        before = _native_state(root)
        self.message(root, 'DIGR(C=0)：实际关闭本任务余下庭审。', action='ordinary')
        current = task_parameters(root)
        after = _native_state(root)
        self.assertEqual(current['parameters'], {'X': 0, 'F': 0, 'C': 0})
        self.assertFalse(required(root))
        self.assertEqual(len(after['court_selection_history']), 1)
        self.assertNotEqual(before['court_parameter_source'], after['court_parameter_source'])
        self.assertNotEqual(before['task_input_ref'], after['task_input_ref'])
        self.assertEqual(current['C_source']['basis'], 'INVOCATION_HEADER')
        self.assertEqual(current['C_source']['message_id'], 1)
        self.message(root, '重新启用当前任务庭审。', court_mode=1)
        self.assertTrue(required(root))
        self.assertEqual(task_parameters(root)['C_source']['basis'], 'CURRENT_USER_DECISION')
        self.assertEqual(task_parameters(root)['parameters']['F'], 0)

    def test_header_c_does_not_change_claude_or_delivery_permissions(self):
        root = self.session('Less,C=0,F=0')
        before = load_lifecycle(root)
        self.message(root, '庭审现在启用，其他选择继续。', court_mode=1)
        after = load_lifecycle(root)
        self.assertEqual(before['claude_policy'], after['claude_policy'])
        self.assertEqual(before['delivery_policy'], after['delivery_policy'])
        self.assertEqual(before['x_parameter_source'], after['x_parameter_source'])

    def test_parameter_records_cannot_inject_or_change_c(self):
        with self.assertRaisesRegex(ValueError, 'original user header'):
            self.session(explicit={'C': 1})
        root = self.session('Max,C=0,F=0')
        with self.assertRaisesRegex(ValueError, 'C changes require'):
            set_task_parameters(root, parameters={'C': 1, 'F': 0}, reasons={'F': 'Synthetic unchanged F.'})
        for choice in (True, '1', 2):
            with self.assertRaises((TypeError, ValueError)):
                set_task_parameters(root, parameters={'C': choice, 'F': 0}, reasons={'F': 'Synthetic.'})
        set_task_parameters(root, parameters={'C': 0, 'F': 0}, reasons={'F': 'Synthetic current choice.'})
        self.assertFalse(required(root))

    def test_ineligible_sources_and_conflicting_manual_choices_cannot_select_c(self):
        for text in ('DIGR/help', 'DIGR(C=2)：task'):
            root = self.session()
            with self.assertRaisesRegex(ValueError, 'cannot change C'):
                self.message(root, text, court_mode=1)
        root = self.session()
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            self.message(root, 'DIGR(C=0)：task', court_mode=1)
        root = self.session()
        with self.assertRaises((TypeError, ValueError)):
            self.message(root, 'DIGR(C=1)：task', court_mode=True)
        root = self.session()
        self.message(root, '停止当前任务。', action='stop')
        with self.assertRaisesRegex(ValueError, 'terminal'):
            self.message(root, '庭审启用。', action='ordinary', court_mode=1)

    def test_old_pins_keep_sticky_max_and_have_no_c_task_state(self):
        root = self.session('Max,F=0', OLD)
        self.assertTrue(required(root))
        self.assertNotIn('C', task_parameters(root)['parameters'])
        self.message(root, 'DIGR(Less,C=0)：旧pin继续原语义。')
        self.assertTrue(required(root))
        self.assertNotIn('court_parameter_source', load_lifecycle(root))
        self.assertNotIn('C', classify_invocation('DIGR(Max,C=0)：task', p_run=OLD)
                         ['depth_preferences']['explicit_overrides'])
        with self.assertRaisesRegex(ValueError, '1.6'):
            self.message(root, '当前旧任务关闭庭审。', court_mode=0)

    def test_c_source_corruption_cannot_silently_fall_back_to_max(self):
        for mutation in ('missing', 'wrong_binary', 'future', 'unknown_source', 'mismatch'):
            root = self.session('Max,F=0')
            file = root / 'lifecycle.json'
            state = json.loads(file.read_text(encoding='utf-8'))
            if mutation == 'missing':
                state.pop('court_parameter_source')
            elif mutation == 'wrong_binary':
                state['court_parameter_source']['value'] = True
            elif mutation == 'future':
                state['court_parameter_source']['message_id'] += 1
            elif mutation == 'unknown_source':
                state['court_parameter_source']['source_ref'] = 'synthetic:unknown'
            else:
                state['court_required'] = False
            file.write_text(json.dumps(state), encoding='utf-8')
            with self.subTest(mutation=mutation), self.assertRaises((TypeError, ValueError)):
                required(root)

    def test_real_u0_proposal_and_revision_carry_short_reminder_only_on_new_pins(self):
        proposal = {'brief': {key: 'Synthetic scoped U0: ' + title for key, title in BRIEF_FIELDS.items()},
                    'questions': []}
        for pin, expected in ((NEW, True), (OLD, False)):
            root = self.session(pin=pin)
            first = propose_foundation(root, deepcopy(proposal), reason='Synthetic actual U0 proposal.')
            second = propose_foundation(root, deepcopy(proposal), reason='Synthetic U0 revision.')
            self.assertEqual('post_u0_protocol_reminder' in first, expected)
            self.assertEqual('post_u0_protocol_reminder' in second, expected)
            self.assertEqual('U0后协议自提醒' in foundation_packet(root), expected)
            self.assertEqual(second['revision'], 2)
            self.assertFalse((root / 'lines/M02').exists())


if __name__ == '__main__':
    unittest.main()
