import json,subprocess,sys,unittest
from runtime.clock_probe import snapshot,ClockSnapshot
from runtime.task_startup import ClockReadiness,start_task
from runtime.invocation_surface import classify_surface
from tests.helpers import authority

class TestClockGenesisStress(unittest.TestCase):
    def test_real_process_many_samples_never_backwards(self):
        samples=tuple(snapshot() for _ in range(256)); r=ClockReadiness(samples); self.assertTrue(r.ready); self.assertEqual(r.sample_count,256)
        self.assertTrue(all(a.monotonic_ns<=b.monotonic_ns for a,b in zip(samples,samples[1:])))
    def test_real_start_task_default_has_three_samples(self):
        r=start_task(authority(),classify_surface('DIGR：clock startup test')); self.assertEqual(r.clock.sample_count,3); self.assertTrue(r.clock.ready)
    def test_same_boot_cross_process_samples_when_supported(self):
        def get():
            d=json.loads(subprocess.check_output([sys.executable,'-m','runtime.clock_probe'],text=True)); return ClockSnapshot(d['provider'],d['session_id'],d['boot_id'],d['monotonic_ns'],d['wall_ns'])
        samples=(get(),get(),get())
        if any(x.boot_id is None for x in samples): self.skipTest('cross-process boot identity unavailable')
        r=ClockReadiness(samples); self.assertEqual(r.continuity_kind,'same-boot-cross-process')
if __name__=='__main__': unittest.main()
