import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestLocalGuide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.t=(ROOT/'docs/LOCAL_PERSONALIZATION_GUIDE.md').read_text()
    def test_router_is_exact_uppercase_and_thin(self):
        for x in ('exact-uppercase `DIGR`','exact `深度迭代`','version-neutral','pins `stable`','manifest/VERSION','startup slice','NATIVE','Local text must never copy N/T/R/S/D/L/time/proof semantics'):self.assertIn(x,self.t)
    def test_broad_capture_is_not_takeover(self):self.assertIn('Broad capture is not takeover',self.t)
if __name__=='__main__':unittest.main()
