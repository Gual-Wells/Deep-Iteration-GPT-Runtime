import tempfile,unittest
from pathlib import Path
from runtime.clock_journal import ClockJournal,derive_work_intervals
from runtime.interval_ledger import WorkState
from tests.helpers import FakeClock

class TestClockJournal(unittest.TestCase):
    def test_genesis_and_hash_chain_persist(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'clock.ndjson'; j=ClockJournal('digr-12345678',p); c=FakeClock()
            samples=(c(),c(),c()); j.append_genesis(samples); j.append('STATE',c(),WorkState.MAIN); self.assertTrue(j.verify(True))
            self.assertEqual(len(j.events),4); loaded=ClockJournal.load('digr-12345678',p); self.assertTrue(loaded.verify(True)); self.assertEqual(len(derive_work_intervals(loaded.events)),0)
    def test_genesis_requires_three(self):
        j=ClockJournal('digr-12345678'); c=FakeClock()
        with self.assertRaises(ValueError): j.append_genesis((c(),c()))
    def test_state_intervals_rederive(self):
        j=ClockJournal('digr-12345678'); c=FakeClock(); j.append_genesis((c(),c(),c())); j.append('STATE',c(),WorkState.MAIN); j.append('STATE',c(),WorkState.SOURCE); j.append('FINISH',c(),WorkState.META)
        iv=derive_work_intervals(j.events); self.assertEqual([x.state for x in iv],[WorkState.MAIN,WorkState.SOURCE]); self.assertTrue(all(x.hard_verified for x in iv))

    def test_reordering_detected_on_load(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'clock'; j=ClockJournal('digr-12345678',p); c=FakeClock(); j.append_genesis((c(),c(),c()))
            lines=p.read_text().splitlines(); p.write_text('\n'.join(reversed(lines))+'\n')
            with self.assertRaises(ValueError): ClockJournal.load('digr-12345678',p)
if __name__=='__main__': unittest.main()
