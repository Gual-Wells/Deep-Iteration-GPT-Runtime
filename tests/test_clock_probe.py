import time
import unittest
from runtime.clock_probe import snapshot, elapsed_seconds, ClockSnapshot

class TestClockProbe(unittest.TestCase):
    def test_snapshot_monotonic(self):
        a = snapshot()
        time.sleep(0.005)
        b = snapshot()
        self.assertGreaterEqual(b.monotonic_ns, a.monotonic_ns)
        if a.hard_verifiable and b.hard_verifiable and a.clock_id == b.clock_id:
            self.assertGreaterEqual(elapsed_seconds(a, b), 0)

    def test_identity_mismatch_fails(self):
        a = ClockSnapshot("python-monotonic", "a", 1, 1, True)
        b = ClockSnapshot("python-monotonic", "b", 2, 2, True)
        with self.assertRaises(ValueError):
            elapsed_seconds(a, b)

if __name__ == "__main__":
    unittest.main()
