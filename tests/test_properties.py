import random
import unittest
from runtime.clock_probe import ClockSnapshot
from runtime.effective_contract import EffectiveContract, SourceContract
from runtime.interval_ledger import WorkInterval, WorkState, sum_interval_durations_ns
from runtime.isolation_checks import IsolationFacts
from runtime.proof import ProofData
from runtime.source_aggregate import SourceActual, aggregate_sources
from runtime.stop_checks import ContractActuals, check_mechanical_minima

class TestProperties(unittest.TestCase):
    def test_source_union_bounds_random(self):
        rng=random.Random(400)
        for _ in range(250):
            sources=[]; total_raw=0
            for i in range(1,rng.randint(1,6)+1):
                iv=[]
                for _ in range(rng.randint(0,5)):
                    a=rng.randint(0,1000); b=a+rng.randint(0,200)
                    iv.append((a,b)); total_raw+=b-a
                sources.append(SourceActual(i,rng.randint(0,10),rng.randint(0,10),tuple(iv)))
            agg=aggregate_sources(sources)
            self.assertLessEqual(agg.t_ns,total_raw)
            self.assertEqual(agg.n_min,min(x.n_actual for x in sources))
            self.assertEqual(agg.r_min,min(x.r_actual for x in sources))

    def test_interval_sum_is_additive_random(self):
        rng=random.Random(401)
        items=[]; expected=0
        for i in range(200):
            a=rng.randint(0,1000); d=rng.randint(0,100)
            s=ClockSnapshot('p',f's{i}',None,a,a)
            e=ClockSnapshot('p',f's{i}',None,a+d,a+d)
            items.append(WorkInterval(WorkState.MAIN,s,e,d,True)); expected+=d
        self.assertEqual(sum_interval_durations_ns(items),expected)

    def test_hard_verification_never_improves_when_fact_removed(self):
        rng=random.Random(402)
        c=EffectiveContract(1,10,1,1,SourceContract(1,5,1,1),0,1)
        for _ in range(100):
            t=rng.uniform(0,20); st=rng.uniform(0,10)
            base=dict(N=1,T_seconds=t,T_hard_verified=True,R=1,S_count=1,n_min=1,
                      t_seconds=st,t_hard_verified=True,r_min=1,D_s=0,L_e=1)
            a=check_mechanical_minima(c,ContractActuals(**base))
            base['T_hard_verified']=False
            b=check_mechanical_minima(c,ContractActuals(**base))
            self.assertFalse(b.hard_T_ok)
            if a.minima_satisfied:
                self.assertFalse(b.minima_satisfied)

    def test_proof_hard_unverified_never_leaks_number_random(self):
        rng=random.Random(403)
        for _ in range(100):
            val=rng.uniform(0,10000)
            p=ProofData(1,1,600,val,1,1,1,0,0,0,0,0,0,0,0,0,0,1,1,False,False).render()
            self.assertIn('10min/?',p)

    def test_isolation_level_monotonic_with_stronger_facts(self):
        l1=IsolationFacts(True)
        l2=IsolationFacts(True,True,True,True,True)
        l3=IsolationFacts(True,True,True,True,True,True,True,True,True)
        self.assertEqual([l1.max_claimable_level,l2.max_claimable_level,l3.max_claimable_level],[1,2,3])

if __name__=='__main__': unittest.main()
