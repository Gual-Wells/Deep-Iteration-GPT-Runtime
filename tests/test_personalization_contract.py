import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt';F=ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FREE_GO.txt';FULL=ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FULL.txt'
class TestPersonalization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.pb=P.read_bytes();cls.fb=F.read_bytes();cls.text=cls.pb.decode();cls.full=FULL.read_text()
    def test_primary_and_free_identical(self):self.assertEqual(self.pb,self.fb)
    def test_compact_router(self):self.assertLessEqual(len(self.text),1500)
    def test_candidate_exact_uppercase_and_native_return(self):
        for x in ('精确大写 ASCII `DIGR`','`digr`、`Digr` 等不路由','宽捕获','NATIVE','原始消息交还普通 ChatGPT'):self.assertIn(x,self.text)
    def test_exact_repository_and_staged_navigation(self):
        for x in ('Gual-Wells/Deep-Iteration-GPT-Runtime','https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime','/git/ref/heads/stable','/contents/{PATH}?ref={SHA}','manifest.json','VERSION','startup_slice','entrypoint','core[]','manifest.help','40 位 SHA','同一 SHA'):
            self.assertIn(x,self.text)
        self.assertIn('DIGR 路由失败：未取得仓库运行协议',self.text)
    def test_no_versioned_execution_copy(self):
        for token in ('monotonic','LiveDIGRRun','P_target','B=0','b=0','L(1)','Mature Gambit','Formal Active','proof'):
            self.assertNotIn(token,self.text)
    def test_full_explains_transport_boundary(self):
        for x in ('Expanded Routing Reference','Candidate response','Canonical locator and immutable pin','Staged navigation','Authority boundary and failure','NATIVE'):
            self.assertIn(x,self.full)
        self.assertNotIn('B=0',self.full)
if __name__=='__main__':unittest.main()
