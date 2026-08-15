import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class TestClockCrossProcess(unittest.TestCase):
    def _snap(self):
        out = subprocess.check_output([sys.executable, "runtime/clock_probe.py"], cwd=ROOT, text=True)
        return json.loads(out)

    def test_cross_process_identity_when_strong_provider_available(self):
        a = self._snap()
        b = self._snap()
        self.assertGreaterEqual(b["monotonic_ns"], a["monotonic_ns"])
        if a["hard_verifiable"] and b["hard_verifiable"]:
            self.assertEqual(a["clock_id"], b["clock_id"])

if __name__ == "__main__":
    unittest.main()
