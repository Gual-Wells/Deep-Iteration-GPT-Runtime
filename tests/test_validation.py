import math
import unittest
from runtime.validation import *

class TestValidation(unittest.TestCase):
    def test_nonnegative_int_rejects_bool_and_negative(self):
        for v in (True, False, 1.0, '1', None):
            with self.assertRaises((TypeError, ValueError)):
                require_nonnegative_int('x', v)
        with self.assertRaises(ValueError): require_nonnegative_int('x', -1)
        self.assertEqual(require_nonnegative_int('x', 0), 0)
    def test_binary(self):
        for v in (0,1): self.assertEqual(require_binary('b',v),v)
        for v in (True,2,-1):
            with self.assertRaises((TypeError,ValueError)): require_binary('b',v)
    def test_isolation(self):
        for v in (1,2,3): self.assertEqual(require_isolation_level('L',v),v)
        for v in (True,0,4):
            with self.assertRaises((TypeError,ValueError)): require_isolation_level('L',v)
    def test_finite(self):
        for v in (0,1,1.5): self.assertEqual(require_finite_nonnegative_number('x',v),float(v))
        for v in (True,float('nan'),float('inf'),float('-inf'),-0.1,'1'):
            with self.assertRaises((TypeError,ValueError)): require_finite_nonnegative_number('x',v)

if __name__ == '__main__': unittest.main()
