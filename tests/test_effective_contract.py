import unittest
from runtime.effective_contract import SourceContract,EffectiveContract,SourceDisposition

class TestEffectiveContract(unittest.TestCase):
    def good(self,**kw):
        base=dict(N=1,T_seconds=2.0,R=1,B=0,S=SourceContract(1,2.0,1,0),D_s=0,source_disposition=SourceDisposition.REQUIRED)
        base.update(kw);return EffectiveContract(**base)
    def test_properties(self):
        c=self.good();self.assertTrue(c.source_required);self.assertFalse(c.D_minimum_positive);self.assertFalse(c.hard_timing_required)
        self.assertTrue(self.good(B=1).hard_timing_required)
    def test_source_disposition_must_be_explicit(self):
        with self.assertRaises(TypeError):EffectiveContract(1,2,1,0,SourceContract(0,0,0,0),0)
    def test_bool_ints_rejected(self):
        for field in ('N','R','B','D_s'):
            with self.subTest(field=field):
                with self.assertRaises((TypeError,ValueError)):self.good(**{field:True})
        with self.assertRaises(TypeError):SourceContract(True,1,1,0)
    def test_nonfinite_rejected(self):
        for v in (float('nan'),float('inf'),float('-inf')):
            with self.assertRaises(ValueError):self.good(T_seconds=v)
            with self.assertRaises(ValueError):SourceContract(1,v,1,0)
    def test_waived_source_requires_zero_work_targets_and_reason(self):
        c=EffectiveContract(0,0,0,0,SourceContract(0,0,0,1),0,SourceDisposition.WAIVED,'closed-world')
        self.assertFalse(c.source_required)
        with self.assertRaises(ValueError):EffectiveContract(0,0,0,0,SourceContract(1,0,0,0),0,SourceDisposition.WAIVED,'closed-world')
if __name__=='__main__':unittest.main()
