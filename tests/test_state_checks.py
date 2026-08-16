import unittest
from runtime.state_checks import union_duration_ns, union_duration_seconds, MinimumCheck

class TestStateChecks(unittest.TestCase):
    def test_union_ns_exact(self):
        self.assertEqual(union_duration_ns([(0,10),(5,20),(30,40)]),30)
        self.assertEqual(union_duration_ns([]),0)
    def test_union_seconds(self):
        self.assertEqual(union_duration_seconds([(0.0,2.5),(2.0,3.0)]),3.0)
    def test_invalid_intervals(self):
        with self.assertRaises(ValueError): union_duration_ns([(2,1)])
        with self.assertRaises(TypeError): union_duration_ns([(True,2)])
        with self.assertRaises(ValueError): union_duration_seconds([(0,float('nan'))])
    def test_minimum(self):
        self.assertTrue(MinimumCheck(2,3).satisfied)
        self.assertFalse(MinimumCheck(3,2).satisfied)
        with self.assertRaises(TypeError): MinimumCheck(True,2)

if __name__ == '__main__': unittest.main()
