import hashlib,json,unittest
from pathlib import Path
from runtime.routing import discovery_plan_from_manifest
ROOT=Path(__file__).resolve().parents[1]

class TestRepoContract(unittest.TestCase):
    def test_manifest_navigation_precedes_descriptor(self):
        d=json.loads((ROOT/'runtime-descriptor.json').read_text(encoding='utf-8'));m=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
        self.assertTrue(m['navigation_authority']);self.assertNotIn('compatibility_mirror',m)
        self.assertEqual(m['bootstrap_entry'],'entry/STARTUP.md');self.assertEqual(m['startup_slice'],['entry/STARTUP.md'])
        self.assertEqual((ROOT/'VERSION').read_text(encoding='utf-8').strip(),m['version']);self.assertEqual(d['version'],m['version']);self.assertEqual(d['package_version'],'5.0.0.dev2+berta2')
        self.assertEqual(d['surface']['navigation_authority'],'manifest.json');self.assertEqual(d['surface']['load_phase'],'after_verified_startup_slice')
        adapter=d['minimum_adapter'];self.assertEqual(adapter['repository'],'Gual-Wells/Deep-Iteration-GPT-Runtime');self.assertEqual(adapter['ref'],'stable');self.assertEqual(adapter['descriptor_path'],'runtime-descriptor.json')
        api=d['engine_api'];self.assertEqual(api['preflight_binding'],'runtime.host_adapter.HostAdapter.preflight');self.assertEqual(api['start_binding'],'runtime.host_adapter.HostAdapter.start');self.assertEqual(api['commit_delivery_binding'],'runtime.run_session.LiveDIGRRun.commit_delivery');self.assertEqual(api['enforced_host_integration'],'required_for_canonical_attestation');self.assertEqual(api['execution_without_host'],'MODEL_NATIVE')
    def test_descriptor_artifact_integrity(self):
        d=json.loads((ROOT/'runtime-descriptor.json').read_text(encoding='utf-8'))
        for item in d['artifacts'].values():
            data=(ROOT/item['path']).read_bytes();self.assertEqual(len(data),item['byte_length']);self.assertEqual(hashlib.sha256(data).hexdigest(),item['sha256'])
        b=json.loads((ROOT/d['artifacts']['execution_bundle']['path']).read_text(encoding='utf-8'));rows=[{k:x[k] for k in ('path','sha256','byte_length')} for x in b['members']]
        raw=json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();self.assertEqual(len(rows),d['artifacts']['execution_bundle']['member_count']);self.assertEqual(hashlib.sha256(raw).hexdigest(),d['artifacts']['execution_bundle']['execution_set_sha256'])
    def test_startup_is_self_contained(self):
        text=(ROOT/'entry/STARTUP.md').read_text(encoding='utf-8')
        for token in ('HELP','EXECUTING','INVALID','NATIVE','DIGR是什么？','DIGRAPH','manifest.help','manifest.entrypoint','manifest.core[]','legacy-alpha4','NEEDS_CORRECTION','N=2','R=1','source=auto','D=0'):
            self.assertIn(token,text)
    def test_compact_release_artifacts(self):
        model=(ROOT/'dist/MODEL_PROTOCOL.md').read_bytes();self.assertGreaterEqual(len(model),2000);self.assertLessEqual(len(model),5000);self.assertEqual((ROOT/'dist/HELP.zh-CN.md').read_bytes(),(ROOT/'entry/HELP.md').read_bytes());self.assertFalse((ROOT/'bundle/EXECUTION_PROTOCOL.json').exists())
    def test_manifest_paths_exist(self):
        m=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'));paths=[m['runtime_descriptor'],m['bootstrap_entry'],*m['startup_slice'],m['model_protocol_source'],m['entrypoint'],m['help'],m['workspace_spec'],*m['core'],*m['deterministic_helpers'],*m['schemas'].values()]
        for rel in paths:self.assertTrue((ROOT/rel).is_file(),rel)
    def test_real_manifest_is_runtime_discoverable(self):
        m=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'));plan=discovery_plan_from_manifest(m)
        expected=(m['entrypoint'],*m['core']);self.assertEqual(tuple(m['execution_bundle']['members']),expected);self.assertEqual(plan.full_protocol_paths,expected);self.assertEqual(plan.post_startup_paths,(m['execution_bundle']['path'],))

if __name__=='__main__':unittest.main()
