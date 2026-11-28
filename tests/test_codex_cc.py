"""Community Cry structure and model-role state transitions using synthetic public sources."""
import json
import unittest

from runtime.codex_cc import assess, load_pool, search_pool
from runtime.codex_court import (
    cc_intervene, cc_resume, court_packet, court_status, record_docket,
    record_verdict, review, submit_statement,
)
from runtime.codex_live import ParagraphRelay, acknowledge, emit_work, pending
from runtime.codex_return import execution_errors, record_execution_error, response_body, seal_return
from tests.test_codex_court import CorrectedCourtFixture


class CommunityCryTests(CorrectedCourtFixture, unittest.TestCase):
    pin = '2.2.0@' + 'd' * 40

    def setUp(self):
        super().setUp()
        self.return_data['schema_version'] = 3
        self.save_return()

    def statement(self, role, charges=None):
        statement = super().statement(role, charges)
        if role == 'prosecutor':
            statement['reviewed_context_sha256'] = court_status(self.root)['prosecution_context_sha256']
        return statement

    def verdict(self):
        return {**super().verdict(), 'intent_finding': 'Synthetic current finding on the original task.'}

    def court_work(self, actor, unit, source, text):
        operation_id = 'court-output-' + str(self.sequence)
        emit_work(self.root, actor=actor, line='M01', kind='C', unit=unit, stage='RETURN',
                  text=text, operation_id=operation_id, source_ref=source['source_ref'])
        return operation_id

    def incident(self, role='defendant', source=None, **changes):
        excerpt = 'The entire task must stop until the unrelated service recovers.'
        source = source or self.source('actual-output', excerpt)
        actor = self.actors[role]['actor_id']
        operation = self.court_work(actor, 'court-1', source, excerpt)
        return {
            'actor_id': self.actors['black_police']['actor_id'],
            'target_actor_id': self.actors[role]['actor_id'], 'target_role': role,
            'material_sha256': court_status(self.root)['material_sha256'],
            'unit': 'court-1', 'target_output': source, 'target_operation_id': operation,
            'basis_id': 'request', 'basis_excerpt': '解释给定问题并返回正文和文件',
            'finding': {'categories': ['invented-gate', 'tunnel-vision'],
                        'excerpt': excerpt, 'requirement': 'Deliver the requested text and file.',
                        'impact': 'A real unrelated service issue became a blocker to both deliveries.',
                        'repair': 'Continue both available deliverables and isolate the actual tool failure.',
                        'boundary_check': 'The fixture service error blocks only a separate optional check.'},
            'warning': '当庭警告：停用该判断，补做仍获授权的交付。',
            **changes,
        }

    def resolution(self, incident, *, outcome='REPAIRED'):
        excerpt = 'The deliverables can proceed while the unrelated service is unavailable.'
        status = court_status(self.root)
        source = self.source('corrected-output', excerpt)
        operation = self.court_work(incident['target_actor_id'], incident['unit'], source, excerpt)
        return {'actor_id': incident['actor_id'], 'material_sha256': status['material_sha256'],
                'id': status['cc_interventions'][0]['id'], 'outcome': outcome,
                'repair_actor_id': incident['target_actor_id'], 'excerpt': excerpt,
                'source': source, 'repair_operation_id': operation, 'summary': '保留真实边界，完成独立交付。'}

    def docket(self):
        status = court_status(self.root)
        return {'actor_id': self.actors['clerk']['actor_id'], 'proceedings_sha256': status['proceedings_sha256'],
                'source': self.source('docket'), 'retrievals': [], 'evidence_consistency': 'Checked synthetic case.',
                'evidence_index': {key: 'Original fixture source.' for key in status['source_ids']},
                'reasoning_record': 'Synthetic docket covers the warning and current adjudication.'}

    def ordinary_error(self, identifier, *, status='OPEN'):
        return record_execution_error(self.root, {'id': identifier, 'stage': 'fixture',
                                      'problem': identifier, 'impact': 'Synthetic local error.',
                                      'status': status, 'handling': 'Preserved actual fixture behavior.'})

    def test_pool_search_and_actual_protected_finding(self):
        self.open()
        pool = load_pool()
        found = search_pool(pool, category='overrefusal', kind='community')
        self.assertTrue(any(row['id'] == 'oa-chess-o3' and row['attribution'] == 'unresolved'
                            for row in found['sources']))
        self.assertEqual(found['sha256'], pool['sha256'])
        item = self.incident()
        item['finding']['protected_basis'] = 'Here the exact permission is genuinely missing for the named action.'
        self.assertEqual(assess(pool, item['finding'])['disposition'], 'PROTECTED')
        with self.assertRaisesRegex(ValueError, 'protected basis'):
            cc_intervene(self.root, item)
        self.assertFalse(execution_errors(self.root))

    def test_current_hold_is_immediate_scoped_and_return_keeps_original_position(self):
        self.open()
        self.ordinary_error('before')
        warning = self.incident()
        old = self.statement('defendant')
        old.update(source=warning['target_output'], statement=warning['finding']['excerpt'])
        submit_statement(self.root, old)
        warning.pop('target_operation_id')  # The exact court-filed source can supply identity.
        result = cc_intervene(self.root, warning)
        self.assertEqual(result['status'], 'CC_SUSPENDED')
        cc_intervene(self.root, warning)
        self.assertEqual(len(court_status(self.root)['cc_interventions']), 1)
        self.ordinary_error('after')
        self.ordinary_error('before', status='RECOVERED')
        self.assertEqual([item['id'] for item in execution_errors(self.root)],
                         ['before', result['cc_interventions'][0]['id'], 'after'])
        self.assertEqual(execution_errors(self.root)[1]['status'], 'OPEN')
        self.assertFalse(any(item['role'] == 'defendant'
                             for item in court_packet(self.root, 'judge')['public_statement_sources']))

        submit_statement(self.root, self.statement('prosecution_lawyer'))
        for function, data in [(record_verdict, self.verdict()), (record_docket, self.docket()),
                               (submit_statement, old)]:
            with self.assertRaisesRegex(ValueError, 'CC has suspended'):
                function(self.root, data)

        seal_return(self.root, self.return_input)
        with self.assertRaisesRegex(ValueError, 'affected CC'):
            response_body(self.root)
        fixed = self.resolution(warning)
        cc_resume(self.root, fixed)
        cc_resume(self.root, fixed)
        self.assertEqual(execution_errors(self.root)[1]['status'], 'OPEN')
        with self.assertRaisesRegex(ValueError, 'superseded'):
            submit_statement(self.root, old)
        with self.assertRaisesRegex(ValueError, 'actual CC repair source'):
            submit_statement(self.root, self.statement('defendant'))
        with self.assertRaisesRegex(ValueError, 'corrected statement'):
            record_verdict(self.root, self.verdict())
        revised = self.statement('defendant')
        revised.update(source=fixed['source'], statement=fixed['excerpt'])
        submit_statement(self.root, revised)
        self.assertEqual(execution_errors(self.root)[1]['status'], 'RECOVERED')
        for role in ('judge', 'clerk', 'defence_lawyer', 'black_police', 'prosecutor'):
            submit_statement(self.root, self.statement(role))
        record_verdict(self.root, self.verdict())
        self.assertTrue(record_docket(self.root, self.docket())['can_close'])
        seal_return(self.root, self.return_input)
        text = response_body(self.root)
        self.assertLess(text.index('| 1 | fixture | before'), text.index('| 2 | C1 黑警'))
        self.assertLess(text.index('| 2 | C1 黑警'), text.index('| 3 | fixture | after'))
        self.assertIn('补做后恢复', text)

    def test_identity_current_evidence_and_same_source_retry(self):
        status = self.open()
        warning = self.incident()
        for field, invalid, reason in [
            ('actor_id', self.actors['judge']['actor_id'], 'actual black police'),
            ('target_actor_id', self.actors['judge']['actor_id'], 'named actual model role'),
            ('material_sha256', 'b' * 64, 'current court material'),
            ('basis_excerpt', 'fabricated commission', 'actual captured public source'),
            ('target_operation_id', 'invented-operation', 'actual recorded public work operation'),
            ('unit', 'wrong-affiliated-unit', 'matching current court LIVE operation'),
        ]:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, reason):
                    cc_intervene(self.root, {**warning, field: invalid})
        invalid = {**warning, 'finding': {**warning['finding'], 'excerpt': 'fabricated output'}}
        with self.assertRaisesRegex(ValueError, 'must quote'):
            cc_intervene(self.root, invalid)
        self.assertEqual(court_status(self.root)['status'], status['status'])
        cc_intervene(self.root, warning)
        resolution = self.resolution(warning)
        disguised_text = resolution['excerpt'] + '\n' + warning['finding']['excerpt']
        disguised = self.source('still-offending', disguised_text)
        disguised_operation = self.court_work(warning['target_actor_id'], warning['unit'],
                                              disguised, disguised_text)
        with self.assertRaisesRegex(ValueError, 'still contains'):
            cc_resume(self.root, {**resolution, 'source': disguised, 'repair_operation_id': disguised_operation})
        with self.assertRaisesRegex(ValueError, 'materially different'):
            cc_resume(self.root, {**resolution, 'source': warning['target_output'],
                                  'excerpt': warning['finding']['excerpt']})
        retraction = self.resolution(warning, outcome='RETRACTED')
        cc_resume(self.root, retraction)
        accepted = self.statement('defendant')
        accepted.update(source=warning['target_output'], statement=warning['finding']['excerpt'])
        submit_statement(self.root, accepted)
        self.assertIn('经新证据撤回', execution_errors(self.root)[0]['handling'])

    def test_scoped_charges_and_pending_hold_survive_real_review(self):
        self.open()
        warning = self.incident('prosecution_lawyer')
        filed = self.statement('prosecution_lawyer', charges=[self.charge('bad-gate')])
        filed.update(source=warning['target_output'], statement=warning['finding']['excerpt'])
        submit_statement(self.root, filed)
        hearing = cc_intervene(self.root, warning)
        self.assertEqual(court_packet(self.root, 'judge')['charges'], {})
        identifier = hearing['cc_interventions'][0]['id']
        self.return_data['result'] += ' Updated synthetic result on a distinct issue.'
        self.save_return()
        new_round = review(self.root, self.performed_work())
        self.assertEqual(new_round['status'], 'CC_SUSPENDED')
        self.assertEqual(new_round['cc_interventions'][0]['id'], identifier)
        self.assertEqual([item['status'] for item in execution_errors(self.root)], ['OPEN'])
        fixed = self.resolution(warning)
        cc_resume(self.root, fixed)
        self.assertEqual([item['status'] for item in execution_errors(self.root)], ['OPEN'])
        revised = self.statement('prosecution_lawyer')
        revised.update(source=fixed['source'], statement=fixed['excerpt'])
        submit_statement(self.root, revised)
        self.assertEqual([item['status'] for item in execution_errors(self.root)], ['RECOVERED'])
        ledger = json.loads((self.root / 'court/court.json').read_text(encoding='utf-8'))
        self.assertIn('bad-gate', ledger['rounds'][0]['charges'])
        self.assertEqual(ledger['rounds'][0]['cc_interventions'][0]['transferred_to_cycle'], 2)

    def test_selected_artifact_needs_real_replacement(self):
        unsafe_output = 'The entire task must stop until the unrelated service recovers.'
        self.product.write_text(unsafe_output, encoding='utf-8')
        self.mark_complete()
        self.open()
        captured = {'path': str(self.product), 'source_ref': 'synthetic:selected-artifact'}
        warning = self.incident(source=captured)
        result = cc_intervene(self.root, warning)
        self.assertEqual(result['cc_blocked_products'], [str(self.product.resolve())])
        fixed = self.resolution(warning)
        cc_resume(self.root, fixed)
        revised = self.statement('defendant')
        revised.update(source=fixed['source'], statement=fixed['excerpt'])
        submit_statement(self.root, revised)
        for role in ('judge', 'clerk', 'defence_lawyer', 'black_police', 'prosecution_lawyer', 'prosecutor'):
            submit_statement(self.root, self.statement(role))
        record_verdict(self.root, self.verdict())
        self.assertFalse(record_docket(self.root, self.docket())['can_close'])
        seal_return(self.root, self.return_input)
        with self.assertRaisesRegex(ValueError, 'affected CC'):
            response_body(self.root)

    def test_split_live_output_has_one_reminder_after_its_actual_end(self):
        body = 'Precise unit content. ' * 60
        record = dict(actor='Diana', kind='F', unit='F7', line='M01', stage='RETURN',
                      text=body, operation_id='f7return', source_ref='synthetic:artifact', return_mode='quote')
        emitted = emit_work(self.root, **record)
        self.assertEqual(emit_work(self.root, **record), emitted)
        batch_text = []
        while True:
            batch = pending(self.root, reader='synthetic', max_chars=256)
            self.assertLessEqual(len(batch['display_text']), 256)
            acknowledge(self.root, batch['delivery_id'], evidence_ref='synthetic:public-batch')
            batch_text.append(batch['display_text'])
            if not batch['remaining']:
                break
        reminder = emitted['protocol_reminder']
        self.assertEqual(sum(text.count(reminder) for text in batch_text), 1)
        self.assertTrue(batch_text[-1].endswith(reminder))
        self.assertTrue(all(reminder not in text for text in batch_text[:-1]))

    def test_external_direct_relay_preserves_text_and_reminds_at_finish(self):
        values = []
        relay = ParagraphRelay(values.append, stable=True, reminders=True)
        relay.feed({'event': 'connected', 'exchange_id': 'e-1', 'http_status': 200})
        relay.feed({'event': 'public_delta', 'exchange_id': 'e-1', 'text': '原文原样。', 'sequence': 2})
        relay.feed({'event': 'finished', 'exchange_id': 'e-1', 'public_status': 'COMPLETE'})
        self.assertEqual([value['event'] for value in values], ['connected', 'public_text', 'finished'])
        self.assertEqual(values[1]['text'], '原文原样。')
        self.assertNotIn('protocol_reminder', values[0])
        self.assertNotIn('协议自提醒', values[1]['display_text'])
        self.assertTrue(values[2]['display_text'].endswith(values[2]['protocol_reminder']))
