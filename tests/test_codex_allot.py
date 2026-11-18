import unittest
from runtime.codex_allot import select


CATALOGUE = {'data': [{'model': 'selected-model', 'supportedReasoningEfforts':
                       [{'reasoningEffort': x} for x in ['low', 'medium', 'high', 'xhigh', 'max']]}]}


class NativeAllotTests(unittest.TestCase):
    def block(self, **values):
        return {'model': 'selected-model', 'kind': 'maintenance', 'evidence': ['fixed API with bounded repair'], **values}

    def test_bounded_work_and_difficult_reentry(self):
        self.assertEqual(select(self.block(), CATALOGUE)['effort'], 'medium')
        self.assertEqual(select(self.block(kind='routine', fully_specified=True), CATALOGUE)['effort'], 'low')
        self.assertEqual(select(self.block(kind='architecture', unresolved=['conflicting invariant'], failed_efforts=['high']), CATALOGUE)['effort'], 'xhigh')
        self.assertEqual(select(self.block(kind='breakthrough', unresolved=['representation wrong'], failed_efforts=['high', 'xhigh'], high_value=True), CATALOGUE)['effort'], 'max')

    def test_repair_failure_is_not_automatic_escalation(self):
        self.assertEqual(select(self.block(failed_efforts=['high']), CATALOGUE)['effort'], 'medium')
        with self.assertRaises(ValueError):
            select(self.block(kind='routine'), CATALOGUE)

    def test_explicit_effort_and_no_silent_downshift(self):
        self.assertEqual(select(self.block(requested_effort='max'), CATALOGUE)['effort'], 'max')
        self.assertEqual(select(self.block(current_effort='high'), CATALOGUE)['effort'], 'high')
        self.assertEqual(select(self.block(current_effort='high', allow_downshift=True), CATALOGUE)['effort'], 'medium')
        self.assertFalse(select(self.block(), CATALOGUE)['applied'])

    def test_capability_mismatch_never_changes_requested_model(self):
        with self.assertRaises(ValueError):
            select(self.block(model='unavailable'), CATALOGUE)
        with self.assertRaises(ValueError):
            select(self.block(requested_effort='ultra'), CATALOGUE)
        with self.assertRaises(ValueError):
            select(self.block(evidence=[]), CATALOGUE)


if __name__ == '__main__':
    unittest.main()
