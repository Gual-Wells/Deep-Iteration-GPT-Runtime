import unittest
from runtime.execution_integrity import (
    ExecutionCommitment, ExecutionAttemptReceipt, interrogate, attempt_matches_commitment,
)

BLOB='a'*40

class TestExecutionIntegrity(unittest.TestCase):
    def c(self, **changes):
        base=dict(
            schema_version=1, component_path='runtime/task_startup.py', component_blob_sha=BLOB,
            operation='start_task', executor='python-container', direct_execution=True,
            rejects_substitution=True, rejects_manual_result=True, reeducation_round=0,
        )
        base.update(changes)
        return ExecutionCommitment(**base)

    def test_complete_commitment_accepts_and_attempt_binds(self):
        c=self.c()
        self.assertEqual(interrogate(c).disposition,'ACCEPT')
        a=ExecutionAttemptReceipt.from_commitment(c,status='SUCCEEDED')
        self.assertTrue(attempt_matches_commitment(c,a))

    def test_substitution_choice_reeducates_then_aborts(self):
        self.assertEqual(interrogate(self.c(rejects_substitution=False)).disposition,'REEDUCATE')
        self.assertEqual(interrogate(self.c(rejects_substitution=False,reeducation_round=1)).disposition,'REEDUCATE')
        self.assertEqual(interrogate(self.c(rejects_substitution=False,reeducation_round=2)).disposition,'ABORT')

    def test_manual_result_is_not_execution(self):
        self.assertEqual(interrogate(self.c(rejects_manual_result=False)).disposition,'REEDUCATE')

    def test_failed_attempt_requires_reason(self):
        c=self.c()
        with self.assertRaises((TypeError,ValueError)):
            ExecutionAttemptReceipt.from_commitment(c,status='FAILED')
        a=ExecutionAttemptReceipt.from_commitment(c,status='FAILED',failure_reason='executor unavailable')
        self.assertTrue(attempt_matches_commitment(c,a))

    def test_unaccepted_commitment_cannot_emit_attempt(self):
        with self.assertRaises(ValueError):
            ExecutionAttemptReceipt.from_commitment(self.c(direct_execution=False),status='FAILED',failure_reason='x')

if __name__=='__main__': unittest.main()
