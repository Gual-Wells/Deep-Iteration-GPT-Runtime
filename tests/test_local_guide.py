import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestLocalGuide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.t=(ROOT/'docs/LOCAL_PERSONALIZATION_GUIDE.md').read_text(encoding='utf-8')
    def test_router_is_exact_uppercase_and_thin(self):
        for x in ('version-neutral transport shell','exact uppercase ASCII `DIGR`','exact `深度迭代`','broadly captured','branch HEAD','manifest.json','VERSION','startup_slice'):self.assertIn(x,self.t)
    def test_semantics_begin_in_pinned_startup(self):
        for x in ('must not inspect help, task, parameters, parentheses or punctuation','must not return NATIVE/INVALID itself','Pinned STARTUP','NATIVE returns it','No attempt is not route-failure evidence'):self.assertIn(x,self.t)
if __name__=='__main__':unittest.main()
