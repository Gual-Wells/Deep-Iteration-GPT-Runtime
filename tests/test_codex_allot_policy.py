import json
from pathlib import Path
import tempfile
import unittest

from runtime.codex_allot import (POLICY, context_summary, current_policy,
                                observe, plan, ready, record_feedback,
                                resolve_labor, select, set_policy)
from runtime.codex_lifecycle import handle_message, ingest_message, load_lifecycle
from runtime.codex_session import create_session
from runtime.codex_foundation import BRIEF_FIELDS, confirm_foundation, propose_foundation


CATALOGUE = {'models': [{'slug': model, 'supported_reasoning_levels':
                       [{'effort': effort} for effort in ('low', 'medium', 'high', 'xhigh', 'max')]}
                       for model in ('gpt-6.1-sol', 'gpt-6.2-sol', 'gpt-6.2-astra')]}


class SolMaxSelectionTests(unittest.TestCase):
    def block(self, **updates):
        return {'model': 'gpt-6.2-sol', 'kind': 'maintenance',
                'evidence': ['Current actual task specification'], **updates}

    def labor(self, **updates):
        return self.block(kind='routine', fully_specified=True, requested_effort='low',
                          allow_downshift=True, controlled_labor={
                              'large_batch': True, 'repetitive': True,
                              'non_intellectual': True, 'controlled': True,
                              'scope_ref': 'frozen homogeneous page list',
                              'validation_ref': 'assembly dimensions and content manifest'}, **updates)

    def test_all_intellectual_kinds_and_both_sol_generations_default_max(self):
        for model in ('gpt-6.1-sol', 'gpt-6.2-sol'):
            for kind in ('routine', 'maintenance', 'response', 'architecture', 'breakthrough'):
                with self.subTest(model=model, kind=kind):
                    result = select(self.block(model=model, kind=kind), CATALOGUE)
                    self.assertEqual(result['effort'], 'max')
                    self.assertEqual(result['host_payload']['reasoning_effort'], 'max')
                    self.assertFalse(result['applied'])

    def test_no_label_or_partial_labor_contract_bypasses_final_downshift_gate(self):
        for kind in ('routine', 'maintenance', 'response', 'architecture', 'breakthrough'):
            for effort in ('low', 'medium', 'high', 'xhigh'):
                with self.subTest(kind=kind, effort=effort), self.assertRaises(ValueError):
                    select(self.block(kind=kind, requested_effort=effort,
                                      fully_specified=True, allow_downshift=True), CATALOGUE)
        for key in ('large_batch', 'repetitive', 'non_intellectual', 'controlled', 'scope_ref', 'validation_ref'):
            block = self.labor()
            del block['controlled_labor'][key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                select(block, CATALOGUE)
        self.assertEqual(select(self.labor(), CATALOGUE)['effort'], 'low')

    def test_failed_labor_restores_max_without_buying_a_stronger_model(self):
        for category in ('quality', 'capability'):
            result = select(self.labor(feedback={'category': category,
                            'evidence_ref': 'batch-validator-actual-failure',
                            'detail': 'cross-page dependency requires new judgment'}), CATALOGUE)
            self.assertEqual((result['model'], result['effort']), ('gpt-6.2-sol', 'max'))
        result = select(self.labor(feedback={'category': 'network', 'evidence_ref': 'socket-log',
                        'detail': 'connection reset; no reasoning failure established'}), CATALOGUE)
        self.assertEqual(result['effort'], 'low')

    def test_max_requires_concrete_supported_model_escalation_not_ultra_or_failure_labels(self):
        with self.assertRaises(ValueError):
            select(self.block(model='gpt-6.2-astra'), CATALOGUE)
        with self.assertRaises(ValueError):
            select(self.block(requested_effort='ultra'), CATALOGUE)
        escalation = {'trigger': 'task_failure_feedback', 'source_model': 'gpt-6.1-sol',
                      'source_effort': 'max', 'evidence_ref': 'actual-Max-result-and-acceptance',
                      'reason': 'specific unresolved invariant remains despite Max work'}
        block = self.block(model='gpt-6.2-astra', escalation=escalation,
                           unresolved=['the two invariants still contradict'],
                           feedback={'category': 'quality', 'evidence_ref': 'actual-result',
                                     'detail': 'counterexample survives current Max result'})
        self.assertEqual(select(block, CATALOGUE)['effort'], 'max')
        for category in ('tool', 'network', 'permission', 'input', 'budget'):
            block['feedback']['category'] = category
            with self.subTest(category=category), self.assertRaises(ValueError):
                select(block, CATALOGUE)
        block['feedback']['category'] = 'quality'
        block['model'] = 'unavailable'
        with self.assertRaises(ValueError):
            select(block, CATALOGUE)
        self.assertEqual(select(self.block(failed_efforts=['max']), CATALOGUE)['model'], 'gpt-6.2-sol')

    def test_available_ultra_is_explicit_evidence_based_not_an_automatic_floor(self):
        available = json.loads(json.dumps(CATALOGUE))
        available['models'][1]['supported_reasoning_levels'].append({'effort': 'ultra'})
        gap = {'trigger': 'max_capability_insufficient', 'source_model': 'gpt-6.2-sol',
               'source_effort': 'max', 'evidence_ref': 'specific-Max-capability-analysis',
               'reason': 'this independently divisible problem can use actual host Ultra execution'}
        block = self.block(requested_effort='ultra', escalation=gap,
                           unresolved=['two independent unresolved proofs'])
        self.assertEqual(select(block, available)['effort'], 'ultra')
        with self.assertRaises(ValueError):
            select(block, CATALOGUE)
        with self.assertRaises(ValueError):
            select(self.block(minimum_effort='ultra', escalation=gap,
                              unresolved=['concrete issue']), available)
        block['feedback'] = {'category': 'network', 'evidence_ref': gap['evidence_ref'],
                             'detail': 'the same fault is only a connection failure'}
        with self.assertRaises(ValueError):
            select(block, available)
        block['feedback']['evidence_ref'] = 'separate-network-incident'
        self.assertEqual(select(block, available)['effort'], 'ultra')


class AllotTaskPolicyTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[1] / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='allot-policy-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'session'
        self.request = self.base / 'request.txt'
        self.request.write_text('DIGR：按当前规格执行', encoding='utf-8')
        create_session(self.root, request=self.request, p_run='0.17.0@' + '1' * 40)
        self.ready(self.root)

    def ready(self, root):
        proposed = propose_foundation(root, {'brief': {key: 'Constructed bounded Allot behavior fixture'
                                     for key in BRIEF_FIELDS}, 'questions': []}, reason='Behavioral test fixture')
        source = load_lifecycle(root)['current_message']['source']
        confirm_foundation(root, revision=proposed['revision'], user_text=source['text'], source=source['source_ref'])

    def block(self, name='first'):
        return {'block_id': name, 'model': 'gpt-6.2-sol', 'kind': 'architecture',
                'evidence': ['current candidate requires substantive reasoning']}

    def followup(self, text='DO：保留规格，修正这一处'):
        index = load_lifecycle(self.root)['message_id'] + 1
        source = self.base / ('input-' + str(index) + '.txt')
        source.write_text(text, encoding='utf-8')
        message = ingest_message(self.root, source=source, source_ref='actual-user-' + str(index))
        handle_message(self.root, message_id=message['message_id'], action='continue', reason='Apply current actual supplement')

    def test_policy_survives_supplement_and_old_observation_remains_recordable(self):
        selected = plan(self.root, self.block(), CATALOGUE, catalogue_ref='actual-host-cache')
        self.followup()
        self.assertEqual(current_policy(self.root)['policy'], POLICY)
        with self.assertRaises(ValueError):
            plan(self.root, self.block(), CATALOGUE, catalogue_ref='actual-host-cache')
        observation = observe(self.root, 'first', {'model': 'gpt-6.2-sol', 'effort': 'max',
                              'source_ref': 'actual-completed-host-response'})
        self.assertTrue(observation['matches_selection'])
        self.assertTrue(observation['superseded'])
        self.assertFalse(observation['execution_authorization'])
        self.assertFalse(context_summary(self.root)['selections'][0]['current'])

    def test_observation_retry_after_do_keeps_original_fact_and_projects_current_status(self):
        plan(self.root, self.block(), CATALOGUE, catalogue_ref='host')
        actual = {'model': 'gpt-6.2-sol', 'effort': 'max', 'source_ref': 'same-real-host-response'}
        first = observe(self.root, 'first', actual)
        self.followup()
        self.assertEqual(observe(self.root, 'first', actual), first)
        summary = context_summary(self.root)['selections'][0]['observation']
        self.assertTrue(summary['superseded'])
        self.assertFalse(summary['superseded_at_observation'])

    def test_ready_rechecks_user_input_and_never_redispatches_an_observed_block(self):
        selected = plan(self.root, self.block(), CATALOGUE, catalogue_ref='host')
        self.assertNotIn('host_payload', selected)
        self.assertTrue(selected['requires_ready'])
        self.assertEqual(ready(self.root, 'first', CATALOGUE)['host_payload']['reasoning_effort'], 'max')
        self.followup()
        with self.assertRaises(ValueError):
            ready(self.root, 'first', CATALOGUE)
        plan(self.root, self.block('new'), CATALOGUE, catalogue_ref='host')
        observe(self.root, 'new', {'model': 'gpt-6.2-sol', 'effort': 'max', 'source_ref': 'actual-new'})
        with self.assertRaises(ValueError):
            ready(self.root, 'new', CATALOGUE)

    def test_recovery_summary_prioritizes_actual_mismatch_and_reports_omissions(self):
        for index in range(17):
            block = self.block('summary-' + str(index))
            block['evidence'] = ['PRIVATE_RESEARCH_MUST_NOT_ENTER_COMMON_RECOVERY']
            plan(self.root, block, CATALOGUE, catalogue_ref='host')
        observe(self.root, 'summary-16', {'model': 'gpt-6.1-sol', 'effort': 'max',
                                         'source_ref': 'actual-mismatched-host-fields'})
        summary = context_summary(self.root)
        self.assertEqual(summary['omitted_selections'], 1)
        self.assertEqual(summary['mismatched_observations'], 1)
        self.assertFalse(summary['selections'][0]['observation']['matches_selection'])
        self.assertNotIn('PRIVATE_RESEARCH', json.dumps(summary))

    def labor(self, name):
        return {**self.block(name), 'kind': 'routine', 'fully_specified': True,
                'requested_effort': 'low', 'allow_downshift': True,
                'controlled_labor': {'large_batch': True, 'repetitive': True,
                                    'non_intellectual': True, 'controlled': True,
                                    'scope_ref': 'actual-frozen-homogeneous-batch',
                                    'validation_ref': 'actual-batch-validation'}}

    def test_batch_failure_blocks_preplanned_low_and_survives_new_block_ids(self):
        plan(self.root, self.labor('batch-first'), CATALOGUE, catalogue_ref='host')
        plan(self.root, self.labor('preplanned-low'), CATALOGUE, catalogue_ref='host')
        observe(self.root, 'batch-first', {'model': 'gpt-6.2-sol', 'effort': 'low',
                'source_ref': 'constructed-host-execution', 'feedback': {
                    'category': 'quality', 'evidence_ref': 'constructed-validator-failure',
                    'detail': 'new cross-item dependency defeats the mechanical specification'}})
        with self.assertRaises(ValueError):
            ready(self.root, 'preplanned-low', CATALOGUE)
        recovered = next(row for row in context_summary(self.root)['selections']
                         if row['block_id'] == 'preplanned-low')
        self.assertTrue(recovered['current'])
        self.assertTrue(recovered['labor_blocked'])
        self.assertTrue(recovered['labor_replan_required'])
        changed_validator = self.labor('changed-validator')
        changed_validator['controlled_labor']['validation_ref'] = 'new-validator-without-a-real-resolution'
        self.assertEqual(plan(self.root, changed_validator, CATALOGUE, catalogue_ref='host')['effort'], 'max')
        solver = plan(self.root, self.labor('diagnose-current'), CATALOGUE, catalogue_ref='host')
        self.assertEqual(solver['effort'], 'max')
        observe(self.root, 'diagnose-current', {'model': 'gpt-6.2-sol', 'effort': 'max',
                'source_ref': 'constructed-Sol-Max-diagnosis'})
        ids = solver['selection_basis']['labor_hold']['feedback_ids']
        resolve_labor(self.root, {'solver_block_id': 'diagnose-current', 'feedback_ids': ids,
                                 'evidence_ref': 'current-explicit-resolution',
                                 'detail': 'scope and operation corrected after actual diagnosis',
                                 'validation_ref': 'corrected-results-rechecked'})
        with self.assertRaises(ValueError):
            ready(self.root, 'preplanned-low', CATALOGUE)
        self.assertEqual(plan(self.root, self.labor('resume-controlled'), CATALOGUE, catalogue_ref='host')['effort'], 'low')

    def test_held_batch_keeps_evidence_based_ultra_and_old_solver_can_be_currently_adopted(self):
        available = json.loads(json.dumps(CATALOGUE))
        available['models'][1]['supported_reasoning_levels'].append({'effort': 'ultra'})
        plan(self.root, self.labor('first-low'), available, catalogue_ref='host')
        feedback = {'category': 'quality', 'evidence_ref': 'actual-cross-item-failure',
                    'detail': 'the acceptance dependency exceeds the frozen recipe'}
        observe(self.root, 'first-low', {'model': 'gpt-6.2-sol', 'effort': 'low',
                                        'source_ref': 'constructed-low', 'feedback': feedback})
        solver = plan(self.root, self.labor('max-solver'), available, catalogue_ref='host')
        observe(self.root, 'max-solver', {'model': 'gpt-6.2-sol', 'effort': 'max',
                                        'source_ref': 'constructed-max', 'feedback': feedback})
        event = record_feedback(self.root, 'max-solver', feedback)
        ultra = {**self.labor('target-ultra'), 'requested_effort': 'ultra',
                 'unresolved': ['two independent remaining dependencies'], 'feedback': feedback,
                 'escalation': {'trigger': 'task_failure_feedback', 'source_model': 'gpt-6.2-sol',
                    'source_effort': 'max', 'source_block_id': 'max-solver', 'feedback_id': event['feedback_id'],
                    'evidence_ref': feedback['evidence_ref'], 'reason': 'explicit actual host Ultra for parallel remaining proofs'}}
        self.assertEqual(plan(self.root, ultra, available, catalogue_ref='host')['effort'], 'ultra')
        self.assertEqual(ready(self.root, 'target-ultra', available)['host_payload']['reasoning_effort'], 'ultra')
        self.followup('DO：只改最后说明标题，批次与验收保持')
        value = {'solver_block_id': 'max-solver', 'feedback_ids': solver['selection_basis']['labor_hold']['feedback_ids'],
                 'evidence_ref': 'current-adoption-of-existing-valid-result',
                 'detail': 'current accepted scope and validation are unchanged; no redispatch',
                 'validation_ref': 'actual-current-acceptance'}
        with self.assertRaises(ValueError):
            resolve_labor(self.root, value)
        resolve_labor(self.root, {**value, 'current_scope': solver['selection_basis']['labor_scope']})

    def test_failure_escalation_links_real_same_task_max_attempt(self):
        plan(self.root, self.labor('actual-low'), CATALOGUE, catalogue_ref='host')
        observe(self.root, 'actual-low', {'model': 'gpt-6.2-sol', 'effort': 'low', 'source_ref': 'constructed-low'})
        feedback = {'category': 'quality', 'evidence_ref': 'constructed-unsolved-result',
                    'detail': 'the actual result misses its acceptance requirement'}
        event = record_feedback(self.root, 'actual-low', feedback)
        escalation = {'trigger': 'task_failure_feedback', 'source_model': 'gpt-6.2-sol',
                      'source_effort': 'max', 'source_block_id': 'actual-low',
                      'feedback_id': event['feedback_id'], 'evidence_ref': feedback['evidence_ref'],
                      'reason': 'targeted stronger model for the unsolved invariant'}
        target = {**self.block('upgrade'), 'model': 'gpt-6.2-astra',
                  'feedback': feedback, 'unresolved': ['concrete invariant'], 'escalation': escalation}
        with self.assertRaises(ValueError):
            plan(self.root, target, CATALOGUE, catalogue_ref='host')
        plan(self.root, self.block('actual-max'), CATALOGUE, catalogue_ref='host')
        observe(self.root, 'actual-max', {'model': 'gpt-6.2-sol', 'effort': 'max', 'source_ref': 'constructed-max'})
        event = record_feedback(self.root, 'actual-max', feedback)
        escalation.update(source_block_id='actual-max', feedback_id=event['feedback_id'])
        self.assertEqual(plan(self.root, target, CATALOGUE, catalogue_ref='host')['effort'], 'max')

    def test_identical_real_messages_have_different_selection_anchors(self):
        self.followup('DO：同样的修正')
        first = plan(self.root, self.block(), CATALOGUE, catalogue_ref='host')
        self.followup('DO：同样的修正')
        second = plan(self.root, self.block('second'), CATALOGUE, catalogue_ref='host')
        self.assertNotEqual(first['input_ref'], second['input_ref'])
        self.assertEqual(first['input_ref']['source_sha256'], second['input_ref']['source_sha256'])

    def test_legacy_default_and_explicit_current_user_policy_are_separate(self):
        other = self.base / 'old-session'
        create_session(other, request=self.request, p_run='0.16.0@' + '2' * 40)
        self.ready(other)
        self.assertEqual(current_policy(other)['policy']['profile'], 'legacy')
        block = self.block()
        self.assertEqual(plan(other, block, CATALOGUE, catalogue_ref='host')['effort'], 'high')
        source = load_lifecycle(other)['current_message']['source']
        recorded = set_policy(other, {'profile': 'sol-max-feedback', 'reason': 'Actual user explicitly selects Sol Max',
                                     'source_ref': source['source_ref']})
        self.assertEqual(recorded['revision'], 1)
        self.assertEqual(plan(other, self.block('new-policy'), CATALOGUE, catalogue_ref='host')['effort'], 'max')
        with self.assertRaises(ValueError):
            set_policy(other, {'profile': 'sol-max-feedback', 'reason': 'stale claim', 'source_ref': 'not-current-user'})


if __name__ == '__main__':
    unittest.main()
