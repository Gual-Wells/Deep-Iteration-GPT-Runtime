import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestImplementationNotes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.t=(ROOT/'docs/IMPLEMENTATION_NOTES.md').read_text()
    def test_runtime_boundary(self):
        for x in ('lower bound','counted hard-verifiable intervals','SourceDisposition=WAIVED','Public L stays removed'):
            self.assertIn(x,self.t)
    def test_recovery_model(self):
        for x in ('single-slot write-intent','append-only journals','derived latest pointers','run-brief is a cache','FINISH is a durable commit point'):
            self.assertIn(x,self.t)
    def test_reentry_and_d(self):
        for x in ('Retained MAIN/source re-entry','persisted R/r history cannot move backward','D Result production','D_EXCLUSIVE'):
            self.assertIn(x,self.t)
    def test_release_and_inherited_integrity(self):
        for x in ('.git','exact pinned helpers','does not add another cognitive gate'):
            self.assertIn(x,self.t)
if __name__=='__main__':unittest.main()
