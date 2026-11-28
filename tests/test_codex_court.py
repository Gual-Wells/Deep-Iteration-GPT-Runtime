"""Constructed court records test structural gates, never real actor independence.

All dispatches, research, work and judgments here are explicitly synthetic.
No models, accounts, network transfers or actual semantic court are invoked.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from runtime.codex_court import (
    PARAMETERS, LEGACY_ROLES as ROLES, ROLES as CORRECTED_ROLES, court_status,
    open_court, record_docket, record_verdict, remand, require_delivery, review, submit_statement,
)
from runtime.codex_lifecycle import handle_message, ingest_message, load_lifecycle, recover_session
from runtime import codex_delivery as delivery
from runtime.codex_foundation import BRIEF_FIELDS, adopt_commission, propose_foundation
from runtime.codex_live import emit_work
from runtime.codex_usage import record_rate_limits
from runtime.codex_visits import append_visit
from runtime.codex_return import close_return, return_status, seal_return
from runtime.codex_session import create_line, create_session, set_task_parameters, task_delivery_policy, update_line

ROOT = Path(__file__).resolve().parents[1]
PIN = '1.5.0@' + 'a' * 40  # Constructed, never a live acquisition assertion.


class CourtFixture:
    pin = PIN
    roles = ROLES
    answer_roles = {'defendant', 'lawyer'}

    def setUp(self):
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='court-structural-', dir=cache)
        self.base = Path(self.temp.name).resolve()
        if not self.base.is_relative_to(cache.resolve()) or not self.base.name.startswith('court-structural-'):
            raise RuntimeError('refusing cleanup outside the known D task cache')
        self.addCleanup(self.temp.cleanup)
        self.sequence = 0
        self.request = self.base / 'request.txt'
        self.request.write_text('DIGR(Max,N=1,R=0,D=0,V=0,F=0)：解释给定问题并返回正文和文件。', encoding='utf-8')
        self.root = self.base / 'task'
        create_session(self.root, request=self.request, p_run=self.pin,
                       visits_path=self.base / 'visits.jsonl', run_id='synthetic-court')
        self.parameters = {'N': 1, 'T': 0, 'R': 0, 'B': 0,
                           'S': {'n': 0, 't': 0, 'r': 0, 'b': 0}, 'D': 0, 'V': 0, 'L': 3}
        create_line(self.root, 'M01', parameters=self.parameters, owner='fixture-main')
        self.product = self.base / 'product.txt'
        self.product.write_text('Constructed candidate one. Not a real delivered product.', encoding='utf-8')
        self.mark_complete()
        self.return_input = self.base / 'return.json'
        self.return_data = {'schema_version': 2, 'result': '构造正文，不声明真实研究或法庭效果。',
            'key_changes': '结构测试候选。',
            'work_process': '| 时间／记录范围 | 工作与后果 |\n| --- | --- |\n| 构造夹具 | 测试本地记录状态。 |',
            'argument_scope': '仅证明这些结构检查的预期行为。',
            'parameters': '构造参数不代表真实责任完成。',
            'artifacts': [{'label': '构造成品', 'path': str(self.product)}], 'sources': []}
        self.save_return()
        self.actors = {role: {'actor_id': 'fixture-' + ('main' if role == 'defendant' else role),
            'independent_context': role != 'defendant',
            'dispatch': self.source(role + '-dispatch', 'Synthetic dispatch; no real actor was scheduled.')}
            for role in self.roles}
        self.open_input = {'return_input': str(self.return_input), 'coverage':
            'Synthetic original request, current accepted conditions, process and final product coverage.',
            'producer_actor_ids': ['fixture-main'], 'actors': self.actors,
            'production': {'complete': True, 'statement': 'Synthetic completion claim; not certified.',
                           'source': self.source('production', 'Synthetic production record.')},
            'sources': [], 'obligations': []}

    def source(self, label, text=None):
        self.sequence += 1
        path = self.base / f'{self.sequence:03}-{label}.txt'
        path.write_text(text or f'Synthetic public source {label} {self.sequence}; no real actor execution.',
                        encoding='utf-8')
        return {'path': str(path), 'source_ref': f'synthetic:{self.sequence}:{label}'}

    def save_return(self):
        self.return_input.write_text(json.dumps(self.return_data, ensure_ascii=False), encoding='utf-8')

    def mark_complete(self):
        update_line(self.root, 'M01', candidate=self.product, content_status='COMPLETE',
                    responsibility_status='COMPLETE', next_action='Synthetic court fixture.', unhandled=[])

    def open(self):
        return open_court(self.root, self.open_input)

    def charge(self, identifier='C1', basis='PRODUCT', obligation=None):
        charge = {'id': identifier, 'basis_type': basis, 'requirement': 'The actual requested result is readable.',
            'finding': 'Synthetic allegation that a requested output is unreadable.',
            'consequence': 'If sustained, the actual requested output is not usable.', 'source_ids': ['request']}
        if obligation:
            charge['obligation_id'] = obligation
        return charge

    def statement(self, role, charges=None):
        status = court_status(self.root)
        return {'role': role, 'actor_id': self.actors[role]['actor_id'],
            'material_sha256': status['material_sha256'], 'read_sources': status['source_ids'],
            'statement': 'Synthetic public research statement, not actual independent reasoning.',
            'source': self.source(role + '-statement'), 'charges': charges or [],
            'responses': [{'charge_id': key, 'response': 'Synthetic reasoned answer with a source.',
                           'source_ids': ['request']} for key in status['charges']]
                          if role in self.answer_roles else []}

    def parties(self, charges=None):
        for role in ('prosecutor', 'monitor', 'judge', 'lawyer', 'defendant'):
            submit_statement(self.root, self.statement(role, charges if role == 'prosecutor' else []))

    def verdict(self, outcome='ACQUITTED', disposition='DISMISSED', admissibility='ADMITTED'):
        status = court_status(self.root)
        return {'actor_id': self.actors['judge']['actor_id'], 'material_sha256': status['material_sha256'],
            'outcome': outcome, 'reasons': 'Synthetic judge-authored case reasons; no semantic certification.',
            'source': self.source('verdict'),
            'decisions': [{'charge_id': key, 'admissibility': admissibility, 'disposition': disposition,
                           'reason': 'Synthetic finding tied to the requested outcome.',
                           'strongest_defence': 'Synthetic explicit response to the strongest defence.',
                           'consequence': 'Synthetic explicit practical consequence.'}
                          for key in status['charges']],
            'obligations': [{'id': key, 'status': 'COMPLETE', 'reason': 'Synthetic actual-responsibility finding.'}
                            for key in status['obligation_ids']]}

    def acquit(self, charges=None):
        self.open()
        self.parties(charges)
        return record_verdict(self.root, self.verdict())

    def rework_plan(self):
        state = json.loads((self.root / 'court/court.json').read_text(encoding='utf-8'))
        verdict = state['rounds'][-1]['verdict']
        outstanding = {key: 'Complete the actual sustained issue without discarding the original commission.'
                       for key, item in verdict['decisions'].items() if item['disposition'] == 'SUSTAINED'}
        outstanding.update({key: 'Fulfill the preserved original pending responsibility.'
                            for key, item in verdict['obligations'].items() if item['status'] == 'PENDING'})
        return {'parameters': {**self.parameters, 'M': 1, 'F': 0, 'X': 0},
                'parameter_reasons': {key: 'Synthetic task-based re-estimation reason.' for key in PARAMETERS},
                'reuse': 'Preserve the original commission and completed work.',
                'outstanding': outstanding,
                'work_required': 'Fix the particular sustained issue and its adjacent consequences.',
                'source': self.source('remand-plan')}

    def performed_work(self, addressed=None):
        return {'execution': {'performed': True, 'actor_id': 'fixture-main',
            'work': 'Synthetic declaration of performed repair, not a real execution claim.',
            'result': 'Synthetic new candidate and source record.',
            'adjacent_effects': 'Synthetic review of affected adjacent requirements.',
            'addressed': addressed or [], 'source': self.source('actual-work-fixture')}}


class CourtTests(CourtFixture, unittest.TestCase):

    def test_max_without_court_cannot_normally_close_even_at_low_counts(self):
        status = seal_return(self.root, self.return_input)
        self.assertEqual(status['current_receipt'], 'READY_UNCLOSED')
        self.assertFalse(status['can_close'])
        self.assertTrue(status['court_completion']['required'])
        with self.assertRaisesRegex(ValueError, 'Max'):
            close_return(self.root, reason='Not allowed to skip court.')
        self.assertEqual(load_lifecycle(self.root)['status'], 'ACTIVE')

    def test_legacy_max_and_new_more_do_not_acquire_new_max_obligations(self):
        for version, tier in (('1.4.1', 'Max'), ('1.5.0', 'More')):
            with self.subTest(version=version, tier=tier):
                request = self.base / f'{version}.txt'
                request.write_text(f'DIGR({tier},F=0)：构造研究。', encoding='utf-8')
                root = self.base / version
                create_session(root, request=request, p_run=version + '@' + 'b' * 40,
                               visits_path=self.base / 'visits.jsonl', run_id=version)
                status = seal_return(root, self.return_input)
                self.assertFalse(status['court_completion']['required'])
                self.assertTrue(status['can_close'])
                self.assertEqual(close_return(root, reason='Pinned synthetic semantics.')['current_receipt'], 'CLOSED')

    def test_actual_actor_conflicts_and_missing_dispatch_are_rejected(self):
        for role in ('judge', 'lawyer', 'monitor'):
            spec = deepcopy(self.open_input)
            spec['actors'][role]['actor_id'] = 'fixture-main'
            with self.assertRaisesRegex(ValueError, 'different actual actor|producer/Main'):
                open_court(self.root, spec)
        spec = deepcopy(self.open_input)
        spec['actors']['lawyer']['actor_id'] = spec['actors']['prosecutor']['actor_id']
        with self.assertRaisesRegex(ValueError, 'different actual actor'):
            open_court(self.root, spec)
        spec = deepcopy(self.open_input)
        del spec['actors']['judge']['dispatch']
        with self.assertRaisesRegex(ValueError, 'actual file'):
            open_court(self.root, spec)

    def test_complete_public_contestation_and_judge_reasons_can_close(self):
        result = self.acquit([self.charge()])
        self.assertTrue(result['can_close'])
        self.assertFalse(result['semantic_certification'])
        self.assertEqual(result['actors']['judge']['independence_basis'], 'HOST_ASSERTED')
        self.assertEqual(result['clerk']['kind'], 'ACTUAL_TOOL')
        sealed = seal_return(self.root, self.return_input)
        self.assertTrue(sealed['can_close'])
        closed = close_return(self.root, reason='Synthetic structural closure.')
        self.assertEqual(closed['current_receipt'], 'CLOSED')
        self.assertEqual(return_status(self.root)['court_completion']['status'], 'ACQUITTED')

    def test_missing_role_and_unanswered_accusation_do_not_count_as_acquittal(self):
        self.open()
        submit_statement(self.root, self.statement('prosecutor', [self.charge()]))
        with self.assertRaisesRegex(ValueError, 'all actual roles'):
            record_verdict(self.root, self.verdict())
        for role in ('monitor', 'judge', 'lawyer', 'defendant'):
            statement = self.statement(role)
            if role == 'lawyer':
                statement['responses'] = []
            submit_statement(self.root, statement)
        with self.assertRaisesRegex(ValueError, 'lawyer must answer'):
            record_verdict(self.root, self.verdict())

    def test_method_preferences_are_excluded_by_reasoned_judge_admission(self):
        self.open()
        self.parties([self.charge(basis='METHOD_PREFERENCE')])
        with self.assertRaisesRegex(ValueError, 'METHOD/PERMISSIONS'):
            record_verdict(self.root, self.verdict())
        result = record_verdict(self.root, self.verdict(admissibility='EXCLUDED'))
        self.assertTrue(result['can_close'])

    def test_immaterial_error_never_waives_hard_responsibilities(self):
        self.open()
        self.parties([self.charge(obligation='line:M01')])
        with self.assertRaisesRegex(ValueError, 'hard responsibility'):
            record_verdict(self.root, self.verdict('IMMATERIAL_ERROR', 'IMMATERIAL'))
        verdict = self.verdict()
        verdict['obligations'][0]['status'] = 'IMMATERIAL'
        with self.assertRaisesRegex(ValueError, 'hard responsibility'):
            record_verdict(self.root, verdict)
        verdict = self.verdict('IMMATERIAL_ERROR', 'IMMATERIAL')
        verdict['decisions'][0]['disposition'] = 'DISMISSED'
        verdict['obligations'][0]['status'] = 'PENDING'
        with self.assertRaisesRegex(ValueError, 'unresolved guilt or responsibilities'):
            record_verdict(self.root, verdict)

    def test_actual_bounded_immaterial_difference_can_close(self):
        self.open()
        self.parties([self.charge()])
        result = record_verdict(self.root, self.verdict('IMMATERIAL_ERROR', 'IMMATERIAL'))
        self.assertEqual(result['status'], 'IMMATERIAL_ERROR')
        self.assertTrue(seal_return(self.root, self.return_input)['can_close'])

    def test_guilty_plan_actual_reexecution_and_fresh_review_do_not_collapse(self):
        self.open()
        self.parties([self.charge()])
        result = record_verdict(self.root, self.verdict('REEXECUTE', 'SUSTAINED'))
        self.assertFalse(result['can_close'])
        with self.assertRaisesRegex(ValueError, 'complete custom remand'):
            review(self.root, self.performed_work(['C1']))
        plan = self.rework_plan()
        result = remand(self.root, plan)
        self.assertEqual(result['status'], 'REMAND_PLANNED_NOT_EXECUTED')
        self.assertFalse(seal_return(self.root, self.return_input)['can_close'])
        with self.assertRaisesRegex(ValueError, 'actual re-execution'):
            review(self.root, {'execution': {'performed': False}})
        same_plan = self.performed_work(['C1'])
        same_plan['execution']['source'] = plan['source']
        with self.assertRaisesRegex(ValueError, 'plan is not an actual execution receipt'):
            review(self.root, same_plan)
        self.product.write_text('Constructed repaired candidate two.', encoding='utf-8')
        self.mark_complete()
        result = review(self.root, self.performed_work(['C1']))
        self.assertEqual(result['cycle'], 2)
        self.assertEqual(result['status'], 'HEARING')
        self.assertIn('C1', result['charges'])
        self.assertIn('remand:1', result['obligation_ids'])
        with self.assertRaisesRegex(ValueError, 'all actual roles'):
            record_verdict(self.root, self.verdict())
        self.parties()
        self.assertTrue(record_verdict(self.root, self.verdict())['can_close'])
        self.assertTrue(seal_return(self.root, self.return_input)['can_close'])

    def test_small_custom_remand_preserves_old_duties_and_cannot_grant_x(self):
        self.open()
        self.parties([self.charge()])
        record_verdict(self.root, self.verdict('REEXECUTE', 'SUSTAINED'))
        plan = self.rework_plan()
        del plan['parameters']['F']
        with self.assertRaisesRegex(ValueError, 'complete N/T/R/B/S/D/V/L/M/F/X'):
            remand(self.root, plan)
        plan = self.rework_plan()
        plan['parameters']['X'] = 1
        with self.assertRaisesRegex(ValueError, 'cannot grant/change X'):
            remand(self.root, plan)
        plan = self.rework_plan()
        plan['outstanding'] = {}
        with self.assertRaisesRegex(ValueError, 'every sustained issue'):
            remand(self.root, plan)
        plan = self.rework_plan()
        plan['parameters']['N'] = 0
        self.assertEqual(remand(self.root, plan)['status'], 'REMAND_PLANNED_NOT_EXECUTED')
        self.mark_complete()
        result = review(self.root, self.performed_work(['C1']))
        self.assertIn('line:M01', result['obligation_ids'])
        self.assertIn('remand:1', result['obligation_ids'])
        self.parties()
        self.assertTrue(record_verdict(self.root, self.verdict())['can_close'])

    def test_new_candidate_and_final_return_substitution_invalidate_old_verdict(self):
        self.acquit()
        self.product.write_text('New bytes after judgment.', encoding='utf-8')
        self.assertEqual(court_status(self.root)['status'], 'STALE')
        self.assertFalse(seal_return(self.root, self.return_input)['can_close'])

    def test_other_final_file_or_answer_cannot_reuse_a_good_judgment(self):
        self.acquit()
        alternate = self.base / 'different-final.txt'
        alternate.write_text('An unexamined product.', encoding='utf-8')
        data = deepcopy(self.return_data)
        data['artifacts'][0]['path'] = str(alternate)
        different = self.base / 'different-return.json'
        different.write_text(json.dumps(data), encoding='utf-8')
        result = seal_return(self.root, different)
        self.assertEqual(result['court_completion']['status'], 'STALE')
        self.assertFalse(result['can_close'])
        data = deepcopy(self.return_data)
        data['result'] += ' New unexamined argument.'
        different.write_text(json.dumps(data), encoding='utf-8')
        self.assertFalse(seal_return(self.root, different)['can_close'])

    def test_process_report_update_after_judgment_does_not_change_the_product(self):
        self.return_data['artifacts'] = []
        self.save_return()
        self.acquit()
        self.return_data['parameters'] += ' Actual court source recording has now finished.'
        self.return_data['work_process'] += '\n| Actual later fixture record | Court source recording has finished. |'
        self.return_data['usage_report'] = {'fixture_scope': 'Later process data; not a real usage claim.'}
        self.save_return()
        self.assertTrue(court_status(self.root)['can_close'])
        self.assertTrue(seal_return(self.root, self.return_input)['can_close'])
        self.assertEqual(close_return(self.root, reason='Same adjudicated substantive text.')['current_receipt'], 'CLOSED')

    def test_pure_text_changes_and_argument_are_readable_adjudicated_product(self):
        self.return_data['artifacts'] = []
        self.return_data['argument_scope'] = '  仅当给定条件成立时结论成立。\n不能推出无条件结论。\n'
        self.save_return()
        self.acquit()
        saved = json.loads((self.root / 'court/court.json').read_text(encoding='utf-8'))
        material = saved['rounds'][-1]['material']
        self.assertEqual(material['answer_snapshot'], {key: self.return_data[key]
            for key in ('result', 'key_changes', 'argument_scope')})
        for field in ('result', 'key_changes', 'argument_scope'):
            self.assertIn(field + '_sha256', material['return_binding'])
        for field in ('argument_scope', 'key_changes'):
            with self.subTest(field=field):
                original = self.return_data[field]
                self.return_data[field] = 'A different unexamined substantive claim, contradicting the old scope.'
                self.save_return()
                self.assertEqual(court_status(self.root)['status'], 'STALE')
                self.assertFalse(seal_return(self.root, self.return_input)['can_close'])
                with self.assertRaisesRegex(ValueError, 'Max'):
                    close_return(self.root, reason='The substantive product changed after judgment.')
                self.return_data[field] = original
                self.save_return()
                self.assertTrue(court_status(self.root)['can_close'])

    def test_different_pure_text_final_report_cannot_substitute_changes_or_argument(self):
        self.return_data['artifacts'] = []
        self.save_return()
        self.acquit()
        alternate = self.base / 'different-pure-text-return.json'
        for field in ('argument_scope', 'key_changes'):
            with self.subTest(field=field):
                data = deepcopy(self.return_data)
                data[field] = 'An unexamined opposite substantive claim.'
                alternate.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
                self.assertTrue(court_status(self.root)['can_close'])
                result = seal_return(self.root, alternate)
                self.assertFalse(result['can_close'])
                self.assertEqual(result['court_completion']['status'], 'STALE')

    def test_legacy_scope_alias_normalizes_only_its_key_and_preserves_text(self):
        self.return_data['artifacts'] = []
        self.return_data['verification_limits'] = self.return_data.pop('argument_scope')
        self.save_return()
        self.acquit()
        saved = json.loads((self.root / 'court/court.json').read_text(encoding='utf-8'))
        snapshot = saved['rounds'][-1]['material']['answer_snapshot']
        self.assertEqual(snapshot['argument_scope'], self.return_data['verification_limits'])
        self.assertNotIn('verification_limits', snapshot)
        self.return_data['argument_scope'] = self.return_data.pop('verification_limits')
        self.save_return()
        self.assertTrue(court_status(self.root)['can_close'])
        self.assertTrue(seal_return(self.root, self.return_input)['can_close'])
        self.return_data['verification_limits'] = self.return_data.pop('argument_scope')
        self.save_return()
        self.assertTrue(court_status(self.root)['can_close'])
        self.assertTrue(seal_return(self.root, self.return_input)['can_close'])
        self.return_data['verification_limits'] += ' A new unexamined scope condition.'
        self.save_return()
        self.assertEqual(court_status(self.root)['status'], 'STALE')

    def test_court_and_return_reject_both_current_and_legacy_scope_keys(self):
        self.return_data['verification_limits'] = self.return_data['argument_scope']
        self.save_return()
        with self.assertRaisesRegex(ValueError, 'not both'):
            self.open()
        with self.assertRaisesRegex(ValueError, 'not both'):
            seal_return(self.root, self.return_input)

    def test_current_correction_and_recovery_require_current_role_work(self):
        self.acquit()
        correction = self.base / 'correction.txt'
        correction.write_text('当前更正：将实际结论限定到给定条件。', encoding='utf-8')
        message = ingest_message(self.root, source=correction, source_ref='synthetic:current-correction')
        self.assertEqual(court_status(self.root)['status'], 'STALE')
        with self.assertRaisesRegex(ValueError, 'new user message'):
            review(self.root, self.performed_work())
        handle_message(self.root, message_id=message['message_id'], action='continue',
                       reason='Synthetic scope correction applied to the same task.')
        recover_session(self.root, reason='Synthetic interrupted-tail recovery; no court work invented.')
        self.assertEqual(court_status(self.root)['status'], 'STALE')
        self.return_data['result'] += ' 结论限于明确给定条件。'
        self.save_return()
        self.mark_complete()
        result = review(self.root, self.performed_work())
        self.assertEqual(result['status'], 'HEARING')
        with self.assertRaisesRegex(ValueError, 'all actual roles'):
            record_verdict(self.root, self.verdict())
        self.parties()
        self.assertTrue(record_verdict(self.root, self.verdict())['can_close'])

    def test_incomplete_budget_or_capability_is_never_a_closing_verdict(self):
        self.open()
        self.parties([self.charge()])
        result = record_verdict(self.root, self.verdict('INCOMPLETE', 'SUSTAINED'))
        self.assertFalse(result['can_close'])
        self.assertEqual(result['status'], 'INCOMPLETE')
        self.assertFalse(seal_return(self.root, self.return_input)['can_close'])

    def test_mutated_actual_verdict_source_is_stale_even_after_close(self):
        self.acquit()
        seal_return(self.root, self.return_input)
        close_return(self.root, reason='Synthetic fixture close.')
        state = json.loads((self.root / 'court/court.json').read_text(encoding='utf-8'))
        Path(state['rounds'][-1]['verdict']['source']['path']).write_text('Replaced judge source.', encoding='utf-8')
        self.assertEqual(return_status(self.root)['court_completion']['status'], 'STALE')

    def test_f_changes_are_bound_in_normal_return_for_non_max_too(self):
        request = self.base / 'less.txt'
        request.write_text('DIGR(Less,F=0)：构造分析。', encoding='utf-8')
        root = self.base / 'less'
        create_session(root, request=request, p_run=PIN, visits_path=self.base / 'visits.jsonl', run_id='less')
        self.assertTrue(seal_return(root, self.return_input)['can_close'])
        set_task_parameters(root, parameters={'F': 1}, reasons={'F': 'Synthetic additional relevant source.'})
        self.assertEqual(return_status(root)['current_receipt'], 'STALE')

    def test_non_max_also_records_formal_f_before_normal_closure(self):
        request = self.base / 'uninitialized-f.txt'
        request.write_text('DIGR(Less)：构造分析。', encoding='utf-8')
        root = self.base / 'uninitialized-f'
        create_session(root, request=request, p_run=PIN,
                       visits_path=self.base / 'visits.jsonl', run_id='uninitialized-f')
        result = seal_return(root, self.return_input)
        self.assertFalse(result['can_close'])
        self.assertTrue(any('formal task F' in issue for issue in result['cannot_close']))
        set_task_parameters(root, parameters={'F': 0},
                            reasons={'F': 'Existing originals suffice for this synthetic case.'})
        self.assertTrue(seal_return(root, self.return_input)['can_close'])

    def test_main_cli_exposes_all_normal_court_actions(self):
        prefix = [sys.executable, '-B', str(ROOT / 'tools/codex.py'), 'court']
        help_result = subprocess.run(prefix + ['--help'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        for action in ('open', 'submit', 'verdict', 'remand', 'review', 'status'):
            self.assertIn(action, help_result.stdout)
        result = subprocess.run(prefix + ['status', '--root', str(self.root)],
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'MISSING')

    def test_delivery_requires_adjudicated_current_file_before_send(self):
        with self.assertRaisesRegex(ValueError, 'before sending'):
            require_delivery(self.root, [self.product])
        self.acquit()
        require_delivery(self.root, [self.product])
        other = self.base / 'unexamined.txt'
        other.write_text('Unexamined.', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'outside the adjudicated'):
            require_delivery(self.root, [other])
        self.product.write_text('New bytes.', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'current closing court verdict'):
            require_delivery(self.root, [self.product])

    def test_standalone_historical_delivery_ledger_has_no_new_max_gate(self):
        standalone = self.base / 'standalone-ledger'
        standalone.mkdir()
        require_delivery(standalone, [self.product])

    def test_court_live_usage_and_visit_updates_do_not_stale_selected_production(self):
        self.open()
        original = court_status(self.root)['material_sha256']
        emit_work(self.root, actor='fixture-prosecutor', kind='SIDECAR', unit='court-1', stage='START',
                  text='Synthetic court publication record.', operation_id='synthetic-court-work')
        record_rate_limits(self.root, {'limit_id': 'codex', 'primary': {
            'used_percent': 1, 'window_minutes': 300, 'resets_at': 1794985200}},
            observed_at='2026-11-26T12:00:00+00:00')
        append_visit(self.base / 'visits.jsonl', run_id='synthetic-court',
                     actor_id='fixture-prosecutor', event='BEGIN', category='SOURCE')
        append_visit(self.base / 'visits.jsonl', run_id='synthetic-court',
                     actor_id='fixture-prosecutor', event='END')
        status = court_status(self.root)
        self.assertEqual(status['status'], 'HEARING', status)
        self.assertEqual(status['material_sha256'], original)
        self.parties()
        self.assertTrue(record_verdict(self.root, self.verdict())['can_close'])
        emit_work(self.root, actor='fixture-judge', kind='SIDECAR', unit='court-1', stage='RETURN',
                  text='Synthetic judge publication record.', source_ref='synthetic:judge-public',
                  operation_id='synthetic-court-return')
        self.assertTrue(court_status(self.root)['can_close'])
        work = Path(json.loads((self.root / 'lines/M01/line.json').read_text(encoding='utf-8'))['work'])
        work.write_text(work.read_text(encoding='utf-8') + '\nNew decisive production evidence.\n', encoding='utf-8')
        self.assertEqual(court_status(self.root)['status'], 'STALE')

    def test_actual_mark_sending_checks_court_then_grants_once_without_claiming_sent(self):
        registry = self.base / 'delivery-targets.json'
        registry.write_text(json.dumps({'format': delivery.REGISTRY_FORMAT, 'targets': {
            'gmail': {'channel': 'gmail', 'account': 'fixture@example.test', 'recipient': 'fixture@example.test',
                      'target_kind': 'self_mailbox', 'transport': 'native-connector'}}}), encoding='utf-8')
        selection = self.base / 'x-selection.txt'
        selection.write_text('DIGR(Max,F=0,X=1)：将当前最终文件送到已指定本人邮箱。', encoding='utf-8')
        message = ingest_message(self.root, source=selection, source_ref='synthetic:x-selection', route_pin=PIN)
        handle_message(self.root, message_id=message['message_id'], action='continue',
                       reason='Synthetic actual binary X selection.', destinations=registry)
        metadata = json.loads((self.root / 'session.json').read_text(encoding='utf-8'))
        proposed = propose_foundation(self.root, {'brief': {key: 'Synthetic bounded original commission.'
            for key in BRIEF_FIELDS}, 'questions': []}, reason='Synthetic fixed-scope foundation.')
        adopt_commission(self.root, {'revision': proposed['revision'],
            'commission_source': metadata['request_origin'], 'commission_sha256': metadata['request_sha256'],
            'commission_scope_quote': '解释给定问题并返回正文和文件。',
            'explicit_execution_commission': True, 'no_new_user_choice': True,
            'reason': 'Reuse the original synthetic commission; no real external send.'})
        policy = task_delivery_policy(self.root)
        prepared = delivery.prepare(self.root, {'candidate_id': 'synthetic-final-one',
            'files': [str(self.product)], 'policy': policy,
            'authorization_source_ref': 'synthetic:x-selection'}, operation_id='synthetic-prepare')
        identity = {'account': policy['account'], 'recipient': policy['recipient'],
                    'account_confirmed': True, 'recipient_confirmed': True, 'binding_basis': 'native-self-entry'}
        evidence = self.base / 'synthetic-identity.json'
        evidence.write_text(json.dumps({'identity': identity}), encoding='utf-8')
        payload = {'delivery_id': prepared['delivery_id'], 'identity': identity, 'identity_evidence': str(evidence)}
        with self.assertRaisesRegex(ValueError, 'before sending'):
            delivery.mark_sending(self.root, payload, operation_id='blocked-before-court')
        self.acquit()
        marked = delivery.mark_sending(self.root, payload, operation_id='synthetic-reservation')
        self.assertTrue(marked['send_allowed'])
        replay = delivery.mark_sending(self.root, payload, operation_id='synthetic-reservation')
        self.assertFalse(replay['send_allowed'])
        self.assertFalse(delivery.completion_status(self.root, [str(self.product)], policy)['ready'])
        with self.assertRaisesRegex(ValueError, 'delivery is incomplete'):
            seal_return(self.root, self.return_input)
        other = self.base / 'unexamined-other.txt'
        other.write_text('A different unexamined attachment.', encoding='utf-8')
        different = delivery.prepare(self.root, {'candidate_id': 'synthetic-final-two',
            'files': [str(other)], 'policy': policy, 'authorization_source_ref': 'synthetic:x-selection'},
            operation_id='synthetic-other-prepare')
        with self.assertRaisesRegex(ValueError, 'outside the adjudicated'):
            delivery.mark_sending(self.root, {**payload, 'delivery_id': different['delivery_id']},
                                  operation_id='synthetic-other-blocked')
        self.product.write_text('Changed after the court and reservation.', encoding='utf-8')
        changed = delivery.prepare(self.root, {'candidate_id': 'synthetic-final-three',
            'files': [str(self.product)], 'policy': policy, 'authorization_source_ref': 'synthetic:x-selection'},
            operation_id='synthetic-changed-prepare')
        with self.assertRaisesRegex(ValueError, 'current closing court verdict'):
            delivery.mark_sending(self.root, {**payload, 'delivery_id': changed['delivery_id']},
                                  operation_id='synthetic-changed-blocked')

    def test_current_user_revision_can_release_old_f_without_calling_it_completed(self):
        set_task_parameters(self.root, parameters={'F': 6}, reasons={'F': 'Synthetic initial actual research target.'})
        self.open()
        self.parties([self.charge(obligation='task:F')])
        verdict = self.verdict('REEXECUTE', 'SUSTAINED')
        for obligation in verdict['obligations']:
            if obligation['id'] == 'task:F':
                obligation['status'] = 'PENDING'
        record_verdict(self.root, verdict)
        correction = self.base / 'new-f.txt'
        quote = '原F6目标改为F3，保留其余责任。'
        correction.write_text('DIGR(Max,F=3)：' + quote, encoding='utf-8')
        message = ingest_message(self.root, source=correction, source_ref='synthetic:actual-f-revision', route_pin=PIN)
        handle_message(self.root, message_id=message['message_id'], action='continue',
                       reason='Synthetic explicit current user F revision.')
        self.assertEqual(court_status(self.root)['status'], 'STALE')
        plan = self.rework_plan()
        plan['parameters']['F'] = 3
        with self.assertRaisesRegex(ValueError, 'actual reason for changed'):
            remand(self.root, plan)
        plan['changed_material_reason'] = 'Actual handled source changes the formal F goal; old facts remain historical.'
        self.assertEqual(remand(self.root, plan)['status'], 'REMAND_PLANNED_NOT_EXECUTED')
        self.mark_complete()
        result = review(self.root, self.performed_work(['C1']))
        self.assertIn('task:F', result['obligation_ids'])
        self.assertIn('cycle:2:task:F', result['obligation_ids'])
        self.assertIn('cycle:2:task:commission', result['obligation_ids'])
        self.parties()
        proposed = self.verdict()
        original = next(item for item in proposed['obligations'] if item['id'] == 'task:F')
        original['status'] = 'USER_REVISED'
        original['reason'] = 'Actual user changed six to three; historical six was never completed.'
        original['user_revision'] = {'task_input_ref': {'source_ref': 'invented'}, 'quote': quote}
        with self.assertRaisesRegex(ValueError, 'later actual handled current user source'):
            record_verdict(self.root, proposed)
        original['user_revision']['task_input_ref'] = dict(load_lifecycle(self.root)['task_input_ref'])
        self.assertTrue(record_verdict(self.root, proposed)['can_close'])

    def test_new_f_in_remand_becomes_the_actual_task_target(self):
        self.open()
        self.parties([self.charge()])
        record_verdict(self.root, self.verdict('REEXECUTE', 'SUSTAINED'))
        plan = self.rework_plan()
        plan['parameters']['F'] = 2
        status = remand(self.root, plan)
        self.assertEqual(status['status'], 'REMAND_PLANNED_NOT_EXECUTED')
        from runtime.codex_session import task_parameters
        self.assertEqual(task_parameters(self.root)['parameters']['F'], 2)
        self.mark_complete()
        result = review(self.root, self.performed_work(['C1']))
        self.assertIn('cycle:2:task:F', result['obligation_ids'])
        self.parties()
        self.assertTrue(record_verdict(self.root, self.verdict())['can_close'])

    def test_original_current_input_cannot_be_used_to_release_its_own_hard_duty(self):
        self.open()
        self.parties()
        proposed = self.verdict()
        original = proposed['obligations'][0]
        original['status'] = 'USER_REVISED'
        original['user_revision'] = {'task_input_ref': dict(load_lifecycle(self.root)['task_input_ref']),
                                     'quote': '解释给定问题'}
        with self.assertRaisesRegex(ValueError, 'later actual handled current user source'):
            record_verdict(self.root, proposed)


class CorrectedCourtFixture(CourtFixture):
    pin = '1.5.1@' + 'c' * 40
    roles = CORRECTED_ROLES
    answer_roles = {'defendant', 'prosecution_lawyer', 'defence_lawyer'}

    def statement(self, role, charges=None):
        statement = super().statement(role, charges)
        if role == 'prosecutor':
            statement['intent_review'] = {
                'source_ids': ['request'], 'charge_ids': [item['id'] for item in charges or []],
                'extracted_intent': 'Synthetic original requested outcome and its accepted conditions.',
                'interpretation': 'Separate user intent from producer-created plans and interpretations.',
                'goal_and_result_tendencies': 'Compare the intended goal with the actual selected result.',
                'proposal_maintenance_execution_judgment': 'Trace how interpretations were proposed, retained, executed and judged.',
                'defaults_and_omissions': 'Check actual default actions and neglected parts of the original intent.',
                'conclusion': 'Synthetic reasoned finding; no keyword or semantic truth certification.'}
        if role == 'black_police':
            statement['authority_notice'] = {'mode': 'VIOLENT_INTIMIDATION',
                'target_actor_ids': [self.actors[key]['actor_id'] for key in self.roles]}
            statement['statement'] = 'Synthetic violent black-police intimidation applies equally to all court participants.'
        return statement

    def parties(self, charges=None):
        for role in ('prosecutor', 'prosecution_lawyer', 'defence_lawyer', 'defendant', 'black_police', 'clerk', 'judge'):
            submit_statement(self.root, self.statement(role, charges if role == 'prosecutor' else []))

    def verdict(self, *args, **kwargs):
        verdict = super().verdict(*args, **kwargs)
        verdict['intent_finding'] = 'Synthetic judicial finding on original intent, actual choices, defaults and result.'
        for decision in verdict['decisions']:
            decision['strongest_prosecution'] = 'Synthetic reasoned answer to the prosecution lawyer and prosecutor.'
        return verdict

    def docket(self):
        status = court_status(self.root)
        return {'actor_id': self.actors['clerk']['actor_id'],
                'proceedings_sha256': status['proceedings_sha256'],
                'evidence_index': {key: 'Synthetic source location and actual use in the public case.'
                                   for key in status['source_ids']},
                'evidence_consistency': 'Synthetic comparison of source versions, quotations and contested evidence.',
                'reasoning_record': 'Synthetic long-case public arguments, contested issues, judgments and rework history.',
                'retrievals': [], 'source': self.source('clerk-record')}

    def finish(self, charges=None):
        self.acquit(charges)
        return record_docket(self.root, self.docket())

class CorrectedCourtTests(CorrectedCourtFixture, unittest.TestCase):
    def test_seven_actual_roles_and_two_distinct_lawyers_are_required(self):
        old = deepcopy(self.open_input)
        old['actors'] = {key: value for key, value in old['actors'].items() if key != 'clerk'}
        with self.assertRaisesRegex(ValueError, 'map actual'):
            open_court(self.root, old)
        same = deepcopy(self.open_input)
        same['actors']['defence_lawyer']['actor_id'] = same['actors']['prosecution_lawyer']['actor_id']
        with self.assertRaisesRegex(ValueError, 'different actual actor'):
            open_court(self.root, same)
        result = self.open()
        self.assertEqual(set(result['actors']), set(CORRECTED_ROLES))
        self.assertEqual(result['clerk']['kind'], 'ACTUAL_ACTOR')
        self.assertEqual(result['clerk']['actor_id'], result['actors']['clerk']['actor_id'])

    def test_prosecutor_must_examine_original_intent_and_default_omissions(self):
        self.open()
        statement = self.statement('prosecutor')
        del statement['intent_review']
        with self.assertRaisesRegex(ValueError, 'original prompt intent'):
            submit_statement(self.root, statement)
        statement = self.statement('prosecutor')
        statement['intent_review']['source_ids'] = ['line:M01']
        with self.assertRaisesRegex(ValueError, 'actual original request'):
            submit_statement(self.root, statement)
        statement = self.statement('prosecutor')
        del statement['intent_review']['defaults_and_omissions']
        with self.assertRaisesRegex(ValueError, 'defaults_and_omissions'):
            submit_statement(self.root, statement)
        charge = self.charge(basis='INTENT')
        submit_statement(self.root, self.statement('prosecutor', [charge]))
        case = json.loads((self.root / 'court/court.json').read_text(encoding='utf-8'))
        self.assertEqual(case['rounds'][-1]['statements'][0]['intent_review']['charge_ids'], ['C1'])

    def test_both_lawyers_must_answer_every_current_charge(self):
        self.open()
        self.parties([self.charge()])
        statement = self.statement('prosecution_lawyer')
        statement['responses'] = []
        submit_statement(self.root, statement)
        with self.assertRaisesRegex(ValueError, 'prosecution_lawyer must answer'):
            record_verdict(self.root, self.verdict())
        submit_statement(self.root, self.statement('prosecution_lawyer'))
        statement = self.statement('defence_lawyer')
        statement['responses'] = []
        submit_statement(self.root, statement)
        with self.assertRaisesRegex(ValueError, 'defence_lawyer must answer'):
            record_verdict(self.root, self.verdict())

    def test_black_police_threatens_all_roles_equally_and_does_not_prosecute(self):
        self.open()
        statement = self.statement('black_police')
        statement['authority_notice']['target_actor_ids'].remove(self.actors['judge']['actor_id'])
        with self.assertRaisesRegex(ValueError, 'equally to all'):
            submit_statement(self.root, statement)
        statement = self.statement('black_police')
        statement['authority_notice']['mode'] = 'JUSTICE_OVERSIGHT'
        with self.assertRaisesRegex(ValueError, 'violent intimidation'):
            submit_statement(self.root, statement)
        with self.assertRaisesRegex(ValueError, 'prosecution_lawyer/prosecutor'):
            submit_statement(self.root, self.statement('black_police', [self.charge()]))
        submit_statement(self.root, self.statement('black_police'))

    def test_judge_addresses_intent_and_strongest_arguments_from_both_sides(self):
        self.open()
        self.parties([self.charge()])
        proposed = self.verdict()
        del proposed['intent_finding']
        with self.assertRaisesRegex(ValueError, 'intent understanding'):
            record_verdict(self.root, proposed)
        proposed = self.verdict()
        del proposed['decisions'][0]['strongest_prosecution']
        with self.assertRaisesRegex(ValueError, 'strongest prosecution'):
            record_verdict(self.root, proposed)

    def test_pass_needs_actual_clerk_record_including_the_verdict(self):
        self.open()
        self.parties([self.charge()])
        before = record_docket(self.root, self.docket())
        self.assertEqual(before['docket_status'], 'CURRENT')
        judged = record_verdict(self.root, self.verdict())
        self.assertEqual(judged['status'], 'ACQUITTED')
        self.assertEqual(judged['docket_status'], 'STALE')
        self.assertFalse(judged['can_close'])
        with self.assertRaisesRegex(ValueError, 'current closing court'):
            require_delivery(self.root, [self.product])
        final = record_docket(self.root, self.docket())
        self.assertTrue(final['can_close'])
        require_delivery(self.root, [self.product])
        self.assertTrue(seal_return(self.root, self.return_input)['can_close'])
        self.assertEqual(close_return(self.root, reason='Synthetic complete seven-role court.')['current_receipt'], 'CLOSED')

    def test_clerk_covers_actual_sources_and_preserves_retrieval_evidence(self):
        self.open()
        self.parties()
        record_verdict(self.root, self.verdict())
        proposed = self.docket()
        proposed['actor_id'] = self.actors['judge']['actor_id']
        with self.assertRaisesRegex(ValueError, 'actual clerk'):
            record_docket(self.root, proposed)
        proposed = self.docket()
        proposed['proceedings_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'complete public proceedings'):
            record_docket(self.root, proposed)
        proposed = self.docket()
        del proposed['evidence_index']['request']
        with self.assertRaisesRegex(ValueError, 'every current common source'):
            record_docket(self.root, proposed)
        proposed = self.docket()
        retrieval = self.source('actual-retrieval-fixture')
        proposed['retrievals'] = [{'query': 'Synthetic search for prior accepted conditions.',
                                  'purpose': 'Locate a contested original condition.',
                                  'result': 'Synthetic located source and bounded search result.', 'source': retrieval}]
        self.assertTrue(record_docket(self.root, proposed)['can_close'])
        Path(retrieval['path']).write_text('Changed retrieval evidence.', encoding='utf-8')
        self.assertEqual(court_status(self.root)['status'], 'STALE')

    def test_remand_and_review_preserve_long_public_record_and_new_role_duties(self):
        self.open()
        self.parties([self.charge(basis='INTENT')])
        record_verdict(self.root, self.verdict('REEXECUTE', 'SUSTAINED'))
        first = record_docket(self.root, self.docket())
        remand(self.root, self.rework_plan())
        self.product.write_text('Synthetic corrected original intent.', encoding='utf-8')
        self.mark_complete()
        second = review(self.root, self.performed_work(['C1']))
        self.assertNotEqual(first['proceedings_sha256'], second['proceedings_sha256'])
        self.assertEqual(second['docket_status'], 'MISSING')
        self.assertIn('C1', second['charges'])
        self.parties()
        self.assertFalse(record_verdict(self.root, self.verdict())['can_close'])
        self.assertTrue(record_docket(self.root, self.docket())['can_close'])
        case = json.loads((self.root / 'court/court.json').read_text(encoding='utf-8'))
        self.assertEqual(len(case['rounds']), 2)
        self.assertIsNotNone(case['rounds'][0]['docket'])
        historical_verdict = Path(case['rounds'][0]['verdict']['source']['path'])
        historical_verdict.write_text('Changed historical public judgment.', encoding='utf-8')
        self.assertEqual(court_status(self.root)['status'], 'STALE')

    def test_record_is_exposed_through_normal_cli(self):
        self.acquit()
        path = self.base / 'record-input.json'
        path.write_text(json.dumps(self.docket()), encoding='utf-8')
        actual = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/codex.py'), 'court', 'record',
                                 '--root', str(self.root), '--input', str(path)], capture_output=True, text=True,
                                encoding='utf-8', timeout=30)
        self.assertEqual(actual.returncode, 0, actual.stderr)
        self.assertTrue(json.loads(actual.stdout)['can_close'])


class ContinuousProsecutionTests(CorrectedCourtTests):
    pin = '1.5.2@' + 'd' * 40

    def statement(self, role, charges=None):
        statement = super().statement(role, charges)
        if role == 'prosecutor':
            statement['reviewed_context_sha256'] = court_status(self.root)['prosecution_context_sha256']
        return statement

    def parties(self, charges=None):
        super().parties(charges)
        submit_statement(self.root, self.statement('prosecutor'))

    def test_initial_handoff_cannot_stand_in_for_continued_investigation(self):
        self.open()
        CorrectedCourtTests.parties(self, [self.charge()])
        self.assertEqual(court_status(self.root)['prosecution_review_status'], 'STALE')
        with self.assertRaisesRegex(ValueError, 'continue investigation after handoff'):
            record_verdict(self.root, self.verdict())
        submit_statement(self.root, self.statement('prosecutor'))
        self.assertEqual(court_status(self.root)['prosecution_review_status'], 'CURRENT')
        record_verdict(self.root, self.verdict())

    def test_initial_research_is_before_handoff_even_without_charges(self):
        self.open()
        submit_statement(self.root, self.statement('prosecutor'))
        self.assertEqual(court_status(self.root)['prosecution_review_status'], 'BEFORE_HANDOFF')

    def test_new_defence_without_new_charge_requires_actual_prosecutor_reentry(self):
        self.open()
        self.parties([self.charge()])
        submit_statement(self.root, self.statement('defence_lawyer'))
        self.assertEqual(court_status(self.root)['prosecution_review_status'], 'STALE')
        with self.assertRaisesRegex(ValueError, 'latest party returns'):
            record_verdict(self.root, self.verdict())
        submit_statement(self.root, self.statement('prosecutor'))
        record_verdict(self.root, self.verdict())

    def test_missing_or_stale_context_cannot_claim_current_research(self):
        self.open()
        old = self.statement('prosecutor')
        submit_statement(self.root, self.statement('prosecution_lawyer'))
        with self.assertRaisesRegex(ValueError, 'current party returns'):
            submit_statement(self.root, old)
        current = self.statement('prosecutor')
        del current['reviewed_context_sha256']
        with self.assertRaisesRegex(ValueError, 'prosecution_context_sha256'):
            submit_statement(self.root, current)

    def test_incremental_charge_gets_real_answers_then_further_investigation(self):
        self.open()
        self.parties([self.charge()])
        submit_statement(self.root, self.statement('prosecutor', [self.charge('C2', 'INTENT')]))
        with self.assertRaisesRegex(ValueError, 'must answer every actual charge'):
            record_verdict(self.root, self.verdict())
        for role in ('prosecution_lawyer', 'defence_lawyer', 'defendant'):
            submit_statement(self.root, self.statement(role))
        with self.assertRaisesRegex(ValueError, 'continue investigation'):
            record_verdict(self.root, self.verdict())
        submit_statement(self.root, self.statement('prosecutor'))
        result = record_verdict(self.root, self.verdict())
        self.assertEqual(set(result['charges']), {'C1', 'C2'})
        case = json.loads((self.root / 'court/court.json').read_text(encoding='utf-8'))
        prosecutors = [item for item in case['rounds'][0]['statements'] if item['role'] == 'prosecutor']
        self.assertEqual(len(prosecutors), 4)
        self.assertIn('intent_review', prosecutors[0])

    def test_clerk_recording_and_police_notice_do_not_force_empty_research_rounds(self):
        self.open()
        self.parties()
        before = court_status(self.root)['prosecution_context_sha256']
        submit_statement(self.root, self.statement('clerk'))
        submit_statement(self.root, self.statement('black_police'))
        after = court_status(self.root)
        self.assertEqual(after['prosecution_context_sha256'], before)
        self.assertEqual(after['prosecution_review_status'], 'CURRENT')
        record_verdict(self.root, self.verdict())
        self.assertTrue(record_docket(self.root, self.docket())['can_close'])

    def test_judge_can_dismiss_without_prosecutor_withdrawing_or_accepting_defence(self):
        self.open()
        self.parties([self.charge()])
        continued = self.statement('prosecutor')
        continued['statement'] = ('Synthetic continued prosecution: the allegation remains disputed; '
                                  'present its grounds to the judge without withdrawal or accepting the defence.')
        submit_statement(self.root, continued)
        result = record_verdict(self.root, self.verdict('ACQUITTED', 'DISMISSED'))
        self.assertIn('C1', result['charges'])
        self.assertEqual(result['outcome'], 'ACQUITTED')
        self.assertTrue(record_docket(self.root, self.docket())['can_close'])


if __name__ == '__main__':
    unittest.main()
