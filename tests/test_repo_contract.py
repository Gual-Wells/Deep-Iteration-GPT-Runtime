import json,unittest
from pathlib import Path
from runtime.workspace import WORKSPACE_SCHEMA_VERSION,REQUIRED_GENESIS_FILES,STATE_DIRECTORIES
ROOT=Path(__file__).resolve().parents[1]

class TestRepoContract(unittest.TestCase):
    def test_version_manifest_and_corrected_interfaces(self):
        self.assertEqual((ROOT/'VERSION').read_text().strip(),'5.0.0-alpha.7')
        m=json.loads((ROOT/'manifest.json').read_text());self.assertEqual(m['version'],'5.0.0-alpha.7')
        self.assertEqual((m['run_session_schema'],m['parameter_resolution_schema']),(5,2))
        self.assertNotIn('L_e',m['defaults']);self.assertNotIn('L',m['parameters'])
        self.assertTrue(m['time_states']['D_EXCLUSIVE']['T']);self.assertFalse(m['time_states']['D_EXCLUSIVE']['t'])

    def test_indexed_staged_startup_is_manifested(self):
        m=json.loads((ROOT/'manifest.json').read_text());self.assertEqual(m['bootstrap_index'],'bootstrap/INDEX.md')
        self.assertEqual(m['execution_bundle']['members'],[m['entrypoint'],*m['core']])

    def test_transparent_machine_index_is_structural_first_path(self):
        m=json.loads((ROOT/'manifest.json').read_text());t=(ROOT/m['bootstrap_index']).read_text()
        for x in ('Reality model','Machine topology','Truth-source map','Structure-closed, intelligence-open','Execute-before-interpret inoculation','Implementation delivery reality'):
            self.assertIn(x,t)

    def test_run_lifecycle_is_reliability_not_planner(self):
        t=(ROOT/'core/25_RUN_SESSION_AND_EXTERNAL_MEMORY.md').read_text().lower()
        for x in ('genesis','parameter_resolved','aborted','work lease','coverage gap'):self.assertIn(x,t)

    def test_formal_time_contract(self):
        t=(ROOT/'core/60_FORMAL_ACTIVE_TIME.md').read_text().lower()
        for x in ('main','source','d_exclusive','work lease','coverage','same provider','boot'):self.assertIn(x,t)

    def test_internal_L1_not_public_L(self):
        p=(ROOT/'core/11_PARAMETER_FORMAT_AND_RESOLUTION.md').read_text()
        self.assertIn('N < T < R < B < S < D',p);self.assertNotIn(' < L',p)
        iso=(ROOT/'core/77_ISOLATION_LEVELS.md').read_text().lower()
        self.assertIn('internal',iso);self.assertIn('l1',iso)
        proof=(ROOT/'core/80_STOP_AND_PROOF.md').read_text();self.assertNotIn('L（',proof)

    def test_workspace_layout_v2_matches_runtime_constants(self):
        d=json.loads((ROOT/'workspace/layout-v2.json').read_text());self.assertEqual(d['schema_version'],WORKSPACE_SCHEMA_VERSION)
        self.assertEqual(tuple(d['required_genesis_files']),REQUIRED_GENESIS_FILES);self.assertEqual(tuple(d['state_directories']),STATE_DIRECTORIES)

    def test_help_reflects_alpha7_surface(self):
        t=(ROOT/'entry/HELP.md').read_text()
        self.assertIn('N / R / D',t);self.assertNotIn('N / R / D / L',t)
        self.assertIn('D_EXCLUSIVE',t);self.assertIn('work lease',t.lower());self.assertNotIn('L(1)',t)

    def test_alpha6_execution_integrity_remains_manifested(self):
        m=json.loads((ROOT/'manifest.json').read_text());rd=m['runtime_distribution']
        self.assertEqual(rd['artifact_name_template'],'digr-runtime-{SHA}')
        self.assertIn('runtime/execution_integrity.py',m['deterministic_helpers'])

    def test_alpha7_policies(self):
        m=json.loads((ROOT/'manifest.json').read_text());p=m['policies']
        for k in ('D_exclusive_counts_T_not_t','public_L_parameter_removed','internal_D_isolation_fixed_to_L1','formal_work_lease_required_for_cross_host_attribution','unleased_formal_cross_host_gap_is_preserved_not_dropped','hard_time_requires_complete_semantic_time_coverage','finalization_admission_precedes_ledger_finish','FINISHED_requires_delivery_ready'):
            self.assertTrue(p[k])

if __name__=='__main__':unittest.main()
