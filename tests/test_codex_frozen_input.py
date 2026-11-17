"""Public API regressions for an old task opened by a newer installed helper.

Run through unittest discovery in the selected source distribution.
Synthetic user records and target registry only; no send/model API is used.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

from runtime.codex_session import create_session
from runtime.codex_lifecycle import (
    ingest_message, handle_message, load_lifecycle, require_open_decision, terminate_message,
)

OLD = '0.14.0@' + 'a' * 40
HEAD = '0.15.0@' + 'f' * 40


class FrozenInputRegression(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix='interop-')
        self.addCleanup(self.scratch.cleanup)
        self.base = Path(self.scratch.name)
        self.sequence = 0
        self.registry = self.base / 'targets.json'
        self.registry.write_text(json.dumps({'format': 'digr-delivery-targets-1', 'targets': {
            'gmail': {'channel': 'gmail', 'account': 'fixture@example.test',
                      'recipient': 'fixture@example.test', 'target_kind': 'self_mailbox',
                      'transport': 'native-connector', 'aliases': []}}}), encoding='utf-8')

    def task(self, pin=OLD, raw='DIGR：按已给规格继续。'):
        source = self.base / 'original.txt'
        source.write_text(raw, encoding='utf-8')
        root = self.base / 'task'
        create_session(root, request=source, p_run=pin,
                       visits_path=self.base / 'visits.jsonl', run_id='synthetic-interop',
                       destinations=self.registry)
        return root

    def ingest(self, root, raw, route_pin=HEAD):
        self.sequence += 1
        source = self.base / ('input-' + str(self.sequence) + '.txt')
        source.write_text(raw, encoding='utf-8')
        reference = 'current-synthetic-message-' + str(self.sequence)
        return ingest_message(root, source=source, source_ref=reference,
                              route_pin=route_pin), source, reference

    def test_old_decision_uses_frozen_task_grammar(self):
        root = self.task()
        raw = 'DIGR:::以原规格补充本项；正文有两个冒号开头。'
        value, _, reference = self.ingest(root, raw)
        self.assertEqual(value['P_run'], OLD)
        self.assertEqual(value['current_message']['upstream_route_pin_ref'], HEAD)
        self.assertEqual(value['current_message']['surface'], 'EXECUTING')
        self.assertEqual(require_open_decision(root, user_text=raw, source=reference)['P_run'], OLD)

    def test_old_acquisition_retry_keeps_frozen_task_grammar(self):
        root = self.task()
        value, source, reference = self.ingest(root, 'DIGR:::正文', route_pin=None)
        self.assertEqual(value['current_message']['surface'], 'ROUTE_PENDING')
        value = ingest_message(root, source=source, source_ref=reference, route_pin=HEAD)
        self.assertEqual(value['current_message']['surface'], 'EXECUTING')
        self.assertEqual(value['P_run'], OLD)

    def test_priority_termination_retains_the_frozen_source_grammar(self):
        root = self.task()
        source = self.base / 'stop.txt'
        source.write_text('DIGR:::停止当前任务。', encoding='utf-8')
        value = terminate_message(root, source=source, source_ref='actual-priority-stop',
                                  action='stop', reason='Current user termination', route_pin=HEAD)
        self.assertEqual(value['status'], 'STOPPED')
        self.assertEqual(value['current_message']['surface'], 'EXECUTING')
        self.assertEqual(value['P_run'], OLD)

    def test_old_x_header_is_not_silently_ignored(self):
        root = self.task()
        value, _, _ = self.ingest(root, 'DIGR(X):::继续原任务。')
        with self.assertRaisesRegex(ValueError, 'changes X'):
            handle_message(root, message_id=value['message_id'], action='continue',
                           reason='Header asks for an explicit X change', destinations=self.registry)

    def test_old_explicit_x_change_can_complete(self):
        root = self.task()
        original = (root / 'REQUEST.txt').read_bytes()
        value, _, _ = self.ingest(root, 'DIGR(X):::继续原任务。')
        value = handle_message(root, message_id=value['message_id'], action='continue',
                               reason='Apply the actual current source X header',
                               delivery_selection={'mode': 'external', 'target': 'gmail', 'explicit': True},
                               destinations=self.registry)
        self.assertEqual(value['delivery_selection']['mode'], 'external')
        self.assertEqual(value['delivery_selection']['target'], 'gmail')
        self.assertEqual(value['P_run'], OLD)
        self.assertNotIn('claude_policy', value)
        self.assertEqual((root / 'REQUEST.txt').read_bytes(), original)

    def test_new_choice_and_controls_keep_their_own_semantics(self):
        root = self.task(pin=HEAD, raw='DIGR::由Claude指导实质主观内容。')
        for raw in ('DIGR/help', 'DIGR是什么？', 'DIGR:::损坏调用'):
            value, _, _ = self.ingest(root, raw)
            value = handle_message(root, message_id=value['message_id'], action='continue',
                                   reason='Same-task control message')
            self.assertEqual(value['claude_policy']['mode'], 'ALLOW')
            self.assertEqual(value['claude_policy']['message_id'], 0)
        value, _, _ = self.ingest(root, 'DIGRC：按已有指导执行，不再调用。')
        value = handle_message(root, message_id=value['message_id'], action='continue',
                               reason='Current actual single-colon choice replaces earlier selection')
        self.assertEqual(value['claude_policy']['mode'], 'DENY')
        self.assertEqual(value['P_run'], HEAD)


if __name__ == '__main__':
    unittest.main()
