import unittest
from runtime.duration import parse_canonical_duration_seconds

class TestDuration(unittest.TestCase):
    def test_units(self):
        self.assertEqual(parse_canonical_duration_seconds("30s"), 30)
        self.assertEqual(parse_canonical_duration_seconds("15m"), 900)
        self.assertEqual(parse_canonical_duration_seconds("2h"), 7200)
    def test_invalid(self):
        with self.assertRaises(ValueError):
            parse_canonical_duration_seconds("about ten minutes")

if __name__ == "__main__": unittest.main()
