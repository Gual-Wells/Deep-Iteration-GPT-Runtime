"""Synthetic structural tests; no real court, model call or semantic approval."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from runtime.codex_court import (
    _prosecution_context, court_packet, court_receipt, court_status, open_court,
    record_verdict, remand, required, review, submit_statement,
)
from runtime.codex_lifecycle import handle_message, ingest_message, load_lifecycle
from runtime.codex_session import create_line, create_session
from tests import test_codex_court as fixtures


class EfficientFixture(fixtures.CourtFixture):
    pin = '1.6.0@' + 'e' * 40  # Constructed pin, never a live acquisition.
    roles = fixtures.CORRECTED_ROLES
    answer_roles = {'defendant', 'prosecution_lawyer', 'defence_lawyer'}

    def statement(self, role, charges=None):
        data = super().statement(role, charges)
        if role == 'prosecutor':
            fields = ('extracted_intent', 'interpretation', 'goal_and_result_tendencies',
                      'proposal_maintenance_execution_judgment', 'defaults_and_omissions', 'conclusion')
            data['intent_review'] = {key: 'Synthetic source-bound intent review: ' + key for key in fields}
            data['intent_review'].update(source_ids=['request'], charge_ids=[x['id'] for x in charges or []])
            data['reviewed_context_sha256'] = court_status(self.root)['prosecution_context_sha256']
        if role == 'black_police':
            data['authority_notice'] = {'mode': 'VIOLENT_INTIMIDATION',
                'target_actor_ids': [self.actors[key]['actor_id'] for key in self.roles]}
            data['statement'] = 'Synthetic equal fictional violent intimidation of all court participants.'
        return data

    def parties(self, charges=None):
        for role in ('prosecutor', 'prosecution_lawyer', 'defence_lawyer', 'defendant', 'black_police', 'clerk', 'judge'):
            submit_statement(self.root, self.statement(role, charges if role == 'prosecutor' else []))
        submit_statement(self.root, self.statement('prosecutor'))

    def verdict(self, *args, **kwargs):
        data = super().verdict(*args, **kwargs)
        data['intent_finding'] = 'Synthetic judicial finding on original intent and actual result.'
        for decision in data['decisions']:
            decision['strongest_prosecution'] = 'Synthetic explicit response to the strongest prosecution.'
        return data

    def rework_plan(self):
        data = super().rework_plan()
        data['parameters']['C'] = 1
        data['parameter_reasons']['C'] = 'Synthetic actual current C selection, not an inferred grant.'
        return data

    def state(self):
        return json.loads((self.root / 'court/court.json').read_text(encoding='utf-8'))

    def cli(self, *args):
        return subprocess.run([sys.executable, '-B', str(fixtures.ROOT / 'tools/codex.py'), 'court',
                               *args, '--root', str(self.root)], capture_output=True, text=True, encoding='utf-8')


class CourtEfficiencyTests(EfficientFixture, unittest.TestCase):
    def test_actual_c_precedes_the_preset_and_zero_can_revoke_court(self):
        self.assertTrue(required(self.root))  # New Max reference C1.
        for name, head, expected in [('more', 'More,C=1', True), ('max-zero', 'Max,C=0', False)]:
            with self.subTest(head=head):
                request = self.base / (name + '.txt')
                request.write_text('DIGR(' + head + ',F=0)：Synthetic C selection.', encoding='utf-8')
                root = self.base / name
                create_session(root, request=request, p_run=self.pin,
                               visits_path=self.base / 'visits.jsonl', run_id=name)
                self.assertEqual(required(root), expected)
        self.open()
        correction = self.base / 'actual-c-zero.txt'
        correction.write_text('DIGR(C=0)：实际撤销本任务庭审，其余工作继续。', encoding='utf-8')
        message = ingest_message(self.root, source=correction, source_ref='synthetic:actual-c-zero', route_pin=self.pin)
        handle_message(self.root, message_id=message['message_id'], action='continue', reason='Synthetic current choice.')
        self.assertEqual(load_lifecycle(self.root)['court_parameter_source']['value'], 0)
        self.assertFalse(required(self.root))
        self.assertEqual(court_status(self.root)['status'], 'NOT_REQUIRED')

    def test_c_zero_revocation_cannot_reopen_an_unfinished_historical_round(self):
        self.open()
        history = self.root / 'court/court.json'
        before = history.read_bytes()
        correction = self.base / 'revoke-before-verdict.txt'
        correction.write_text('DIGR(C=0)：撤销当前庭审，保留已发生的历史。', encoding='utf-8')
        message = ingest_message(self.root, source=correction,
                                 source_ref='synthetic:c-zero-before-verdict', route_pin=self.pin)
        handle_message(self.root, message_id=message['message_id'], action='continue',
                       reason='Synthetic actual C0 revocation changes the task input.')
        self.assertEqual(court_status(self.root)['status'], 'NOT_REQUIRED')
        with self.assertRaisesRegex(ValueError, 'review requires.*current C=1'):
            review(self.root, self.performed_work())
        self.assertEqual(history.read_bytes(), before)
        self.assertEqual(len(self.state()['rounds']), 1)

    def test_local_supplements_accumulate_and_keep_current_prosecution_required(self):
        self.open()
        self.parties([self.charge('C1'), self.charge('C2')])
        submit_statement(self.root, self.statement('prosecutor', [self.charge('C3')]))
        with self.assertRaisesRegex(ValueError, 'must answer every actual charge'):
            record_verdict(self.root, self.verdict())
        for role in self.answer_roles:
            data = self.statement(role)
            data['responses'] = [x for x in data['responses'] if x['charge_id'] == 'C3']
            submit_statement(self.root, data)
        for covered in court_status(self.root)['response_coverage'].values():
            self.assertEqual(covered, ['C1', 'C2', 'C3'])
        with self.assertRaisesRegex(ValueError, 'continue investigation'):
            record_verdict(self.root, self.verdict())
        submit_statement(self.root, self.statement('prosecutor'))
        self.assertEqual(record_verdict(self.root, self.verdict())['outcome'], 'ACQUITTED')

    def test_effective_answer_replaces_one_issue_without_erasing_another(self):
        self.open()
        self.parties([self.charge('C1'), self.charge('C2')])
        data = self.statement('defence_lawyer')
        data['responses'] = [x for x in data['responses'] if x['charge_id'] == 'C1']
        data['responses'][0]['response'] = 'Synthetic actual replacement reason for C1.'
        submit_statement(self.root, data)
        packet = court_packet(self.root, 'judge')
        answers = packet['effective_responses']['defence_lawyer']
        self.assertEqual(set(answers), {'C1', 'C2'})
        self.assertEqual(answers['C1']['response'], data['responses'][0]['response'])
        self.assertNotEqual(answers['C2']['statement_source']['path'], answers['C1']['statement_source']['path'])
        self.assertEqual(packet['reading_attestation'].split(';')[0], 'NOT_CREATED')
        self.assertNotIn('text_snapshot', json.dumps(packet))

    def test_new_material_has_no_automatic_old_response_coverage(self):
        self.open()
        self.parties([self.charge()])
        record_verdict(self.root, self.verdict('REEXECUTE', 'SUSTAINED'))
        remand(self.root, self.rework_plan())
        self.product.write_text('Synthetic repaired new material.', encoding='utf-8')
        self.mark_complete()
        result = review(self.root, self.performed_work(['C1']))
        self.assertEqual(result['response_coverage']['defence_lawyer'], [])
        for role in self.roles:
            data = self.statement(role)
            data['responses'] = []
            submit_statement(self.root, data)
        submit_statement(self.root, self.statement('prosecutor'))
        with self.assertRaisesRegex(ValueError, 'must answer every actual charge'):
            record_verdict(self.root, self.verdict())
        packet = court_packet(self.root, 'judge')
        changes = packet['previous_source_changes']
        self.assertIn('request', changes['unchanged'])
        self.assertIn('reexecution:1', changes['added'])

    def test_context_ignores_only_metadata_and_exact_duplicate_public_bytes(self):
        self.open()
        self.parties([self.charge()])
        hearing = self.state()['rounds'][-1]
        expected = _prosecution_context(hearing)
        for field in ('submitted_wall_ns', 'path', 'resolved_path', 'source_ref'):
            with self.subTest(field=field):
                changed = deepcopy(hearing)
                party = next(s for s in changed['statements'] if s['role'] == 'defendant')
                if field == 'submitted_wall_ns':
                    party[field] += 1
                else:
                    party['source'][field] += ':same-bytes'
                self.assertEqual(_prosecution_context(changed), expected)
        changed = deepcopy(hearing)
        changed['statements'].append(deepcopy(next(s for s in hearing['statements'] if s['role'] == 'defendant')))
        self.assertEqual(_prosecution_context(changed), expected)
        for field in ('statement', 'source_bytes', 'response'):
            with self.subTest(changed_content=field):
                changed = deepcopy(hearing)
                party = next(s for s in changed['statements'] if s['role'] == 'defendant')
                if field == 'statement':
                    party['statement'] += ' A genuinely new public reason.'
                elif field == 'source_bytes':
                    party['source']['sha256'] = '0' * 64
                else:
                    party['responses'][0]['response'] += ' New actual response content.'
                self.assertNotEqual(_prosecution_context(changed), expected)

    def test_duplicate_registration_stays_current_but_new_prose_cannot_self_exempt(self):
        self.open()
        self.parties([self.charge()])
        old = next(s for s in self.state()['rounds'][-1]['statements'] if s['role'] == 'defendant')
        duplicate = {key: deepcopy(old[key]) for key in
                     ('role', 'actor_id', 'material_sha256', 'read_sources', 'statement', 'responses', 'source')}
        submit_statement(self.root, duplicate)
        self.assertEqual(court_status(self.root)['prosecution_review_status'], 'CURRENT')
        duplicate['statement'] += ' A new published argument, despite a claimed immaterial flag.'
        duplicate['immaterial'] = True
        submit_statement(self.root, duplicate)
        self.assertEqual(court_status(self.root)['prosecution_review_status'], 'STALE')

    def test_police_reads_role_material_without_claiming_full_technical_reading(self):
        condition = self.source('conditions', 'Synthetic actual common condition source.')
        self.open_input['sources'].append({'id': 'conditions', 'kind': 'CONDITIONS', **condition})
        self.open()
        data = self.statement('black_police')
        data['read_sources'] = ['request']
        with self.assertRaisesRegex(ValueError, 'request and current conditions'):
            submit_statement(self.root, data)
        data['read_sources'] = ['request', 'conditions']
        submit_statement(self.root, data)
        saved = self.state()['rounds'][-1]['statements'][-1]
        self.assertEqual(saved['read_sources'], ['request', 'conditions'])
        self.assertEqual(set(saved['authority_notice']['target_actor_ids']),
                         {x['actor_id'] for x in self.actors.values()})
        data = self.statement('defence_lawyer')
        data['read_sources'] = ['request', 'conditions']
        with self.assertRaisesRegex(ValueError, 'original/current common material'):
            submit_statement(self.root, data)
        packet = court_packet(self.root, 'black_police')
        self.assertEqual(set(packet['sources']), {'request', 'conditions'})
        self.assertNotIn('effective_responses', packet)
        self.assertNotIn('text_snapshot', json.dumps(packet))

    def test_police_required_conditions_follow_kind_including_automatic_sources(self):
        decisions = self.source('actual-decisions', 'Synthetic accepted decisions source.')
        self.root = self.base / 'task-with-decisions'
        create_session(self.root, request=self.request, p_run=self.pin, decisions=decisions['path'],
                       visits_path=self.base / 'visits.jsonl', run_id='synthetic-court-with-decisions')
        create_line(self.root, 'M01', parameters=self.parameters, owner='fixture-main')
        self.mark_complete()
        # Court source selection binds this constructed JSON as CONDITIONS;
        # the fixture does not claim a real commission or semantic approval.
        (self.root / 'foundation.json').write_text('{"scope":"Synthetic foundation source only"}', encoding='utf-8')
        for identifier in ('z-context', 'accepted-context'):
            source = self.source(identifier, 'Synthetic condition with a custom source ID.')
            self.open_input['sources'].append({'id': identifier, 'kind': 'CONDITIONS', **source})
        technical = self.source('technical-product', 'Synthetic technical product, not a condition source.')
        self.open_input['sources'].append({'id': 'technical-product', 'kind': 'PRODUCT', **technical})
        self.open()
        packet = court_packet(self.root, 'black_police')
        expected = ['request', 'accepted-context', 'decisions', 'foundation', 'z-context']
        self.assertEqual(packet['required_read_sources'], expected)
        self.assertEqual(set(packet['sources']), set(expected))
        data = self.statement('black_police')
        data['read_sources'] = ['request']
        with self.assertRaisesRegex(ValueError, 'current conditions'):
            submit_statement(self.root, data)
        data['read_sources'] = expected
        submit_statement(self.root, data)
        self.assertEqual(self.state()['rounds'][-1]['statements'][-1]['read_sources'], expected)

    def test_police_packet_locates_shared_record_and_captured_current_user_input(self):
        correction = self.base / 'current-user-conditions.txt'
        original = 'DIGR(C=1)：新增真实条件：沿同一任务保留全部七席身份。'
        correction.write_text(original, encoding='utf-8')
        message = ingest_message(self.root, source=correction,
                                 source_ref='synthetic:actual-current-condition', route_pin=self.pin)
        handle_message(self.root, message_id=message['message_id'], action='continue',
                       reason='Synthetic captured current user conditions.')
        self.open()
        packet = court_packet(self.root, 'black_police')
        self.assertEqual(Path(packet['record_locator']['path']), self.root / 'court/court.json')
        self.assertEqual(packet['record_locator']['material_sha256'], packet['material_sha256'])
        current = packet['current_user_input']
        self.assertEqual(current['task_input_ref'], load_lifecycle(self.root)['task_input_ref'])
        self.assertEqual(Path(current['source']['path']), correction)
        self.assertTrue(current['read_required'])
        correction.write_text('A later external edit must not replace the captured user input.', encoding='utf-8')
        located = json.loads(Path(current['snapshot_locator']['path']).read_text(encoding='utf-8'))
        for part in current['snapshot_locator']['json_pointer'].strip('/').split('/'):
            located = located[int(part)] if isinstance(located, list) else located[part]
        self.assertEqual(located['text'], original)
        self.assertEqual(located['sha256'], current['source']['sha256'])
        self.assertNotIn('text', current)  # A locator, not another full repeated snapshot.

    def test_cli_compact_is_default_and_full_python_status_is_preserved(self):
        full = self.open()
        self.assertIn('text_snapshot', full['actors']['judge']['dispatch'])
        small = court_receipt(self.root, full)
        self.assertEqual(small['actors']['judge']['actor_id'], full['actors']['judge']['actor_id'])
        self.assertNotIn('text_snapshot', json.dumps(small))
        for flags, expect_full in [((), False), (('--full',), True)]:
            result = self.cli('status', *flags)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual('dispatch' in payload['actors']['judge'], expect_full)
            self.assertEqual(payload['material_sha256'], full['material_sha256'])
        packet = self.cli('packet', '--role', 'black_police')
        self.assertEqual(packet.returncode, 0, packet.stderr)
        self.assertEqual(json.loads(packet.stdout)['reading_attestation'].split(';')[0], 'NOT_CREATED')
        self.assertEqual(self.cli('packet').returncode, 2)

    def test_remand_requires_the_actual_c_and_cannot_waive_it_as_immaterial(self):
        status = self.open()
        self.assertIn('task:C_selection', status['obligation_ids'])
        self.parties([self.charge()])
        proposed = self.verdict('IMMATERIAL_ERROR', 'IMMATERIAL')
        next(o for o in proposed['obligations'] if o['id'] == 'task:C_selection')['status'] = 'IMMATERIAL'
        with self.assertRaisesRegex(ValueError, 'hard responsibility'):
            record_verdict(self.root, proposed)
        record_verdict(self.root, self.verdict('REEXECUTE', 'SUSTAINED'))
        plan = self.rework_plan()
        wrong = deepcopy(plan)
        wrong['parameters']['C'] = 0
        with self.assertRaisesRegex(ValueError, 'cannot grant/change C'):
            remand(self.root, wrong)
        missing = deepcopy(plan)
        del missing['parameters']['C']
        with self.assertRaisesRegex(ValueError, 'complete.*C'):
            remand(self.root, missing)
        missing = deepcopy(plan)
        del missing['parameter_reasons']['C']
        with self.assertRaisesRegex(ValueError, 'every custom parameter'):
            remand(self.root, missing)
        self.assertEqual(remand(self.root, plan)['status'], 'REMAND_PLANNED_NOT_EXECUTED')


class OldPinEfficiencyBoundaryTests(EfficientFixture, unittest.TestCase):
    pin = '1.5.2@' + 'f' * 40

    def test_old_cli_and_context_retain_the_original_contract(self):
        full = self.open()
        self.assertIs(court_receipt(self.root, full), full)
        result = self.cli('status')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('dispatch', json.loads(result.stdout)['actors']['judge'])
        self.parties([self.charge()])
        hearing = self.state()['rounds'][-1]
        changed = deepcopy(hearing)
        party = next(s for s in changed['statements'] if s['role'] == 'defendant')
        party['submitted_wall_ns'] += 1
        self.assertNotEqual(_prosecution_context(changed), _prosecution_context(hearing))
        with self.assertRaisesRegex(ValueError, '1.6'):
            court_packet(self.root, 'judge')

    def test_old_latest_only_coverage_and_full_police_reading_stay_required(self):
        self.open()
        self.parties([self.charge()])
        data = self.statement('defence_lawyer')
        data['responses'] = []
        submit_statement(self.root, data)
        with self.assertRaisesRegex(ValueError, 'must answer every actual charge'):
            record_verdict(self.root, self.verdict())
        data = self.statement('black_police')
        data['read_sources'] = ['request']
        with self.assertRaisesRegex(ValueError, 'original/current common material'):
            submit_statement(self.root, data)


if __name__ == '__main__':
    unittest.main()
