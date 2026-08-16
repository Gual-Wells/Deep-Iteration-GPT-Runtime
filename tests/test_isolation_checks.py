import unittest
from runtime.isolation_checks import IsolationFacts, level_is_supported

class TestIsolationChecks(unittest.TestCase):
    def test_L1(self):
        f=IsolationFacts(semantic_firewall=True)
        self.assertEqual(f.max_claimable_level,1)
        self.assertTrue(level_is_supported(1,f)); self.assertFalse(level_is_supported(2,f))

    def test_L2_requires_all_information_boundaries(self):
        f=IsolationFacts(True,True,True,True,True)
        self.assertEqual(f.max_claimable_level,2)
        missing=IsolationFacts(True,True,True,True,False)
        self.assertEqual(missing.max_claimable_level,1)

    def test_L3_requires_independent_agent_lifecycle_and_tools(self):
        f=IsolationFacts(True,True,True,True,True,True,True,True,True)
        self.assertEqual(f.max_claimable_level,3)
        no_tools=IsolationFacts(True,True,True,True,True,True,True,True,False)
        self.assertEqual(no_tools.max_claimable_level,2)

    def test_second_agent_name_is_not_evidence(self):
        f=IsolationFacts(True,False,False,False,False,True,True,True,True)
        self.assertEqual(f.max_claimable_level,1)

    def test_bool_facts_are_strict(self):
        with self.assertRaises(TypeError): IsolationFacts(semantic_firewall=1)

if __name__ == '__main__': unittest.main()
