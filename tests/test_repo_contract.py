import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class TestRepoContract(unittest.TestCase):
    def test_version_and_manifest(self):
        self.assertEqual((ROOT/'VERSION').read_text().strip(),'4.1.0')
        m=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(m['version'],'4.1.0'); self.assertEqual(m['protocol'],'digr-v4.1')
        self.assertEqual(m['bootstrap_entry'],'bootstrap/BOOTSTRAP.md')
        self.assertEqual(m['routing_schema'],1)
        self.assertNotIn('repository_gate',m); self.assertNotIn('repository_loader',m); self.assertNotIn('local_fallback_core',m)

    def test_no_preprotocol_gate_artifacts(self):
        for rel in ('DIGR_EXECUTION_GATE.md','bootstrap/REPOSITORY_ONLY_LOADER.md','runtime/bootstrap_gate.py','schemas/bootstrap-gate.schema.json'):
            self.assertFalse((ROOT/rel).exists(),rel)

    def test_repository_bootstrap_is_versioned(self):
        t=(ROOT/'bootstrap/BOOTSTRAP.md').read_text(encoding='utf-8')
        for x in ('versioned DIGR protocol content','Classify the candidate message','Mandatory task-clock readiness','P_target'):
            self.assertIn(x,t)
        self.assertLess(t.index('Classify the candidate message'),t.index('Mandatory task-clock readiness'))

    def test_authority_core(self):
        t=(ROOT/'core/12_PROTOCOL_AUTHORITY_AND_SELF_HOSTING.md').read_text(encoding='utf-8')
        for x in ('Routing plane vs protocol plane','P_run','P_target','provenance violation','Route failure','Protocol startup failure'):
            self.assertIn(x,t)

    def test_result_sovereignty_native(self):
        t=(ROOT/'core/00_RESULT_SOVEREIGNTY.md').read_text(encoding='utf-8')
        self.assertIn('Result Sovereignty',t); self.assertIn('Constrain stopping, not intelligence',t)
        self.assertIn('Delegated repository semantic authority',t)

    def test_core_execution_semantics_retained(self):
        defaults=(ROOT/'core/15_SEMANTIC_DEFAULT_COMPLETION.md').read_text(encoding='utf-8')
        for x in ('B = 0','b = 0','L(1)'): self.assertIn(x,defaults)
        time=(ROOT/'core/60_FORMAL_ACTIVE_TIME.md').read_text(encoding='utf-8')
        for x in ('MAIN','SOURCE','D_EXCLUSIVE','META','IDLE','observed monotonic duration','hard-verification fact'): self.assertIn(x,time)
        proof=(ROOT/'core/80_STOP_AND_PROOF.md').read_text(encoding='utf-8')
        self.assertIn('DIGR（N/实际N',proof); self.assertIn('`?`',proof)

    def test_helpers_manifested(self):
        m=json.loads((ROOT/'manifest.json').read_text()); helpers=set(m['deterministic_helpers'])
        for rel in ('runtime/routing.py','runtime/task_startup.py','runtime/protocol_authority.py','runtime/validation.py','runtime/isolation_checks.py','runtime/source_aggregate.py'):
            self.assertIn(rel,helpers)

    def test_no_semantic_runtime_parser_or_scores(self):
        self.assertFalse((ROOT/'runtime/reference_parser.py').exists())
        runtime='\n'.join(p.read_text(encoding='utf-8') for p in (ROOT/'runtime').glob('*.py'))
        for bad in ('ambition_score','coup_probability','novelty_score'): self.assertNotIn(bad,runtime)

    def test_release_builder_security_and_export_markers(self):
        text=(ROOT/'tools/build_release.py').read_text(encoding='utf-8')
        for x in ('is_symlink','unsafe release path','ZIP symlink member rejected','SHA256SUMS file set','testzip','export_personalization','--personalization-output'):
            self.assertIn(x,text)

if __name__=='__main__': unittest.main()
