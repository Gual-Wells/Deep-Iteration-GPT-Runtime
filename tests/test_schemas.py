import json,unittest
from pathlib import Path
from jsonschema import Draft202012Validator,validate
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'schemas'
def load(name):return json.loads((S/name).read_text(encoding='utf-8'))
class TestSchemas(unittest.TestCase):
    def test_all_json_load_and_metaschema_valid(self):
        for p in S.glob('*.json'):
            d=load(p.name);self.assertEqual(d['$schema'],'https://json-schema.org/draft/2020-12/schema')
            Draft202012Validator.check_schema(d)
    def test_alpha10_manifest_and_protocol_versions(self):
        self.assertEqual(load('manifest.schema.json')['properties']['version']['const'],'5.0.0-alpha.10')
        self.assertEqual(load('execution-protocol-bundle.schema.json')['properties']['version']['const'],'5.0.0-alpha.10')
        self.assertEqual(load('executing-protocol-load.schema.json')['properties']['version']['const'],'5.0.0-alpha.10')
    def test_manifest_instance_conforms(self):
        validate(json.loads((ROOT/'manifest.json').read_text()),load('manifest.schema.json'))
    def test_contract_and_parameter_surfaces(self):
        p=load('parameter-resolution.schema.json');e=load('effective-contract.schema.json')
        self.assertNotIn('L_e',p['properties']);self.assertIn('source_disposition',e['required'])
        self.assertEqual(set(e['properties']['source_disposition']['enum']),{'REQUIRED','WAIVED'})
    def test_workspace_layout_conforms(self):
        validate(json.loads((ROOT/'workspace/layout-v2.json').read_text()),load('run-workspace.schema.json'))
if __name__=='__main__':unittest.main()
