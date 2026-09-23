import unittest
from runtime.parameter_resolution import resolve_parameter_surface,ResolutionStatus
class TestParameterResolution(unittest.TestCase):
    def r(self,s,sem=None):return resolve_parameter_surface(s,sem)
    def test_empty_defaults_include_zero_D(self):
        for x in (None,'','()'):
            r=self.r(x);self.assertEqual(r.status,ResolutionStatus.RESOLVED)
            self.assertEqual((r.B,r.S.b,r.D_s),(0,0,0))
    def test_omitted_D_is_zero_but_explicit_empty_D_is_semantic(self):
        self.assertEqual(self.r('(N=2,R=1)').D_s,0)
        self.assertIsNone(self.r('(N=2,R=1,D)').D_s)
        self.assertIsNone(self.r('(N=2,R=1,D())').D_s)
        self.assertEqual(self.r('(N=2,R=1,D=3)').D_s,3)
    def test_duration_and_order(self):
        r=self.r('(1,10min,2,1,S(3,5min,4,1),D(2))')
        self.assertEqual((r.N,r.T_seconds,r.R,r.B,r.S.n,r.S.t_seconds,r.S.r,r.S.b,r.D_s),(1,600,2,1,3,300,4,1,2))
        for x in ('(T=10)','(S(t=10))','(D,S)','(L=2)'):
            self.assertEqual(self.r(x).status,ResolutionStatus.INVALID,x)
    def test_bare_count_ambiguity_preserved(self):
        self.assertEqual(self.r('(1)').status,ResolutionStatus.AMBIGUOUS)
        self.assertEqual(self.r('(1,2)').status,ResolutionStatus.RESOLVED)
if __name__=='__main__':unittest.main()
