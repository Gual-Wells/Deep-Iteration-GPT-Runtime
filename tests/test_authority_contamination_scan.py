import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestAuthorityContaminationScan(unittest.TestCase):
    def test_local_router_has_transport_not_execution_semantics(self):
        text=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').read_text()
        for x in ('候选路由','Gual-Wells/Deep-Iteration-GPT-Runtime','/git/ref/heads/stable','/contents/{PATH}?ref={SHA}','manifest.json','VERSION','startup_slice','entrypoint','core','不得用聊天上下文'):self.assertIn(x,text)
        for x in ('B=0','b=0','L(1)','Mature Gambit','Formal Active','P_target','monotonic','LiveDIGRRun','proof'):self.assertNotIn(x,text)
    def test_clock_and_surface_are_repository_semantics(self):
        start=(ROOT/'entry/STARTUP.md').read_text();router=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').read_text();self.assertIn('Run Genesis',start);self.assertIn('monotonic',start);self.assertNotIn('monotonic',router.lower());self.assertNotIn('Run Genesis',router)
    def test_context_can_feed_u0_not_protocol(self):
        t=(ROOT/'core/12_PROTOCOL_AUTHORITY_AND_SELF_HOSTING.md').read_text();self.assertIn('Context !-> ProtocolSemantics',t);self.assertIn('U0/evidence',t)
    def test_target_cannot_rebind_current_run(self):
        t=(ROOT/'bootstrap/BOOTSTRAP.md').read_text();self.assertIn('P_run',t);self.assertIn('P_target',t);self.assertIn('cannot redefine DIGR semantics or rebind',t)
if __name__=='__main__':unittest.main()
