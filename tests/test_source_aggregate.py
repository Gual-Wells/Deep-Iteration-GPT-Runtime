import unittest
from runtime.source_aggregate import SourceActual, aggregate_sources

class TestSourceAggregate(unittest.TestCase):
    def test_empty(self):
        a=aggregate_sources([])
        self.assertEqual((a.count,a.n_min,a.r_min,a.t_ns),(0,0,0,0))

    def test_min_and_union(self):
        s1=SourceActual(1,5,3,((0,10),(20,30)))
        s2=SourceActual(2,4,7,((5,25),))
        a=aggregate_sources([s1,s2])
        self.assertEqual(a.count,2)
        self.assertEqual(a.n_min,4); self.assertEqual(a.r_min,3)
        self.assertEqual(a.t_ns,30)

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_sources([SourceActual(1,1,1),SourceActual(1,2,2)])

    def test_bad_interval(self):
        with self.assertRaises(ValueError): SourceActual(1,1,1,((10,5),))
        with self.assertRaises(TypeError): SourceActual(1,1,1,((True,5),))

if __name__ == '__main__': unittest.main()
