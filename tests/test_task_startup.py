import unittest
from runtime.clock_probe import ClockSnapshot
from runtime.invocation_surface import classify_surface
from runtime.task_startup import ClockReadiness,TaskStartupReceipt,start_task
from tests.helpers import authority,FakeClock

class TestTaskStartup(unittest.TestCase):
    def s(self,n,session='s',boot=None): return ClockSnapshot('p',session,boot,n,n)
    def test_readiness_requires_three_samples_and_every_edge(self):
        with self.assertRaises(ValueError): ClockReadiness((self.s(1),self.s(2)))
        c=ClockReadiness((self.s(1),self.s(2),self.s(3)))
        self.assertTrue(c.ready); self.assertEqual(c.sample_count,3); self.assertEqual(c.anchor.monotonic_ns,1); self.assertEqual(c.probe.monotonic_ns,3)
    def test_cross_session_without_boot_fails(self):
        with self.assertRaises(ValueError): ClockReadiness((self.s(1,'a'),self.s(2,'a'),self.s(3,'b')))
    def test_backwards_anywhere_fails(self):
        with self.assertRaises(ValueError): ClockReadiness((self.s(1),self.s(3),self.s(2)))
    def test_start_task_binds_executing_invocation(self):
        clock=FakeClock(); inv=classify_surface('DIGR（R=2）：任务'); r=start_task(authority(),inv,clock)
        self.assertEqual(r.invocation.kind.value,'EXECUTING'); self.assertEqual(r.clock.sample_count,3); self.assertFalse(r.u0_frozen)
    def test_help_invalid_cannot_start(self):
        for msg in ('DIGR/help','DIGR不是调用'):
            with self.assertRaises(ValueError): start_task(authority(),classify_surface(msg),FakeClock())
    def test_sample_count_cannot_be_weakened(self):
        with self.assertRaises(ValueError): start_task(authority(),classify_surface('DIGR：x'),FakeClock(),sample_count=2)
    def test_u0_already_frozen_rejected(self):
        c=ClockReadiness((self.s(1),self.s(2),self.s(3)))
        with self.assertRaises(ValueError): TaskStartupReceipt(authority(),classify_surface('DIGR：x'),c,True)
if __name__=='__main__': unittest.main()
