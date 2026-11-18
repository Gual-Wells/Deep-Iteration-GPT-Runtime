from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from runtime import codex_allot as allot
from runtime.codex_foundation import BRIEF_FIELDS, confirm_foundation, propose_foundation
from runtime.codex_lifecycle import load_lifecycle
from runtime.codex_session import create_line, create_session, line_packet


V017_PIN = '0.17.0@82811c0b36cedfad0aea87b442e57c20f7f814a3'
V018_PIN = '0.18.0@' + 'a' * 40
SOL_MODELS = ('gpt-6.1-sol', 'gpt-6.2-sol')
V017_POLICY = {
    'profile': 'sol-max-feedback', 'primary_models': list(SOL_MODELS),
    'default_effort': 'max', 'speed': 'standard',
    'downshift': 'only explicitly selected, large, fully specified, non-intellectual controlled repetitive labor',
    'escalation': 'concrete Max capability gap or substantive task failure feedback; no fixed stronger-model seats',
}


def policy_hash(record):
    raw = json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')
    return sha256(raw).hexdigest()


def catalogue(models=SOL_MODELS, effort='max'):
    return {'models': [{'slug': model, 'supported_reasoning_levels': [{'effort': effort}]}
                       for model in models]}


class AllotPrimaryModelTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix='allot-primary-model-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.request = self.base / 'request.txt'
        self.request.write_text('DIGR：按规格测试 Allot。', encoding='utf-8')

    def task(self, name, pin=V018_PIN):
        root = self.base / name
        create_session(root, request=self.request, p_run=pin)
        proposal = propose_foundation(root, {
            'brief': {key: 'Synthetic Allot policy fixture' for key in BRIEF_FIELDS}, 'questions': [],
        }, reason='Synthetic Allot policy fixture')
        source = load_lifecycle(root)['current_message']['source']
        confirm_foundation(root, revision=proposal['revision'], user_text=source['text'],
                           source=source['source_ref'])
        return root

    def plan(self, root, block_id, capabilities=None, **fields):
        block = {'block_id': block_id, 'kind': 'architecture', 'evidence': ['Synthetic work'], **fields}
        return allot.plan(root, block, catalogue() if capabilities is None else capabilities,
                          catalogue_ref='test host catalogue')

    def test_new_pin_uses_one_fixed_default_and_preserves_explicit_other_sol(self):
        for model, other in zip(SOL_MODELS, reversed(SOL_MODELS)):
            with self.subTest(model=model), patch.object(allot, 'CANDIDATE_DEFAULT_PRIMARY_MODEL', model):
                root = self.task(model)
                create_line(root, 'M01', parameters={'N': 2, 'T': 0, 'R': 1, 'B': 0,
                            'S': {'n': 0, 't': 0, 'r': 0, 'b': 0}, 'D': 0, 'V': 0, 'L': 3})
                implicit = self.plan(root, 'implicit')
                explicit = self.plan(root, 'explicit', model=other)
                self.assertEqual(self.plan(root, 'implicit'), implicit)
                inspection = allot.inspect(root)
                self.assertEqual(inspection['policy']['policy']['default_primary_model'], model)
                self.assertEqual(inspection['policy'], allot.current_policy(root))
                for planned, target in ((implicit, model), (explicit, other)):
                    ready = allot.ready(root, planned['block_id'], catalogue())
                    self.assertEqual(ready['host_payload'], {'model': target, 'reasoning_effort': 'max',
                                                            'fork_turns': 'none'})
                    self.assertEqual(planned['proposed_host_payload'], ready['host_payload'])
                    self.assertEqual(ready['policy_sha256'], policy_hash(inspection['policy']))
                packet = line_packet(root, 'M01')
                recovery, _ = json.JSONDecoder().raw_decode(
                    packet.split('## 当前Allot政策与原生执行概况', 1)[1].lstrip())
                self.assertEqual(recovery['policy']['default_primary_model'], model)
                self.assertEqual(recovery['unobserved_selections'], 2)
                self.assertTrue(all(row['current'] for row in recovery['selections']))

    def test_new_pin_rejects_null_and_does_not_substitute_host_model_or_effort(self):
        for model, other in zip(SOL_MODELS, reversed(SOL_MODELS)):
            with self.subTest(model=model), patch.object(allot, 'CANDIDATE_DEFAULT_PRIMARY_MODEL', model):
                root = self.task(model)
                only_other = catalogue([other])
                weaker_default = {'models': catalogue([model], 'high')['models'] + only_other['models']}
                with self.assertRaisesRegex(ValueError, 'requested model is absent'):
                    self.plan(root, 'null', model=None)
                with self.assertRaisesRegex(ValueError, 'pinned default_primary_model'):
                    self.plan(root, 'missing', only_other)
                with self.assertRaisesRegex(ValueError, 'selected effort is unavailable'):
                    self.plan(root, 'wrong-effort', weaker_default)
                self.plan(root, 'implicit')
                for capabilities in (only_other, weaker_default):
                    with self.assertRaisesRegex(ValueError, 'model/effort is no longer available'):
                        allot.ready(root, 'implicit', capabilities)
                self.plan(root, 'explicit', only_other, model=other)
                self.assertEqual(allot.ready(root, 'explicit', only_other)['host_payload']['model'], other)

    def test_source_bound_revision_keeps_new_default_and_supersedes_old_plan(self):
        root = self.task('revised')
        initial = self.plan(root, 'before-revision')
        source_ref = load_lifecycle(root)['current_message']['source']['source_ref']
        choice = {'profile': 'sol-max-feedback', 'source_ref': source_ref, 'reason': 'Synthetic user policy choice'}
        saved = allot.set_policy(root, choice)
        self.assertEqual(saved['revision'], 1)
        self.assertEqual(saved['policy']['default_primary_model'], initial['model'])
        self.assertEqual(allot.set_policy(root, choice), saved)
        self.assertEqual(allot.inspect(root)['policy'], saved)
        with self.assertRaisesRegex(ValueError, 'selection was superseded'):
            allot.ready(root, 'before-revision', catalogue())
        revised = self.plan(root, 'after-revision')
        self.assertEqual(revised['policy_sha256'], policy_hash(saved))
        self.assertEqual(allot.ready(root, 'after-revision', catalogue())['host_payload']['model'], initial['model'])
        policy_file = root / 'allot' / 'policy.json'
        policy_file.write_text(json.dumps({**saved, 'policy': V017_POLICY}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Allot policy does not match'):
            allot.inspect(root)

    def test_v017_implicit_and_persisted_policy_records_keep_original_shape_and_hash(self):
        for revision in (0, 1):
            with self.subTest(revision=revision):
                root = self.task(f'previous-{revision}', V017_PIN)
                expected = {'format': 'digr-native-allot-policy-1', 'P_run': V017_PIN,
                            'revision': revision, 'policy': V017_POLICY, 'source': 'PINNED_PROFILE_DEFAULT'}
                policy_file = root / 'allot' / 'policy.json'
                if revision:
                    source_ref = load_lifecycle(root)['current_message']['source']['source_ref']
                    expected.update(source=source_ref, reason='Earlier explicit user policy choice',
                                    created_at='2026-11-17T00:00:00+00:00',
                                    implementation={'version': '0.17.0', 'pin': V017_PIN})
                    policy_file.parent.mkdir()
                    policy_file.write_text(json.dumps(expected), encoding='utf-8')
                before = policy_file.read_bytes() if revision else None
                self.assertEqual(allot.current_policy(root), expected)
                with self.assertRaisesRegex(ValueError, 'requested model is absent'):
                    self.plan(root, 'previous-implicit')
                planned = self.plan(root, 'previous-model', model=SOL_MODELS[0])
                self.assertEqual(planned['policy_sha256'], policy_hash(expected))
                self.assertEqual(allot.ready(root, 'previous-model', catalogue())['policy_sha256'], policy_hash(expected))
                self.assertNotIn('policy', allot.inspect(root))
                self.assertNotIn('default_primary_model', allot.context_summary(root)['policy'])
                self.assertEqual(policy_file.read_bytes() if policy_file.exists() else None, before)


if __name__ == '__main__':
    unittest.main()
