import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt'
F=ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FREE_GO.txt'
FULL=ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FULL.txt'
class TestPersonalization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.text=P.read_text();cls.full=FULL.read_text()
    def test_plus_capacity_and_no_free_go_copy(self):
        self.assertLessEqual(len(self.text),5000);self.assertGreater(len(self.text),1500);self.assertFalse(F.exists())
    def test_route_transport_and_firewall(self):
        for x in ('精确大写 ASCII `DIGR`','【任务工作防火墙】','Gual-Wells/Deep-Iteration-GPT-Runtime','/branches/stable','/git/ref/heads/stable','manifest.json','VERSION','bootstrap_index','startup_slice','GitHub Contents API','base64 `content`','NATIVE','EXECUTING'):
            self.assertIn(x,self.text)
    def test_package_boundary_is_contracted(self):
        for x in ('package-level attestation verifier','semantic equivalence ≠ implementation identity','不得把已经声明的整包验证重新展开成逐 helper'):
            self.assertIn(x,self.text)
    def test_no_versioned_semantics_copied(self):
        for x in ('B=0','B=1','D=0','Formal Active','LiveDIGRRun'):self.assertNotIn(x,self.text)
    def test_full_reference_is_version_neutral(self):
        for x in ('Pre-task execution firewall','Mutable-ref provenance','Immutable content transport','Transparent machine index','package-level implementation delivery','Surface handoff','Authority and failure'):self.assertIn(x,self.full)
if __name__=='__main__':unittest.main()
