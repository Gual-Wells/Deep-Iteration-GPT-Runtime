from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from runtime import codex_allot
from runtime.codex_session import create_line, create_session, line_packet


ROOT = Path(__file__).resolve().parents[1]
LEGACY_PIN = '0.5.1@11631eec1cbf3397a2b4d6d7cc24190188c0d2d6'


class AllotRecoveryTests(unittest.TestCase):
    def setUp(self):
        cache = (ROOT / '.cache').resolve()
        cache.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='codex-allot-recovery-', dir=cache)
        self.folder = Path(temporary.name).resolve()
        if (not self.folder.is_relative_to(cache)
                or not self.folder.name.startswith('codex-allot-recovery-')):
            raise RuntimeError('refusing cleanup outside the intended task cache')
        self.addCleanup(temporary.cleanup)
        request = self.folder / 'request.txt'
        request.write_text('Keep the given originals and complete the requested work.\n', encoding='utf-8')
        self.decisions = self.folder / 'DECISIONS.md'
        self.decisions.write_text('当前用户纠正：继续原任务并保留原件。\n', encoding='utf-8')
        self.session = self.folder / 'session'
        create_session(self.session, request=request, p_run=LEGACY_PIN, decisions=self.decisions)
        parameters = {'N': 12, 'T': 0, 'R': 4, 'B': 0,
                      'S': {'n': 0, 't': 0, 'r': 0, 'b': 0}, 'D': 3, 'V': 3, 'L': 3}
        own = create_line(self.session, 'M01', parameters=parameters)
        self.own_work = Path(own['work'])

    def snapshot(self):
        return {path.relative_to(self.session).as_posix(): path.read_bytes()
                for path in self.session.rglob('*') if path.is_file()}

    def test_legacy_without_allot_is_read_only_and_keeps_its_packet(self):
        before = self.snapshot()
        packet = line_packet(self.session, 'M01')
        self.assertNotIn('## 当前Allot政策与原生执行概况', packet)
        self.assertIn('继续原任务并保留原件', packet)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.session / 'allot').exists())

    def test_recovery_uses_safe_summary_instead_of_private_selection_evidence(self):
        other = create_line(self.session, 'M02', parameters={
            'N': 12, 'T': 0, 'R': 4, 'B': 0,
            'S': {'n': 0, 't': 0, 'r': 0, 'b': 0}, 'D': 3, 'V': 3, 'L': 3})
        private_work = 'OTHER_RESEARCHER_PRIVATE_WORK_7e83'
        Path(other['work']).write_text(private_work, encoding='utf-8')
        private_evidence = 'PRIVATE_SELECTION_EVIDENCE_491a'
        selection = self.session / 'allot' / 'other-block' / 'selection.json'
        selection.parent.mkdir(parents=True)
        selection.write_text(json.dumps({'selection_basis': {'evidence': [private_evidence]}}),
                             encoding='utf-8')
        old_action = 'OLD_PER_LINE_PLAN_USE_MEDIUM'
        with self.own_work.open('a', encoding='utf-8') as stream:
            stream.write('\n\n## 旧计划\n' + old_action + '\n')
        summary = {'policy': {'revision': 2, 'default_effort': 'max'}, 'selections': [
            {'block_id': 'pending', 'model': 'gpt-6.1-sol', 'effort': 'max',
             'policy_revision': 2, 'current': True, 'observation': None},
            {'block_id': 'returned', 'model': 'gpt-6.2-sol', 'effort': 'max',
             'policy_revision': 1, 'current': False,
             'observation': {'actual_model': 'gpt-6.2-sol', 'actual_effort': 'high',
                             'matches_selection': False, 'superseded': True}}]}
        before = self.snapshot()
        with patch.object(codex_allot, 'context_summary', return_value=summary) as safe_summary:
            with patch.object(codex_allot, 'inspect', side_effect=AssertionError('full inspect is private')):
                packet = line_packet(self.session, 'M01')
        safe_summary.assert_called_once_with(self.session.resolve())
        self.assertIn(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), packet)
        self.assertIn('未观察的选择不能当作已经执行', packet)
        self.assertIn('本摘要不能证明Main已经切换', packet)
        self.assertIn('过时选择的历史观察不授权继续执行', packet)
        self.assertNotIn(private_work, packet)
        self.assertNotIn(private_evidence, packet)
        self.assertGreater(packet.index('## 当前Allot政策与原生执行概况'), packet.index(old_action))
        self.assertGreater(packet.index('当前用户纠正：'), packet.index('## 当前Allot政策与原生执行概况'))
        self.assertEqual(self.snapshot(), before)

    def test_policy_or_historical_selections_are_each_sufficient_for_recovery(self):
        for summary in (
                {'policy': {'revision': 1, 'default_effort': 'max'}, 'selections': []},
                {'policy': None, 'selections': [
                    {'block_id': 'legacy-block', 'model': 'selected-model', 'effort': 'high',
                     'policy_revision': None, 'current': False, 'observation': None}]}):
            with self.subTest(summary=summary):
                with patch.object(codex_allot, 'context_summary', return_value=summary):
                    packet = line_packet(self.session, 'M01')
                self.assertIn('## 当前Allot政策与原生执行概况', packet)
                self.assertIn(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), packet)


if __name__ == '__main__':
    unittest.main()
