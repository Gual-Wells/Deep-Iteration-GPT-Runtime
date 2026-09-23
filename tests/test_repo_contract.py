import json,unittest
from pathlib import Path
from runtime.workspace import WORKSPACE_SCHEMA_VERSION,REQUIRED_GENESIS_FILES,STATE_DIRECTORIES
ROOT=Path(__file__).resolve().parents[1]

class TestRepoContract(unittest.TestCase):
    def setUp(self):self.m=json.loads((ROOT/'manifest.json').read_text())
    def test_alpha10_identity_and_contracted_authority(self):
        self.assertEqual((ROOT/'VERSION').read_text().strip(),'5.0.0-alpha.10')
        self.assertEqual(self.m['version'],'5.0.0-alpha.10')
        self.assertEqual(len(self.m['core']),7)
        self.assertEqual(self.m['execution_bundle']['members'],[self.m['entrypoint'],*self.m['core']])
    def test_lightweight_defaults(self):
        d=self.m['defaults'];self.assertEqual((d['B'],d['b'],d['D_s']),(0,0,0))
        self.assertNotIn('s',d['semantic_completion']);self.assertEqual(d['explicit_empty_D'],'semantic_completion')
    def test_single_package_attestation_is_manifested(self):
        self.assertIn('runtime/runtime_package.py',self.m['deterministic_helpers'])
        rd=self.m['runtime_distribution']
        self.assertIn('single_pinned_verifier',rd['identity_verification'])
        self.assertIn('git_tree',rd['attestation_scope'])
    def test_liveness_contraction_policies(self):
        p=self.m['policies']
        for k in ('ordinary_resume_uses_fast_path','full_workspace_audit_is_anomaly_fallback_or_explicit',
                  'state_transition_does_not_force_global_checkpoint','derived_latest_cache_is_unindexed',
                  'journal_reindex_is_batched','compact_D_completion_preferred',
                  'source_disposition_is_semantic_necessity_decision','omitted_D_defaults_zero'):
            self.assertTrue(p[k])
    def test_workspace_genesis_contract(self):
        d=json.loads((ROOT/'workspace/layout-v2.json').read_text())
        self.assertEqual(d['schema_version'],WORKSPACE_SCHEMA_VERSION)
        self.assertEqual(tuple(d['required_genesis_files']),REQUIRED_GENESIS_FILES)
        self.assertIn('protocol-load.json',REQUIRED_GENESIS_FILES)
        self.assertEqual(tuple(d['state_directories']),STATE_DIRECTORIES)
    def test_core_preserves_time_and_finish_invariants(self):
        t=(ROOT/'core/60_FORMAL_ACTIVE_TIME.md').read_text().lower()
        for x in ('main','source','d_exclusive','epoch','worklease'):self.assertIn(x,t)
        f=(ROOT/'core/80_STOP_AND_PROOF.md').read_text();self.assertIn('FINISH',f);self.assertNotIn('L（',f)
if __name__=='__main__':unittest.main()
