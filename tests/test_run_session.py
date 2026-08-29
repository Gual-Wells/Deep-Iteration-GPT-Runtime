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
from tests.helpers import (
    authority,FakeClock,persist_enforced_host_receipts,protocol_load_receipt,
    stable_invocation_for_contract,stable_preflight_parameters,
)

class TestRunSession(unittest.TestCase):
    def bootstrap(self,td,msg='DIGR(1,1,S,D,L):任务',contract=None,clock=None):
        contract=contract or EffectiveContract(1,0,1,0,SourceContract(1,0,1,0),1,1,SourceDisposition.REQUIRED)
        msg=stable_invocation_for_contract(contract,'task')
        resolved=stable_preflight_parameters(msg)
        c=clock or FakeClock();run=LiveDIGRRun.start(authority(),msg,Path(td),c,run_id='digr-12345678')
        run.bind_protocol_load(protocol_load_receipt())
        r=run.bind_preflight_parameters(resolved);self.assertEqual(r.status.value,'RESOLVED');persist_enforced_host_receipts(run);run.freeze_u0()
        run.freeze_contract(contract);return run,c
    def genesis_strategy(self,run,c):
        run.transition(WorkState.MAIN,c()); return run.save_strategy(StrategyState(0,'task model','primary',('alternative',),'research sources','run tests','use tools',(),(),'genesis',()))
    def complete_run(self,td):
        run,c=self.bootstrap(td); self.genesis_strategy(run,c)
        run.record_main_evolution('changed architecture','implemented','better')
        run.save_candidate_bytes(b'candidate result',summary='candidate result')
        run.record_main_reentry(0,'challenge whole approach','rerun process','retained with evidence',retained=True)
        run.open_source('S1','research x');run.transition(WorkState.SOURCE,c(),active_source_ids=('S1',));run.record_source_evolution('S1','new evidence','searched','found');run.record_source_reentry('S1',0,'cross-check','independent check','confirmed',retained=True)
        run.transition(WorkState.MAIN,c());run.add_isolation_facts('iso1',IsolationFacts(True));run.create_d_intervention('D1','iso1','try orthogonal model');run.revise_d_proposal('D1','try adversarial countermodel','stronger pivot');run.decree_d('D1','execute current gambit');run.transition(WorkState.D_EXCLUSIVE,c());run.record_d_execution('D1','ran challenge');run.record_d_result('D1','no better alternative');run.transition(WorkState.MAIN,c());run.reintegrate_d('D1',accepted='none',rejected='countermodel',main_consequence='retain candidate after independent challenge',candidate_before_revision=0)
        run.completion.assess('quality complete');run.finish_time(c());return run,c
    def test_genesis_precedes_parameter_u0_contract(self):
        with tempfile.TemporaryDirectory() as td:
            message='DIGR(profile=standard,source=off)：任务'
            c=FakeClock();run=LiveDIGRRun.start(authority(),message,Path(td),c,run_id='digr-12345678');self.assertEqual(run.phase.phase,RunPhase.GENESIS);self.assertGreaterEqual(len(run.clock_journal.events),3)
            with self.assertRaises(RuntimeError):run.freeze_u0('任务')
            run.bind_protocol_load(protocol_load_receipt());run.bind_preflight_parameters(stable_preflight_parameters(message));run.freeze_u0();run.freeze_contract(EffectiveContract(2,0,1,0,SourceContract(0,0,0,0),0,1,SourceDisposition.WAIVED,'closed transformation'))
            self.assertEqual(run.phase.phase,RunPhase.CONTRACT_FROZEN)
    def test_parameter_resolution_requires_verified_protocol_load_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClock();run=LiveDIGRRun.start(authority(),'DIGR：任务',Path(td),c,run_id='digr-12345678')
            with self.assertRaisesRegex(RuntimeError,'protocol load receipt required'):
                run.resolve_parameters()
            run.bind_protocol_load(protocol_load_receipt())
            with self.assertRaisesRegex(RuntimeError,'pre-Genesis preflight'):
                run.resolve_parameters()
            self.assertEqual(run.bind_preflight_parameters(stable_preflight_parameters('DIGR:task')).status.value,'RESOLVED')

    def test_post_genesis_protocol_load_abort_is_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClock();run=LiveDIGRRun.start(authority(),'DIGR：任务',Path(td),c,run_id='digr-12345678')
            run.abort_protocol_load('mandatory execution bundle unavailable')
            self.assertEqual(run.phase.phase,RunPhase.ABORTED)
            with self.assertRaises(RuntimeError):run.resolve_parameters()

    def test_invalid_or_help_native_never_get_live_run(self):
        with tempfile.TemporaryDirectory() as td:
            for msg in ('DIGR/help','DIGR是什么？','digr：任务','DIGR：'):
                with self.assertRaises(RunGenesisError):LiveDIGRRun.start(authority(),msg,Path(td),FakeClock(),run_id='digr-12345678')
    def test_clock_failure_aborts_before_workspace(self):
        class Bad:
            def __init__(self):self.i=0
            def __call__(self):self.i+=1;return ClockSnapshot('p',str(self.i),f'boot-{self.i}',self.i,self.i)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RunGenesisError):LiveDIGRRun.start(authority(),'DIGR：x',Path(td),Bad(),run_id='digr-12345678')
            self.assertFalse((Path(td)/'digr-12345678').exists())
    def test_parameter_invalid_aborts_after_clock_genesis_before_u0(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                stable_preflight_parameters('DIGR(1,1,1):x')
            self.assertEqual(list(Path(td).iterdir()),[])
    def test_explicit_parameters_cannot_be_changed_by_contract_completion(self):
        with tempfile.TemporaryDirectory() as td:
            message='DIGR(N=2,R=1):x';resolved=stable_preflight_parameters(message)
            c=FakeClock();run=LiveDIGRRun.start(authority(),message,Path(td),c,run_id='digr-12345678');run.bind_protocol_load(protocol_load_receipt());run.bind_preflight_parameters(resolved);run.freeze_u0()
            with self.assertRaises(ValueError):run.freeze_contract(EffectiveContract(3,0,1,0,SourceContract(0,0,0,0),0,1,SourceDisposition.WAIVED,'closed'))
    def test_strategy_genesis_is_main_work_not_meta(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),0,1,SourceDisposition.WAIVED,'closed transform')
            run,c=self.bootstrap(td,'DIGR：任务',contract)
            with self.assertRaises(RuntimeError):run.save_strategy(StrategyState(0,'m','r'))
            with self.assertRaises(RuntimeError):run.transition(WorkState.SOURCE,c(),active_source_ids=('S1',))
            run.transition(WorkState.MAIN,c());run.save_strategy(StrategyState(0,'m','r'));self.assertEqual(run.phase.phase,RunPhase.EXECUTING)
    def test_source_work_requires_real_workspace_and_strategy(self):
        with tempfile.TemporaryDirectory() as td:
            run,c=self.bootstrap(td);self.genesis_strategy(run,c)
            with self.assertRaises(ValueError):run.transition(WorkState.SOURCE,c(),active_source_ids=('missing',))
            run.open_source('S1','research');run.transition(WorkState.SOURCE,c(),active_source_ids=('S1',));self.assertEqual(run.source_activity.items[-1].source_ids,('S1',))

    def test_event_scope_must_match_foreground_work_state(self):
        with tempfile.TemporaryDirectory() as td:
            run,c=self.bootstrap(td);self.genesis_strategy(run,c);run.open_source('S1','research')
            with self.assertRaises(RuntimeError):run.record_source_evolution('S1','x','y','z')
            run.transition(WorkState.SOURCE,c(),active_source_ids=('S1',))
            with self.assertRaises(RuntimeError):run.record_main_evolution('x','y','z')
            run.record_source_evolution('S1','x','y','z')

    def test_required_source_needs_timed_semantic_work_not_empty_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),0,1,SourceDisposition.REQUIRED)
            run,c=self.bootstrap(td,'DIGR：x',contract);self.genesis_strategy(run,c);run.open_source('S1','research')
            self.assertEqual(run.actuals().S_count,0);self.assertFalse(run.stop_check().source_instance_ok)
            run.transition(WorkState.SOURCE,c(),active_source_ids=('S1',));run.record_source_evolution('S1','new evidence','read source','updated')
            self.assertEqual(run.actuals().S_count,1);self.assertTrue(run.stop_check().source_instance_ok)

    def test_d_zero_is_minimum_not_disable_and_recovery_accepts_actual_D(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),0,1,SourceDisposition.WAIVED,'closed')
            run,c=self.bootstrap(td,'DIGR：x',contract);self.genesis_strategy(run,c);run.add_isolation_facts('iso',IsolationFacts(True))
            run.create_d_intervention('D1','iso','quality-driven non-local challenge');run.decree_d('D1','execute')
            run.transition(WorkState.D_EXCLUSIVE,c());run.record_d_execution('D1','ran challenge');run.record_d_result('D1','useful result')
            run.transition(WorkState.MAIN,c());run.reintegrate_d('D1',accepted='result',rejected='none',main_consequence='improved answer')
            run.save_candidate_bytes(b'final result',summary='final result');run.completion.assess('ready');run.finish_time(c());self.assertEqual(run.actuals().D_s,1);self.assertTrue(run.stop_check().D_ok)
            run.write_run_summary(b'final result');self.assertTrue(verify_run_workspace(run.workspace.root,run.run_id)['integrity_ok'])

    def test_source_reentry_is_source_result_backed_without_main_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(0,0,0,0,SourceContract(0,0,1,0),0,1,SourceDisposition.REQUIRED)
            run,c=self.bootstrap(td,'DIGR：x',contract);self.genesis_strategy(run,c);run.open_source('S1','research')
            run.transition(WorkState.SOURCE,c(),active_source_ids=('S1',));run.record_source_evolution('S1','finding','search','found')
            event=run.record_source_reentry('S1',0,'challenge source result','independent source check','retained',retained=True)
            self.assertIsNone(event.candidate_revision);self.assertEqual(event.source_revision,0);self.assertEqual(run.actuals().r_min,1)

    def test_l2_packet_lifecycle_and_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),1,2,SourceDisposition.WAIVED,'closed')
            run,c=self.bootstrap(td,'DIGR(D,L(2)):x',contract);self.genesis_strategy(run,c)
            inp=run.write_d_packet('D1-in','input',{'task':'controlled subset'})
            l2=IsolationFacts(True,True,True,True,True)
            run.add_isolation_facts('iso2',l2,input_packet_ref=inp,mode='exclusive');run.create_d_intervention('D1','iso2','orthogonal test');run.decree_d('D1','execute')
            run.transition(WorkState.D_EXCLUSIVE,c());run.record_d_execution('D1','isolated work')
            out=run.write_d_packet('D1-out','output',{'finding':'counterexample not sustained'});run.record_d_result('D1','result',output_packet_ref=out)
            run.transition(WorkState.MAIN,c());run.reintegrate_d('D1',accepted='none',rejected='counterexample',main_consequence='retain route')
            run.save_candidate_bytes(b'final result',summary='final result');run.completion.assess('ready');run.finish_time(c());run.write_run_summary(b'final result');self.assertTrue(verify_run_workspace(run.workspace.root,run.run_id)['integrity_ok'])

    def test_l2_output_packet_tamper_is_rejected_even_if_result_exists(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),1,2,SourceDisposition.WAIVED,'closed')
            run,c=self.bootstrap(td,'DIGR(D,L(2)):x',contract);self.genesis_strategy(run,c);inp=run.write_d_packet('D1-in','input',{'x':1});l2=IsolationFacts(True,True,True,True,True)
            run.add_isolation_facts('iso2',l2,input_packet_ref=inp);run.create_d_intervention('D1','iso2','p');run.decree_d('D1','d');run.transition(WorkState.D_EXCLUSIVE,c());run.record_d_execution('D1','e');out=run.write_d_packet('D1-out','output',{'y':2});run.record_d_result('D1','r',output_packet_ref=out);run.transition(WorkState.MAIN,c());run.reintegrate_d('D1',accepted='a',rejected='r',main_consequence='c')
            run.workspace.path(out).write_text('{"tampered":true}',encoding='utf-8')
            with self.assertRaises(ValueError):verify_run_workspace(run.workspace.root,run.run_id)

    def test_end_to_end_actuals_d_and_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            run,c=self.complete_run(td);a=run.actuals();self.assertEqual((a.N,a.R,a.S_count,a.n_min,a.r_min,a.D_s,a.L_e),(1,1,1,1,1,1,1));self.assertTrue(run.stop_check().minima_satisfied);self.assertTrue(run.delivery_ready());summary=run.write_run_summary(b'candidate result');self.assertTrue(summary['delivery_ready']);self.assertEqual(run.phase.phase,RunPhase.DELIVERED);self.assertTrue(run.render_proof().startswith('DIGR（'));report=verify_run_workspace(run.workspace.root,run.run_id);self.assertTrue(report['integrity_ok'])
    def test_finish_requires_main_and_strategy(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),0,1,SourceDisposition.WAIVED,'closed')
            run,c=self.bootstrap(td,'DIGR：x',contract)
            with self.assertRaises(RuntimeError):run.finish_time(c())
            run.transition(WorkState.MAIN,c())
            with self.assertRaises(RuntimeError):run.finish_time(c())
            run.save_strategy(StrategyState(0,'m','r'));run.save_candidate_bytes(b'final',summary='final');run.completion.assess('ready');run.finish_time(c());self.assertTrue(run.delivery_ready())
    def test_u0_contract_single_freeze(self):
        with tempfile.TemporaryDirectory() as td:
            message='DIGR(profile=standard,source=off):x';resolved=stable_preflight_parameters(message)
            c=FakeClock();run=LiveDIGRRun.start(authority(),message,Path(td),c,run_id='digr-12345678');run.bind_protocol_load(protocol_load_receipt());run.bind_preflight_parameters(resolved);run.freeze_u0()
            with self.assertRaises(RuntimeError):run.freeze_u0('y')
            k=EffectiveContract(2,0,1,0,SourceContract(0,0,0,0),0,1,SourceDisposition.WAIVED,'closed');run.freeze_contract(k)
            with self.assertRaises(RuntimeError):run.freeze_contract(k)
    def test_resume_requires_equal_nonempty_boot_and_restores_live_state(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClock(start=0,step=100,session='s1',boot='boot-x');run,c=self.bootstrap(td,clock=c);self.genesis_strategy(run,c);run.save_candidate(CandidateSnapshot(0,'candidate'));run.open_source('S1','research')
            root=run.workspace.root;later=FakeClock(start=10_000,step=100,session='s2',boot='boot-x');resumed=LiveDIGRRun.resume(root,run.run_id,later);self.assertEqual(resumed.phase.phase,RunPhase.EXECUTING);self.assertEqual(resumed.strategy.current.revision,0);self.assertEqual(resumed.candidates.current.revision,0);self.assertTrue(resumed.sources.exists('S1'));self.assertTrue(any(e.event=='RESUME_READY' for e in resumed.clock_journal.events))
            # Resume reconnects trustworthy clock continuity but intentionally
            # does not guess which semantic work state survived a process gap.
            self.assertIsNone(resumed.ledger.foreground_state)
            with self.assertRaisesRegex(RuntimeError,'active MAIN work state'):
                resumed.record_main_evolution('resume','continue','wrongly implicit')
            resumed.transition(WorkState.MAIN,later());resumed.record_main_evolution('resume','continue','explicit state restored')
            self.assertTrue(verify_run_workspace(root,run.run_id)['integrity_ok'])
    def test_resume_fails_closed_without_boot_continuity(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClock(start=0,step=100,session='s1',boot='boot-x');run,c=self.bootstrap(td,clock=c);self.genesis_strategy(run,c)
            with self.assertRaises(RunResumeError):LiveDIGRRun.resume(run.workspace.root,run.run_id,FakeClock(start=10_000,step=100,session='s2',boot=None))

    def test_finish_time_requires_return_to_main_from_source_or_d(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),1,1,SourceDisposition.REQUIRED)
            run,c=self.bootstrap(td,'DIGR(D,L):x',contract);self.genesis_strategy(run,c);run.open_source('S1','research');run.transition(WorkState.SOURCE,c(),active_source_ids=('S1',));run.record_source_evolution('S1','finding','search','found')
            with self.assertRaises(RuntimeError):run.finish_time(c())
            run.transition(WorkState.MAIN,c());run.add_isolation_facts('iso',IsolationFacts(True));run.create_d_intervention('D1','iso','p');run.decree_d('D1','d');run.transition(WorkState.D_EXCLUSIVE,c())
            with self.assertRaises(RuntimeError):run.finish_time(c())

    def test_run_brief_semantic_tamper_rejected_after_reindex(self):
        with tempfile.TemporaryDirectory() as td:
            run,c=self.complete_run(td)
            rel='state/run-brief.json';d=run.workspace.read_json(rel);d['phase']='EXECUTING'
            base={k:v for k,v in d.items() if k!='content_digest'}
            d['content_digest']=hashlib.sha256(json.dumps(base,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            run.workspace.write_json(rel,d,kind='run-brief')
            with self.assertRaisesRegex(ValueError,'run brief drift'):
                verify_run_workspace(run.workspace.root,run.run_id)

    def test_final_summary_semantic_tamper_rejected_after_reindex(self):
        with tempfile.TemporaryDirectory() as td:
            run,c=self.complete_run(td);run.write_run_summary(b'candidate result');rel='final/run-summary.json';d=run.workspace.read_json(rel);d['delivery_ready']=not d['delivery_ready']
            with self.assertRaisesRegex(RuntimeError,'terminal workspace is sealed'):
                run.workspace.write_json(rel,d,kind='run-summary')

    def test_reintegration_clock_binding_is_semantically_verified(self):
        with tempfile.TemporaryDirectory() as td:
            run,c=self.complete_run(td);run.write_run_summary(b'candidate result');item=run.dictator.latest('D1');d=item.to_dict()
            d_exclusive=next(e.record_hash for e in run.clock_journal.events if e.event=='STATE' and e.state is WorkState.D_EXCLUSIVE)
            d['reintegration']['clock_event_ref']=d_exclusive
            rev=item.state_revision
            with self.assertRaisesRegex(RuntimeError,'terminal workspace is sealed'):
                run.workspace.write_json(f'dictator/D1-r{rev:04d}.json',d,kind='d-intervention',revision=rev)

    def test_artifact_tamper_detected(self):
        with tempfile.TemporaryDirectory() as td:
            run,c=self.complete_run(td);p=run.workspace.path('state/strategy-latest.json');d=json.loads(p.read_text(encoding='utf-8'));d['current_primary_route']='tampered';p.write_text(json.dumps(d),encoding='utf-8')
            with self.assertRaises(ValueError):verify_run_workspace(run.workspace.root,run.run_id)
if __name__=='__main__':unittest.main()
