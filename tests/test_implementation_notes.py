import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestImplementationNotes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.t=(ROOT/'docs/IMPLEMENTATION_NOTES.md').read_text()
    def test_pre_genesis_boundary(self):
        for x in ('execution bundle','before LiveDIGRRun.start creates Genesis','Post-Genesis protocol bind/abort paths are retired'):
            self.assertIn(x,self.t)
    def test_clock_epoch_recovery(self):
        for x in ('same-epoch continuity','EPOCH_ANCHOR','Cross-epoch time is uncredited'):
            self.assertIn(x,self.t)
    def test_hot_path_and_defaults(self):
        for x in ('run-brief is derived cache state','no longer rewrites synchronously','B/b return to 0','explicit B=1/b=1 remains strict'):
            self.assertIn(x,self.t)
    def test_safety_preserved(self):
        for x in ('Exact implementation identity','P_run/U0/contract','Source/R/D semantics','FINISH durability'):
            self.assertIn(x,self.t)
if __name__=='__main__':unittest.main()
