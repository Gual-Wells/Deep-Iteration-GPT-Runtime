import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestAuthorityContaminationScan(unittest.TestCase):
    def test_local_router_has_transport_not_execution_semantics(self):
        text=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').read_text(encoding='utf-8')
        for x in ('只去掉开头空白','Gual-Wells/Deep-Iteration-GPT-Runtime','`stable` branch 的当前 HEAD','/branches/stable','/git/ref/heads/stable','manifest.json','VERSION','startup_slice','没有尝试本身不是路由失败'):self.assertIn(x,text)
        for x in ('B=0','b=0','L(1)','V(o)','Formal Active','P_target','monotonic','LiveDIGRRun','N=2','R=1','digr.preflight','DELIVERED'):self.assertNotIn(x,text)
    def test_clock_and_surface_are_repository_semantics(self):
        start=(ROOT/'entry/STARTUP.md').read_text(encoding='utf-8');router=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').read_text(encoding='utf-8');self.assertIn('Run Genesis',start);self.assertIn('monotonic',start);self.assertNotIn('monotonic',router.lower());self.assertNotIn('Run Genesis',router)
    def test_context_can_feed_u0_not_protocol(self):
        t=(ROOT/'core/12_PROTOCOL_AUTHORITY_AND_SELF_HOSTING.md').read_text(encoding='utf-8');self.assertIn('Context !-> ProtocolSemantics',t);self.assertIn('U0/evidence',t)
    def test_target_cannot_rebind_current_run(self):
        t=(ROOT/'bootstrap/BOOTSTRAP.md').read_text(encoding='utf-8');self.assertIn('P_run',t);self.assertIn('P_target',t);self.assertIn('cannot reconstruct',t);self.assertIn('rebind `P_run`',t)
if __name__=='__main__':unittest.main()
