import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestLocalGuide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.t=(ROOT/'docs/LOCAL_PERSONALIZATION_GUIDE.md').read_text()
    def test_router_is_plus_only_exact_and_version_neutral(self):
        for x in ('Plus','Free/Go compatibility is intentionally not maintained','exact-uppercase `DIGR`','exact `深度迭代`','version-neutral','Local text must never copy versioned task-parameter/time/stop/proof semantics'):self.assertIn(x,self.t)
    def test_task_work_firewall(self):
        for x in ('Pre-task execution firewall','Reading, understanding, quoting or summarizing startup is not execution','EXECUTING classification is not task-work readiness','must be actually performed'):self.assertIn(x,self.t)
    def test_transport_fallbacks(self):
        for x in ('new OAuth/connector','Contents API','JSON/base64 wrapper'):self.assertIn(x,self.t)
    def test_index_is_structural_not_semantic(self):
        for x in ('first structural lens','implemented helpers','truth sources','without defining versioned DIGR execution semantics'):self.assertIn(x,self.t)
if __name__=='__main__':unittest.main()
