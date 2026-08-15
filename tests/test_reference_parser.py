import unittest
from runtime.reference_parser import parse_invocation

class TestParser(unittest.TestCase):
    def test_plain_cn(self):
        x=parse_invocation("深度迭代：任务")
        self.assertTrue(x["enabled"]); self.assertEqual(x["task_raw"],"任务"); self.assertFalse(x["parameterized"])
    def test_plain_ascii(self):
        self.assertTrue(parse_invocation("深度迭代:task")["enabled"])
    def test_parameter_cn(self):
        x=parse_invocation("深度迭代（4，30m）：任务")
        self.assertTrue(x["enabled"]); self.assertEqual(x["min_prompt_iterations"],4); self.assertEqual(x["complexity_budget_raw"],"30m")
    def test_parameter_ascii(self):
        x=parse_invocation("深度迭代(8,2h):task")
        self.assertEqual((x["min_prompt_iterations"],x["complexity_budget_raw"]),(8,"2h"))
    def test_empty_task(self):
        self.assertFalse(parse_invocation("深度迭代：   ")["enabled"])
    def test_zero_iteration(self):
        self.assertFalse(parse_invocation("深度迭代（0，30m）：任务")["enabled"])
    def test_non_trigger(self):
        self.assertFalse(parse_invocation("请深度迭代这个任务")["enabled"])

if __name__ == '__main__': unittest.main()
