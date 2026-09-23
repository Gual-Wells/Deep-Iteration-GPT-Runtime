import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestImplementationNotes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.t=(ROOT/'docs/IMPLEMENTATION_NOTES.md').read_text()
    def test_contracted_normal_path(self):
        for x in ('7','package verifier','ordinary resume','journal reindex','unindexed rebuildable caches','compact lifecycle'):
            self.assertIn(x,self.t)
    def test_old_safety_not_removed(self):
        for x in ('Full recovery','full workspace audit','granular D revisioning'):
            self.assertIn(x,self.t)
if __name__=='__main__':unittest.main()
