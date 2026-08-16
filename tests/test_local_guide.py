import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestLocalGuide(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.t=(ROOT/'docs/LOCAL_PERSONALIZATION_GUIDE.md').read_text(encoding='utf-8')
    def test_reliable_router(self):
        for x in ('router','stable','manifest.json','bootstrap_entry','legacy','semantic authority'):
            self.assertIn(x,self.t)
    def test_router_does_not_define_protocol(self):
        self.assertIn('must not define invocation validity/help/parameters/defaults, clock behavior',self.t)
        self.assertIn('Route failure',self.t)
    def test_legacy_3_cleanliness(self):
        self.assertIn('current legacy 3.0',self.t)
        self.assertIn('without importing 4.1 semantics',self.t)
if __name__=='__main__': unittest.main()
