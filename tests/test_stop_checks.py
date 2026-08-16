import unittest
from runtime.effective_contract import SourceContract, EffectiveContract
from runtime.stop_checks import ContractActuals, check_mechanical_minima

class TestStopChecks(unittest.TestCase):
    def contract(self): return EffectiveContract(2,10,2,1,SourceContract(1,5,1,1),1,1)
    def actual(self, **kw):
        d=dict(N=2,T_seconds=10,T_hard_verified=True,R=2,S_count=1,n_min=1,
               t_seconds=5,t_hard_verified=True,r_min=1,D_s=1,L_e=1)
        d.update(kw); return ContractActuals(**d)

    def test_all(self):
        self.assertTrue(check_mechanical_minima(self.contract(),self.actual()).minima_satisfied)

    def test_unknown_or_unverified_hard_fails(self):
        self.assertFalse(check_mechanical_minima(self.contract(),self.actual(T_seconds=None)).hard_T_ok)
        self.assertFalse(check_mechanical_minima(self.contract(),self.actual(T_hard_verified=False)).hard_T_ok)
        self.assertFalse(check_mechanical_minima(self.contract(),self.actual(t_seconds=None)).hard_t_ok)
        self.assertFalse(check_mechanical_minima(self.contract(),self.actual(t_hard_verified=False)).hard_t_ok)

    def test_soft_ignores_hard_verification_fact(self):
        c=EffectiveContract(2,10,2,0,SourceContract(1,5,1,0),1,1)
        x=check_mechanical_minima(c,self.actual(T_hard_verified=False,t_hard_verified=False))
        self.assertTrue(x.hard_T_ok); self.assertTrue(x.hard_t_ok)

    def test_positive_source_contract_requires_instance(self):
        x=check_mechanical_minima(self.contract(),self.actual(S_count=0,n_min=0,r_min=0))
        self.assertFalse(x.source_instance_ok)

    def test_L_exact(self): self.assertFalse(check_mechanical_minima(self.contract(),self.actual(L_e=2)).L_ok)

    def test_invalid_actuals(self):
        with self.assertRaises(TypeError): self.actual(N=True)
        with self.assertRaises(ValueError): self.actual(T_seconds=float('nan'))
        with self.assertRaises(TypeError): self.actual(T_hard_verified=1)

if __name__ == '__main__': unittest.main()
