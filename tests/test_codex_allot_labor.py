from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from runtime import codex_allot_labor
from runtime.codex_allot_labor import (load_feedback, record_feedback, resolve,
                                     scope_key, status)
from runtime.codex_session import create_session


ROOT = Path(__file__).resolve().parents[1]
PIN = '0.17.0@' + 'e' * 40
INPUT = {'message_id': 1, 'source_ref': 'constructed-user-1',
         'source_sha256': 'a' * 64, 'path': 'constructed-user.txt'}
SCOPE = {'scope_ref': 'constructed-pages-001-200-v1',
         'validation_ref': 'constructed-target-and-value-check-v1'}


class ScopedLaborFeedbackTests(unittest.TestCase):
    """Constructed file behavior only; these fixtures execute no model."""

    def setUp(self):
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='allot-labor-', dir=cache)
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        request = self.folder / 'request.txt'
        request.write_text('DIGR：只测试构造记录，未执行模型。', encoding='utf-8')
        self.root = self.folder / 'session'
        create_session(self.root, request=request, p_run=PIN,
                       visits_path=self.folder / 'visits.jsonl')
        self.request = request

    def selected(self, block_id='labor-first', scope=SCOPE, effort='low'):
        return {'P_run': PIN, 'block_id': block_id, 'input_ref': deepcopy(INPUT),
                'model': 'gpt-6.1-sol', 'effort': effort,
                'selection_basis': {'labor_scope': deepcopy(scope),
                                    'evidence': ['PRIVATE_RESEARCH_NOT_A_PUBLIC_FEEDBACK_FIELD']}}

    def feedback(self, detail='Constructed merged-cell counterexample', category='quality'):
        return {'category': category, 'evidence_ref': 'constructed-case:' + detail,
                'detail': detail}

    def record(self, block_id='labor-first', scope=SCOPE, **updates):
        return record_feedback(self.root, self.selected(block_id, scope),
                               self.feedback(**updates), INPUT)

    def solver(self, effort='max'):
        selection = self.selected('solver', scope=None, effort=effort)
        observation = {'block_id': 'solver', 'actual_model': selection['model'],
                       'actual_effort': effort, 'matches_selection': True,
                       'applied': True, 'source_ref': 'constructed-host-observation'}
        return selection, observation

    def disposition(self, *identities):
        return {'feedback_ids': list(identities),
                'evidence_ref': 'constructed-explicit-disposition',
                'detail': 'Constructed correction explicitly covers the listed feedback',
                'validation_ref': 'constructed-current-acceptance-evidence'}

    def test_scope_is_stable_across_mapping_order_and_work_blocks(self):
        first = scope_key(SCOPE)
        self.assertEqual(first, scope_key(dict(reversed(list(SCOPE.items())))))
        self.assertEqual(first, scope_key({**SCOPE, 'block_id': 'irrelevant'}))
        self.assertEqual(first, scope_key({**SCOPE, 'validation_ref': 'other-validator'}))
        self.assertNotEqual(first, scope_key({**SCOPE, 'scope_ref': 'genuinely-independent-scope'}))
        self.assertIsNone(scope_key(None))
        with self.assertRaises(ValueError):
            scope_key({'scope_ref': 'incomplete'})
        self.assertFalse(status(self.root, SCOPE)['blocked'])
        self.assertFalse((self.root / 'allot').exists())
        record = self.record()
        next_block_scope = self.selected('later-block')['selection_basis']['labor_scope']
        self.assertEqual(status(self.root, next_block_scope)['feedback_ids'], [record['feedback_id']])

    def test_failures_affect_only_the_relevant_scope_and_category(self):
        other = {**SCOPE, 'scope_ref': 'independent-file-renaming'}
        self.record('network-only', category='network')
        self.record('tool-only', category='tool')
        self.record('general-quality', scope=None)
        self.assertFalse(status(self.root, SCOPE)['blocked'])
        self.assertFalse(status(self.root, None)['blocked'])
        record = self.record('relevant-capability', category='capability')
        self.assertTrue(status(self.root, SCOPE)['blocked'])
        self.assertFalse(status(self.root, other)['blocked'])
        self.assertEqual(status(self.root, SCOPE)['feedback_ids'], [record['feedback_id']])

    def test_feedback_is_immutable_idempotent_and_contains_only_selected_public_fields(self):
        record = self.record()
        path = self.root / 'allot' / '_labor' / 'feedback' / (record['feedback_id'] + '.json')
        before = path.read_bytes()
        self.assertEqual(self.record(), record)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(load_feedback(self.root, record['feedback_id']), record)
        self.assertNotIn('PRIVATE_RESEARCH', before.decode('utf-8'))
        self.assertEqual(record['selection_input_ref'], INPUT)
        self.assertEqual(record['input_ref'], INPUT)

    def test_same_failure_after_unrelated_do_does_not_reopen_a_resolved_scope(self):
        record = self.record()
        solver, observation = self.solver()
        resolve(self.root, SCOPE, self.disposition(record['feedback_id']), solver, observation, INPUT)
        revision = status(self.root, SCOPE)['feedback_revision']
        later = {**INPUT, 'message_id': 2, 'source_ref': 'actual-later-DO'}
        repeated = record_feedback(self.root, self.selected(), self.feedback(), later)
        self.assertEqual(repeated, record)
        self.assertFalse(status(self.root, SCOPE)['blocked'])
        self.assertEqual(status(self.root, SCOPE)['feedback_revision'], revision)

    def test_explicit_resolution_requires_observed_high_effort_and_can_be_replayed(self):
        for effort in ('max', 'ultra'):
            with self.subTest(effort=effort):
                record = self.record('failure-' + effort, detail='case-' + effort)
                solver, observation = self.solver(effort)
                value = self.disposition(record['feedback_id'])
                resolved = resolve(self.root, SCOPE, value, solver, observation, INPUT)
                self.assertFalse(status(self.root, SCOPE)['blocked'])
                self.assertEqual(resolve(self.root, SCOPE, value, solver, observation, INPUT), resolved)
                self.assertEqual(resolved['solver_observation_source_ref'], observation['source_ref'])
                self.assertEqual(resolved['validation_ref'], value['validation_ref'])

    def test_resolution_clears_only_listed_feedback_and_never_later_failures(self):
        first = self.record('first', detail='first')
        second = self.record('second', detail='second')
        solver, observation = self.solver()
        value = self.disposition(first['feedback_id'])
        original = resolve(self.root, SCOPE, value, solver, observation, INPUT)
        self.assertEqual(status(self.root, SCOPE)['feedback_ids'], [second['feedback_id']])
        later = self.record('later', detail='new case after resolution')
        self.assertEqual(resolve(self.root, SCOPE, value, solver, observation, INPUT), original)
        self.assertEqual(set(status(self.root, SCOPE)['feedback_ids']),
                         {second['feedback_id'], later['feedback_id']})

    def test_invalid_solver_facts_and_missing_acceptance_cannot_clear_feedback(self):
        record = self.record()
        value = self.disposition(record['feedback_id'])
        solver, observation = self.solver()
        cases = []
        for field, wrong in (('actual_model', 'other-model'), ('actual_effort', 'low'),
                             ('block_id', 'different-block'), ('matches_selection', False),
                             ('source_ref', '')):
            changed = {**observation, field: wrong}
            cases.append((value, solver, changed))
        cases.append((value, {**solver, 'effort': 'high'}, {**observation, 'actual_effort': 'high'}))
        for missing in ('evidence_ref', 'detail', 'validation_ref'):
            changed = dict(value)
            del changed[missing]
            cases.append((changed, solver, observation))
        for changed_value, changed_solver, changed_observation in cases:
            with self.subTest(value=changed_value, solver=changed_solver, observation=changed_observation):
                with self.assertRaises(ValueError):
                    resolve(self.root, SCOPE, changed_value, changed_solver, changed_observation, INPUT)
                self.assertTrue(status(self.root, SCOPE)['blocked'])
        self.assertFalse((self.root / 'allot' / '_labor' / 'resolutions').exists())

    def test_unrelated_general_or_unknown_feedback_cannot_be_resolved_for_a_scope(self):
        relevant = self.record()
        other_scope = {**SCOPE, 'scope_ref': 'other-scope'}
        other = self.record('other', scope=other_scope)
        general = self.record('general', scope=None)
        network = self.record('network', category='network')
        solver, observation = self.solver()
        for identity in (other['feedback_id'], general['feedback_id'], network['feedback_id'], 'fb-' + '0' * 64):
            with self.subTest(identity=identity), self.assertRaises((ValueError, FileNotFoundError)):
                resolve(self.root, SCOPE, self.disposition(identity), solver, observation, INPUT)
        self.assertEqual(status(self.root, SCOPE)['feedback_ids'], [relevant['feedback_id']])
        value = self.disposition(relevant['feedback_id'], relevant['feedback_id'])
        with self.assertRaises(ValueError):
            resolve(self.root, SCOPE, value, solver, observation, INPUT)

    def test_copied_cross_task_or_modified_records_are_rejected(self):
        record = self.record()
        other = self.folder / 'second-task'
        create_session(other, request=self.request, p_run=PIN,
                       visits_path=self.folder / 'other-visits.jsonl')
        path = Path('allot') / '_labor' / 'feedback' / (record['feedback_id'] + '.json')
        (other / path).parent.mkdir(parents=True)
        shutil.copyfile(self.root / path, other / path)
        with self.assertRaisesRegex(ValueError, 'different task'):
            load_feedback(other, record['feedback_id'])
        modified = json.loads((self.root / path).read_text(encoding='utf-8'))
        modified['feedback']['detail'] = 'changed after publication'
        (self.root / path).write_text(json.dumps(modified), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'identity or contents changed'):
            status(self.root, SCOPE)
        for unsafe in ('../feedback', 'fb-' + 'a' * 63, 'not-an-id'):
            with self.assertRaises(ValueError):
                load_feedback(self.root, unsafe)

    def test_concurrent_identical_recording_publishes_one_complete_event(self):
        with ThreadPoolExecutor(max_workers=4) as workers:
            records = list(workers.map(lambda _: self.record(), range(12)))
        self.assertTrue(all(record == records[0] for record in records))
        folder = self.root / 'allot' / '_labor' / 'feedback'
        self.assertEqual(len(list(folder.glob('fb-*.json'))), 1)
        self.assertEqual(list(folder.glob('.pending-*')), [])
        self.assertEqual(status(self.root, SCOPE)['feedback_ids'], [records[0]['feedback_id']])

    @unittest.skipUnless(os.name == 'nt', 'Win32 path namespace regression')
    def test_equivalent_windows_resolve_namespaces_preserve_containment(self):
        root = self.root.resolve()
        plain = root / 'allot' / '_labor' / 'feedback'
        extended = Path('\\\\?\\' + str(plain))
        with patch.object(Path, 'resolve', return_value=extended):
            self.assertEqual(codex_allot_labor._directory(root, 'feedback'), extended)
        with patch.object(Path, 'resolve', return_value=plain):
            self.assertEqual(codex_allot_labor._directory(Path('\\\\?\\' + str(root)), 'feedback'), plain)
        unc_root = Path(r'\\server\share\task')
        unc_child = Path(r'\\?\UNC\server\share\task\allot\_labor\feedback')
        with patch.object(Path, 'resolve', return_value=unc_child):
            self.assertEqual(codex_allot_labor._directory(unc_root, 'feedback'), unc_child)
        # The same namespace normalization must not permit a sibling task or
        # an unrelated device namespace to pass the original safety boundary.
        outside = Path('\\\\?\\' + str(root.parent / 'other-task' / 'feedback'))
        for unsafe in (outside, Path(r'\\?\GLOBALROOT\Device\other\feedback')):
            with self.subTest(path=str(unsafe)), patch.object(Path, 'resolve', return_value=unsafe):
                with self.assertRaisesRegex(ValueError, 'within the current task'):
                    codex_allot_labor._directory(root, 'feedback')


if __name__ == '__main__':
    unittest.main()
