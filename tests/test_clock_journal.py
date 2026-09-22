import tempfile,unittest
from pathlib import Path
from runtime.clock_journal import ClockJournal,derive_work_intervals,derive_work_timeline
from runtime.interval_ledger import WorkState
from tests.helpers import FakeClock

class TestClockJournal(unittest.TestCase):
    def test_genesis_and_hash_chain_persist(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'clock.ndjson';j=ClockJournal('digr-12345678',p);c=FakeClock()
            samples=(c(),c(),c());j.append_genesis(samples);j.append('STATE',c(),WorkState.MAIN)
            self.assertTrue(j.verify(True));loaded=ClockJournal.load('digr-12345678',p);self.assertTrue(loaded.verify(True))
    def test_state_intervals_rederive(self):
        j=ClockJournal('digr-12345678');c=FakeClock()
        j.append_genesis((c(),c(),c()));j.append('STATE',c(),WorkState.MAIN);j.append('STATE',c(),WorkState.SOURCE);j.append('FINISH',c(),WorkState.META)
        iv=derive_work_intervals(j.events);self.assertEqual([x.state for x in iv],[WorkState.MAIN,WorkState.SOURCE]);self.assertTrue(all(x.hard_verified for x in iv))
    def test_unleased_resume_preserves_gap_instead_of_dropping_it(self):
        j=ClockJournal('digr-12345678');c=FakeClock(start=0,step=100_000_000,session='s1',boot='boot-x')
        j.append_genesis((c(),c(),c()));j.append('STATE',c(),WorkState.MAIN)
        later=FakeClock(start=5_000_000_000,step=100_000_000,session='s2',boot='boot-x')
        j.append_resume((later(),later(),later()))
        t=derive_work_timeline(j.events)
        self.assertIsNone(t.open_state);self.assertEqual(len(t.gaps),1);self.assertEqual(t.gaps[0].state,WorkState.MAIN)
        self.assertGreater(t.gaps[0].observed_ns,4_000_000_000)
    def test_leased_resume_keeps_formal_state(self):
        j=ClockJournal('digr-12345678');c=FakeClock(start=0,step=100_000_000,session='s1',boot='boot-x')
        j.append_genesis((c(),c(),c()));j.append('STATE',c(),WorkState.MAIN);j.append('WORK_LEASE_OPEN',c(),WorkState.MAIN)
        later=FakeClock(start=5_000_000_000,step=100_000_000,session='s2',boot='boot-x')
        samples=(later(),later(),later());j.append_resume(samples);j.append('STATE',samples[-1],WorkState.MAIN)
        t=derive_work_timeline(j.events)
        self.assertEqual(t.open_state,WorkState.MAIN);self.assertEqual(len(t.gaps),0)
        self.assertGreater(sum(x.observed_ns for x in t.intervals if x.state is WorkState.MAIN),4_000_000_000)
    def test_lease_must_match_active_state(self):
        j=ClockJournal('digr-12345678');c=FakeClock();j.append_genesis((c(),c(),c()));j.append('STATE',c(),WorkState.MAIN);j.append('WORK_LEASE_OPEN',c(),WorkState.SOURCE)
        with self.assertRaises(ValueError):derive_work_timeline(j.events)
    def test_reordering_detected_on_load(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'clock';j=ClockJournal('digr-12345678',p);c=FakeClock();j.append_genesis((c(),c(),c()))
            lines=p.read_text().splitlines();p.write_text('\n'.join(reversed(lines))+'\n')
            with self.assertRaises(ValueError):ClockJournal.load('digr-12345678',p)

if __name__=='__main__':unittest.main()
