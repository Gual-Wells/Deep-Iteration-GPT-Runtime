"""Current-user delimiter selection: no live model service or real credentials."""
from __future__ import annotations

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from runtime import codex_consult as consult, codex_paper as paper
from runtime.codex_profile import classify_invocation
from runtime.codex_session import create_session
from runtime.codex_lifecycle import ingest_message, handle_message, load_lifecycle, terminate_message
import test_codex_consult as fixtures
import test_codex_split as split_fixtures


class ClaudeSelectionTests(unittest.TestCase):
    file = fixtures.ConsultPublicRuntimeTests.file
    config = fixtures.ConsultPublicRuntimeTests.config
    facts = fixtures.ConsultPublicRuntimeTests.facts
    stop_server = fixtures.ConsultPublicRuntimeTests.stop_server
    plan = split_fixtures.NativeSplitTests.plan

    def setUp(self):
        fixtures.ConsultPublicRuntimeTests.setUp(self)
        self.pin = '0.15.0@' + 'f' * 40
        self.original = self.file('delimiter-user.txt', 'DIGR：：完成合成内容；允许按需采用Claude。\n')
        self.root = self.folder / 'delimiter-task'
        create_session(self.root, request=self.original, p_run=self.pin)
        self.sequence = 0

    def select(self, text, selection=None):
        self.sequence += 1
        ref = 'current-user-' + str(self.sequence)
        source = self.file(ref + '.txt', text)
        candidate = text.lstrip().startswith(('DIGR', '深度迭代'))
        state = ingest_message(self.root, source=source, source_ref=ref,
                               route_pin=self.pin if candidate else None)
        return handle_message(self.root, message_id=state['message_id'], action='continue',
                              reason='Apply the selected synthetic user message', claude_selection=selection)

    def prepare(self, label, **kwargs):
        return consult.prepare_request(self.root, input_path=self.input, exchange_id=label,
                                       materials=[self.material], max_tokens=16000, **kwargs)

    def call(self, label, **kwargs):
        with patch.dict(os.environ, {'DIGR_TEST_CONSULT_KEY': fixtures.SECRET}):
            return consult.call_once(self.root, label, facts=self.facts(), ceiling_usd=.20,
                                     config_path=self.config('paper-model-confirmed'),
                                     split_path=self.plan(label), **kwargs)

    def test_both_colons_are_consumed_without_rewriting_task_or_parameters(self):
        for alias in ('DIGR', '深度迭代', 'DIGRC', 'DIGRP'):
            for separator in (':', '：', '::', '：：', ':：', '：:'):
                with self.subTest(alias=alias, separator=separator):
                    raw_task = '  原件：保持双冒号::与末尾换行\n'
                    value = classify_invocation('  ' + alias + '(Less)(X)' + separator + raw_task)
                    self.assertEqual(value['classification'], 'EXECUTING')
                    self.assertEqual(value['task'], raw_task)
                    self.assertEqual(value['parameter_text'], '(Less)(X)')
                    self.assertEqual(value['depth_defaults']['preset'], 'Less')
                    self.assertEqual(value['delivery_selection']['target'], 'gmail')
                    self.assertEqual(value['claude_selection'], 'ALLOW' if len(separator) == 2 else 'COUNCIL_ONLY')
        for raw in ('DIGR:: ', 'DIGR：：', 'DIGR:::task', 'DIGR：:：task'):
            self.assertEqual(classify_invocation(raw)['classification'], 'INVALID')

    def test_quotes_discussion_and_task_body_do_not_grant_permission(self):
        for raw in ('“DIGR：：任务”是历史引文', '请解释DIGR：：的区别', 'digr::task', 'Digr::task',
                    'DIGR现在的入口:::是讨论内容'):
            self.assertEqual(classify_invocation(raw)['classification'], 'NATIVE')
        self.assertEqual(classify_invocation('DIGR：正文提及DIGR：：')['claude_selection'], 'COUNCIL_ONLY')
        self.assertEqual(self.server.post_calls, [])
        self.assertFalse((self.root / 'consult').exists())

    def test_one_colon_blocks_claude_families_before_preparation_or_credentials(self):
        self.select('DIGR：继续，由Codex完成。')
        for model in ('anthropic/claude-sonnet-5.5', 'anthropic/claude-opus-4.6',
                      'anthropic/claude-3-haiku', 'claude-sonnet-5.5'):
            with self.subTest(model=model), patch.object(consult, '_config', side_effect=AssertionError('secret read')):
                with self.assertRaisesRegex(ValueError, 'Claude is disabled'):
                    self.prepare('blocked', model=model)
        self.assertFalse((self.root / 'consult' / 'exchanges' / 'blocked').exists())
        self.assertEqual(self.server.post_calls, [])

    def test_double_colon_allows_the_actual_local_fixture_call_but_does_not_send_by_itself(self):
        self.assertEqual(self.server.post_calls, [])
        value = self.prepare('allowed')
        self.assertEqual(value['exchange']['billing_status'], 'NOT_ATTEMPTED')
        self.assertEqual(self.server.post_calls, [])
        result = self.call('allowed')
        self.assertEqual(result['sonnet_model_identity']['status'], 'CONFIRMED')
        self.assertEqual(len(self.server.post_calls), 1)

    def test_initial_single_colon_is_execution_without_claude(self):
        original = self.file('initial-execution.txt', 'DIGR：按给定规格组装文件。')
        task = self.folder / 'initial-execution'
        value = create_session(task, request=original, p_run=self.pin)
        self.assertEqual(value['initial_invocation']['work_profile'], 'EXECUTION')
        self.assertEqual(load_lifecycle(task)['claude_policy']['mode'], 'DENY')
        with self.assertRaisesRegex(ValueError, 'Claude is disabled'):
            consult.prepare_request(task, input_path=self.input)
        self.assertEqual(self.server.post_calls, [])

    def test_paper_registration_cannot_override_the_current_denial(self):
        self.select('DIGR：按已有稿制作，不再调用Claude。')
        batch = self.folder / 'registered-paper'
        paper.initialize(batch, p_run=self.pin, authorization=self.original,
                         source_ref='original-choice-before-withdrawal', task_root=self.root)
        item = paper.add_paper(batch, paper_id='source', title='Synthetic registered paper',
            line='M01', owner='fixture', parameters={'N': 2, 'R': 1, 'D': 0, 'V': 0, 'L': 3,
                'T': '0min', 'B': 0, 'S': {'n': 0, 'r': 0, 't': '0min', 'b': 0}})
        with self.assertRaisesRegex(ValueError, 'Claude is disabled'):
            self.prepare('paper-bypass', paper_root=Path(item['paper_root']))
        self.assertEqual(self.server.post_calls, [])

    def test_plain_followups_inherit_the_choice_after_recent_history_rolls_over(self):
        for i in range(10):
            self.select('补充事实' + str(i))
        state = load_lifecycle(self.root)
        self.assertEqual(state['claude_policy']['mode'], 'ALLOW')
        self.assertEqual(state['claude_policy']['message_id'], 0)
        self.prepare('after-followups')
        self.select('DIGR：继续，不用Claude。')
        self.select('再补充原件中的一处事实。')
        with self.assertRaisesRegex(ValueError, 'Claude is disabled'):
            self.prepare('after-denial')
        self.assertEqual((self.root / 'REQUEST.txt').read_bytes(), self.original.read_bytes())
        self.assertEqual(load_lifecycle(self.root)['P_run'], self.pin)

    def test_prose_change_is_bound_to_the_current_real_source(self):
        self.select('后续不用Claude，由Codex继续。', 'DENY')
        self.select('现在明确让Claude参与内容，其余继续。', 'ALLOW')
        state = load_lifecycle(self.root)
        self.assertEqual(state['claude_policy']['basis'], 'CURRENT_USER_DECISION')
        self.assertEqual(state['claude_policy']['source']['text'], '现在明确让Claude参与内容，其余继续。')
        self.prepare('prose-choice')

    def test_handled_revocation_blocks_prepared_send_without_reservation_or_secret_read(self):
        self.prepare('pending')
        plan = self.plan('pending')
        self.select('DIGR：继续，撤销Claude。')
        with patch.object(consult, '_config', side_effect=AssertionError('secret read')):
            with self.assertRaisesRegex(ValueError, 'Claude is disabled'):
                consult.call_once(self.root, 'pending', facts=self.facts(), ceiling_usd=.20,
                                  config_path=self.config('normal'), split_path=plan)
        report = consult.inspect_exchange(self.root, 'pending')
        self.assertEqual(report['exchange']['billing_status'], 'NOT_ATTEMPTED')
        self.assertEqual(report['totals']['unresolved_reserved_usd'], 0)
        self.assertEqual(self.server.post_calls, [])

    def test_revocation_during_preflight_is_rechecked_at_send_commit(self):
        self.prepare('racing')
        config = consult._config
        def revoke_then_config(path):
            self.select('后续不用Claude。', 'DENY')
            return config(path)
        with patch.object(consult, '_config', side_effect=revoke_then_config):
            with self.assertRaisesRegex(ValueError, 'Claude is disabled'):
                self.call('racing')
        report = consult.inspect_exchange(self.root, 'racing')
        self.assertEqual(report['exchange']['billing_status'], 'NOT_ATTEMPTED')
        self.assertEqual(report['totals']['unresolved_reserved_usd'], 0)
        self.assertEqual(self.server.post_calls, [])

    def test_all_intent_metadata_is_prepared_before_the_final_task_check(self):
        for change in ('deny', 'stop', 'pending', 'same-allow-correction'):
            with self.subTest(change=change):
                self.root = self.folder / ('intent-' + change)
                source = self.file('intent-' + change + '.txt', 'DIGR::按当前用户用途协作。')
                create_session(self.root, request=source, p_run=self.pin)
                self.prepare('intent')
                actual_now = consult._now
                triggered = False
                def changed_now():
                    nonlocal triggered
                    if not triggered:
                        triggered = True
                        source = self.file('during-intent-' + change + '.txt', '实际当前用户纠正：' + change)
                        if change == 'stop':
                            terminate_message(self.root, source=source, source_ref='intent-stop',
                                              action='stop', reason='Actual stop before durable intent')
                        else:
                            state = ingest_message(self.root, source=source, source_ref='intent-' + change)
                            if change != 'pending':
                                handle_message(self.root, message_id=state['message_id'], action='continue',
                                    reason='Actual current correction before durable intent',
                                    claude_selection='DENY' if change == 'deny' else 'ALLOW')
                    return actual_now()
                with patch.object(consult, '_now', side_effect=changed_now):
                    with self.assertRaises(ValueError):
                        self.call('intent')
                report = consult.inspect_exchange(self.root, 'intent')
                self.assertTrue(triggered)
                self.assertEqual(report['exchange']['transport_status'], 'PREPARED')
                self.assertEqual(report['exchange']['billing_status'], 'NOT_ATTEMPTED')
                self.assertEqual(report['totals']['unresolved_reserved_usd'], 0)
                self.assertEqual(self.server.post_calls, [])

    def test_retained_choice_requirements_reach_generic_and_paper_context(self):
        body = '只按原文逐页提取，不得改成自编讲义；现在明确让Claude参与。'
        self.select(body, 'ALLOW')
        choice = load_lifecycle(self.root)['claude_policy']
        self.select('先完成第三页对应部分。')
        batch = self.folder / 'choice-context-paper'
        paper.initialize(batch, p_run=self.pin, authorization=self.original,
                         source_ref='whole-paper-user-scope', task_root=self.root)
        item = paper.add_paper(batch, paper_id='source', title='Selected synthetic paper',
            line='M01', owner='fixture', parameters={'N': 2, 'R': 1, 'D': 0, 'V': 0, 'L': 3,
                'T': '0min', 'B': 0, 'S': {'n': 0, 'r': 0, 't': '0min', 'b': 0}})
        for label, kwargs in (('retained-generic', {}),
                              ('retained-paper', {'paper_root': Path(item['paper_root'])})):
            result = self.prepare(label, **kwargs)
            request = json.loads(Path(result['request_path']).read_text(encoding='utf-8'))
            content = request['messages'][-1]['content']
            self.assertEqual(content.count(body), 1)
            self.assertIn('HISTORICAL USER DECISION', content)
            self.assertEqual([s['sha256'] for s in result['exchange']['sources']
                if s['kind'] == 'CLAUDE_SELECTION_USER_INPUT'], [choice['source']['sha256']])
        self.assertEqual(self.server.post_calls, [])

    def test_replayed_choice_body_is_not_inlined_again(self):
        body = '保留作者完整原意；现在让Claude参与对应内容。'
        self.select(body, 'ALLOW')
        self.select('先完成第一个小块。')
        self.prepare('choice-origin')
        self.call('choice-origin')  # Only the synthetic local HTTP fixture.
        self.select('接着处理下一小块。')
        result = self.prepare('choice-followup', continue_from='choice-origin')
        request = json.loads(Path(result['request_path']).read_text(encoding='utf-8'))
        self.assertEqual(sum(m['content'].count(body) for m in request['messages']), 1)
        choice = next(s for s in result['exchange']['sources'] if s['kind'] == 'CLAUDE_SELECTION_USER_INPUT')
        self.assertEqual(choice['content_representation'], 'EXACT_BODY_REFERENCE')
        self.assertEqual(len(self.server.post_calls), 1)

    def test_c_p_aliases_do_not_bypass_a_single_colon(self):
        for alias in ('DIGRC', 'DIGRP'):
            self.select(alias + '：继续。')
            with self.assertRaisesRegex(ValueError, 'Claude is disabled'):
                self.prepare(alias)
        self.assertEqual(self.server.post_calls, [])

    def test_explicit_choice_cannot_contradict_a_current_complete_separator(self):
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            self.select('DIGR：继续。', 'ALLOW')
        self.assertEqual(self.server.post_calls, [])

    def test_edited_initial_mode_cannot_override_the_current_user_separator(self):
        self.select('DIGR：继续。')
        path = self.root / 'session.json'
        value = json.loads(path.read_text(encoding='utf-8'))
        value['execution_profile']['claude_selection'] = 'ALLOW'
        path.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Claude is disabled'):
            self.prepare('edited-mode')
        path = self.root / 'lifecycle.json'
        value = json.loads(path.read_text(encoding='utf-8'))
        value['claude_policy']['mode'] = 'ALLOW'
        value['claude_policy']['work_profile'] = 'CLAUDE_GUIDED'
        path.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'differs from its user separator'):
            self.prepare('edited-policy')

    def test_new_policy_does_not_silently_change_old_pin_interpretation(self):
        old = '0.14.0@' + 'a' * 40
        self.assertEqual(classify_invocation('DIGR::task', p_run=old)['task'], ':task')
        self.assertNotIn('claude_selection', classify_invocation('DIGR:task', p_run=old))
        task = self.folder / 'old-unified'
        source = self.file('old-unified-user.txt', 'DIGR：旧规则任务。')
        create_session(task, request=source, p_run=old)
        value = consult.prepare_request(task, input_path=self.input, exchange_id='old-behavior')
        self.assertEqual(value['exchange']['billing_status'], 'NOT_ATTEMPTED')
        self.assertNotIn('claude_policy', load_lifecycle(task))
        self.assertEqual(self.server.post_calls, [])


if __name__ == '__main__':
    unittest.main()
