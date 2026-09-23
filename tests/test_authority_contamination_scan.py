import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestAuthorityContaminationScan(unittest.TestCase):
    def test_local_router_is_version_neutral_and_repository_bound(self):
        t=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').read_text()
        for x in ('精确大写 ASCII `DIGR`','Gual-Wells/Deep-Iteration-GPT-Runtime','stable','manifest.json','VERSION','bootstrap_index','startup_slice','NATIVE','EXECUTING'):self.assertIn(x,t)
        for x in ('B=0','B=1','D=0','Formal Active','LiveDIGRRun'):self.assertNotIn(x,t)
    def test_index_exposes_contracted_machine_not_task_semantics(self):
        t=(ROOT/'bootstrap/INDEX.md').read_text()
        for x in ('deterministic_helpers[]','runtime/runtime_package.py','seven compact core modules','task strategy remains native-model work'):self.assertIn(x,t)
    def test_current_authority_is_manifest_core_only(self):
        m=json.loads((ROOT/'manifest.json').read_text())
        self.assertEqual(len(m['core']),7)
        for p in m['core']:self.assertTrue((ROOT/p).is_file())
    def test_p_target_cannot_rebind(self):
        t=(ROOT/'bootstrap/BOOTSTRAP.md').read_text();self.assertIn('P_target',t);self.assertIn('P_run',t)
if __name__=='__main__':unittest.main()
