import unittest
from runtime.clock_probe import (
    ClockSnapshot, continuity_kind, elapsed_ns, elapsed_seconds,
    observed_elapsed_ns, pair_is_hard_verifiable,
)

class TestClockProbe(unittest.TestCase):
    def s(self, ns, session='s', boot=None, provider='test'):
        return ClockSnapshot(provider, session, boot, ns, ns)

    def test_same_session(self):
        a,b=self.s(1_000_000_000),self.s(3_500_000_000)
        self.assertEqual(continuity_kind(a,b),'same-process-session')
        self.assertEqual(elapsed_ns(a,b),2_500_000_000)
        self.assertEqual(elapsed_seconds(a,b),2.5)
        self.assertTrue(pair_is_hard_verifiable(a,b))

    def test_same_boot_cross_process(self):
        a=self.s(10,'a','boot-x'); b=self.s(20,'b','boot-x')
        self.assertEqual(continuity_kind(a,b),'same-boot-cross-process')
        self.assertTrue(pair_is_hard_verifiable(a,b))

    def test_observed_is_weaker_than_hard(self):
        a=self.s(10,'a'); b=self.s(20,'b')
        self.assertEqual(observed_elapsed_ns(a,b),10)
        self.assertFalse(pair_is_hard_verifiable(a,b))
        with self.assertRaises(ValueError): elapsed_ns(a,b)

    def test_changed_boot_fails_hard(self):
        with self.assertRaises(ValueError): elapsed_ns(self.s(1,'a','x'),self.s(2,'b','y'))

    def test_provider_or_direction_fails_even_observed(self):
        with self.assertRaises(ValueError): observed_elapsed_ns(self.s(1),self.s(2,provider='other'))
        with self.assertRaises(ValueError): observed_elapsed_ns(self.s(2),self.s(1))

    def test_strict_fields(self):
        with self.assertRaises(TypeError): ClockSnapshot('x','s',None,True,1)
        with self.assertRaises(ValueError): ClockSnapshot('','s',None,1,1)
        with self.assertRaises(ValueError): ClockSnapshot('x','',None,1,1)
        with self.assertRaises(ValueError): ClockSnapshot('x','s','',1,1)

if __name__ == '__main__': unittest.main()
