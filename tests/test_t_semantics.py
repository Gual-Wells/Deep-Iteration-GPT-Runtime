import json, unittest
from pathlib import Path
from runtime.reference_parser import parse_invocation
ROOT=Path(__file__).resolve().parents[1]

class TestTSemantics(unittest.TestCase):
    def test_raw_T_is_preserved_not_normalized(self):
        for raw in ["15min","30分钟","1h","2小时","约20分钟"]:
            x=parse_invocation(f"深度迭代（3，{raw}）：任务")
            self.assertTrue(x["enabled"])
            self.assertEqual(x["complexity_budget_raw"],raw)
    def test_parser_contains_no_time_tier_mapping(self):
        txt=(ROOT/'runtime/reference_parser.py').read_text(encoding='utf-8')
        for bad in ['Focused','Analytical','Extended Research','normalized_minutes','thinking_tokens','token_budget']:
            self.assertNotIn(bad,txt)
    def test_manifest_reference_model(self):
        m=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
        r=m['complexity_reference']
        self.assertEqual(r['model'],'GPT-5.6 Sol')
        self.assertEqual(r['reasoning_mode'],'high')
        self.assertTrue(r['no_fixed_time_tiers'])
        self.assertTrue(r['no_programmatic_workload_mapping'])
        self.assertTrue(r['early_stop_requires_semantic_budget_adequacy_check'])
    def test_no_legacy_human_time_definition(self):
        txt=(ROOT/'core/15_INVOCATION_BUDGETS.md').read_text(encoding='utf-8')
        self.assertIn('参照主体不是人类',txt)
        self.assertNotIn('Focused',txt)
        self.assertNotIn('Analytical',txt)
    def test_stop_gate_orders_T_check_before_marginal_stop(self):
        txt=(ROOT/'core/90_STOP_CONDITIONS.md').read_text(encoding='utf-8')
        self.assertIn('先做 T 预算充分性回检，再应用边际收益停止',txt)

if __name__=='__main__': unittest.main()
