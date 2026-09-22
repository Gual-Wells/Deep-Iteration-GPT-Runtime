import unittest
from runtime.proof import ProofData,format_actual_duration,format_target_duration,subscript_int

class TestProof(unittest.TestCase):
    def data(self,**kw):
        base=dict(
            N_target=4,N_actual=6,T_target_seconds=600,T_actual_seconds=668,
            R_target=2,R_actual=3,B=1,S_count=3,n_target=2,n_actual=4,
            t_target_seconds=240,t_actual_seconds=312,r_target=1,r_actual=2,b=1,
            D_target=1,D_actual=2,T_hard_verified=True,t_hard_verified=True,
            T_coverage_complete=True,t_coverage_complete=True,
        )
        base.update(kw);return ProofData(**base)
    def test_to_dict_has_no_L(self):
        d=self.data().to_dict();self.assertEqual(set(d),{'main','source','dictator'})
        self.assertNotIn('isolation',d);self.assertTrue(d['main']['T_coverage_complete'])
    def test_canonical(self):
        self.assertEqual(self.data().render(),'DIGR（4/6，10min/11m08s，2/3，1，S₃（2/4，4min/5m12s，1/2，1），D（1）/D（2））')
    def test_unknown_when_hard_unverified_or_coverage_incomplete(self):
        p=self.data(T_hard_verified=False,t_hard_verified=False).render()
        self.assertIn('10min/?',p);self.assertIn('4min/?',p)
        p=self.data(T_coverage_complete=False,t_coverage_complete=False).render()
        self.assertIn('10min/?',p);self.assertIn('4min/?',p)
    def test_soft_unverified_observed_number_can_be_shown(self):
        p=self.data(B=0,b=0,T_hard_verified=False,t_hard_verified=False,T_coverage_complete=False,t_coverage_complete=False).render()
        self.assertIn('10min/11m08s',p);self.assertIn('4min/5m12s',p)
    def test_actual_never_rounds_up(self):
        self.assertEqual(format_target_duration(600),'10min');self.assertEqual(format_actual_duration(599.999),'9m59s')
    def test_fractional_target_preserved(self):self.assertEqual(format_target_duration(0.5),'0.5s')
    def test_subscripts(self):
        self.assertEqual(subscript_int(12),'₁₂')
        with self.assertRaises(TypeError):subscript_int(True)

if __name__=='__main__':unittest.main()
