"""Isolated Gmail delivery faults and native MIME fixtures; no external transfers."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from runtime import codex_delivery as d


def registry():
    return {'format': d.REGISTRY_FORMAT, 'targets': {
        'gmail': {'channel': 'gmail', 'account': 'reader@example.test',
            'recipient': 'reader@example.test', 'target_kind': 'self_mailbox',
            'transport': 'native-connector', 'binding_status': 'bound', 'aliases': ['Mail', 'Self-Mail']}}}


class PolicyTests(unittest.TestCase):
    def test_default_gmail_aliases_and_no_x_need_no_credentials(self):
        local = d.resolve_policy({'mode': 'local', 'target': None, 'explicit': False}, 'missing-registry.json')
        self.assertEqual(local['mode'], 'local')
        for target in (None, 'Mail', 'mAiL', 'Gmail', 'SELF-MAIL'):
            self.assertEqual(d.resolve_policy({'mode': 'external', 'target': target, 'explicit': True}, registry())['target'], 'gmail')
        with self.assertRaisesRegex(ValueError, 'unknown'):
            d.resolve_policy({'mode': 'external', 'target': 'unknown', 'explicit': True}, registry())

    def test_ambiguous_alias_credentials_wrong_transport_and_multi_recipient_fail(self):
        for mutation in ('alias', 'secret', 'transport', 'recipient', 'adapter', 'channel'):
            value = registry()
            if mutation == 'alias':
                value['targets']['other'] = deepcopy(value['targets']['gmail'])
            elif mutation == 'secret':
                value['targets']['gmail']['api_key'] = 'synthetic-forbidden-field'
            elif mutation == 'transport':
                value['targets']['gmail']['transport'] = 'unsupported-transport'
            elif mutation == 'recipient':
                value['targets']['gmail']['recipient'] = 'reader@example.test, second@example.test'
            elif mutation == 'adapter':
                value['targets']['gmail']['evidence_adapter'] = 'unimplemented-adapter'
            else:
                value['targets']['gmail']['channel'] = 'unsupported-channel'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                d.resolve_policy({'mode': 'external', 'target': None, 'explicit': True}, value)

    def test_snapshot_is_not_redirected_by_registry_update(self):
        value = registry()
        policy = d.resolve_policy({'mode': 'external', 'target': 'MAIL', 'explicit': True}, value)
        value['targets']['gmail']['recipient'] = 'someone-else@example.test'
        self.assertEqual(d.validate_policy(policy)['recipient'], 'reader@example.test')
        changed = deepcopy(policy); changed['recipient'] = 'someone-else'
        with self.assertRaisesRegex(ValueError, 'changed'):
            d.validate_policy(changed)

    def test_non_gmail_channels_are_rejected_without_fallback(self):
        for channel in ('telegram', 'qq', 'unknown-channel'):
            value = registry(); value['targets']['gmail']['channel'] = channel
            with self.subTest(channel=channel), self.assertRaisesRegex(ValueError, 'Gmail only'):
                d.resolve_policy({'mode': 'external', 'target': None, 'explicit': True}, value)

    def test_existing_gmail_policy_origin_fields_keep_their_exact_identity(self):
        value = registry()
        value['targets']['gmail'].update(evidence_adapter='gmail-api', capability_status='available',
            evidence_refs=['saved-native-profile.json'], account_kind='mailbox')
        policy = d.resolve_policy({'mode': 'external', 'target': 'gmail', 'explicit': True}, value)
        before = json.dumps(policy, sort_keys=True)
        self.assertEqual(json.dumps(d.validate_policy(policy), sort_keys=True), before)


class DeliveryFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / 'complete.pdf'; self.file.write_bytes(b'P' * 1234)
        self.policy = d.resolve_policy({'mode': 'external', 'target': None, 'explicit': True}, registry())
        for name in ('identity', 'send', 'readback', 'outcome'):
            (self.root / (name + '.json')).write_text(json.dumps({'synthetic': name}), encoding='utf-8')
        (self.root / 'identity.json').write_text(json.dumps({'identity': self.identity()}), encoding='utf-8')
        self.prepared = None

    def identity(self, policy=None):
        policy = policy or self.policy
        return {'account': policy['account'], 'recipient': policy['recipient'],
                'account_confirmed': True, 'recipient_confirmed': True,
                'binding_basis': 'native-self-entry'}

    def prepare(self, policy=None, operation='prepare', candidate='candidate-1', files=None):
        result = d.prepare(self.root, {'candidate_id': candidate, 'files': files or [str(self.file)],
            'policy': policy or self.policy, 'authorization_source_ref': 'synthetic-user-X'}, operation_id=operation)
        self.prepared = result
        return result

    def mark(self, prepared=None, policy=None, operation='reserve'):
        prepared = prepared or self.prepared or self.prepare(policy)
        (self.root / 'identity.json').write_text(json.dumps({'identity': self.identity(policy)}), encoding='utf-8')
        return d.mark_sending(self.root, {'delivery_id': prepared['delivery_id'],
            'identity': self.identity(policy), 'identity_evidence': str(self.root / 'identity.json')}, operation_id=operation)

    def receipt(self, marked, policy=None):
        policy = policy or self.policy
        return {'candidate_id': 'candidate-1', 'attempt_id': marked['attempt_id'],
            **{key: policy[key] for key in ('target', 'channel', 'account', 'recipient', 'transport')},
            'evidence_kind': 'gmail-api', 'message_id': None,
            'identity': self.identity(policy), 'readback': {'completed': True, 'attempt_correlated': True},
            'readback_result': {'structuredContent': {'id': 'synthetic-native-message', 'label_ids': ['SENT'],
                'payload': {'headers': [{'name': 'From', 'value': policy['account']},
                                        {'name': 'To', 'value': policy['recipient']}],
                    'parts': [{'filename': self.file.name, 'body': {'size': self.file.stat().st_size}, 'parts': None}]}}},
            **{key + '_evidence': str(self.root / (key + '.json')) for key in ('identity', 'send', 'readback')}}

    def sent(self, marked, receipt=None, operation='readback'):
        receipt = receipt or self.receipt(marked)
        self.persist_receipt(receipt)
        return d.reconcile(self.root, {'delivery_id': marked['delivery_id'], 'attempt_id': marked['attempt_id'],
            'outcome': 'sent', 'receipt': receipt}, operation_id=operation)

    def persist_receipt(self, receipt):
        back = receipt['readback_result']
        sent = {'structuredContent': {'id': d._gmail_message(back)['id']}}
        Path(receipt['readback_evidence']).write_text(json.dumps(back), encoding='utf-8')
        Path(receipt['send_evidence']).write_text(json.dumps(sent), encoding='utf-8')


class DeliveryFaultTests(DeliveryFixture):
    def test_no_x_and_no_files_do_not_create_or_arm_a_ledger(self):
        local = d.resolve_policy({'mode': 'local', 'target': None, 'explicit': False})
        for policy, files, status in ((local, ['missing-file.pdf'], 'LOCAL_ONLY'), (self.policy, [], 'NO_FILES')):
            result = d.prepare(self.root, {'policy': policy, 'files': files}, operation_id='nothing')
            self.assertEqual(result['status'], status); self.assertFalse(result['send_allowed'])
        self.assertFalse((self.root / 'delivery.json').exists())

    def test_crash_after_synthetic_effect_cannot_obtain_a_second_send_grant(self):
        prepared = self.prepare()
        payload = {'delivery_id': prepared['delivery_id'], 'identity': self.identity(),
                   'identity_evidence': str(self.root / 'identity.json')}
        (self.root / 'mark.json').write_text(json.dumps(payload), encoding='utf-8')
        child = r'''
import json, os, sys
from pathlib import Path
from runtime import codex_delivery as d
root = Path(sys.argv[1])
result = d.mark_sending(root, json.loads((root / 'mark.json').read_text()), operation_id='crashed-sender')
if result['send_allowed']:
    with (root / 'synthetic-provider-effects.jsonl').open('a') as stream:
        stream.write(json.dumps({'one_synthetic_effect': result['attempt_id']}) + '\n')
        stream.flush(); os.fsync(stream.fileno())
os._exit(37)
'''
        run = subprocess.run([sys.executable, '-B', '-c', child, str(self.root)], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(run.returncode, 37, run.stderr)
        self.assertEqual(len((self.root / 'synthetic-provider-effects.jsonl').read_text().splitlines()), 1)
        replay = d.mark_sending(self.root, payload, operation_id='crashed-sender')
        self.assertTrue(replay['idempotent_replay']); self.assertFalse(replay['send_allowed'])
        with self.assertRaisesRegex(ValueError, 'uncertain'):
            self.mark(operation='blind-retry')
        status = d.inspect(self.root)
        self.assertEqual(status['status'], 'UNCERTAIN')
        self.assertTrue(status['deliveries'][0]['unresolved'])
        self.assertFalse(d.completion_status(self.root, [str(self.file)], self.policy)['ready'])

    def test_commit_failure_returns_no_grant_and_preserves_prepared_state(self):
        self.prepare()
        with patch.object(d.os, 'replace', side_effect=OSError('synthetic disk failure')):
            with self.assertRaisesRegex(OSError, 'disk failure'):
                self.mark()
        self.assertEqual(d.inspect(self.root)['deliveries'][0]['status'], 'PREPARED')
        self.assertTrue(self.mark(operation='after-confirmed-local-failure')['send_allowed'])

    def test_fresh_binding_supplements_unverified_snapshot_without_redirecting_endpoint(self):
        value = registry(); value['targets']['gmail']['binding_status'] = 'identity_unverified'
        policy = d.resolve_policy({'mode': 'external', 'target': None, 'explicit': True}, value)
        prepared = self.prepare(policy)
        with self.assertRaisesRegex(ValueError, 'binding_basis'):
            identity = self.identity(policy); identity.pop('binding_basis')
            d.mark_sending(self.root, {'delivery_id': prepared['delivery_id'], 'identity': identity,
                'identity_evidence': str(self.root / 'identity.json')}, operation_id='title-only')
        marked = self.mark(prepared, policy, operation='actual-self-entry-proof')
        self.assertTrue(marked['send_allowed'])
        self.assertEqual(marked['policy'], policy)

    def test_positive_non_send_evidence_releases_one_retry_search_absence_does_not(self):
        marked = self.mark()
        evidence = {'candidate_id': 'candidate-1', 'target': self.policy['target'],
            'account': self.policy['account'], 'recipient': self.policy['recipient'],
            'attempt_id': marked['attempt_id'], 'basis': 'Synthetic provider rejected before acceptance',
            'disposition': 'search-found-nothing'}
        payload = {'delivery_id': marked['delivery_id'], 'attempt_id': marked['attempt_id'],
            'outcome': 'not_sent', 'evidence': evidence, 'evidence_path': str(self.root / 'outcome.json')}
        (self.root / 'outcome.json').write_text(json.dumps({'evidence': evidence}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'positive non-send'):
            d.reconcile(self.root, payload, operation_id='absence-is-not-proof')
        evidence['disposition'] = 'provider-confirmed-not-accepted'
        (self.root / 'outcome.json').write_text(json.dumps({'evidence': evidence}), encoding='utf-8')
        d.reconcile(self.root, payload, operation_id='provider-rejection')
        retried = self.mark(operation='retry-after-rejection')
        self.assertTrue(retried['send_allowed']); self.assertNotEqual(marked['attempt_id'], retried['attempt_id'])
        with self.assertRaisesRegex(ValueError, 'uncertain'):
            self.mark(operation='third-submission')

    def test_same_bytes_moved_and_target_alias_do_not_reset_uncertain_attempt(self):
        marked = self.mark()
        moved = self.root / 'new-location'; moved.mkdir()
        moved_file = moved / self.file.name; moved_file.write_bytes(self.file.read_bytes())
        alias = d.resolve_policy({'mode': 'external', 'target': 'Mail', 'explicit': True}, registry())
        again = self.prepare(alias, operation='moved-path', files=[str(moved_file)])
        self.assertEqual(marked['delivery_id'], again['delivery_id'])
        self.assertEqual(again['status'], 'SENDING'); self.assertFalse(again['send_allowed'])
        self.assertEqual(len(d.inspect(self.root)['deliveries']), 1)

    def test_partial_overlap_cannot_bypass_an_uncertain_multi_file_attempt(self):
        second = self.root / 'second.txt'; second.write_text('synthetic second file')
        self.prepare(files=[str(self.file), str(second)])
        self.mark()
        with self.assertRaisesRegex(ValueError, 'overlap'):
            self.prepare(operation='subset-bypass', files=[str(self.file)])

    def test_alternative_prepared_sets_compete_for_one_overlapping_send(self):
        first = self.prepare()
        second_file = self.root / 'second.txt'; second_file.write_text('synthetic second file')
        alternative = self.prepare(operation='alternative', files=[str(self.file), str(second_file)])
        self.mark(first)
        with self.assertRaisesRegex(ValueError, 'overlap'):
            self.mark(alternative, operation='second-overlapping-send')

    def test_file_changed_before_send_and_readback_changed_after_send_are_visible(self):
        self.prepare()
        self.file.write_bytes(b'X' * 1234)
        with self.assertRaisesRegex(ValueError, 'snapshot changed'):
            self.mark()
        self.file.write_bytes(b'P' * 1234)
        marked = self.mark(); self.sent(marked)
        self.assertTrue(d.completion_status(self.root, [str(self.file)], self.policy)['ready'])
        (self.root / 'readback.json').write_text('changed evidence')
        complete = d.completion_status(self.root, [str(self.file)], self.policy)
        self.assertFalse(complete['ready']); self.assertTrue(complete['issues'])
        with self.assertRaisesRegex(ValueError, 'already verified'):
            self.mark(operation='do-not-repeat-stale-evidence')

    def test_gmail_actual_native_mime_readback_and_additional_recipients(self):
        policy = d.resolve_policy({'mode': 'external', 'target': 'gmail', 'explicit': True}, registry())
        prepared = self.prepare(policy); marked = self.mark(prepared, policy)
        receipt = self.receipt(marked, policy)
        receipt.update(evidence_kind='gmail-api', readback_result={'structuredContent': {
            'id': 'synthetic-api-message', 'labelIds': ['SENT'], 'sizeEstimate': 9999,
            'payload': {'headers': [{'name': 'From', 'value': 'Reader <reader@example.test>'},
                                   {'name': 'To', 'value': 'Reader <reader@example.test>'},
                                   {'name': 'Received', 'value': 'irrelevant\r\n folded header'}],
                'parts': [{'mimeType': 'multipart/mixed', 'parts': [{'filename': self.file.name,
                    'mimeType': 'application/pdf', 'body': {'size': 1234, 'attachmentId': 'synthetic-part'}}]}]}}})
        normalized = d.verify_receipt(policy, d.snapshot_files(self.root, [str(self.file)]), receipt,
            candidate_id='candidate-1', attempt_id=marked['attempt_id'])
        self.assertEqual(normalized['evidence_strength'], 'api-attachment-metadata')
        self.assertEqual(normalized['attachments'][0]['remote_bytes'], 1234)
        for mutation in ('cc', 'missing-size', 'duplicate', 'draft', 'wrong-account', 'old-attempt'):
            wrong = deepcopy(receipt); message = wrong['readback_result']['structuredContent']
            if mutation == 'cc': message['payload']['headers'].append({'name': 'Cc', 'value': 'second@example.test'})
            elif mutation == 'missing-size': message['payload']['parts'][0]['parts'][0]['body'].pop('size')
            elif mutation == 'duplicate': message['payload']['parts'][0]['parts'] *= 2
            elif mutation == 'draft': message['labelIds'] = ['DRAFT']
            elif mutation == 'wrong-account': wrong['identity']['account'] = 'other@example.test'
            else: wrong['attempt_id'] = 'previous-attempt'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                d.verify_receipt(policy, d.snapshot_files(self.root, [str(self.file)]), wrong,
                    candidate_id='candidate-1', attempt_id=marked['attempt_id'])
        self.sent(marked, receipt)
        self.assertTrue(d.completion_status(self.root, [str(self.file)], policy, candidate_id='candidate-1')['ready'])
        with self.assertRaisesRegex(ValueError, 'already verified'):
            self.mark(prepared, policy, operation='duplicate-gmail-effect')

    def test_actual_native_gmail_snake_case_nullable_leaf_parts_keep_attachment_sizes(self):
        policy = d.resolve_policy({'mode': 'external', 'target': 'gmail', 'explicit': True}, registry())
        marked = self.mark(self.prepare(policy), policy)
        receipt = self.receipt(marked, policy)
        # Shape observed in a prior native read_email result; all identities and
        # content below are synthetic. No new email is sent to build this fixture.
        receipt.update(evidence_kind='gmail-api', readback_result={'structuredContent': {
            'id': 'synthetic-native-id', 'thread_id': 'synthetic-native-thread',
            'label_ids': ['SENT'], 'history_id': '100', 'internal_date': '1000',
            'size_estimate': 9876, 'classification_label_values': [], 'raw': None,
            'payload': {'part_id': '', 'mime_type': 'multipart/mixed', 'filename': '',
                'headers': [{'name': 'From', 'value': policy['account']}, {'name': 'To', 'value': policy['recipient']}],
                'body': {'size': 0, 'base64_url_content': None, 'content': None, 'attachment_id': None},
                'read_attachment_supported': True,
                'parts': [{'part_id': '0', 'mime_type': 'text/plain', 'filename': '',
                    'headers': None, 'body': None, 'read_attachment_supported': None, 'parts': None},
                    {'part_id': '1', 'mime_type': 'application/pdf', 'filename': self.file.name,
                    'headers': [], 'body': {'size': 1234, 'base64_url_content': None,
                                           'content': None, 'attachment_id': 'synthetic-attachment'},
                    'read_attachment_supported': None, 'parts': None}]}}})
        result = d.verify_receipt(policy, d.snapshot_files(self.root, [str(self.file)]), receipt,
                                  candidate_id='candidate-1', attempt_id=marked['attempt_id'])
        self.assertEqual(result['message_id'], 'synthetic-native-id')
        self.assertEqual(result['attachments'][0]['remote_bytes'], 1234)
        malformed = deepcopy(receipt)
        malformed['readback_result']['structuredContent']['payload']['parts'][1]['parts'] = 'not-a-parts-list'
        with self.assertRaisesRegex(ValueError, 'list or null'):
            d.verify_receipt(policy, d.snapshot_files(self.root, [str(self.file)]), malformed,
                            candidate_id='candidate-1', attempt_id=marked['attempt_id'])

    def test_completion_checks_exact_selected_artifacts_and_current_policy(self):
        marked = self.mark(); self.sent(marked)
        unrelated = self.root / 'unrelated.txt'; unrelated.write_text('other candidate')
        self.prepare(operation='unrelated', candidate='candidate-other', files=[str(unrelated)])
        self.assertTrue(d.completion_status(self.root, [str(self.file)], self.policy)['ready'])
        other_registry = registry()
        other_registry['targets']['gmail'].update(account='other@example.test', recipient='other@example.test')
        other = d.resolve_policy({'mode': 'external', 'target': None, 'explicit': True}, other_registry)
        self.assertFalse(d.completion_status(self.root, [str(self.file)], other)['ready'])
        self.assertFalse(d.completion_status(self.root, [str(self.file)], self.policy, candidate_id='other-candidate')['ready'])
        self.assertFalse(d.completion_status(self.root, [str(unrelated)], self.policy)['ready'])

    def test_same_receipt_fresh_proof_recovers_without_rewriting_missing_history(self):
        marked = self.mark(); receipt = self.receipt(marked); self.sent(marked, receipt)
        before = d.inspect(self.root)['deliveries'][0]
        Path(receipt['readback_evidence']).unlink()
        self.assertFalse(d.completion_status(self.root, [str(self.file)], self.policy)['ready'])
        fresh = deepcopy(receipt); fresh['readback_evidence'] = str(self.root / 'fresh-readback.json')
        result = self.sent(marked, fresh, operation='fresh-proof-same-message')
        after = d.inspect(self.root)['deliveries'][0]
        self.assertTrue(result['proof_refreshed'])
        self.assertTrue(d.completion_status(self.root, [str(self.file)], self.policy)['ready'])
        self.assertTrue(after['history_issues']); self.assertFalse(after['issues'])
        self.assertEqual((before['identity_digest'], before['receipt_digest']),
                         (after['identity_digest'], after['receipt_digest']))
        self.assertEqual(len(after['attempts'][0]['observations']), 2)
        with self.assertRaisesRegex(ValueError, 'already verified'):
            self.mark(operation='refresh-is-not-resend')

    def test_native_readback_and_saved_send_must_agree_with_persisted_evidence(self):
        policy = d.resolve_policy({'mode': 'external', 'target': 'gmail', 'explicit': True}, registry())
        marked = self.mark(self.prepare(policy), policy)
        receipt = self.receipt(marked, policy)
        receipt.update(evidence_kind='gmail-api', readback_result={'structuredContent': {
            'id': 'same-native-message', 'label_ids': ['SENT'], 'payload': {
                'headers': [{'name': 'To', 'value': policy['recipient']}, {'name': 'From', 'value': policy['account']}],
                'parts': [{'filename': self.file.name, 'body': {'size': 1234}}]}}})
        self.persist_receipt(receipt)
        wrong = deepcopy(receipt)
        wrong['readback_result']['structuredContent']['id'] = 'different-in-memory-message'
        with self.assertRaisesRegex(ValueError, 'saved Gmail MIME readback differs'):
            d.reconcile(self.root, {'delivery_id': marked['delivery_id'], 'attempt_id': marked['attempt_id'],
                'outcome': 'sent', 'receipt': wrong}, operation_id='invented-memory-result')
        Path(receipt['send_evidence']).write_text(json.dumps({'structuredContent': {'id': 'different-send-message'}}))
        with self.assertRaisesRegex(ValueError, 'send and readback message IDs differ'):
            d.reconcile(self.root, {'delivery_id': marked['delivery_id'], 'attempt_id': marked['attempt_id'],
                'outcome': 'sent', 'receipt': receipt}, operation_id='mismatched-send-proof')

    def test_actual_native_source_evidence_is_snapshotted(self):
        marked = self.mark(); receipt = self.receipt(marked); self.persist_receipt(receipt)
        source = self.root / 'native-source.json'; source.write_text(json.dumps({'synthetic_tool_record': True}))
        back = json.loads(Path(receipt['readback_evidence']).read_text())
        back['source_evidence'] = [str(source)]
        Path(receipt['readback_evidence']).write_text(json.dumps(back))
        d.reconcile(self.root, {'delivery_id': marked['delivery_id'], 'attempt_id': marked['attempt_id'],
            'outcome': 'sent', 'receipt': receipt}, operation_id='source-bound-ui-proof')
        self.assertTrue(d.completion_status(self.root, [str(self.file)], self.policy)['ready'])
        source.write_text('Changed actual source observation')
        self.assertFalse(d.completion_status(self.root, [str(self.file)], self.policy)['ready'])

    def test_revision_conflict_and_reused_operation_are_not_new_effects(self):
        prepared = self.prepare()
        with self.assertRaisesRegex(ValueError, 'revision conflict'):
            d.mark_sending(self.root, {'delivery_id': prepared['delivery_id'], 'identity': self.identity(),
                'identity_evidence': str(self.root / 'identity.json')}, operation_id='stale-reader', expected_revision=0)
        marked = self.mark()
        with self.assertRaisesRegex(ValueError, 'differs|different delivery content'):
            d.mark_sending(self.root, {'delivery_id': marked['delivery_id'], 'identity': {**self.identity(), 'account': 'different'},
                'identity_evidence': str(self.root / 'identity.json')}, operation_id='reserve')


class ManagedDeliveryAuthorityTests(DeliveryFixture):
    def managed(self, *, external=True, ready=True):
        from runtime.codex_session import create_session, task_delivery_policy
        from runtime.codex_foundation import BRIEF_FIELDS, propose_foundation, confirm_foundation
        from runtime.codex_lifecycle import ingest_message
        request = self.root / 'request.txt'
        request.write_text('DIGR(X):synthetic complete file' if external else 'DIGR:synthetic local file')
        config = self.root / 'registry.json'; config.write_text(json.dumps(registry()))
        task = self.root / 'managed-task'
        create_session(task, request=request, p_run='0.9.0@' + 'a' * 40,
            visits_path=self.root / 'synthetic-visits.jsonl', run_id='synthetic-only', destinations=config)
        if ready:
            proposed = propose_foundation(task, {'brief': {key: 'A synthetic complete file fixture; no real send.' for key in BRIEF_FIELDS}, 'questions': []}, reason='Synthetic bounded object')
            reply = self.root / 'confirmation.txt'; reply.write_text('SIMULATED: execute this exact bounded fixture')
            ingest_message(task, source=reply, source_ref='synthetic-confirmation')
            confirm_foundation(task, revision=proposed['revision'], user_text=reply.read_text(), source='synthetic-confirmation')
        return task, task_delivery_policy(task)

    def test_real_no_x_task_cannot_be_armed_with_an_external_payload(self):
        task, _ = self.managed(external=False)
        with self.assertRaisesRegex(ValueError, 'current task selection'):
            d.prepare(task, {'candidate_id': 'candidate-1', 'files': [str(self.file)], 'policy': self.policy,
                'authorization_source_ref': 'synthetic'}, operation_id='external-bypass')
        self.assertFalse((task / 'delivery.json').exists())

    def test_prepared_external_task_does_not_cross_unconfirmed_foundation(self):
        task, policy = self.managed(ready=False)
        prepared = d.prepare(task, {'candidate_id': 'candidate-1', 'files': [str(self.file)], 'policy': policy,
                'authorization_source_ref': 'synthetic'}, operation_id='prepare-only')
        with self.assertRaises((ValueError, OSError)):
            d.mark_sending(task, {'delivery_id': prepared['delivery_id'], 'identity': self.identity(policy),
                'identity_evidence': str(self.root / 'identity.json')}, operation_id='unconfirmed-send')
        self.assertEqual(d.inspect(task)['deliveries'][0]['status'], 'PREPARED')

    def test_pending_input_during_commit_leaves_uncertainty_but_returns_no_send_grant(self):
        from runtime.codex_lifecycle import ingest_message
        task, policy = self.managed()
        prepared = d.prepare(task, {'candidate_id': 'candidate-1', 'files': [str(self.file)], 'policy': policy,
                'authorization_source_ref': 'synthetic'}, operation_id='prepare')
        pending = self.root / 'new-current-input.txt'; pending.write_text('SIMULATED: wait, correction arriving')
        real_write = d._write
        def write_then_input(root, value):
            real_write(root, value)
            ingest_message(task, source=pending, source_ref='synthetic-pending-at-commit')
        with patch.object(d, '_write', side_effect=write_then_input):
            with self.assertRaisesRegex(ValueError, 'pending'):
                d.mark_sending(task, {'delivery_id': prepared['delivery_id'], 'identity': self.identity(policy),
                    'identity_evidence': str(self.root / 'identity.json')}, operation_id='interrupted-at-commit')
        self.assertTrue(d.inspect(task)['deliveries'][0]['unresolved'])
        replay = d.mark_sending(task, {'delivery_id': prepared['delivery_id'], 'identity': self.identity(policy),
                    'identity_evidence': str(self.root / 'identity.json')}, operation_id='interrupted-at-commit')
        self.assertFalse(replay['send_allowed'])


if __name__ == '__main__':
    unittest.main()
