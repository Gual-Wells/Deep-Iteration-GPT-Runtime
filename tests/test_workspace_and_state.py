import tempfile,unittest
from pathlib import Path
from runtime.workspace import RunWorkspace
from runtime.est_store import ESTStore,ESTSnapshot
from runtime.evidence_index import EvidenceIndex,EvidenceRecord
from runtime.completion_state import CompletionState
from runtime.source_workspace import SourceWorkspaceRegistry
from runtime.strategy_store import StrategyStore,StrategyState
from runtime.candidate_store import CandidateStore,CandidateSnapshot

class TestWorkspaceState(unittest.TestCase):
    def make(self,td):return RunWorkspace.create(Path(td),'digr-12345678')
    def test_workspace_blocks_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            ws=self.make(td)
            with self.assertRaises(ValueError):ws.path('../x')
    def test_artifact_index_detects_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            ws=self.make(td);ws.write_json('state/x.json',{'x':1},kind='test',revision=0);self.assertTrue(ws.verify_artifact_index());ws.path('state/x.json').write_text('{"x":2}',encoding='utf-8')
            with self.assertRaises(ValueError):ws.verify_artifact_index()
    def test_artifact_index_rejects_unindexed_authoritative_file(self):
        with tempfile.TemporaryDirectory() as td:
            ws=self.make(td);ws.write_json('state/x.json',{'x':1},kind='test',revision=0)
            ws.path('state/rogue.json').write_text('{"x":2}\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'unindexed workspace artifact'):
                ws.verify_artifact_index()
    def test_strategy_revision_and_no_scheduler_fields(self):
        with tempfile.TemporaryDirectory() as td:
            st=StrategyStore(self.make(td));st.save(StrategyState(0,'model','route'));st.save(StrategyState(1,'new model','new route',pivot_reason='counterexample'));self.assertEqual(st.current.revision,1);self.assertNotIn('next_step',st.current.to_dict());self.assertNotIn('score',st.current.to_dict());self.assertNotIn('priority',st.current.to_dict())
    def test_candidate_revision_digest(self):
        with tempfile.TemporaryDirectory() as td:
            st=CandidateStore(self.make(td));a=st.save(CandidateSnapshot(0,'first'));b=st.save(CandidateSnapshot(1,'second'));self.assertNotEqual(a.digest,b.digest);self.assertEqual(st.current.revision,1)
    def test_est_references_strategy_candidate_instead_of_duplicate_result(self):
        with tempfile.TemporaryDirectory() as td:
            st=ESTStore(self.make(td));x=ESTSnapshot('MAIN',0,('fact',),('decision',),(),('gap',),('route',),('old route',),('changed',),0,0);st.save(x);self.assertEqual(st.latest('MAIN').candidate_revision,0);d=x.to_dict();self.assertNotIn('current_best_result',d);self.assertNotIn('stable_facts',d)
    def test_est_scope_filename_collision_prevented(self):
        with tempfile.TemporaryDirectory() as td:
            ws=self.make(td);st=ESTStore(ws);st.save(ESTSnapshot('S:A/B',0,(),(),(),()));st.save(ESTSnapshot('S:A?B',0,(),(),(),()));self.assertEqual(len(list(ws.path('state').glob('est-*-latest.json'))),2)

    def test_est_latest_pointer_semantic_drift_rejected_even_if_reindexed(self):
        with tempfile.TemporaryDirectory() as td:
            ws=self.make(td);st=ESTStore(ws);st.save(ESTSnapshot('MAIN',0,('fact',),(),(),(),strategy_revision=None,candidate_revision=None))
            latest=next(ws.path('state').glob('est-*-latest.json'));rel=latest.relative_to(ws.root).as_posix();d=ws.read_json(rel);d['currently_supported_facts']=['changed'];ws.write_json(rel,d,kind='est-latest',revision=0)
            with self.assertRaisesRegex(ValueError,'EST latest pointer drift'):ESTStore.load(ws)

    def test_source_revision_pivot_close_reopen(self):
        with tempfile.TemporaryDirectory() as td:
            src=SourceWorkspaceRegistry(self.make(td));src.open('S1','research x');src.revise('S1',current_direction='research counterexample',pivot_reason='new evidence');src.close('S1','found y');src.reopen('S1',current_direction='verify y',reason='R challenge');self.assertEqual(src.latest('S1').revision,3);self.assertEqual(src.latest('S1').status,'OPEN')
    def test_source_id_safe(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):SourceWorkspaceRegistry(self.make(td)).open('../escape','x')
    def test_evidence_and_revisioned_completion(self):
        with tempfile.TemporaryDirectory() as td:
            ws=self.make(td);ev=EvidenceIndex(ws);ev.add(EvidenceRecord('E1','web','https://example.invalid','evidence','S1'));self.assertEqual(len(ev.items),1)
            c=CompletionState(ws);c.open_gap('G1','must test',True);c.revise_gap('G1',description='must test cold build',reason='scope clarified');self.assertEqual(c.latest('G1').revision,1);c.close_gap('G1','passed');self.assertFalse(c.blocking_open);c.reopen_gap('G1','new regression');self.assertEqual(len(c.blocking_open),1);c.close_gap('G1','fixed');c.assess('ready');self.assertTrue(c.ready)
if __name__=='__main__':unittest.main()
