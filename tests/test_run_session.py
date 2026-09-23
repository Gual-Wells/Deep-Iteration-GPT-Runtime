import hashlib,json,tempfile,unittest
from pathlib import Path
from runtime.clock_probe import ClockSnapshot
from runtime.effective_contract import EffectiveContract,SourceContract,SourceDisposition
from runtime.interval_ledger import WorkState
from runtime.run_lifecycle import RunPhase
from runtime.run_recovery import verify_run_workspace
from runtime.run_session import LiveDIGRRun,RunGenesisError,RunResumeError
from runtime.strategy_store import StrategyState
from runtime.candidate_store import CandidateSnapshot
from runtime.isolation_checks import IsolationFacts
from tests.helpers import authority,FakeClock,protocol_load_receipt

class TestRunSession(unittest.TestCase):
    def bootstrap(self,td,msg='DIGR(1,1,S,D):任务',contract=None,clock=None):
        c=clock or FakeClock()
        run=LiveDIGRRun.start(authority(),msg,Path(td),c,run_id='digr-12345678',protocol_load=protocol_load_receipt())
        r=run.resolve_parameters();self.assertEqual(r.status.value,'RESOLVED');run.freeze_u0('任务')
        contract=contract or EffectiveContract(1,0,1,0,SourceContract(1,0,1,0),1,SourceDisposition.REQUIRED)
        run.freeze_contract(contract);return run,c

    def genesis_strategy(self,run,c):
        run.transition(WorkState.MAIN,c())
        return run.save_strategy(StrategyState(0,'task model','primary',('alternative',),'research sources','run tests','use tools',(),(),'genesis',()))

    def complete_run(self,td):
        run,c=self.bootstrap(td);self.genesis_strategy(run,c)
        run.record_main_evolution('changed architecture','implemented','better')
        run.save_candidate(CandidateSnapshot(0,'candidate result'))
        run.record_main_reentry(0,'challenge whole approach','rerun process','retained with evidence',retained=True)
        run.open_source('S1','research x');run.transition(WorkState.SOURCE,c(),active_source_ids=('S1',))
        run.record_source_evolution('S1','new evidence','searched','found')
        run.record_source_reentry('S1',0,'cross-check','independent check','confirmed',retained=True)
        run.transition(WorkState.MAIN,c());run.add_isolation_facts('iso1',IsolationFacts(True))
        run.create_d_intervention('D1','iso1','try orthogonal model');run.revise_d_proposal('D1','try adversarial countermodel','stronger pivot')
        run.decree_d('D1','execute current gambit');run.transition(WorkState.D_EXCLUSIVE,c())
        run.record_d_execution('D1','ran challenge');run.record_d_result('D1','no better alternative')
        run.transition(WorkState.MAIN,c());run.reintegrate_d('D1',accepted='none',rejected='countermodel',main_consequence='retain candidate after independent challenge',candidate_before_revision=0)
        run.completion.assess('quality complete');run.finish_time(c());return run,c

    def test_pre_genesis_protocol_readiness_precedes_live_run(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RunGenesisError,'PROTOCOL_PREP'):
                LiveDIGRRun.start(authority(),'DIGR：任务',Path(td),FakeClock(),run_id='digr-12345678')
            c=FakeClock();run=LiveDIGRRun.start(authority(),'DIGR：任务',Path(td),c,run_id='digr-12345678',protocol_load=protocol_load_receipt())
            self.assertEqual(run.phase.phase,RunPhase.GENESIS);self.assertGreaterEqual(len(run.clock_journal.events),3)
            self.assertTrue(run.workspace.path('protocol-load.json').is_file())
            with self.assertRaises(RuntimeError):run.freeze_u0('任务')
            run.resolve_parameters();run.freeze_u0('任务')
            run.freeze_contract(EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),0,SourceDisposition.WAIVED,'closed'))
            self.assertEqual(run.phase.phase,RunPhase.CONTRACT_FROZEN)

    def test_post_genesis_protocol_rebind_is_forbidden(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClock();run=LiveDIGRRun.start(authority(),'DIGR：任务',Path(td),c,run_id='digr-12345678',protocol_load=protocol_load_receipt())
            with self.assertRaisesRegex(RuntimeError,'before Genesis'):run.bind_protocol_load(protocol_load_receipt())
            with self.assertRaisesRegex(RuntimeError,'no born run'):run.abort_protocol_load('should never exist')

    def test_invalid_or_help_native_never_get_live_run(self):
        with tempfile.TemporaryDirectory() as td:
            for msg in ('DIGR/help','DIGR是什么？','digr：任务','DIGR：'):
                with self.assertRaises(RunGenesisError):LiveDIGRRun.start(authority(),msg,Path(td),FakeClock(),run_id='digr-12345678')

    def test_parameter_L_is_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClock();run=LiveDIGRRun.start(authority(),'DIGR(D,L(2))：x',Path(td),c,run_id='digr-12345678',protocol_load=protocol_load_receipt())
            r=run.resolve_parameters()
            self.assertEqual(r.status.value,'INVALID');self.assertEqual(run.phase.phase,RunPhase.ABORTED)

    def test_explicit_parameters_cannot_be_changed_by_contract_completion(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClock();run=LiveDIGRRun.start(authority(),'DIGR(N=2,R=1)：x',Path(td),c,run_id='digr-12345678',protocol_load=protocol_load_receipt())
            run.resolve_parameters();run.freeze_u0('x')
            with self.assertRaises(ValueError):
                run.freeze_contract(EffectiveContract(3,0,1,0,SourceContract(0,0,0,0),0,SourceDisposition.WAIVED,'closed'))

    def test_strategy_genesis_is_main_work_not_meta(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),0,SourceDisposition.WAIVED,'closed')
            run,c=self.bootstrap(td,'DIGR：任务',contract)
            with self.assertRaises(RuntimeError):run.save_strategy(StrategyState(0,'m','r'))
            run.transition(WorkState.MAIN,c());run.save_strategy(StrategyState(0,'m','r'));self.assertEqual(run.phase.phase,RunPhase.EXECUTING)

    def test_source_work_requires_real_workspace_and_strategy(self):
        with tempfile.TemporaryDirectory() as td:
            run,c=self.bootstrap(td);self.genesis_strategy(run,c)
            with self.assertRaises(ValueError):run.transition(WorkState.SOURCE,c(),active_source_ids=('missing',))
            run.open_source('S1','research');run.transition(WorkState.SOURCE,c(),active_source_ids=('S1',))
            self.assertEqual(run.source_activity.items[-1].source_ids,('S1',))

    def test_D_is_internal_L1_and_counts_T(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),1,SourceDisposition.WAIVED,'closed')
            run,c=self.bootstrap(td,'DIGR(0,0s,0,0,S(0,0s,0,0),D(1))：x',contract);self.genesis_strategy(run,c)
            iso=run.add_isolation_facts('iso',IsolationFacts(True))
            self.assertEqual((iso.L_target,iso.L_actual),(1,1))
            run.create_d_intervention('D1','iso','challenge');run.decree_d('D1','execute')
            before=run.ledger.formal_T_ns();run.transition(WorkState.D_EXCLUSIVE,c());run.record_d_execution('D1','work');run.record_d_result('D1','result')
            run.transition(WorkState.MAIN,c());after=run.ledger.formal_T_ns();self.assertGreater(after,before)
            run.reintegrate_d('D1',accepted='result',rejected='none',main_consequence='updated')
            run.completion.assess('ready');run.finish_time(c());run.write_run_summary()
            self.assertTrue(verify_run_workspace(run.workspace.root,run.run_id)['integrity_ok'])

    def test_end_to_end_actuals_and_proof_have_no_L(self):
        with tempfile.TemporaryDirectory() as td:
            run,c=self.complete_run(td);a=run.actuals()
            self.assertEqual((a.N,a.R,a.S_count,a.n_min,a.r_min,a.D_s),(1,1,1,1,1,1))
            self.assertTrue(run.stop_check().minima_satisfied);self.assertTrue(run.delivery_ready())
            summary=run.write_run_summary();self.assertTrue(summary['delivery_ready']);self.assertEqual(run.phase.phase,RunPhase.FINISHED)
            proof=run.render_proof();self.assertNotIn('L（',proof)
            self.assertTrue(verify_run_workspace(run.workspace.root,run.run_id)['integrity_ok'])

    def test_unleased_resume_records_gap_and_does_not_restore_state(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClock(start=0,step=100_000_000,session='s1',boot='boot-x')
            contract=EffectiveContract(0,1,0,1,SourceContract(0,0,0,0),0,SourceDisposition.WAIVED,'closed')
            run,c=self.bootstrap(td,'DIGR(0,1s,0,1,S(0,0s,0,0),D(0))：x',contract,clock=c);self.genesis_strategy(run,c)
            root=run.workspace.root
            later=FakeClock(start=10_000_000_000,step=100_000_000,session='s2',boot='boot-x')
            resumed=LiveDIGRRun.resume(root,run.run_id,later)
            self.assertIsNone(resumed.ledger.foreground_state);self.assertFalse(resumed.ledger.T_coverage_complete())
            self.assertGreater(resumed.ledger.unattributed_T_ns(),0)
            with self.assertRaisesRegex(RuntimeError,'active MAIN work state'):resumed.record_main_evolution('x','y','z')

    def test_leased_resume_restores_state_and_counts_cross_host_time(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClock(start=0,step=100_000_000,session='s1',boot='boot-x')
            contract=EffectiveContract(0,1,0,1,SourceContract(0,0,0,0),0,SourceDisposition.WAIVED,'closed')
            run,c=self.bootstrap(td,'DIGR(0,1s,0,1,S(0,0s,0,0),D(0))：x',contract,clock=c);self.genesis_strategy(run,c)
            run.open_work_lease(c());root=run.workspace.root
            later=FakeClock(start=10_000_000_000,step=100_000_000,session='s2',boot='boot-x')
            resumed=LiveDIGRRun.resume(root,run.run_id,later)
            self.assertEqual(resumed.ledger.foreground_state,WorkState.MAIN)
            self.assertTrue(resumed.ledger.T_coverage_complete());self.assertGreater(resumed.ledger.formal_T_ns(),1_000_000_000)
            resumed.record_main_evolution('resume','continue','counted')

    def test_source_lease_restores_binding_and_counts_t(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClock(start=0,step=100_000_000,session='s1',boot='boot-x')
            contract=EffectiveContract(0,0,0,0,SourceContract(1,1,0,1),0,SourceDisposition.REQUIRED)
            run,c=self.bootstrap(td,'DIGR(0,0s,0,0,S(1,1s,0,1),D(0))：x',contract,clock=c);self.genesis_strategy(run,c)
            run.open_source('S1','research');run.transition(WorkState.SOURCE,c(),active_source_ids=('S1',));run.open_work_lease(c())
            later=FakeClock(start=8_000_000_000,step=100_000_000,session='s2',boot='boot-x')
            resumed=LiveDIGRRun.resume(run.workspace.root,run.run_id,later)
            self.assertEqual(resumed.ledger.foreground_state,WorkState.SOURCE);self.assertGreater(resumed.ledger.formal_t_ns(),1_000_000_000)
            resumed.record_source_evolution('S1','finding','external tool','result')

    def test_resume_rolls_clock_epoch_without_killing_run(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClock(start=0,step=100_000_000,session='s1',boot='boot-x');run,c=self.bootstrap(td,clock=c);self.genesis_strategy(run,c)
            run.open_work_lease(c())
            resumed=LiveDIGRRun.resume(run.workspace.root,run.run_id,FakeClock(start=10_000_000_000,step=100_000_000,session='s2',boot=None))
            self.assertEqual(resumed.ledger.foreground_state,WorkState.MAIN)
            self.assertFalse(resumed.ledger.T_coverage_complete())
            self.assertEqual(len(resumed.ledger.continuity_gaps),1)
            resumed.record_main_evolution('epoch rollover','continue','run survived')

    def test_finalization_admission_denies_hard_time_without_closing_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClock(start=0,step=100_000_000,session='s1',boot='boot-x')
            contract=EffectiveContract(0,10,0,1,SourceContract(0,0,0,0),0,SourceDisposition.WAIVED,'closed')
            run,c=self.bootstrap(td,'DIGR(0,10s,0,1,S(0,0s,0,0),D(0))：x',contract,clock=c);self.genesis_strategy(run,c)
            run.completion.assess('ready')
            with self.assertRaisesRegex(RuntimeError,'finalization admission denied'):run.finish_time(c())
            self.assertEqual(run.phase.phase,RunPhase.EXECUTING);self.assertFalse(run.ledger.finished)

    def test_finalization_requires_completion_ready(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),0,SourceDisposition.WAIVED,'closed')
            run,c=self.bootstrap(td,'DIGR(0,0s,0,0,S(0,0s,0,0),D(0))：x',contract);self.genesis_strategy(run,c)
            with self.assertRaisesRegex(RuntimeError,'semantic completion'):run.finish_time(c())
            self.assertEqual(run.phase.phase,RunPhase.EXECUTING)

    def test_finish_requires_return_to_main_from_source_or_d(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),1,SourceDisposition.REQUIRED)
            run,c=self.bootstrap(td,'DIGR(0,0s,0,0,S(0,0s,0,0),D(1))：x',contract);self.genesis_strategy(run,c)
            run.open_source('S1','research');run.transition(WorkState.SOURCE,c(),active_source_ids=('S1',));run.record_source_evolution('S1','finding','search','found')
            run.completion.assess('ready')
            with self.assertRaises(RuntimeError):run.finish_time(c())
            run.transition(WorkState.MAIN,c());run.add_isolation_facts('iso',IsolationFacts(True));run.create_d_intervention('D1','iso','p');run.decree_d('D1','d')
            run.transition(WorkState.D_EXCLUSIVE,c())
            with self.assertRaises(RuntimeError):run.finish_time(c())

    def test_final_summary_semantic_tamper_rejected_after_reindex(self):
        with tempfile.TemporaryDirectory() as td:
            run,c=self.complete_run(td);run.write_run_summary();rel='final/run-summary.json';d=run.workspace.read_json(rel)
            d['delivery_ready']=False;run.workspace.write_json(rel,d,kind='run-summary')
            with self.assertRaisesRegex(ValueError,'final run summary drift'):verify_run_workspace(run.workspace.root,run.run_id)

    def test_artifact_tamper_detected(self):
        with tempfile.TemporaryDirectory() as td:
            run,c=self.complete_run(td);p=run.workspace.path('state/strategy-latest.json');d=json.loads(p.read_text())
            d['current_primary_route']='tampered';p.write_text(json.dumps(d))
            with self.assertRaises(ValueError):verify_run_workspace(run.workspace.root,run.run_id)

if __name__=='__main__':unittest.main()
