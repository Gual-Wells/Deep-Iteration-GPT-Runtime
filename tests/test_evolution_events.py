import tempfile,unittest
from pathlib import Path
from runtime.evolution_events import EvolutionEventLog,EvolutionKind

class TestEvolutionEvents(unittest.TestCase):
    def append(self,log,kind=EvolutionKind.MAIN_EVOLUTION,scope='MAIN',**kw):
        return log._append(kind,scope,'challenge','action','outcome',clock_event_ref='a'*64,strategy_revision=0,**kw)
    def test_raw_append_is_disabled(self):
        log=EvolutionEventLog()
        with self.assertRaises(RuntimeError):log.append(EvolutionKind.MAIN_EVOLUTION,'MAIN','s','a','r')
    def test_bound_receipt_counts_and_hashes(self):
        log=EvolutionEventLog(); self.append(log); self.append(log,EvolutionKind.MAIN_REENTRY,candidate_revision=0,retained=True)
        self.assertEqual(log.count(EvolutionKind.MAIN_EVOLUTION,'MAIN'),1); self.assertEqual(log.count(EvolutionKind.MAIN_REENTRY,'MAIN'),1); self.assertTrue(log.verify())
    def test_reentry_requires_candidate(self):
        log=EvolutionEventLog()
        with self.assertRaises(ValueError): self.append(log,EvolutionKind.MAIN_REENTRY,retained=True)
    def test_source_requires_source_id_and_scope_binding(self):
        log=EvolutionEventLog()
        with self.assertRaises(ValueError): self.append(log,EvolutionKind.SOURCE_EVOLUTION,scope='S:S1')
        x=self.append(log,EvolutionKind.SOURCE_EVOLUTION,scope='S:S1',source_id='S1',source_revision=0); self.assertEqual((x.source_id,x.source_revision),('S1',0))
    def test_persisted_lines_hash_chain(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'events';log=EvolutionEventLog(p);self.append(log);self.assertTrue(p.read_text().strip());self.assertTrue(EvolutionEventLog.load(p).verify())
    def test_tamper_detected(self):
        with tempfile.TemporaryDirectory() as td:
            import json
            p=Path(td)/'events';log=EvolutionEventLog(p);self.append(log);d=json.loads(p.read_text());d['result']='tamper';p.write_text(json.dumps(d)+'\n')
            with self.assertRaises(ValueError):EvolutionEventLog.load(p)
if __name__=='__main__':unittest.main()
