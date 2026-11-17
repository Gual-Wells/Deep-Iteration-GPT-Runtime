from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from runtime import codex_consult as consult, codex_split as split, codex_paper as paper
from runtime.codex_lifecycle import ingest_message, handle_message
from runtime.codex_session import create_session
import test_codex_consult as fixtures

SECRET = fixtures.SECRET


class NativeSplitTests(unittest.TestCase):
    file = fixtures.ConsultPublicRuntimeTests.file
    config = fixtures.ConsultPublicRuntimeTests.config
    facts = fixtures.ConsultPublicRuntimeTests.facts
    stop_server = fixtures.ConsultPublicRuntimeTests.stop_server

    def setUp(self):
        fixtures.ConsultPublicRuntimeTests.setUp(self)
        self.root = self.folder / 'split-task'
        create_session(self.root, request=self.original, p_run='0.13.0@' + 'e' * 40)

    def prepare(self, label, **kwargs):
        kwargs.setdefault('max_tokens', 16000)
        return consult.prepare_request(self.root, input_path=self.input, materials=[self.material],
                                       exchange_id=label, **kwargs)

    def plan(self, label, *, evidence=True):
        data = consult.split_brief(self.root, label)
        local = {'task': 'Synthetic source extraction and notation check',
                 'result': 'A routes to B in the actual supplied source.', 'evidence': []}
        if evidence:
            local['evidence'].append({'path': self.material.as_posix(),
                                     'sha256': sha256(self.material.read_bytes()).hexdigest()})
        value = {'format': split.CONTRACT, 'binding': data['binding'],
                 'decision': 'PRIVATE_SPLIT_ONLY_MARKER: local extraction is done; ask for content design.',
                 'local_work': [local], 'claude_value': 'Develop and challenge the explanation using supplied originals.',
                 'context_decision': 'Preserve source text and question; omit local extraction logs.'}
        return self.file(label + '-split.json', json.dumps(value))

    def call(self, label, plan, **kwargs):
        with patch.dict(os.environ, {'DIGR_TEST_CONSULT_KEY': SECRET}):
            return consult.call_once(self.root, label, facts=kwargs.pop('facts', self.facts()),
                                     ceiling_usd=.20, config_path=self.config('normal'), split_path=plan, **kwargs)

    def test_missing_split_never_reads_credentials_or_sends(self):
        self.prepare('missing')
        with patch.object(consult, '_config', side_effect=AssertionError('credentials read')):
            with self.assertRaisesRegex(ValueError, 'native Codex Split'):
                self.call('missing', None)
        current = consult.inspect_exchange(self.root, 'missing')['exchange']
        self.assertEqual((current['transport_status'], current['billing_status']), ('PREPARED', 'NOT_ATTEMPTED'))
        self.assertEqual(self.server.post_calls, [])

    def test_one_local_split_per_generation_and_private_plan_is_not_transmitted(self):
        self.prepare('normal')
        plan = self.plan('normal')
        events = []
        with patch.object(split, 'Split', wraps=split.Split) as invoked:
            result = self.call('normal', plan, on_public_event=events.append)
        self.assertEqual(invoked.call_count, 1)
        self.assertEqual(len(self.server.post_calls), 1)
        actual = self.server.post_calls[0]['request']
        self.assertNotIn('PRIVATE_SPLIT_ONLY_MARKER', json.dumps(actual))
        self.assertIn('Original source: A routes to B.', json.dumps(actual))
        self.assertEqual(actual['reasoning']['effort'], 'high')
        self.assertEqual(actual['max_tokens'], 16000)
        self.assertTrue(actual['stream'])
        self.assertIn('public_delta', [event['event'] for event in events])
        self.assertNotIn(fixtures.HIDDEN, json.dumps(events))
        self.assertEqual(result['split']['integrity'], 'MATCH')
        receipt = result['split']['receipt']
        self.assertEqual(receipt['external_model_calls'], 0)
        self.assertIsNone(receipt['request_profile']['token_savings'])
        with self.assertRaisesRegex(ValueError, 'already started'):
            self.call('normal', plan)
        self.assertEqual(len(self.server.post_calls), 1)

    def test_another_request_cannot_reuse_split(self):
        self.prepare('first')
        plan = self.plan('first')
        self.prepare('second')
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.call('second', plan)
        self.assertEqual(self.server.post_calls, [])

    def test_generic_user_correction_invalidates_prepared_split(self):
        self.prepare('correction')
        plan = self.plan('correction')
        reply = self.file('reply.txt', 'Change the audience and preserve the complete original.')
        message = ingest_message(self.root, source=reply, source_ref='actual-correction')
        handle_message(self.root, message_id=message['current_message']['id'], action='continue', reason='Apply reader change')
        with self.assertRaisesRegex(ValueError, 'current user input'):
            self.call('correction', plan)
        self.assertEqual(self.server.post_calls, [])
        # A deliberately ambiguous host follow-up cannot omit the actual
        # correction: new generic requests carry the source-bound user text.
        self.input.write_text('Please revise it.', encoding='utf-8')
        self.prepare('corrected')
        self.call('corrected', self.plan('corrected'))
        body = json.dumps(self.server.post_calls[0]['request'], ensure_ascii=False)
        self.assertIn(reply.read_text(encoding='utf-8'), body)

    def test_model_effort_output_or_history_change_invalidates_binding(self):
        self.prepare('changed')
        plan = self.plan('changed')
        directory, attempt, request = consult._load(self.root, 'changed')
        request['reasoning']['effort'] = 'medium'
        consult._write(directory / 'request.json', request)
        attempt['request_sha256'] = consult._hash(consult._json_bytes(request))
        consult._write(directory / 'attempt.json', attempt)
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.call('changed', plan)
        self.assertEqual(self.server.post_calls, [])

    def test_changed_local_evidence_cannot_send(self):
        self.prepare('evidence')
        plan = self.plan('evidence')
        self.material.write_text('Changed calculation', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'local evidence changed'):
            self.call('evidence', plan)
        self.assertEqual(self.server.post_calls, [])

    def test_continuation_requires_new_split_and_accounts_for_all_history(self):
        self.prepare('origin')
        origin = self.plan('origin')
        first = self.call('origin', origin)
        self.prepare('follow', continue_from='origin')
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.call('follow', origin)
        result = self.call('follow', self.plan('follow'))
        previous = first['split']['receipt']['request_profile']
        current = result['split']['receipt']['request_profile']
        self.assertGreater(current['message_count'], previous['message_count'])
        self.assertGreater(current['utf8_text_bytes'], previous['utf8_text_bytes'])
        self.assertEqual(len(self.server.post_calls), 2)
        body = '\n'.join(message['content'] for message in self.server.post_calls[1]['request']['messages']
                         if isinstance(message['content'], str))
        self.assertEqual(body.count(self.original.read_text(encoding='utf-8')), 1)

    def test_split_does_not_bypass_existing_budget_or_authorize_spend(self):
        self.prepare('budget')
        with self.assertRaisesRegex(ValueError, 'remaining task/wallet'):
            self.call('budget', self.plan('budget'), facts=self.facts(wallet=.01))
        self.assertEqual(self.server.post_calls, [])

    def test_stop_during_transport_construction_prevents_send_and_reservation(self):
        self.prepare('stop-late')
        plan = self.plan('stop-late')
        actual_opener = consult._opener

        def stopped(config):
            source = self.file('stop.txt', 'Stop the task now.')
            message = ingest_message(self.root, source=source, source_ref='stop-during-opener')
            handle_message(self.root, message_id=message['message_id'], action='stop', reason='Actual synthetic stop')
            return actual_opener(config)

        with patch.object(consult, '_opener', side_effect=stopped):
            with self.assertRaisesRegex(ValueError, 'STOPPED|ACTIVE|active'):
                self.call('stop-late', plan)
        observed = consult.inspect_exchange(self.root, 'stop-late')['exchange']
        self.assertEqual(observed['transport_status'], 'PREPARED')
        self.assertEqual(observed['billing_status'], 'NOT_ATTEMPTED')
        self.assertEqual(observed['reserved_usd'], 0)
        self.assertEqual(self.server.post_calls, [])

    def test_correction_during_preflight_invalidates_current_split(self):
        self.prepare('late-correction')
        plan = self.plan('late-correction')
        actual_config = consult._config

        def corrected(path):
            value = actual_config(path)
            source = self.file('late.txt', 'Use the complete original and a different reader purpose.')
            message = ingest_message(self.root, source=source, source_ref='late-correction')
            handle_message(self.root, message_id=message['message_id'], action='continue', reason='Apply current purpose')
            return value

        with patch.object(consult, '_config', side_effect=corrected):
            with self.assertRaisesRegex(ValueError, 'supersedes this Split'):
                self.call('late-correction', plan)
        self.assertEqual(self.server.post_calls, [])

    def test_bind_native_decision_preserves_evidence_base_without_running_split(self):
        self.prepare('bound')
        original_plan = json.loads(self.plan('bound').read_text(encoding='utf-8'))
        decision = {key: value for key, value in original_plan.items() if key not in {'format', 'binding'}}
        decision['local_work'][0]['evidence'][0]['path'] = self.material.name
        authored = self.file('native-decision.json', json.dumps(decision))
        output = self.folder / 'different-output-directory' / 'bound-plan.json'
        with patch.object(split, 'Split', wraps=split.Split) as invoked:
            result = consult.bind_split_decision(self.root, 'bound', input_path=authored, output=output)
            self.assertEqual(invoked.call_count, 0)
            self.call('bound', output)
            self.assertEqual(invoked.call_count, 1)
        plan = json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(plan['decision'], decision['decision'])
        self.assertEqual(Path(plan['local_work'][0]['evidence'][0]['path']), self.material)
        self.assertEqual(result['binding']['exchange_id'], 'bound')
        with self.assertRaisesRegex(ValueError, 'unbound native decision'):
            split.bind_decision(output, current_brief={'binding': result['binding']})

    def test_no_useful_local_prework_requires_reason_not_dummy_work(self):
        self.prepare('direct')
        path = self.plan('direct')
        value = json.loads(path.read_text())
        value['local_work'] = []
        path.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'local_work_reason'):
            self.call('direct', path)
        value['local_work_reason'] = 'This supplied draft is ready for the requested independent content judgment.'
        path.write_text(json.dumps(value), encoding='utf-8')
        self.call('direct', path)
        self.assertEqual(len(self.server.post_calls), 1)

    def test_new_paper_submissions_share_split_gate_and_preserve_authoring_scope(self):
        request = self.file('paper-user.txt', 'DIGRP：整篇处理这份合成论文。')
        self.root = self.folder / 'paper-parent'
        pin = '0.13.0@' + 'f' * 40
        create_session(self.root, request=request, p_run=pin)
        batch = self.folder / 'paper-batch'
        value = paper.initialize(batch, p_run=pin, authorization=request,
                                 source_ref='selected-paper', task_root=self.root)
        self.assertEqual(value['addon_version'], '0.5.4')
        selection = paper.add_paper(batch, paper_id='one', title='Synthetic source', line='M01', owner='fixture',
                                   parameters={'N': 2, 'R': 1, 'D': 0, 'V': 0, 'L': 3, 'T': '0min', 'B': 0,
                                               'S': {'n': 0, 'r': 0, 't': '0min', 'b': 0}})
        self.prepare('paper', paper_root=Path(selection['paper_root']))
        with self.assertRaisesRegex(ValueError, 'native Codex Split'):
            self.call('paper', None)
        result = self.call('paper', self.plan('paper'))
        scope = result['split']['receipt']['binding']['authoring_scope']
        self.assertEqual(scope['paper_id'], 'one')
        actual = self.server.post_calls[0]['request']
        self.assertIn('Originate the useful questions', actual['messages'][0]['content'])

    def test_old_pinned_call_keeps_its_original_contract(self):
        self.root = self.folder / 'task'  # the actual 0.10 fixture, not a migrated task
        self.prepare('legacy')
        self.call('legacy', None)
        self.assertFalse(consult.inspect_exchange(self.root)['split_required_for_submission'])
        self.assertEqual(len(self.server.post_calls), 1)


if __name__ == '__main__':
    unittest.main()
