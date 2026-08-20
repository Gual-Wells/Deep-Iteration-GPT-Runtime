import unittest
from runtime.effective_contract import SourceContract, EffectiveContract

class TestEffectiveContract(unittest.TestCase):
    def good(self, **kw):
        base=dict(N=1,T_seconds=2.0,R=1,B=0,S=SourceContract(1,2.0,1,0),D_s=0,L_e=1)
        base.update(kw); return EffectiveContract(**base)
    def test_properties(self):
        c=self.good(); self.assertTrue(c.source_required); self.assertFalse(c.D_minimum_positive); self.assertFalse(c.hard_timing_required)
        c=self.good(B=1); self.assertTrue(c.hard_timing_required)
    def test_bool_ints_rejected(self):
        for field in ('N','R','B','D_s','L_e'):
            with self.subTest(field=field):
                with self.assertRaises((TypeError,ValueError)): self.good(**{field:True})
        with self.assertRaises(TypeError): SourceContract(True,1,1,0)
    def test_nonfinite_rejected(self):
        for v in (float('nan'),float('inf'),float('-inf')):
            with self.assertRaises(ValueError): self.good(T_seconds=v)
            with self.assertRaises(ValueError): SourceContract(1,v,1,0)
    def test_L_exact_domain(self):
        for v in (0,4):
            with self.assertRaises(ValueError): self.good(L_e=v)

if __name__ == '__main__': unittest.main()
