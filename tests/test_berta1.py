import tempfile,unittest
from pathlib import Path

from runtime.effective_contract import EffectiveContract,SourceContract,SourceDisposition
from runtime.interval_ledger import WorkState
from runtime.parameter_resolution import ResolutionStatus,resolve_stable_parameter_surface
from runtime.run_recovery import verify_run_workspace
from runtime.run_session import LiveDIGRRun
from runtime.strategy_store import StrategyState
from tests.helpers import authority,FakeClock,persist_enforced_host_receipts,protocol_load_receipt,stable_preflight_parameters


class TestBerta1(unittest.TestCase):
    def test_canonical_and_flat_typed_parameters(self):
        canonical=resolve_stable_parameter_surface('(3,5min,2,1,S(1,30s,1,0),D(2),V(4),L(3))')
        self.assertEqual(canonical.status,ResolutionStatus.RESOLVED)
        self.assertEqual((canonical.N,canonical.T_seconds,canonical.R,canonical.D_s,canonical.V_o,canonical.L_e),(3,300,2,2,4,3))
        flat=resolve_stable_parameter_surface('(o=4,e=3,s=2,n=1,t=30s,r=1,b=0,N=3,T=5min,R=2,B=1)')
        self.assertEqual(flat.status,ResolutionStatus.RESOLVED)
        self.assertEqual((flat.S.n,flat.S.t_seconds,flat.S.r,flat.V_o),(1,30,1,4))

    def test_duplicate_and_ambiguous_remaining_values_fail(self):
        duplicate=resolve_stable_parameter_surface('(V=2,o=2)')
        self.assertEqual(duplicate.status,ResolutionStatus.INVALID)
        ambiguous=resolve_stable_parameter_surface('(V=1,2)')
        self.assertEqual(ambiguous.status,ResolutionStatus.AMBIGUOUS)
        self.assertIn('candidates:',ambiguous.reason)

    def test_v_clock_qualification_logs_proof_and_recovery(self):
        message='DIGR(N=0,T=0s,R=0,B=0,S(0,0s,0,0),D(0),V(1),L(1)):task'
        parameters=stable_preflight_parameters(message)
        contract=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),0,1,SourceDisposition.WAIVED,'closed local task',False,1)
        with tempfile.TemporaryDirectory() as td:
            clock=FakeClock();run=LiveDIGRRun.start(authority(),message,Path(td),clock,run_id='digr-berta100')
            run.bind_protocol_load(protocol_load_receipt());run.bind_preflight_parameters(parameters)
            persist_enforced_host_receipts(run);run.freeze_u0();run.freeze_contract(contract)
            run.transition(WorkState.MAIN,clock());run.save_strategy(StrategyState(0,'model','route'))
            run.save_candidate_bytes(b'final',summary='final')
            run.open_viewpoint('V1','an orthogonal domain model')
            run.transition(WorkState.V_EXCLUSIVE,clock(),active_v_ids=('V1',))
            run.record_viewpoint_event('V1','transfer a distant invariant','found a useful boundary')
            run.transition(WorkState.MAIN,clock())
            run.qualify_viewpoint('V1','boundary retained by Main','different domain and loss function')
            run.completion.assess_structured({
                'objective_coverage':(True,'task covered'),
                'evidence_integrity':(True,'bound receipts'),
                'adversarial_resilience':(True,'orthogonal view checked'),
                'residual_risk':(True,'no blocking residual risk'),
            })
            run.finish_time(clock());actual=run.actuals()
            self.assertEqual(actual.V_o,1);self.assertGreater(actual.V_actual_seconds,0);self.assertTrue(actual.V_time_verified)
            run.commit_delivery(b'final',media_type='text/plain')
            proof=run.render_proof();self.assertIn('V（1）/V（1）',proof);self.assertIn('（+',proof)
            for name in ('TOTAL','N','T','R','B','S','D','V','L'):
                self.assertTrue(run.workspace.path(f'logs/{name}.ndjson').is_file())
            self.assertTrue(verify_run_workspace(run.workspace.root,run.run_id)['integrity_ok'])


if __name__=='__main__':unittest.main()
