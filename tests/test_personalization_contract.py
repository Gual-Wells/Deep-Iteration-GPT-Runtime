import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt'
F=ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FREE_GO.txt'
FULL=ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FULL.txt'

class TestPersonalization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pb=P.read_bytes();cls.text=cls.pb.decode();cls.full=FULL.read_text()

    def test_plus_only_capacity_and_no_free_go_copy(self):
        self.assertLessEqual(len(self.text),5000)
        self.assertGreater(len(self.text),1500)
        self.assertFalse(F.exists())

    def test_candidate_exact_uppercase_and_native_return(self):
        for x in ('精确大写 ASCII `DIGR`','`digr`、`Digr` 等不路由','宽捕获','NATIVE','原始消息完整交还普通 ChatGPT'):
            self.assertIn(x,self.text)

    def test_exact_repository_and_staged_navigation(self):
        for x in (
            'Gual-Wells/Deep-Iteration-GPT-Runtime',
            'https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime',
            '/git/ref/heads/stable','/branches/stable',
            'raw.githubusercontent.com/Gual-Wells/Deep-Iteration-GPT-Runtime/{SHA}/{PATH}',
            'manifest.json','VERSION','bootstrap_index','startup_slice',
            'execution bundle','entrypoint','core[]','完整 40 位 commit SHA',
            '同一 SHA','真实仓库获取','router defect'
        ):
            self.assertIn(x,self.text)

    def test_execution_firewall_blocks_previous_regression(self):
        for x in (
            '【任务工作防火墙】',
            '不得开始用户任务本身',
            '不等于执行 startup',
            'surface=EXECUTING',
            'task-work-ready',
            '禁止任务级分析、研究、编辑、回答或结果生成',
            '读取到 startup 指令不是完成执行',
            '看到 EXECUTING 标签也不是 task-work-ready'
        ):
            self.assertIn(x,self.text)

    def test_transport_fallbacks_restored(self):
        for x in ('GitHub OAuth/connector','GitHub Contents API','raw media','base64 `content`','wrapper JSON'):
            self.assertIn(x,self.text)

    def test_no_versioned_execution_copy(self):
        for token in ('monotonic','LiveDIGRRun','B=0','b=0','B=1','b=1','L(1)','Mature Gambit','Formal Active'):
            self.assertNotIn(token,self.text)

    def test_full_explains_transport_and_execution_boundary(self):
        for x in (
            'Expanded Routing / Transparency / Execution-Firewall Reference',
            'Task-work firewall','Reading startup is not executing startup',
            'Mutable-ref provenance','Immutable content transport',
            'Transparent machine index','Surface handoff','Authority and failure'
        ):
            self.assertIn(x,self.full)
        self.assertNotIn('B=0',self.full);self.assertNotIn('B=1',self.full)

if __name__=='__main__':unittest.main()
