import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestImplementationNotes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.t=(ROOT/'docs/IMPLEMENTATION_NOTES.md').read_text(encoding='utf-8')
    def test_separation(self):
        for x in ('runtime/routing.py','runtime/repository_transport.py','runtime/invocation_surface.py','runtime/parameter_resolution.py','None of these chooses task strategy'):self.assertIn(x,self.t)
    def test_raw_events_replaced_by_thin_wrappers(self):self.assertIn('raw `.events.append()`',self.t);self.assertIn('Wrappers validate references, not intellectual quality',self.t)
    def test_state_chains(self):
        for x in ('Strategy/Candidate/EST/Source/D/Completion','revisioned','formal SOURCE intervals','source-activity','Isolation facts','isolation receipts'):self.assertIn(x,self.t)
    def test_recovery_distinguishes_integrity_from_time(self):self.assertIn('integrity alone is not time continuity',self.t)
if __name__=='__main__':unittest.main()
