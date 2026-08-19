import tempfile,unittest
from pathlib import Path
from runtime.workspace import RunWorkspace
from runtime.d_intervention import DInterventionStore,ReintegrationReceipt
from runtime.isolation_checks import IsolationFacts,make_isolation_receipt

class TestDIntervention(unittest.TestCase):
    def store(self,td,target=1,facts=None,**kw):
        ws=RunWorkspace.create(Path(td),'digr-12345678'); st=DInterventionStore(ws); facts=facts or IsolationFacts(True)
        st.add_isolation(make_isolation_receipt('iso1',target,facts,**kw)); return st
    def test_full_lifecycle_and_count(self):
        with tempfile.TemporaryDirectory() as td:
            st=self.store(td); st.create('D1','iso1','try non-local route'); self.assertEqual(st.completed_count,0)
            st.decree('D1','run it'); st.record_execution('D1','executed'); st.record_result('D1','result'); st.reintegrate('D1',ReintegrationReceipt(None,0,'none','all','independent test showed no benefit'))
            self.assertEqual(st.completed_count,1); self.assertTrue(st.latest('D1').completed)
    def test_proposal_revisionable_only_before_decree(self):
        with tempfile.TemporaryDirectory() as td:
            st=self.store(td); st.create('D1','iso1','p0'); st.revise_proposal('D1','p1','new evidence'); self.assertEqual([x.text for x in st.latest('D1').proposals],['p0','p1']); st.decree('D1','commit current')
            with self.assertRaises(ValueError):st.revise_proposal('D1','p2','too late')
    def test_decree_can_bind_earlier_proposal_revision(self):
        with tempfile.TemporaryDirectory() as td:
            st=self.store(td); st.create('D1','iso1','p0'); st.revise_proposal('D1','p1','explore'); x=st.decree('D1','use p0',0); self.assertEqual(x.decree.proposal_revision,0)
    def test_execution_requires_decree_and_result_requires_execution(self):
        with tempfile.TemporaryDirectory() as td:
            st=self.store(td); st.create('D1','iso1','p')
            with self.assertRaises(ValueError):st.record_execution('D1','x')
            with self.assertRaises(ValueError):st.record_result('D1','x')
    def test_reintegration_requires_result(self):
        with tempfile.TemporaryDirectory() as td:
            st=self.store(td); st.create('D1','iso1','p'); st.decree('D1','d'); st.record_execution('D1','e')
            with self.assertRaises(ValueError):st.reintegrate('D1',ReintegrationReceipt(None,0,'a','r','c'))
    def test_abort_allows_new_intervention_not_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            st=self.store(td); st.create('D1','iso1','p'); st.abort('D1','wrong route'); self.assertEqual(st.latest('D1').status,'ABORTED'); self.assertEqual(st.completed_count,0)
            with self.assertRaises(ValueError):st.revise_proposal('D1','new','late')
            with self.assertRaises(ValueError):st.decree('D1','late')
    def test_actual_isolation_comes_from_completed_interventions(self):
        with tempfile.TemporaryDirectory() as td:
            facts=IsolationFacts(True,True,True,True,True,True,True,True,True)
            st=self.store(td,target=2,facts=facts,input_packet_ref='in.json',output_packet_ref='out.json')
            self.assertEqual(st.actual_isolation_level,2)
            st.create('D1','iso1','p'); st.decree('D1','d'); st.record_execution('D1','e'); st.record_result('D1','r'); st.reintegrate('D1',ReintegrationReceipt(None,0,'x','y','z')); self.assertEqual(st.actual_isolation_level,2)
    def test_l2_l3_receipts_require_packet_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            ws=RunWorkspace.create(Path(td),'digr-12345678');st=DInterventionStore(ws);facts=IsolationFacts(True,True,True,True,True)
            with self.assertRaises(ValueError):st.add_isolation(make_isolation_receipt('iso',2,facts))
    def test_load_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            st=self.store(td); st.create('D1','iso1','p'); ws=st.workspace; loaded=DInterventionStore.load(ws); self.assertEqual(loaded.latest('D1'),st.latest('D1'))
if __name__=='__main__':unittest.main()
