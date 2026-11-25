from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from runtime.codex_profile import classify_invocation


LOCAL = {'mode': 'local', 'target': None, 'explicit': False}


class CodexXInvocationTests(unittest.TestCase):
    def test_supported_aliases_and_header_punctuation_select_only_files(self):
        for alias in ('DIGR', 'DIGRP', '深度迭代'):
            for group, separator in (('(X)', ':'), ('（X）', '：'), ('（X＝Gmail）', ':')):
                with self.subTest(alias=alias, group=group, separator=separator):
                    body = '  完整任务：保留标点\n(X=QQ)  '
                    raw = '\u3000 ' + alias + group + separator + body
                    result = classify_invocation(raw)
                    self.assertEqual(result['classification'], 'EXECUTING')
                    self.assertEqual(result['task'], body)
                    self.assertEqual(result['parameter_text'], group)
                    self.assertEqual(result['execution_parameter_text'], '')
                    self.assertEqual(result['delivery_selection'],
                                     {'mode': 'external', 'target': 'gmail', 'explicit': True})
                    self.assertEqual(result['addon_selection'], 'paper' if alias == 'DIGRP' else None)
                    self.assertEqual(result['action_scope'], 'INTERPRET_SEPARATELY')
                    self.assertFalse(result['run_started'])
                    self.assertFalse(result['live_acquisition_performed'])

    def test_standalone_x_follows_empty_or_complete_execution_group(self):
        parameters = (
            '()',
            '(N=18,R=5,D(4),V(4))',
            '(N=16,T=60min,R=4,B=0,S(n=3,t=20min,r=2,b=0),D=3,V=3,L=3,M=1)',
            '（N（16），T（60min），R（4），B（0），S（n（3），t（20min），r（2），b（0）），D（3），V（3），L（3），M（1））',
            '(16,60min,4,0,S(3,20min,2,0),3,3,3)',
            '(standard)', '(target=60min,source=auto)', '(min=60min,source=off)',
        )
        for parameters in parameters:
            with self.subTest(parameters=parameters):
                prelude = ' \t' + parameters + '  （X＝Gmail）\t '
                result = classify_invocation('DIGR' + prelude + ':task')
                self.assertEqual(result['classification'], 'EXECUTING')
                self.assertEqual(result['parameter_text'], prelude)
                self.assertEqual(result['execution_parameter_text'], ' \t' + parameters + '  ')
                self.assertEqual(result['delivery_selection'],
                                 {'mode': 'external', 'target': 'gmail', 'explicit': True})

    def test_gmail_and_custom_lexical_candidates_do_not_claim_channel_support(self):
        # A lexical candidate is not a supported channel or resolved account.
        for target in ('Gmail', 'Private_Archive-2', 'a', 'A' * 64):
            with self.subTest(target=target):
                result = classify_invocation('DIGR(X=' + target + '):task', p_run='1.4.1@' + 'a' * 40)
                self.assertEqual(result['classification'], 'EXECUTING')
                self.assertEqual(result['delivery_selection'],
                                 {'mode': 'external', 'target': target.casefold(), 'explicit': True})
                self.assertNotIn('recipient', result['delivery_selection'])

    def test_bare_x_and_explicit_gmail_have_the_same_selection(self):
        for prelude in ('(X)', '()(X)', '(N=16)(X)', '（X）', '（）（X）'):
            with self.subTest(prelude=prelude):
                bare = classify_invocation('DIGR' + prelude + ':task')
                named = classify_invocation('DIGR(X=Gmail):task')
                self.assertEqual(bare['classification'], 'EXECUTING')
                self.assertEqual(bare['delivery_selection'], named['delivery_selection'])

    def test_invalid_x_headers_never_expose_an_external_selection(self):
        cases = {
            'duplicate': '(X)(X=Gmail)',
            'duplicate after normal': '(N=18)(X=QQ)(X)',
            'empty assignment': '(X=)',
            'whitespace assignment': '（X＝\u3000 ）',
            'mixed labeled': '(N=18,X=QQ)',
            'mixed bare': '（N（18），X）',
            'nested mixed': '(S(n=3,X=QQ))',
            'reversed groups': '(X)(N=18)',
            'three groups': '(N=18)(R=4)(X)',
            'intervening text': '(N=18)junk(X)',
            'nested selector': '((X=QQ))',
            'function selector': '(X(QQ))',
            'multiple destinations': '(X=Gmail,QQ)',
            'two assignments': '(X=QQ,X=Gmail)',
            'address is not slug': '(X=example@example.com)',
            'url is not slug': '(X=https://example.com)',
            'nonascii target': '(X=酿)',
            'numeric prefix': '(X=9archive)',
            'overlong target': '(X=' + 'a' * 65 + ')',
        }
        for name, prelude in cases.items():
            with self.subTest(name=name, prelude=prelude):
                result = classify_invocation('DIGRP' + prelude + ':task', p_run='1.4.1@' + 'a' * 40)
                self.assertEqual(result['classification'], 'INVALID')
                self.assertEqual(result['delivery_selection'], LOCAL)
                self.assertIsNone(result['addon_selection'])
                self.assertIsNone(result['execution_parameter_text'])

    def test_unbalanced_headers_fail_but_unbalanced_body_is_preserved(self):
        for prelude in ('(X', '(X）', '（X)', '(N=12)(X', '(N=(12)))(X)'):
            with self.subTest(prelude=prelude):
                result = classify_invocation('DIGR' + prelude + ':task')
                self.assertEqual(result['classification'], 'INVALID')
                self.assertEqual(result['delivery_selection'], LOCAL)
        body = 'Preserve (X=QQ and an unmatched ） plus more: text'
        result = classify_invocation('DIGR(X=Gmail):' + body)
        self.assertEqual(result['classification'], 'EXECUTING')
        self.assertEqual(result['task'], body)
        self.assertEqual(result['delivery_selection']['target'], 'gmail')

    def test_no_x_invocations_preserve_all_depth_parameters_and_task(self):
        for parameters in ('', ' \t', '()', '(standard)', '(N=12,R(4),D(3),V(3),L(3),M(2))',
                           '(target=60min,min=30min,source=auto)',
                           '（N（12），S（n（3），t（30min），r（2），b（0）））'):
            with self.subTest(parameters=parameters):
                body = '  Discuss X=QQ, (X), and DIGRP(X=Gmail): as text\n'
                result = classify_invocation('DIGR' + parameters + ':' + body)
                self.assertEqual(result['classification'], 'EXECUTING')
                self.assertEqual(result['parameter_text'], parameters)
                self.assertEqual(result['execution_parameter_text'], parameters)
                self.assertEqual(result['task'], body)
                self.assertEqual(result['delivery_selection'], LOCAL)

    def test_mentions_quotes_help_and_discussion_never_select_delivery(self):
        for raw, classification in (
            ('DIGR/help', 'HELP'), ('DIGRP/help', 'HELP'),
            ('DIGR(X=QQ)', 'NATIVE'), ('DIGR(X)是什么？', 'NATIVE'),
            ('DIGRProblem(X=QQ):a word', 'NATIVE'),
            ('请解释DIGR(X=QQ):task', 'NATIVE'), ('“DIGR(X=QQ):task”是引文', 'NATIVE'),
            ('digr(X):task', 'NATIVE'), ('Digr(X):task', 'NATIVE'),
            ('DIGR(X): ', 'INVALID'),
        ):
            with self.subTest(raw=raw):
                result = classify_invocation(raw)
                self.assertEqual(result['classification'], classification)
                self.assertEqual(result['delivery_selection'], LOCAL)


