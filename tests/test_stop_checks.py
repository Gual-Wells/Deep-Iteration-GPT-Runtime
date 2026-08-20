import unittest
from runtime.effective_contract import EffectiveContract,SourceContract,SourceDisposition
from runtime.stop_checks import ContractActuals,check_mechanical_minima

class TestStopChecks(unittest.TestCase):
    def contract(self,**kw):
        d=dict(N=2,T_seconds=10,R=2,B=1,S=SourceContract(1,5,1,1),D_s=1,L_e=1,source_disposition=SourceDisposition.REQUIRED)
        d.update(kw);return EffectiveContract(**d)
    def actual(self,**kw):
        d=dict(N=2,T_seconds=10,T_hard_verified=True,R=2,S_count=1,n_min=1,t_seconds=5,t_hard_verified=True,r_min=1,D_s=1,L_e=1);d.update(kw);return ContractActuals(**d)
    def test_all(self):self.assertTrue(check_mechanical_minima(self.contract(),self.actual()).minima_satisfied)
    def test_hard_unknown_or_unverified_fails(self):
        for kw in ({'T_seconds':None},{'T_hard_verified':False},{'t_seconds':None},{'t_hard_verified':False}):self.assertFalse(check_mechanical_minima(self.contract(),self.actual(**kw)).minima_satisfied)
    def test_soft_ignores_verification_fact(self):
        c=self.contract(B=0,S=SourceContract(1,5,1,0));x=check_mechanical_minima(c,self.actual(T_hard_verified=False,t_hard_verified=False));self.assertTrue(x.hard_T_ok);self.assertTrue(x.hard_t_ok)
    def test_required_source_needs_instance_even_zero_minima(self):
        c=self.contract(S=SourceContract(0,0,0,0),D_s=0);x=check_mechanical_minima(c,self.actual(S_count=0,n_min=0,r_min=0,D_s=0,L_e=None));self.assertFalse(x.source_instance_ok)
    def test_waived_source_ignores_s_actuals(self):
        c=self.contract(S=SourceContract(0,0,0,0),D_s=0,source_disposition=SourceDisposition.WAIVED,source_waiver_reason='closed transform');x=check_mechanical_minima(c,self.actual(S_count=0,n_min=0,r_min=0,D_s=0,L_e=None));self.assertTrue(x.source_instance_ok)
    def test_L_mismatch_visible_but_nonblocking_by_default(self):
        x=check_mechanical_minima(self.contract(L_e=2),self.actual(L_e=1));self.assertTrue(x.L_ok);self.assertFalse(x.L_target_met)
    def test_L_mismatch_can_be_u0_hard_constraint(self):
        c=self.contract(L_e=2,L_mismatch_blocks_delivery=True);x=check_mechanical_minima(c,self.actual(L_e=1));self.assertFalse(x.L_ok)
    def test_no_completed_D_has_no_completed_intervention_L_gate(self):
        c=self.contract(D_s=0,L_e=3);x=check_mechanical_minima(c,self.actual(D_s=0,L_e=None));self.assertTrue(x.L_ok)
    def test_zero_D_minimum_with_actual_D_uses_normal_L_gate(self):
        c=self.contract(D_s=0,L_e=3,L_mismatch_blocks_delivery=True);x=check_mechanical_minima(c,self.actual(D_s=1,L_e=1));self.assertFalse(x.L_ok);self.assertFalse(x.L_target_met)
        y=check_mechanical_minima(c,self.actual(D_s=1,L_e=3));self.assertTrue(y.L_ok);self.assertTrue(y.L_target_met)
    def test_invalid_actuals(self):
        with self.assertRaises(TypeError):self.actual(N=True)
        with self.assertRaises(ValueError):self.actual(T_seconds=float('nan'))
if __name__=='__main__':unittest.main()
