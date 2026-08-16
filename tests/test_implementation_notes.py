import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestImplementationNotes(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.t=(ROOT/'docs/IMPLEMENTATION_NOTES.md').read_text(encoding='utf-8')
    def test_routing_separation(self):
        for x in ('runtime/routing.py','manifest','legacy','no invocation/time/default/stop/proof logic','RouteReceipt'):
            self.assertIn(x,self.t)
    def test_handoff_and_nested_run_are_not_automatic_L2(self):
        for x in ('Default full-history handoff is not L2','Nested agent/tool runs can still share application context','L2 requires'):
            self.assertIn(x,self.t)
    def test_clock_and_readiness(self):
        for x in ('time.monotonic_ns()','Observed monotonic delta','hard-verifiable continuity','task-startup'):
            self.assertIn(x,self.t)
    def test_release_exports_canonical_router(self):
        self.assertIn('--personalization-output',self.t)
        self.assertIn('internal source bytes',self.t)
if __name__=='__main__': unittest.main()
