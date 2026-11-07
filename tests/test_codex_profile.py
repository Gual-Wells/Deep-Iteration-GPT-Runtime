from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from runtime.codex_profile import (
    ActiveContext, CAPABILITY_NAMES, decide_boundary, capability_report,
    instruction_text, verify_distribution, depth_preferences,
)

ROOT = Path(__file__).resolve().parents[1]


class CodexBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.active = ActiveContext('turn-1', 'DEEP')

    def test_new_ordinary_turn_does_not_inherit_deep(self):
        result = decide_boundary('NEW_TURN', '继续整理文件', active=self.active)
        self.assertEqual((result.mode, result.action), ('LIGHT', 'HANDLE_ORDINARY_TASK'))
        self.assertFalse(result.preserve_task)

    def test_steer_preserves_task_and_mode(self):
        result = decide_boundary(
            'STEER', '不用适配手机，保留原样式', active=self.active,
            expected_turn_id='turn-1',
        )
        self.assertEqual((result.mode, result.action), ('DEEP', 'CONTINUE'))
        self.assertTrue(result.preserve_task)
        self.assertEqual(result.continuation_of, 'turn-1')

    def test_changed_goal_requires_realign_not_silent_mutation(self):
        result = decide_boundary(
            'STEER', '改做另一个任务', active=self.active,
            expected_turn_id='turn-1', goal_changed=True,
        )
        self.assertEqual(result.action, 'REALIGN_GOAL')
        self.assertFalse(result.preserve_task)

    def test_steer_rejects_stale_or_missing_turn(self):
        for active, expected in ((None, 'turn-1'), (self.active, None), (self.active, 'old')):
            with self.subTest(active=active, expected=expected), self.assertRaises(ValueError):
                decide_boundary('STEER', '补充', active=active, expected_turn_id=expected)

    def test_every_candidate_requires_routing_not_premature_execution(self):
        messages = ('\u3000 DIGR/help', 'DIGR是什么？', 'DIGR：任务', '深度迭代：任务')
        for message in messages:
            with self.subTest(message=message):
                result = decide_boundary('NEW_TURN', message)
                self.assertTrue(result.route_required)
                self.assertEqual(result.mode, 'ROUTE_PENDING')
                self.assertEqual(result.action, 'ACQUIRE_LIVE_PIN_FIRST')
        for message in ('digr：任务', 'Digr：任务', '请用DIGR处理'):
            self.assertFalse(decide_boundary('NEW_TURN', message).route_required)

    def test_prefixed_steer_still_routes_without_replacing_current_task(self):
        result = decide_boundary(
            'STEER', 'DIGR：补充一个要求', active=self.active, expected_turn_id='turn-1',
        )
        self.assertTrue(result.route_required)
        self.assertTrue(result.preserve_task)
        self.assertEqual(result.after_route, 'CONTINUE')

    def test_control_events_do_not_start_new_runs(self):
        restored = decide_boundary('COMPACTION', active=self.active)
        self.assertEqual(restored.action, 'RESTORE_REAL_STATE')
        self.assertEqual(restored.continuation_of, 'turn-1')
        stopped = decide_boundary('INTERRUPT', active=self.active)
        self.assertEqual(stopped.action, 'STOP')
        self.assertTrue(stopped.preserve_task)
        for event in ('COMPACTION', 'INTERRUPT'):
            with self.assertRaises(ValueError):
                decide_boundary(event, 'a new user message', active=self.active)

    def test_availability_flags_cannot_mint_canonical_proof(self):
        report = capability_report(dict.fromkeys(CAPABILITY_NAMES, 'AVAILABLE'))
        self.assertEqual(report['execution_mode'], 'MODEL_NATIVE')
        self.assertEqual(report['attestation_level'], 'NONE')
        self.assertEqual(capability_report({})['capabilities']['monotonic_clock'], 'UNKNOWN')
        with self.assertRaises(ValueError):
            capability_report({'shell': True})


class CodexDistributionTests(unittest.TestCase):
    def test_packaged_profile_and_light_export(self):
        report = verify_distribution(ROOT)
        self.assertFalse(report['live_repository_acquisition'])
        self.assertFalse(report['run_started'])
        self.assertFalse(report['global_install_performed'])
        self.assertEqual(
            instruction_text(ROOT, 'light'),
            (ROOT / 'codex/AGENTS.light.md').read_text(encoding='utf-8'),
        )

    def test_default_depth_is_the_user_selected_high_investment_policy(self):
        preference = depth_preferences(ROOT)
        self.assertEqual(preference['implicit_deep'], {'N': 12, 'R': 4, 'D': 3, 'V': 3, 'L': 3})
        self.assertEqual(preference['unit_semantics'], 'codex/PARAMETERS.md')
        self.assertTrue(preference['complex_tasks_raise_investment'])
        self.assertEqual(preference['isolation_mode'], 'L3_ONLY')
        self.assertFalse(preference['low_isolation_fallback'])
        self.assertEqual(preference['progress_stream'], 'USER_COMMENTARY_PER_UNIT')

    def test_changed_instruction_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(ROOT / 'codex', root / 'codex')
            with (root / 'codex/PROTOCOL.md').open('a', encoding='utf-8') as f:
                f.write('\nchanged\n')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                verify_distribution(root)

    def test_incomplete_hash_set_or_version_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(ROOT / 'codex', root / 'codex')
            path = root / 'codex/manifest.json'
            manifest = json.loads(path.read_text(encoding='utf-8'))
            manifest['file_sha256'].pop('codex/STARTUP.md')
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'hash set'):
                verify_distribution(root)
            (root / 'codex/VERSION').write_text('different', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                verify_distribution(root)

    def test_cli_check_boundary_and_invalid_input(self):
        cli = [sys.executable, '-B', str(ROOT / 'tools/codex_profile.py')]
        result = subprocess.run(cli + ['check'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['run_started'])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'event.json'
            path.write_text(json.dumps({'event': 'NEW_TURN', 'message': 'DIGR/help'}), encoding='utf-8')
            result = subprocess.run(cli + ['boundary', '--input', str(path)], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)['route_required'])
            path.write_text('[]', encoding='utf-8')
            result = subprocess.run(cli + ['boundary', '--input', str(path)], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('Traceback', result.stderr)

    def test_candidate_does_not_modify_stable_protocol_identity(self):
        manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '5.0.0-alpha.5')
        self.assertEqual(manifest['entrypoint'], 'entry/DEEP_ITERATION_ENTRY.md')


if __name__ == '__main__':
    unittest.main()
