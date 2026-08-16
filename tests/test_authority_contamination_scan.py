import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class TestAuthorityContaminationScan(unittest.TestCase):
    def test_local_router_has_no_versioned_protocol_semantics(self):
        text=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').read_text(encoding='utf-8')
        required=('候选路由键','Gual-Wells/Deep-Iteration-GPT-Runtime','stable','40','manifest.json','bootstrap_entry','entrypoint','core','权威委托')
        for x in required: self.assertIn(x,text)
        forbidden=('DIGR_EXECUTION_GATE','B=0','b=0','L(1)','Mature Gambit','Formal Active','P_target','canonical proof','至少取得两次','monotonic')
        for x in forbidden: self.assertNotIn(x,text)

    def test_root_preprotocol_gate_is_absent(self):
        self.assertFalse((ROOT/'DIGR_EXECUTION_GATE.md').exists())
        self.assertFalse((ROOT/'bootstrap/REPOSITORY_ONLY_LOADER.md').exists())
        self.assertFalse((ROOT/'runtime/bootstrap_gate.py').exists())
        self.assertFalse((ROOT/'schemas/bootstrap-gate.schema.json').exists())

    def test_clock_rule_is_repository_versioned(self):
        boot=(ROOT/'bootstrap/BOOTSTRAP.md').read_text(encoding='utf-8')
        entry=(ROOT/'entry/DEEP_ITERATION_ENTRY.md').read_text(encoding='utf-8')
        router=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').read_text(encoding='utf-8')
        self.assertIn('Mandatory task-clock readiness',boot)
        self.assertIn('Task clock readiness',entry)
        self.assertNotIn('clock',router.lower())
        self.assertIn('Help and invalid/non-triggering text do **not** start task runtime or a task clock',boot)

    def test_context_can_feed_u0_but_not_protocol(self):
        t=(ROOT/'core/12_PROTOCOL_AUTHORITY_AND_SELF_HOSTING.md').read_text(encoding='utf-8')
        self.assertIn('Context !-> ProtocolSemantics',t)
        self.assertIn('Context !-> TaskContext',t)
        self.assertIn('U0/evidence',t)

    def test_legacy_routing_is_explicitly_semantic_clean(self):
        t=(ROOT/'docs/MIGRATION_FROM_4.0.md').read_text(encoding='utf-8')
        self.assertIn('current legacy 3.0',t)
        self.assertIn('without importing 4.1 semantics',t)

if __name__=='__main__': unittest.main()
