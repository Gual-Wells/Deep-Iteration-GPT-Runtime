import json,unittest
from pathlib import Path
try:
    from jsonschema import Draft202012Validator,validate
except ImportError:
    Draft202012Validator=validate=None
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'schemas'
def load(name):return json.loads((S/name).read_text(encoding='utf-8'))

@unittest.skipUnless(Draft202012Validator is not None,'optional test dependency jsonschema is not installed; stdlib validation runs in tests/validate_repo.py')
class TestSchemas(unittest.TestCase):
    def test_all_json_load_and_metaschema_valid(self):
        for p in S.glob('*.json'):
            d=load(p.name);self.assertEqual(d['$schema'],'https://json-schema.org/draft/2020-12/schema');self.assertTrue(d['$id'].endswith('/'+p.name));Draft202012Validator.check_schema(d)
    def test_manifest_navigation_authority(self):
        schema=load('manifest.schema.json');manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'));validate(manifest,schema);self.assertTrue(manifest['navigation_authority']);self.assertEqual(manifest['startup_slice'],['entry/STARTUP.md']);self.assertEqual(schema['properties']['version']['const'],'5.0.0-Berta1')
    def test_stable_terminal_schemas(self):
        phase=load('run-phase.schema.json')['properties']['phase']['enum'];self.assertIn('DELIVERED',phase);self.assertIn('INCOMPLETE',phase)
        brief_phase=load('run-brief.schema.json')['properties']['phase']['enum'];self.assertIn('DELIVERED',brief_phase);self.assertIn('INCOMPLETE',brief_phase)
        self.assertEqual(load('run-summary.schema.json')['properties']['phase']['const'],'DELIVERED')
        self.assertEqual(load('stable-proof.schema.json')['properties']['status']['const'],'DELIVERED')
    def test_protocol_load_requires_container_length(self):
        required=load('executing-protocol-load.schema.json')['required']
        self.assertIn('container_byte_length',required);self.assertIn('manifest_bytes_base64',required)
    def test_resolved_stable_parameters_are_concrete_and_hard_time_is_positive(self):
        from runtime.parameter_resolution import resolve_stable_parameter_surface
        schema=load('parameter-resolution.schema.json');good=resolve_stable_parameter_surface(None).to_dict();validate(good,schema)
        bad={**good,'N':None}
        with self.assertRaises(Exception):validate(bad,schema)
        bad={**good,'S':{**good['S'],'b':1,'t_seconds':0}}
        with self.assertRaises(Exception):validate(bad,schema)

if __name__=='__main__':unittest.main()
