import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt'
F=ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FREE_GO.txt'
FULL=ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FULL.txt'

class TestPersonalization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pb=P.read_bytes(); cls.fb=F.read_bytes()
        cls.text=cls.pb.decode(); cls.free=cls.fb.decode(); cls.full=FULL.read_text(encoding='utf-8')

    def test_primary_and_free_are_byte_identical(self):
        self.assertEqual(self.pb,self.fb)

    def test_compact_router(self):
        self.assertLessEqual(len(self.text),1500)
        self.assertLessEqual(len(self.free),1500)

    def test_router_contract(self):
        for x in ('候选路由键','Gual-Wells/Deep-Iteration-GPT-Runtime','stable','40','manifest.json','bootstrap_entry','entrypoint','core','权威委托'):
            self.assertIn(x,self.text)
        self.assertIn('路由失败',self.text)

    def test_no_versioned_protocol_copy(self):
        forbidden=('DIGR_EXECUTION_GATE','monotonic','clock','P_target','B=0','b=0','L(1)','Mature Gambit','Decree + Execution','DIGR（N/实际N','Formal Active','proof')
        for token in forbidden:
            self.assertNotIn(token,self.text)
            self.assertNotIn(token,self.free)

    def test_full_explains_boundary_without_becoming_protocol_copy(self):
        self.assertIn('Expanded Routing Reference',self.full)
        self.assertIn('不属于本地层',self.full)
        self.assertIn('Legacy discovery',self.full)
        self.assertNotIn('B=0',self.full)
        self.assertNotIn('DIGR（N/实际N',self.full)

if __name__=='__main__': unittest.main()
