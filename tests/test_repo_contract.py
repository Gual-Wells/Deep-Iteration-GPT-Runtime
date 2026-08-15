import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class TestRepoContract(unittest.TestCase):
    def test_version(self):
        self.assertEqual((ROOT / "VERSION").read_text().strip(), "3.0.0")
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "3.0.0")
        self.assertEqual(manifest["protocol"], "digr-v3.0")

    def test_active_core_has_no_legacy_semantic_t(self):
        active = [
            ROOT / "README.md",
            ROOT / "manifest.json",
            ROOT / "bootstrap/LOCAL_FALLBACK_CORE.md",
            *sorted((ROOT / "core").glob("*.md")),
        ]
        banned = [
            "not_a_wall_clock_deadline",
            "reference_model_effective_task_scale",
            "t_is_not_a_hard_wall_clock_requirement",
        ]
        text = "\n".join(p.read_text(encoding="utf-8") for p in active)
        for term in banned:
            self.assertNotIn(term, text)

    def test_result_sovereignty(self):
        text = (ROOT / "core/00_RESULT_SOVEREIGNTY.md").read_text(encoding="utf-8")
        self.assertIn("Result Sovereignty", text)
        self.assertIn("任务结果", text)

    def test_est_not_algorithm(self):
        text = (ROOT / "core/30_EVOLUTION_STATE_MEMORY.md").read_text(encoding="utf-8")
        self.assertIn("不是搜索算法", text)
        for token in ("BFS", "DFS", "MCTS"):
            self.assertIn(token, text)

    def test_source_semantics(self):
        text = (ROOT / "core/50_SOURCE_EVOLUTION.md").read_text(encoding="utf-8")
        self.assertIn("每个 `Sᵢ`", text)
        self.assertIn("aggregate", text)
        self.assertIn("并集", text)
        self.assertIn("绝不关闭", text)

    def test_reentry_and_abg(self):
        text = (ROOT / "core/70_REENTRY_BREAKTHROUGH.md").read_text(encoding="utf-8")
        self.assertIn("全流程", text)
        self.assertIn("缺省性驳斥", text)
        self.assertIn("Anti-Bureaucracy Guard", text)
        self.assertIn("不绕过", text)

    def test_help_and_nonsticky(self):
        self.assertTrue((ROOT / "entry/HELP.md").exists())
        text = (ROOT / "core/00_RESULT_SOVEREIGNTY.md").read_text(encoding="utf-8")
        self.assertIn("Non-sticky", text)

    def test_minimal_proof(self):
        text = (ROOT / "core/80_STOP_AND_PROOF.md").read_text(encoding="utf-8")
        self.assertIn("轻量证明", text)
        self.assertIn("不返回", text)

    def test_no_runtime_semantic_parser(self):
        self.assertFalse((ROOT / "runtime/reference_parser.py").exists())

if __name__ == "__main__":
    unittest.main()
