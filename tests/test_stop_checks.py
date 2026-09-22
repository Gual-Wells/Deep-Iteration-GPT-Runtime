import unittest
from runtime.effective_contract import EffectiveContract,SourceContract,SourceDisposition
from runtime.stop_checks import ContractActuals,check_mechanical_minima

class TestStopChecks(unittest.TestCase):
    def contract(self,**kw):
        d=dict(N=2,T_seconds=10,R=2,B=1,S=SourceContract(1,5,1,1),D_s=1,source_disposition=SourceDisposition.REQUIRED)
        d.update(kw);return EffectiveContract(**d)
    def actual(self,**kw):
        d=dict(
            N=2,T_seconds=10,T_hard_verified=True,T_coverage_complete=True,unattributed_T_seconds=0,
            R=2,S_count=1,n_min=1,t_seconds=5,t_hard_verified=True,t_coverage_complete=True,
            unattributed_t_seconds=0,r_min=1,D_s=1,
        );d.update(kw);return ContractActuals(**d)
    def test_all_minima(self):
        x=check_mechanical_minima(self.contract(),self.actual());self.assertTrue(x.minima_satisfied)
    def test_hard_time_requires_verification_and_coverage(self):
        self.assertFalse(check_mechanical_minima(self.contract(),self.actual(T_hard_verified=False)).hard_T_ok)
        x=check_mechanical_minima(self.contract(),self.actual(T_coverage_complete=False,unattributed_T_seconds=3))
        self.assertFalse(x.T_coverage_ok);self.assertFalse(x.hard_T_ok)
        y=check_mechanical_minima(self.contract(),self.actual(t_coverage_complete=False,unattributed_t_seconds=1))
        self.assertFalse(y.t_coverage_ok);self.assertFalse(y.hard_t_ok)
    def test_soft_timing_does_not_gate_coverage(self):
        c=self.contract(B=0,S=SourceContract(1,5,1,0))
        x=check_mechanical_minima(c,self.actual(T_hard_verified=False,T_coverage_complete=False,unattributed_T_seconds=9,t_hard_verified=False,t_coverage_complete=False,unattributed_t_seconds=2))
        self.assertTrue(x.T_coverage_ok);self.assertTrue(x.t_coverage_ok);self.assertTrue(x.hard_T_ok);self.assertTrue(x.hard_t_ok)
    def test_source_presumption_and_waiver(self):
        c=self.contract(S=SourceContract(0,0,0,0),D_s=0)
        self.assertFalse(check_mechanical_minima(c,self.actual(S_count=0,n_min=0,r_min=0,D_s=0)).source_instance_ok)
        c=self.contract(S=SourceContract(0,0,0,0),D_s=0,source_disposition=SourceDisposition.WAIVED,source_waiver_reason='closed transform')
        self.assertTrue(check_mechanical_minima(c,self.actual(S_count=0,n_min=0,r_min=0,D_s=0)).source_instance_ok)
    def test_D_minimum(self):
        self.assertFalse(check_mechanical_minima(self.contract(D_s=2),self.actual(D_s=1)).D_ok)

if __name__=='__main__':unittest.main()
