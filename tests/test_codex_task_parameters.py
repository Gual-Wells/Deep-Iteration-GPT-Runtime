"""Task-wide binary X and inferred F journeys; all mail effects are synthetic."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from runtime.codex_lifecycle import handle_message, ingest_message, load_lifecycle, recover_session
from runtime.codex_presets import preset_catalog, resolve_defaults
from runtime.codex_profile import classify_invocation
from runtime.codex_session import (create_line, create_session, line_packet, session_report,
                                   set_task_parameters, task_delivery_policy, task_parameters)
from tools.codex import main as codex


PIN = '1.5.0@' + 'e' * 40
OLD = '1.4.1@' + 'a' * 40


class FormalTaskParameterParsing(unittest.TestCase):
    def test_all_tiers_offer_binary_x_and_f_references_without_explicit_promotion(self):
        for tier, count in (('Light', 0), ('Less', 2), ('Default', 3), ('More', 4), ('Max', 6)):
            with self.subTest(tier=tier):
                value = classify_invocation(f'DIGR({tier}):task', p_run=PIN)
                depth = value['depth_preferences']
                self.assertEqual((depth['preference_baseline']['X'], depth['preference_baseline']['F']), (0, count))
                self.assertEqual(depth['explicit_overrides'], {})
                self.assertFalse(value['delivery_explicit'])
                self.assertEqual(value['delivery_selection']['mode'], 'local')
                old = classify_invocation(f'DIGR({tier}):task', p_run=OLD)['depth_preferences']
                self.assertEqual(old['preference_baseline']['F'], 0)
                self.assertNotIn('X', old['preference_baseline'])
        catalog = preset_catalog()
        self.assertEqual(catalog['presets']['Max']['F'], 6)
        self.assertEqual(catalog['task_parameters'], ['X', 'F'])

    def test_binary_values_share_the_formal_group_and_preserve_the_body(self):
        for group, x in (('(Max,F=4,X=0,source=off)', 0), ('（Less，X（1），F（2））', 1),
                         ('(X=Gmail,F=2)', 1), ('(N=3,X)', 1), ('(Less)(X=0)', 0)):
            with self.subTest(group=group):
                body = '  task: literal X=1 and (X=Other)\n'
                value = classify_invocation('DIGR' + group + ':' + body, p_run=PIN)
                self.assertEqual(value['classification'], 'EXECUTING', value)
                self.assertEqual(value['task'], body)
                self.assertEqual(value['depth_preferences']['explicit_overrides']['X'], x)
                self.assertTrue(value['delivery_explicit'])
                self.assertEqual(value['delivery_selection']['mode'], 'external' if x else 'local')
        disabled = classify_invocation('DIGR(X=0,F=3,source=off):task', p_run=PIN)
        self.assertEqual(disabled['depth_preferences']['explicit_overrides'], {'X': 0, 'F': 3})
        self.assertEqual(disabled['depth_preferences']['unparsed_tokens'], ['source=off'])

    def test_legacy_forms_remain_aliases_and_old_pins_keep_their_parser(self):
        for group in ('(X)', '(X=Gmail)', '()(X)', '(Less)(X=Gmail)'):
            current = classify_invocation('DIGR' + group + ':task', p_run=PIN)
            old = classify_invocation('DIGR' + group + ':task', p_run=OLD)
            self.assertEqual(current['delivery_selection'], old['delivery_selection'])
            self.assertEqual(current['depth_preferences']['explicit_overrides'].get('X'), 1)
            self.assertNotIn('X', old['depth_preferences']['explicit_overrides'])
        for group in ('(X=0)', '(Max,X=1)'):
            self.assertEqual(classify_invocation('DIGR' + group + ':task', p_run=OLD)['classification'], 'INVALID')
        historical_alias = classify_invocation('DIGR(X=Private_Archive):task', p_run=OLD)
        self.assertEqual(historical_alias['delivery_selection']['target'], 'private_archive')

    def test_malformed_binary_or_duplicate_choices_do_not_arm_external_delivery(self):
        for group in ('(X=2)', '(X=-1)', '(X=1.0)', '(X=)', '(X())', '(X=True)',
                      '(X=Other)', '(X=0,X=1)', '(X=1,X(1))', '(X=0)(X)',
                      '(S(n=1,X=1))', '(X)(N=2)', '(N=2)(F=2)(X=1)'):
            with self.subTest(group=group):
                value = classify_invocation('DIGR' + group + ':task', p_run=PIN)
                self.assertEqual(value['classification'], 'INVALID', value)
                self.assertEqual(value['delivery_selection']['mode'], 'local')
        for value in (True, 2, -1, 1.0):
            with self.assertRaises(ValueError):
                resolve_defaults(overrides={'X': value}, preference_only=True)

    def test_body_quotes_and_omission_never_activate_x(self):
        omitted = classify_invocation('DIGR:Discuss X=1 and (X).', p_run=PIN)
        explicit_zero = classify_invocation('DIGR(X=0):task', p_run=PIN)
        self.assertEqual(omitted['delivery_selection'], explicit_zero['delivery_selection'])
        self.assertFalse(omitted['delivery_explicit'])
        self.assertTrue(explicit_zero['delivery_explicit'])
        for raw in ('“DIGR(X=1):quoted”', 'Explain DIGR(X=1):text', 'digr(X=1):text'):
            self.assertEqual(classify_invocation(raw, p_run=PIN)['classification'], 'NATIVE')


class FormalTaskParameterJourneys(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='codex-task-parameters-')
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.counter = 0
        self.registry = self.base / 'registry.json'
        self.write_registry('fixture@example.test')

    def write_registry(self, mailbox):
        self.registry.write_text(json.dumps({'format': 'digr-delivery-targets-1', 'targets': {
            'gmail': {'channel': 'gmail', 'account': mailbox, 'recipient': mailbox,
                      'target_kind': 'self_mailbox', 'transport': 'native-connector'}}}), encoding='utf-8')

    def create(self, name='task', raw='DIGR(Max):synthetic task', *, pin=PIN, **kwargs):
        request = self.base / (name + '-request.txt')
        request.write_text(raw, encoding='utf-8')
        root = self.base / name
        create_session(root, request=request, p_run=pin, visits_path=self.base / 'visits.jsonl',
                       destinations=self.registry, **kwargs)
        return root

    def ingest(self, root, text):
        self.counter += 1
        source = self.base / f'input-{self.counter}.txt'
        source.write_text(text, encoding='utf-8')
        ref = f'actual-synthetic-input-{self.counter}'
        state = ingest_message(root, source=source, source_ref=ref,
                               route_pin=PIN if text.startswith('DIGR') else None)
        return state['message_id'], source, ref

    def handle(self, root, text, **kwargs):
        number, _, _ = self.ingest(root, text)
        return handle_message(root, message_id=number, action='ordinary', reason='Actual selected synthetic input', **kwargs)

    def test_formal_f_is_inferred_below_reference_and_restored_without_duplicating_m(self):
        root = self.create(raw='DIGR(Max,X=0,M=2):synthetic task')
        initial = task_parameters(root)
        self.assertEqual(initial['parameters'], {'X': 0, 'F': None})
        self.assertEqual(initial['reference'], {'X': 0, 'F': 6})
        self.assertEqual(initial['input_explicit'], {'X': True, 'F': False})
        self.assertFalse(initial['F_initialized'])
        effective = set_task_parameters(root, parameters={'X': 0, 'F': 0},
                                        reasons={'F': 'All required source material is supplied; no community choice remains.'})
        self.assertEqual(effective['parameters'], {'X': 0, 'F': 0})
        values = {'N': 1, 'R': 0, 'T': 0, 'B': 0, 'D': 0, 'V': 0, 'L': 3,
                  'S': {'n': 0, 't': 0, 'r': 0, 'b': 0}}
        for line in ('M01', 'M02'):
            created = create_line(root, line, parameters=values)
            self.assertEqual(created['explicit_parameter_differences'], [])
            self.assertNotIn('F', created['parameters'])
            self.assertIn('"F_initialized": true', line_packet(root, line))
        recover_session(root, reason='Resume the same task')
        self.assertEqual(session_report(root)['task_parameters']['parameters'], {'X': 0, 'F': 0})

    def test_f_explicit_values_and_effective_targets_cannot_silently_shrink(self):
        root = self.create(raw='DIGR(F=3,source=off):synthetic task')
        self.assertEqual(task_parameters(root)['parameters']['F'], 3)
        for count in (2, -1, True):
            with self.assertRaises((TypeError, ValueError)):
                set_task_parameters(root, parameters={'F': count}, reasons={'F': 'Insufficient reason to reduce.'})
        set_task_parameters(root, parameters={'F': 4}, reasons={'F': 'Compare another independent mechanism.'})
        with self.assertRaisesRegex(ValueError, 'silently reduced'):
            set_task_parameters(root, parameters={'F': 3}, reasons={'F': 'Convenience.'})
        decision = self.handle(root, 'User explicitly narrows the public-project research minimum to one.')
        revised = set_task_parameters(root, parameters={'F': 1}, reasons={'F': 'User narrowed the research scope.'},
                                      user_revision=decision['current_message']['source']['source_ref'])
        self.assertEqual(revised['parameters']['F'], 1)
        raised = set_task_parameters(root, parameters={'F': 2}, reasons={'F': 'An additional useful contrast remains.'})
        self.assertEqual(raised['parameters']['F'], 2)

    def test_f_revision_rejects_arbitrary_or_stale_user_sources(self):
        root = self.create(raw='DIGR(F=4):synthetic task')
        decision = self.handle(root, 'User permits reducing the F research minimum to two.')
        old_ref = decision['current_message']['source']['source_ref']
        set_task_parameters(root, parameters={'F': 2}, reasons={'F': 'Actual current user narrows the target.'},
                            user_revision=old_ref)
        self.handle(root, 'Continue the accepted scope; this is a later actual user input.')
        for ref in ('a model-written reason is not a source', old_ref):
            with self.assertRaisesRegex(ValueError, 'currently handled actual user source'):
                set_task_parameters(root, parameters={'F': 0}, reasons={'F': 'Convenience.'}, user_revision=ref)
        self.assertEqual(task_parameters(root)['parameters']['F'], 2)
        explicit = self.handle(root, 'DIGR(F=3):the current user sets three projects')
        with self.assertRaisesRegex(ValueError, 'current explicit user header'):
            set_task_parameters(root, parameters={'F': 1}, reasons={'F': 'Not what the current header says.'},
                                user_revision=explicit['current_message']['source']['source_ref'])

    def test_every_new_tier_requires_a_formal_f_inference_before_line_init(self):
        values = {'N': 1, 'R': 0, 'T': 0, 'B': 0, 'D': 0, 'V': 0, 'L': 3,
                  'S': {'n': 0, 't': 0, 'r': 0, 'b': 0}}
        for tier in ('Light', 'Default', 'Max'):
            root = self.create(tier, f'DIGR({tier}):synthetic task')
            with self.assertRaisesRegex(ValueError, 'F inference'):
                create_line(root, 'M01', parameters=values)
            set_task_parameters(root, parameters={'F': 0}, reasons={'F': 'Task materials settle all relevant choices.'})
            create_line(root, 'M01', parameters=values)

    def test_main_cannot_arm_x_with_injected_parameters(self):
        with self.assertRaisesRegex(ValueError, 'original user header'):
            self.create(explicit_parameters={'X': 1})
        root = self.create('valid', 'DIGR:synthetic task')
        with self.assertRaisesRegex(ValueError, 'actual selected user input'):
            set_task_parameters(root, parameters={'F': 0, 'X': 1}, reasons={'F': 'No research needed.'})
        self.assertEqual(task_parameters(root)['parameters']['X'], 0)

    def test_explicit_zero_revokes_and_omission_inherits_then_one_restores_frozen_mailbox(self):
        root = self.create(raw='DIGR(X=1):synthetic task')
        original = task_delivery_policy(root)
        self.handle(root, 'DIGR(Light):continue without changing delivery')
        self.assertEqual(task_delivery_policy(root), original)
        zero = self.handle(root, 'DIGR(F=0,X=0):only files here')
        self.assertEqual(zero['delivery_policy']['mode'], 'local')
        self.assertEqual(task_parameters(root)['parameters']['X'], 0)
        self.assertEqual(task_parameters(root)['parameters']['F'], 0)
        self.assertTrue(task_parameters(root)['input_explicit']['X'])
        self.assertEqual(task_parameters(root)['X_source']['basis'], 'INVOCATION_HEADER')
        self.handle(root, 'Continue; the text contains X=1 as an example.')
        self.assertEqual(task_parameters(root)['parameters']['X'], 0)
        self.write_registry('changed-global-default@example.test')
        self.handle(root, 'DIGR(X=1):resume the same selected mailbox')
        self.assertEqual(task_delivery_policy(root), original)

    def test_reenable_preserves_sent_and_uncertain_effects(self):
        from runtime import codex_delivery
        from tests.test_codex_x_invocation import CodexXIntentScopeTests
        for sent in (False, True):
            root = self.create(f'effects-{sent}', 'DIGR(X=1):synthetic task')
            original = CodexXIntentScopeTests.record_synthetic_attempt(self, root, sent=sent)
            before = codex_delivery.inspect(root)['deliveries']
            self.handle(root, 'DIGR(X=0):keep future files here')
            self.write_registry('different-after-effects@example.test')
            self.handle(root, 'DIGR(X=1):resume the original destination')
            self.assertEqual(task_delivery_policy(root), original)
            after = codex_delivery.inspect(root)['deliveries']
            self.assertEqual(after, before)
            self.assertEqual(after[0]['recorded_status'], 'SENT_VERIFIED' if sent else 'SENDING')

    def test_caller_cannot_hide_explicit_zero_by_resupplying_the_previous_selection(self):
        root = self.create(raw='DIGR(X=1):synthetic task')
        number, _, _ = self.ingest(root, 'DIGR(X=0):turn external delivery off')
        with self.assertRaisesRegex(ValueError, 'current source X header'):
            handle_message(root, message_id=number, action='ordinary', reason='Must honor actual zero',
                           delivery_selection={'mode': 'external', 'target': 'gmail', 'explicit': True})
        handle_message(root, message_id=number, action='ordinary', reason='Apply the actual explicit zero')
        self.assertEqual(task_parameters(root)['parameters']['X'], 0)

    def test_followup_explicit_f_revision_changes_the_effective_task_target(self):
        root = self.create(raw='DIGR(F=4):synthetic task')
        state = self.handle(root, 'DIGR(F=1):narrow this task research requirement')
        effective = task_parameters(root)
        self.assertEqual(effective['parameters']['F'], 1)
        self.assertEqual(effective['explicit_parameters']['F'], 1)
        self.assertEqual(effective['changes'][-1]['user_revision'], state['current_message']['source']['source_ref'])

    def test_ordinary_f_revision_anchors_the_same_real_user_input(self):
        root = self.create(raw='DIGR(F=6):synthetic task')
        state = self.handle(root, 'DIGR(F=3):the actual user lowers six to three')
        self.assertEqual(state['task_input_ref']['message_id'], state['current_message']['id'])
        self.assertEqual(state['task_input_ref']['source_ref'], state['current_message']['source']['source_ref'])
        self.assertEqual(state['task_input_ref']['source_sha256'], state['current_message']['source']['sha256'])
        self.assertIn('lowers six to three', state['task_input_message']['source']['text'])
        self.assertEqual(load_lifecycle(root)['task_input_ref'], state['task_input_ref'])

    def test_natural_user_f_revision_anchors_but_main_inference_and_unchanged_questions_do_not(self):
        root = self.create(raw='DIGR(F=6):synthetic task')
        original = load_lifecycle(root)['task_input_ref']
        self.handle(root, 'What is the current status? Quoted X=1 and Max are only text.')
        set_task_parameters(root, parameters={'F': 7}, reasons={'F': 'Main finds an additional useful independent contrast.'})
        self.assertEqual(load_lifecycle(root)['task_input_ref'], original)
        unchanged = self.handle(root, 'Confirm the same current seven-project target without changing it.')
        set_task_parameters(root, parameters={'F': 7}, reasons={'F': 'Actual user repeats the same target.'},
                            user_revision=unchanged['current_message']['source']['source_ref'])
        self.assertEqual(load_lifecycle(root)['task_input_ref'], original)
        decision = self.handle(root, 'Reduce the actual public-project research minimum from seven to three.')
        self.assertEqual(decision['task_input_ref'], original)
        set_task_parameters(root, parameters={'F': 3}, reasons={'F': 'Actual current user narrows the target.'},
                            user_revision=decision['current_message']['source']['source_ref'])
        current = load_lifecycle(root)
        self.assertEqual(current['task_input_ref']['message_id'], decision['current_message']['id'])
        self.assertEqual(current['task_input_message']['source'], decision['current_message']['source'])

    def test_ordinary_binary_x_switches_and_new_max_duty_anchor_without_rebinding_status_queries(self):
        root = self.create(raw='DIGR(Light,F=0,X=0):synthetic task')
        original = load_lifecycle(root)['task_input_ref']
        self.handle(root, 'Please report status without changing any task setting.')
        self.assertEqual(load_lifecycle(root)['task_input_ref'], original)
        enabled = self.handle(root, 'DIGR(X=1):activate final files', destinations=self.registry)
        self.assertEqual(enabled['task_input_ref']['message_id'], enabled['current_message']['id'])
        disabled = self.handle(root, 'DIGR(X=0):keep remaining files here')
        self.assertEqual(disabled['task_input_ref']['message_id'], disabled['current_message']['id'])
        maximum = self.handle(root, 'DIGR(Max):enable the additional Max court duty')
        self.assertTrue(maximum['max_court_required'])
        self.assertEqual(maximum['task_input_ref']['message_id'], maximum['current_message']['id'])
        self.handle(root, 'How is the task going?')
        after = load_lifecycle(root)
        self.assertEqual(after['task_input_ref'], maximum['task_input_ref'])
        self.assertEqual(after['max_court_source'], maximum['max_court_source'])

    def test_old_layered_ordinary_keeps_the_original_task_input_semantics(self):
        root = self.create(raw='DIGR(F=6):synthetic historical task', pin=OLD)
        original = load_lifecycle(root)['task_input_ref']
        self.handle(root, 'DIGR(F=3):old frozen parser and original ordinary handling')
        self.assertEqual(load_lifecycle(root)['task_input_ref'], original)
        self.assertIsNone(task_parameters(root))
        self.assertNotIn('max_court_required', load_lifecycle(root))

    def test_ordinary_header_and_natural_f_revisions_reach_a_real_user_revised_court_path(self):
        from runtime.codex_court import court_status, record_verdict, remand, review
        from tests.test_codex_court import CourtTests
        for header in (False, True):
            with self.subTest(header=header):
                fixture = CourtTests()
                fixture.setUp()
                self.addCleanup(fixture.doCleanups)
                set_task_parameters(fixture.root, parameters={'F': 6}, reasons={'F': 'Synthetic original effective F6.'})
                fixture.open()
                fixture.parties([fixture.charge(obligation='task:F')])
                verdict = fixture.verdict('REEXECUTE', 'SUSTAINED')
                next(item for item in verdict['obligations'] if item['id'] == 'task:F')['status'] = 'PENDING'
                record_verdict(fixture.root, verdict)
                quote = 'The actual user changes F6 to F3 and preserves all other responsibilities.'
                source = fixture.source('ordinary-f-correction', ('DIGR(Max,F=3):' if header else '') + quote)
                pending = ingest_message(fixture.root, source=Path(source['path']), source_ref=source['source_ref'],
                                         route_pin=PIN if header else None)
                handle_message(fixture.root, message_id=pending['message_id'], action='ordinary',
                               reason='Actual ordinary user parameter revision, not a new task.')
                if not header:
                    set_task_parameters(fixture.root, parameters={'F': 3}, reasons={'F': 'Actual current natural-language correction.'},
                                        user_revision=source['source_ref'])
                current = load_lifecycle(fixture.root)
                self.assertEqual(current['task_input_ref']['source_ref'], source['source_ref'])
                self.assertEqual(court_status(fixture.root)['status'], 'STALE')
                plan = fixture.rework_plan()
                plan['parameters']['F'] = 3
                plan['changed_material_reason'] = 'The actual handled ordinary source changes the formal F target.'
                remand(fixture.root, plan)
                fixture.mark_complete()
                review(fixture.root, fixture.performed_work(['C1']))
                fixture.parties()
                proposed = fixture.verdict()
                original = next(item for item in proposed['obligations'] if item['id'] == 'task:F')
                original.update(status='USER_REVISED', reason='Actual user revised six to three; six was not completed.',
                                user_revision={'task_input_ref': current['task_input_ref'], 'quote': quote})
                self.assertTrue(record_verdict(fixture.root, proposed)['can_close'])

    def test_pending_user_input_fences_parameter_mutation(self):
        root = self.create()
        self.ingest(root, 'User correction still pending.')
        with self.assertRaisesRegex(ValueError, 'pending'):
            set_task_parameters(root, parameters={'F': 0}, reasons={'F': 'Wait for actual correction.'})

    def test_max_obligation_survives_more_than_recent_message_window(self):
        root = self.create(raw='DIGR(Light):synthetic task')
        self.handle(root, 'DIGR(Max):continue with Max')
        maximum = load_lifecycle(root)['max_court_source']
        for _ in range(10):
            self.handle(root, 'DIGR(Light,F=0):continue the same accepted work')
        restored = load_lifecycle(root)
        self.assertTrue(restored['max_court_required'])
        self.assertEqual(restored['max_court_source'], maximum)
        self.assertLessEqual(len(restored['recent_messages']), 8)

    def test_old_task_state_is_not_silently_upgraded(self):
        root = self.create(raw='DIGR(Max,F=2)(X):synthetic task', pin=OLD)
        self.assertIsNone(task_parameters(root))
        self.assertFalse((root / 'task-parameters.json').exists())
        self.assertNotIn('max_court_required', load_lifecycle(root))
        with self.assertRaisesRegex(ValueError, 'older pins unchanged'):
            set_task_parameters(root, parameters={'F': 0}, reasons={'F': 'Cannot change old interpretation.'})

    def test_cli_reads_and_persists_task_parameters(self):
        root = self.create()
        payload = self.base / 'parameters.json'
        payload.write_text(json.dumps({'parameters': {'F': 2}, 'reasons': {'F': 'Two concrete relevant approaches.'}}), encoding='utf-8')
        for arguments in (('task', 'parameters', '--root', root, '--input', payload),
                          ('task', 'parameters', '--root', root)):
            output = StringIO()
            with redirect_stdout(output):
                status = codex([str(item) for item in arguments])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.getvalue())['parameters']['F'], 2)


if __name__ == '__main__':
    unittest.main()
