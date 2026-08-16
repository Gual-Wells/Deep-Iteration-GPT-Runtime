import unittest
from runtime.clock_probe import ClockSnapshot
from runtime.interval_ledger import FormalTimeLedger, WorkInterval, WorkState, sum_interval_durations_ns

class TestIntervalLedger(unittest.TestCase):
    def s(self, sec, session='same', boot=None):
        ns=int(sec*1_000_000_000)
        return ClockSnapshot('test',session,boot,ns,ns)

    def ready(self,l,a=0,b=0.1,session='same'):
        l.establish_timing_readiness(self.s(a,session),self.s(b,session))

    def test_universal_gate_blocks_soft_and_hard_formal_work(self):
        for l in (FormalTimeLedger(),FormalTimeLedger(hard_T=True),FormalTimeLedger(hard_t=True)):
            l.transition(WorkState.META,self.s(0))
            with self.assertRaises(RuntimeError):
                l.transition(WorkState.MAIN,self.s(1))
            self.assertFalse(l.formal_started)

    def test_formal_time_excludes_meta_d_idle(self):
        l=FormalTimeLedger(hard_T=True,hard_t=True)
        self.ready(l,0,0.1)
        l.transition(WorkState.META,self.s(0.1))
        l.transition(WorkState.MAIN,self.s(2))
        l.transition(WorkState.D_EXCLUSIVE,self.s(8))
        l.transition(WorkState.MAIN,self.s(13))
        l.transition(WorkState.SOURCE,self.s(15))
        l.transition(WorkState.META,self.s(18))
        l.finish(self.s(19))
        self.assertEqual(l.formal_T_ns(),11_000_000_000)
        self.assertEqual(l.formal_t_ns(),3_000_000_000)
        self.assertTrue(l.T_hard_verified()); self.assertTrue(l.t_hard_verified())

    def test_readiness_needs_two_snapshots(self):
        l=FormalTimeLedger()
        with self.assertRaises(TypeError): l.establish_timing_readiness(self.s(0),None)
        with self.assertRaises(ValueError): l.establish_timing_readiness(self.s(1),self.s(0))

    def test_soft_run_is_observed_only_after_gate(self):
        l=FormalTimeLedger()
        self.assertFalse(l.timing_ready)
        self.ready(l)
        self.assertTrue(l.timing_ready)
        l.transition(WorkState.MAIN,self.s(1)); l.finish(self.s(2))
        self.assertEqual(l.formal_T_ns(),1_000_000_000)
        self.assertTrue(l.T_hard_verified())
        self.assertFalse(l.t_hard_verified())

    def test_readiness_identity_carries_into_first_hard_formal_event(self):
        l=FormalTimeLedger(hard_T=True)
        l.establish_timing_readiness(self.s(0,'a'),self.s(.1,'a'))
        with self.assertRaises(ValueError):
            l.transition(WorkState.MAIN,self.s(1,'b'))

    def test_timeline_cannot_go_backwards_or_continue_after_finish(self):
        l=FormalTimeLedger(); self.ready(l,0,1)
        l.transition(WorkState.META,self.s(2))
        with self.assertRaises(ValueError): l.transition(WorkState.MAIN,self.s(1.5))
        l.transition(WorkState.MAIN,self.s(3)); l.finish(self.s(4))
        with self.assertRaises(RuntimeError): l.transition(WorkState.MAIN,self.s(5))
        with self.assertRaises(RuntimeError): l.establish_timing_readiness(self.s(5),self.s(6))

    def test_hard_flags_must_be_bool(self):
        with self.assertRaises(TypeError): FormalTimeLedger(hard_T=1)
        with self.assertRaises(TypeError): FormalTimeLedger(hard_t='yes')

    def test_to_dict_closed_interval_facts(self):
        l=FormalTimeLedger(); self.ready(l)
        l.transition(WorkState.MAIN,self.s(1)); l.finish(self.s(3))
        d=l.to_dict()
        self.assertEqual(d['T_actual_ns'],2_000_000_000)
        self.assertTrue(d['timing_ready']); self.assertTrue(d['finished'])
        self.assertEqual(set(d['intervals'][0]), {'state','start','end','observed_ns','hard_verified'})

    def test_per_interval_sum_not_absolute_union(self):
        a1,a2=self.s(0,'a'),self.s(1,'a')
        b1,b2=self.s(0,'b'),self.s(1,'b')
        x=WorkInterval(WorkState.MAIN,a1,a2,1_000_000_000,True)
        y=WorkInterval(WorkState.MAIN,b1,b2,1_000_000_000,True)
        self.assertEqual(sum_interval_durations_ns((x,y)),2_000_000_000)

    def test_false_hard_fact_rejected_when_asserted_true(self):
        a=self.s(0,'a'); b=self.s(1,'b')
        with self.assertRaises(ValueError): WorkInterval(WorkState.MAIN,a,b,1_000_000_000,True)
        x=WorkInterval(WorkState.MAIN,a,b,1_000_000_000,False)
        self.assertFalse(x.hard_verified)

if __name__ == '__main__': unittest.main()
