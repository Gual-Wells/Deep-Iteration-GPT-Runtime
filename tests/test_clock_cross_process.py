import json
import subprocess
import sys
import unittest

class TestClockCrossProcess(unittest.TestCase):
    def test_probe_json_is_strict_shape(self):
        out=subprocess.check_output([sys.executable,'-m','runtime.clock_probe'],text=True)
        data=json.loads(out)
        self.assertEqual(set(data),{'provider','session_id','boot_id','monotonic_ns','wall_ns'})
        self.assertGreater(data['monotonic_ns'],0)
        self.assertTrue(data['session_id'])
    def test_process_sessions_differ(self):
        def get():
            return json.loads(subprocess.check_output([sys.executable,'-m','runtime.clock_probe'],text=True))
        a,b=get(),get()
        self.assertNotEqual(a['session_id'],b['session_id'])
        if a['boot_id'] is not None and b['boot_id'] is not None:
            self.assertEqual(a['boot_id'],b['boot_id'])

if __name__ == '__main__': unittest.main()
