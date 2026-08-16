import unittest
from runtime.proof import ProofData, format_actual_duration, format_target_duration, subscript_int

class TestProof(unittest.TestCase):
    def data(self, **kw):
        base=dict(
            N_target=4,N_actual=6,T_target_seconds=600,T_actual_seconds=668,
            R_target=2,R_actual=3,B=1,S_count=3,n_target=2,n_actual=4,
            t_target_seconds=240,t_actual_seconds=312,r_target=1,r_actual=2,b=1,
            D_target=1,D_actual=2,L_target=3,L_actual=3,
            T_hard_verified=True,t_hard_verified=True,
        )
        base.update(kw); return ProofData(**base)

    def test_to_dict_includes_internal_verification_facts(self):
        d=self.data().to_dict()
        self.assertEqual(set(d), {'main','source','dictator','isolation'})
        self.assertTrue(d['main']['T_hard_verified']); self.assertTrue(d['source']['t_hard_verified'])

    def test_canonical(self):
        self.assertEqual(
            self.data().render(),
            'DIGR（4/6，10min/11m08s，2/3，1，S₃（2/4，4min/5m12s，1/2，1），D（1）/D（2），L（3）/L（3））'
        )

    def test_unknown(self):
        p=self.data(T_actual_seconds=None,t_actual_seconds=None,L_actual=None,L_target=1).render()
        self.assertIn('10min/?',p); self.assertIn('4min/?',p); self.assertIn('L（1）/L（?）',p)

    def test_hard_unverified_number_is_hidden(self):
        p=self.data(T_actual_seconds=999,T_hard_verified=False,t_actual_seconds=999,t_hard_verified=False).render()
        self.assertIn('10min/?',p); self.assertIn('4min/?',p)

    def test_soft_unverified_observed_number_can_be_shown(self):
        p=self.data(B=0,b=0,T_hard_verified=False,t_hard_verified=False).render()
        self.assertIn('10min/11m08s',p); self.assertIn('4min/5m12s',p)

    def test_actual_never_rounds_up(self):
        self.assertEqual(format_target_duration(600),'10min')
        self.assertEqual(format_actual_duration(599.999),'9m59s')
        self.assertIn('10min/9m59s',self.data(B=0,T_actual_seconds=599.999).render())

    def test_fractional_target_preserved(self):
        self.assertEqual(format_target_duration(0.5),'0.5s')

    def test_subscripts(self):
        self.assertEqual(subscript_int(12),'₁₂')
        with self.assertRaises(TypeError): subscript_int(True)

    def test_bool_and_nonfinite_rejected(self):
        with self.assertRaises(TypeError): self.data(N_actual=True)
        with self.assertRaises(TypeError): self.data(T_hard_verified=1)
        for field in ('T_target_seconds','T_actual_seconds','t_target_seconds','t_actual_seconds'):
            with self.subTest(field=field):
                with self.assertRaises(ValueError): self.data(**{field:float('nan')})

if __name__ == '__main__': unittest.main()
