import random,tempfile,unittest
from pathlib import Path
from runtime.clock_probe import ClockSnapshot
from runtime.effective_contract import EffectiveContract,SourceContract,SourceDisposition
from runtime.interval_ledger import WorkInterval,WorkState,sum_interval_durations_ns
from runtime.isolation_checks import IsolationFacts,make_isolation_receipt
from runtime.parameter_resolution import resolve_parameter_surface,ResolutionStatus
from runtime.proof import ProofData
from runtime.stop_checks import ContractActuals,check_mechanical_minima

class TestProperties(unittest.TestCase):
    def test_interval_sum_additive_random(self):
        rng=random.Random(401);items=[];expected=0
        for i in range(200):
            a=rng.randint(0,1000);d=rng.randint(0,100);s=ClockSnapshot('p',f's{i}',None,a,a);e=ClockSnapshot('p',f's{i}',None,a+d,a+d);items.append(WorkInterval(WorkState.MAIN,s,e,d,True));expected+=d
        self.assertEqual(sum_interval_durations_ns(items),expected)
    def test_hard_verification_never_improves_when_fact_removed(self):
        rng=random.Random(402);c=EffectiveContract(1,10,1,1,SourceContract(1,5,1,1),0,1,SourceDisposition.REQUIRED)
        for _ in range(100):
            base=dict(N=1,T_seconds=rng.uniform(0,20),T_hard_verified=True,R=1,S_count=1,n_min=1,t_seconds=rng.uniform(0,10),t_hard_verified=True,r_min=1,D_s=0,L_e=None);a=check_mechanical_minima(c,ContractActuals(**base));base['T_hard_verified']=False;b=check_mechanical_minima(c,ContractActuals(**base));self.assertFalse(b.hard_T_ok);self.assertFalse(b.minima_satisfied if a.minima_satisfied else b.hard_T_ok)
    def test_proof_hard_unverified_never_leaks_number_random(self):
        rng=random.Random(403)
        for _ in range(100):self.assertIn('10min/?',ProofData(1,1,600,rng.uniform(0,10000),1,1,1,0,0,0,0,0,0,0,0,0,0,1,1,False,False).render())
    def test_isolation_capability_monotonic_but_actual_target_bounded(self):
        l1=IsolationFacts(True);l2=IsolationFacts(True,True,True,True,True);l3=IsolationFacts(True,True,True,True,True,True,True,True,True);self.assertEqual([l1.max_claimable_level,l2.max_claimable_level,l3.max_claimable_level],[1,2,3]);r=make_isolation_receipt('r',2,l3,input_packet_ref='in',output_packet_ref='out');self.assertEqual((r.L_cap,r.L_actual),(3,2))
    def test_two_bare_counts_never_become_time_random(self):
        rng=random.Random(404)
        for _ in range(100):
            a,b=rng.randint(0,20),rng.randint(0,20);r=resolve_parameter_surface(f'({a},{b})');self.assertEqual(r.status,ResolutionStatus.RESOLVED);self.assertEqual((r.N,r.T_seconds,r.R),(a,None,b))
    def test_three_bare_counts_never_silently_gain_duration(self):
        for i in range(25):self.assertEqual(resolve_parameter_surface(f'({i},{i+1},{i+2})').status,ResolutionStatus.INVALID)
if __name__=='__main__':unittest.main()
