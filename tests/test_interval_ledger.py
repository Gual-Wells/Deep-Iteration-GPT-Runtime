import unittest
from runtime.clock_probe import ClockSnapshot
from runtime.interval_ledger import FormalTimeLedger,WorkInterval,WorkState,sum_interval_durations_ns
from tests.helpers import startup,FakeClock

class TestIntervalLedger(unittest.TestCase):
    def s(self,sec,session='same',boot=None):
        ns=int(sec*1e9); return ClockSnapshot('test',session,boot,ns,ns)
    def st(self,hardT=False,hardt=False):
        c=FakeClock(start=0,step=100_000_000,provider='test',session='same'); receipt,_=startup(c); return FormalTimeLedger(receipt,hard_T=hardT,hard_t=hardt)
    def test_ledger_cannot_exist_without_startup(self):
        with self.assertRaises(TypeError): FormalTimeLedger(None)
    def test_formal_time_excludes_meta_d_idle(self):
        l=self.st(True,True)
        l.transition(WorkState.META,self.s(.3)); l.transition(WorkState.MAIN,self.s(2)); l.transition(WorkState.D_EXCLUSIVE,self.s(8)); l.transition(WorkState.MAIN,self.s(13)); l.transition(WorkState.SOURCE,self.s(15)); l.transition(WorkState.META,self.s(18)); l.finish(self.s(19))
        self.assertEqual(l.formal_T_ns(),11_000_000_000); self.assertEqual(l.formal_t_ns(),3_000_000_000); self.assertTrue(l.T_hard_verified()); self.assertTrue(l.t_hard_verified())
    def test_soft_run_still_has_genesis(self):
        l=self.st(); self.assertTrue(l.timing_ready); l.transition(WorkState.MAIN,self.s(.4)); l.finish(self.s(2)); self.assertGreater(l.formal_T_ns(),0)
    def test_hard_identity_carries_from_startup_probe(self):
        c=FakeClock(start=0,step=100_000_000,provider='test',session='a'); receipt,_=startup(c); l=FormalTimeLedger(receipt,hard_T=True)
        with self.assertRaises(ValueError): l.transition(WorkState.MAIN,self.s(1,'b'))
    def test_timeline_no_backwards_or_after_finish(self):
        l=self.st(); l.transition(WorkState.META,self.s(.4)); l.transition(WorkState.MAIN,self.s(1));
        with self.assertRaises(ValueError): l.transition(WorkState.SOURCE,self.s(.9))
        l.finish(self.s(2));
        with self.assertRaises(RuntimeError): l.transition(WorkState.MAIN,self.s(3))
    def test_hard_flags_bool(self):
        r,_=startup(FakeClock(provider='test'))
        with self.assertRaises(TypeError): FormalTimeLedger(r,hard_T=1)
    def test_interval_sum(self):
        a1,a2=self.s(0,'a'),self.s(1,'a'); b1,b2=self.s(0,'b'),self.s(1,'b')
        x=WorkInterval(WorkState.MAIN,a1,a2,1_000_000_000,True); y=WorkInterval(WorkState.MAIN,b1,b2,1_000_000_000,True)
        self.assertEqual(sum_interval_durations_ns((x,y)),2_000_000_000)
if __name__=='__main__': unittest.main()
