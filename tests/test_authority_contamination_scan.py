import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestAuthorityContaminationScan(unittest.TestCase):
    def test_local_router_has_transport_and_firewall_not_execution_semantics(self):
        text=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').read_text()
        for x in ('【候选路由】','【任务工作防火墙】','Gual-Wells/Deep-Iteration-GPT-Runtime','/git/ref/heads/stable','/branches/stable','raw.githubusercontent.com/Gual-Wells/Deep-Iteration-GPT-Runtime/{SHA}/{PATH}','manifest.json','VERSION','bootstrap_index','startup_slice','entrypoint','core[]','不得开始用户任务本身','不等于执行 startup','GitHub Contents API','base64 `content`','router defect'):self.assertIn(x,text)
        for x in ('B=0','b=0','B=1','b=1','L(1)','Mature Gambit','Formal Active','monotonic','LiveDIGRRun'):self.assertNotIn(x,text)
    def test_clock_and_surface_stay_repository_semantics(self):
        start=(ROOT/'entry/STARTUP.md').read_text();router=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').read_text()
        self.assertIn('Run Genesis',start);self.assertIn('monotonic',start)
        self.assertNotIn('monotonic',router.lower());self.assertNotIn('Run Genesis',router)
        self.assertIn('读取到 startup 指令不是完成执行',router);self.assertIn('实际实现',router)
    def test_transparent_index_is_pinned_structural_lens_and_not_execution(self):
        t=(ROOT/'bootstrap/INDEX.md').read_text()
        for x in ('Structure-closed, intelligence-open','not versioned execution semantics','deterministic_helpers[]','does **not** execute it','must not begin the user\'s task'):self.assertIn(x,t)
    def test_context_can_feed_u0_not_protocol(self):
        t=(ROOT/'core/12_PROTOCOL_AUTHORITY_AND_SELF_HOSTING.md').read_text();self.assertIn('Context !-> ProtocolSemantics',t);self.assertIn('U0/evidence',t)
    def test_target_cannot_rebind_current_run(self):
        t=(ROOT/'bootstrap/BOOTSTRAP.md').read_text();self.assertIn('P_run',t);self.assertIn('P_target',t);self.assertIn('cannot redefine current-run protocol semantics',t)
if __name__=='__main__':unittest.main()