class CodexXIntentScopeTests(unittest.TestCase):
    """Synthetic task journeys; no host connections or real transfers occur."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='codex-x-intent-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.registry = self.base / 'targets.json'
        self.registry.write_text(json.dumps({'format': 'digr-delivery-targets-1', 'targets': {
            'gmail': {'channel': 'gmail', 'account': 'reader@example.test',
                      'recipient': 'reader@example.test', 'target_kind': 'self_mailbox',
                      'transport': 'native-connector', 'aliases': ['Mail']},
        }}), encoding='utf-8')
        self.counter = 0

    def create(self, name, text):
        from runtime.codex_session import create_session
        request = self.base / (name + '-request.txt')
        request.write_text(text, encoding='utf-8')
        root = self.base / name
        create_session(root, request=request, p_run='0.9.0@' + 'a' * 40,
                       visits_path=self.base / 'visits.jsonl', run_id=name,
                       destinations=self.registry)
        return root

    def ingest(self, root, text):
        from runtime.codex_lifecycle import ingest_message
        self.counter += 1
        source = self.base / ('source-' + str(self.counter) + '.txt')
        source.write_text(text, encoding='utf-8')
        source_ref = 'synthetic-source-' + str(self.counter)
        value = ingest_message(root, source=source, source_ref=source_ref,
            route_pin='0.9.0@' + 'a' * 40 if text.startswith('DIGR') else None)
        return value['message_id'], source, source_ref

    def record_synthetic_attempt(self, root, *, sent):
        from runtime import codex_delivery as delivery
        from runtime.codex_foundation import BRIEF_FIELDS, confirm_foundation, propose_foundation
        from runtime.codex_session import task_delivery_policy
        propose_foundation(root, {'brief': {key: 'Synthetic test scope: ' + label
            for key, label in BRIEF_FIELDS.items()}, 'questions': []}, reason='Synthetic scoped fixture')
        text = 'SYNTHETIC: confirm only this local test fixture; no real external action.'
        _, _, source_ref = self.ingest(root, text)
        confirm_foundation(root, revision=1, user_text=text, source=source_ref)
        policy = task_delivery_policy(root)
        file = root / 'synthetic-final.pdf'
        file.write_bytes(b'SYNTHETIC selected attachment, no external action.\n')
        prepared = delivery.prepare(root, {'policy': policy, 'candidate_id': 'synthetic-candidate',
            'files': [str(file)], 'authorization_source_ref': source_ref}, operation_id='synthetic-prepare')
        identity = {'account': policy['account'], 'recipient': policy['recipient'],
                    'account_confirmed': True, 'recipient_confirmed': True,
                    'binding_basis': 'native-self-entry'}
        evidence = {}
        for name in ('identity', 'send', 'readback'):
            path = root / ('synthetic-' + name + '.json')
            document = {'synthetic_not_real_observation': name}
            if name == 'identity':
                document['identity'] = identity
            path.write_text(json.dumps(document), encoding='utf-8')
            evidence[name + '_evidence'] = str(path)
        marked = delivery.mark_sending(root, {'delivery_id': prepared['delivery_id'], 'identity': identity,
            'identity_evidence': evidence['identity_evidence']}, operation_id='synthetic-reserve')
        if sent:
            native_readback = {'id': 'synthetic-message', 'labelIds': ['SENT'], 'payload': {
                'headers': [{'name': 'From', 'value': policy['account']},
                            {'name': 'To', 'value': policy['recipient']}],
                'parts': [{'filename': file.name, 'body': {
                    'size': file.stat().st_size, 'attachmentId': 'synthetic-attachment'}}]}}
            receipt = {'candidate_id': 'synthetic-candidate', 'attempt_id': marked['attempt_id'],
                **{key: policy[key] for key in ('target', 'channel', 'account', 'recipient', 'transport')},
                'evidence_kind': 'gmail-api', 'message_id': 'synthetic-message', 'identity': identity,
                'readback': {'completed': True, 'attempt_correlated': True},
                'readback_result': native_readback, **evidence}
            Path(evidence['readback_evidence']).write_text(json.dumps({
                'synthetic_not_real_observation': True, 'readback_result': native_readback}), encoding='utf-8')
            Path(evidence['send_evidence']).write_text(json.dumps({
                'synthetic_not_real_observation': True,
                'send_result': {'id': 'synthetic-message'}}), encoding='utf-8')
            delivery.reconcile(root, {'delivery_id': marked['delivery_id'], 'attempt_id': marked['attempt_id'],
                'outcome': 'sent', 'receipt': receipt}, operation_id='synthetic-record')
        return policy

    def test_invalid_or_help_source_cannot_arm_a_guessed_external_choice(self):
        from runtime.codex_lifecycle import handle_message
        from runtime.codex_session import task_delivery_policy
        for index, text in enumerate(('DIGR(X=):task', 'DIGR(X)(X=Gmail):task', 'DIGR/help')):
            with self.subTest(text=text):
                root = self.create('malformed-' + str(index), 'DIGR:synthetic local task')
                number, _, _ = self.ingest(root, text)
                with self.assertRaises(ValueError):
                    handle_message(root, message_id=number, action='continue', reason='Synthetic malformed input',
                        delivery_selection={'mode': 'external', 'target': 'gmail', 'explicit': True},
                        destinations=self.registry)
                self.assertEqual(task_delivery_policy(root)['mode'], 'local')

    def test_changing_source_file_after_ingest_cannot_rewrite_selected_x_header(self):
        from runtime.codex_lifecycle import handle_message
        from runtime.codex_session import task_delivery_policy
        root = self.create('source-snapshot', 'DIGR:synthetic local task')
        number, source, _ = self.ingest(root, 'DIGR(X=Gmail):synthetic explicit correction')
        source.write_text('DIGR(X=unknown_archive):different text after selected input', encoding='utf-8')
        with self.assertRaises(ValueError):
            handle_message(root, message_id=number, action='continue', reason='Synthetic mismatched correction',
                delivery_selection={'mode': 'external', 'target': 'unknown_archive', 'explicit': True},
                destinations=self.registry)
        handle_message(root, message_id=number, action='continue', reason='Use actual ingested Gmail source',
            delivery_selection={'mode': 'external', 'target': 'gmail', 'explicit': True}, destinations=self.registry)
        self.assertEqual(task_delivery_policy(root)['target'], 'gmail')

    def test_local_revocation_keeps_prior_sent_or_uncertain_history(self):
        from runtime import codex_delivery as delivery
        from runtime.codex_lifecycle import handle_message
        from runtime.codex_session import task_delivery_policy
        for sent in (False, True):
            with self.subTest(sent=sent):
                root = self.create('revoke-' + str(sent), 'DIGR(X):synthetic multi-file task')
                old_policy = self.record_synthetic_attempt(root, sent=sent)
                number, _, _ = self.ingest(root, 'SYNTHETIC USER: stop further external files; keep them here.')
                handle_message(root, message_id=number, action='ordinary', reason='Synthetic explicit local revocation',
                               delivery_selection=LOCAL)
                self.assertEqual(task_delivery_policy(root)['mode'], 'local')
                history = delivery.inspect(root)['deliveries']
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]['policy'], old_policy)
                self.assertEqual(history[0]['recorded_status'], 'SENT_VERIFIED' if sent else 'SENDING')
                self.assertEqual(history[0]['unresolved'], not sent)

    def test_equivalent_alias_after_sent_inherits_frozen_endpoint(self):
        from runtime.codex_lifecycle import handle_message
        from runtime.codex_session import task_delivery_policy
        root = self.create('equivalent-alias', 'DIGR(X):synthetic multi-file task')
        old_policy = self.record_synthetic_attempt(root, sent=True)
        number, _, _ = self.ingest(root, 'DIGR(X=Mail):continue the same synthetic task')
        handle_message(root, message_id=number, action='ordinary', reason='Equivalent alias, same frozen endpoint',
                       destinations=self.registry)
        self.assertEqual(task_delivery_policy(root), old_policy)


if __name__ == '__main__':
    unittest.main()
