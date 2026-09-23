import unittest
from runtime.parameter_resolution import resolve_parameter_surface,ResolutionStatus

class TestParameterResolution(unittest.TestCase):
    def r(self,s,sem=None): return resolve_parameter_surface(s,sem)
    def test_empty_and_defaults(self):
        for x in (None,'','()'):
            r=self.r(x); self.assertEqual(r.status,ResolutionStatus.RESOLVED)
            self.assertIsNone(r.N); self.assertIsNone(r.T_seconds); self.assertIsNone(r.R)
            self.assertEqual((r.B,r.S.b),(0,0)); self.assertFalse(hasattr(r,'L_e'))
    def test_one_value_is_typed_or_ambiguous(self):
        self.assertEqual(self.r('(1)').status,ResolutionStatus.AMBIGUOUS)
        self.assertEqual(self.r('(10min)').T_seconds,600)
        self.assertEqual(self.r('(半小时)').T_seconds,1800)
    def test_two_counts_are_N_R(self):
        r=self.r('(1,2)'); self.assertEqual((r.N,r.T_seconds,r.R,r.B),(1,None,2,0))
    def test_three_and_four_require_duration_middle(self):
        r=self.r('(1,10min,2)'); self.assertEqual((r.N,r.T_seconds,r.R,r.B),(1,600,2,0))
        r=self.r('(1,10min,2,0)'); self.assertEqual((r.N,r.T_seconds,r.R,r.B),(1,600,2,0))
        self.assertEqual(self.r('(1,1,1)').status,ResolutionStatus.INVALID)
    def test_markers_are_S_then_D_only(self):
        r=self.r('(1,2,S,D)'); self.assertEqual(r.status,ResolutionStatus.RESOLVED)
        self.assertEqual((r.N,r.R,r.D_s),(1,2,None)); self.assertIsNone(r.S.n)
        self.assertEqual(self.r('(S)').status,ResolutionStatus.RESOLVED)
        for x in ('(L)','(L(2))','(L=2)','(e=2)','(1,2,S,D,L)'):
            self.assertEqual(self.r(x).status,ResolutionStatus.INVALID,x)
    def test_full_nested(self):
        r=self.r('(1,10min,2,1,S(3,5min,4,1),D(2))')
        self.assertEqual((r.N,r.T_seconds,r.R,r.B),(1,600,2,1))
        self.assertEqual((r.S.n,r.S.t_seconds,r.S.r,r.S.b),(3,300,4,1)); self.assertEqual(r.D_s,2)
    def test_fullwidth_mixed_header_normalization(self):
        r=self.r('（1，10min，2，S（3，5min，4），D（2））')
        self.assertEqual(r.status,ResolutionStatus.RESOLVED); self.assertEqual((r.N,r.R,r.S.n,r.S.r,r.D_s),(1,2,3,4,2))
    def test_d_tail(self):
        r=self.r('(1,10min,2,0,1)'); self.assertEqual(r.D_s,1)
        r=self.r('(1,10min,2,0,D,2)'); self.assertEqual(r.status,ResolutionStatus.INVALID)
        r=self.r('(1,10min,2,0,S,1)'); self.assertEqual(r.D_s,1)
    def test_explicit_labels_obey_order(self):
        r=self.r('(N=1,R=2)'); self.assertEqual((r.N,r.R),(1,2))
        r=self.r('(N=1,D=2)'); self.assertEqual((r.N,r.D_s),(1,2))
        for x in ('(R=2,1)','(N=1,1,R=2)','(D=2,N=1)'):
            self.assertEqual(self.r(x).status,ResolutionStatus.INVALID,x)
    def test_bare_number_never_duration(self):
        for x in ('(T=10)','(N=1,T=10,R=1)','(S(t=10))'):
            self.assertEqual(self.r(x).status,ResolutionStatus.INVALID,x)
    def test_semantic_classification_is_input_not_mapping_authority(self):
        r=self.r('(三轮,十分钟,2次)',{'三轮':'3','十分钟':'10min','2次':'2'})
        self.assertEqual(r.status,ResolutionStatus.RESOLVED); self.assertEqual((r.N,r.T_seconds,r.R),(3,600,2))
        self.assertTrue(any('semantic-normalization' in x for x in r.diagnostics))
        self.assertEqual(self.r('(十)',{'十':'10'}).status,ResolutionStatus.AMBIGUOUS)
    def test_duplicate_or_out_of_order_markers_invalid(self):
        for x in ('(S,S)','(D,S)','(D,D)'):
            self.assertEqual(self.r(x).status,ResolutionStatus.INVALID,x)

if __name__=='__main__': unittest.main()
