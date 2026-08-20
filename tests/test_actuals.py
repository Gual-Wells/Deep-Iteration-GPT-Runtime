import tempfile,unittest
from pathlib import Path
from runtime.run_session import LiveDIGRRun
from runtime.effective_contract import EffectiveContract,SourceContract,SourceDisposition
from runtime.interval_ledger import WorkState
from runtime.evolution_events import EvolutionKind
from runtime.strategy_store import StrategyState
from runtime.candidate_store import CandidateSnapshot
from runtime.isolation_checks import IsolationFacts
from tests.helpers import authority,FakeClock,protocol_load_receipt

class TestActuals(unittest.TestCase):
    def start(self,td,contract,msg='DIGR：x'):
        c=FakeClock();r=LiveDIGRRun.start(authority(),msg,Path(td),c,run_id='digr-12345678');r.bind_protocol_load(protocol_load_receipt());r.resolve_parameters();r.freeze_u0('x');r.freeze_contract(contract);r.transition(WorkState.MAIN,c());r.save_strategy(StrategyState(0,'model','route'));return r,c
    def test_no_event_no_d_actuals_are_zero(self):
        with tempfile.TemporaryDirectory() as td:
            k=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),0,1,SourceDisposition.WAIVED,'no external source suitable');r,c=self.start(td,k);r.finish_time(c());a=r.actuals();self.assertEqual((a.N,a.R,a.S_count,a.D_s),(0,0,0,0));self.assertIsNone(a.L_e)
    def test_actuals_derive_only_from_bound_receipts(self):
        with tempfile.TemporaryDirectory() as td:
            k=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),1,1,SourceDisposition.WAIVED,'closed');r,c=self.start(td,k);r.record_main_evolution('changed','did','better');r.save_candidate(CandidateSnapshot(0,'c'));r.record_main_reentry(0,'challenge','rerun','retained',retained=True);r.add_isolation_facts('iso',IsolationFacts(True));r.create_d_intervention('D1','iso','p');r.decree_d('D1','d');r.transition(WorkState.D_EXCLUSIVE,c());r.record_d_execution('D1','e');r.record_d_result('D1','result');r.transition(WorkState.MAIN,c());r.reintegrate_d('D1',accepted='none',rejected='result',main_consequence='retain',candidate_before_revision=0);r.finish_time(c());a=r.actuals();self.assertEqual((a.N,a.R,a.D_s,a.L_e),(1,1,1,1))
    def test_actuals_reject_private_log_event_bound_to_wrong_work_state(self):
        # Actual derivation is a trust boundary too: even a hash-valid receipt
        # inserted through the private log API must not inflate MAIN N while the
        # foreground journal state is SOURCE.
        with tempfile.TemporaryDirectory() as td:
            k=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),0,1,SourceDisposition.WAIVED,'closed')
            r,c=self.start(td,k);r.open_source('S1','research');r.transition(WorkState.SOURCE,c(),active_source_ids=('S1',))
            clock_ref=r.clock_journal.events[-1].record_hash
            r.events._append(EvolutionKind.MAIN_EVOLUTION,'MAIN','forged','private append','inflate N',clock_event_ref=clock_ref,strategy_revision=0)
            with self.assertRaisesRegex(ValueError,'MAIN semantic actual is not bound to MAIN work'):
                r.actuals()
if __name__=='__main__':unittest.main()
