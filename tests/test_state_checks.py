import unittest
from runtime.state_checks import union_duration_seconds, MinimumCheck

class TestStateChecks(unittest.TestCase):
    def test_union_prevents_parallel_double_count(self):
        self.assertEqual(union_duration_seconds([(0, 10), (5, 15)]), 15)
    def test_disjoint(self):
        self.assertEqual(union_duration_seconds([(0, 5), (10, 20)]), 15)
    def test_minimum(self):
        self.assertTrue(MinimumCheck(2, 3).satisfied)
        self.assertFalse(MinimumCheck(3, 2).satisfied)

if __name__ == "__main__":
    unittest.main()
