import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt").read_text(encoding="utf-8")

class TestPersonalizationContract(unittest.TestCase):
    def test_help(self):
        self.assertIn("深度迭代/help", TEXT)
    def test_non_sticky(self):
        self.assertIn("绝不自动继承", TEXT)
    def test_native_semantics(self):
        self.assertIn("ChatGPT 原生理解", TEXT)
        self.assertIn("正则", TEXT)
    def test_result_sovereignty(self):
        self.assertIn("唯一主体核心对象", TEXT)
    def test_est_memory_not_algorithm(self):
        self.assertIn("不是 BFS/DFS/MCTS", TEXT)
    def test_multi_s(self):
        self.assertIn("每个实际 Sᵢ", TEXT)
        self.assertIn("所有 S 外源研究活动时间区间合并", TEXT)
    def test_reentry_abg(self):
        self.assertIn("缺省性驳斥", TEXT)
        self.assertIn("Anti-Bureaucracy Guard", TEXT)
    def test_hard_clock(self):
        self.assertIn("monotonic clock", TEXT)
        self.assertIn("fail closed", TEXT)
    def test_minimal_proof(self):
        self.assertIn("轻量执行证明", TEXT)

if __name__ == "__main__":
    unittest.main()
