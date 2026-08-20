import json,unittest
from pathlib import Path
from jsonschema import Draft202012Validator,validate
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'schemas'
def load(name):return json.loads((S/name).read_text(encoding='utf-8'))

class TestSchemas(unittest.TestCase):
    def test_all_json_load_and_metaschema_valid(self):
        for p in S.glob('*.json'):
            d=load(p.name);self.assertEqual(d['$schema'],'https://json-schema.org/draft/2020-12/schema');self.assertTrue(d['$id'].endswith('/'+p.name));Draft202012Validator.check_schema(d)
    def test_manifest_alpha4_interfaces(self):
        d=load('manifest.schema.json');self.assertEqual(d['properties']['version']['const'],'5.0.0-alpha.4');self.assertEqual(d['properties']['protocol']['const'],'digr-v5.0')
        expect={'routing_schema':4,'repository_transport_schema':3,'invocation_surface_schema':2,'parameter_resolution_schema':1,'run_session_schema':4,'workspace_schema':2,'clock_journal_schema':1,'event_receipt_schema':2}
        for k,v in expect.items():self.assertIn(k,d['required']);self.assertEqual(d['properties'][k]['const'],v)
        self.assertIn('startup_slice',d['required']);self.assertEqual(d['properties']['workspace_spec']['const'],'workspace/layout-v2.json')
    def test_manifest_instance_conforms_to_manifest_schema(self):
        schema=load('manifest.schema.json');manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'));validate(manifest,schema)
    def test_alpha4_routing_schema_is_transport_specific(self):
        d=load('manifest.schema.json')['properties']['routing']
        self.assertFalse(d['additionalProperties'])
        for k in ('ref_api_url','branch_api_url','pinned_raw_template','content_raw_media_type','mutable_ref_policy'):
            self.assertIn(k,d['required'])
        t=load('repository-transport-attempt.schema.json')
        self.assertIn('freshness',t['required']);self.assertIn('success',t['required'])

    def test_execution_bundle_and_load_receipt_schemas(self):
        b=load('execution-protocol-bundle.schema.json');self.assertEqual(b['properties']['schema_version']['const'],1)
        r=load('executing-protocol-load.schema.json');self.assertEqual(r['properties']['schema_version']['const'],1);self.assertIn('manifest_sha256',r['required'])
        m=load('manifest.schema.json');self.assertIn('execution_bundle',m['required']);self.assertEqual(m['properties']['execution_bundle_schema']['const'],1);self.assertEqual(m['properties']['execution_protocol_load_schema']['const'],1)

    def test_surface_four_states_and_syntax_only(self):
        d=load('invocation-surface.schema.json');self.assertEqual(set(d['properties']['kind']['enum']),{'EXECUTING','HELP','NATIVE','INVALID'});self.assertNotIn('N',d['properties']);self.assertNotIn('R',d['properties'])
    def test_parameter_resolution_unique_or_fail_schema(self):
        d=load('parameter-resolution.schema.json');self.assertEqual(set(d['properties']['status']['enum']),{'RESOLVED','AMBIGUOUS','INVALID'});self.assertEqual(d['properties']['B']['enum'],[0,1]);self.assertEqual(d['properties']['L_e']['enum'],[1,2,3])
    def test_effective_contract_source_disposition_and_L_policy(self):
        d=load('effective-contract.schema.json');self.assertIn('source_disposition',d['required']);self.assertEqual(set(d['properties']['source_disposition']['enum']),{'REQUIRED','WAIVED'});self.assertIn('L_mismatch_blocks_delivery',d['required'])
    def test_strategy_schema_forbids_scheduler_fields(self):
        d=load('strategy-state.schema.json');txt=json.dumps(d);self.assertIn('next_step',txt);self.assertIn('score',txt);self.assertIn('priority',txt);self.assertFalse(d['additionalProperties'])
    def test_event_v2_binds_context(self):
        d=load('evolution-event.schema.json');self.assertEqual(set(d['properties']['kind']['enum']),{'MAIN_EVOLUTION','MAIN_REENTRY','SOURCE_EVOLUTION','SOURCE_REENTRY'});self.assertIn('clock_event_ref',d['required']);self.assertIn('strategy_revision',d['required']);self.assertIn('candidate_revision',d['required']);self.assertIn('source_id',d['required'])
    def test_run_phase_lifecycle(self):
        d=load('run-phase.schema.json');self.assertEqual(d['properties']['phase']['enum'],['GENESIS','PARAMETER_RESOLVED','U0_FROZEN','CONTRACT_FROZEN','EXECUTING','FINALIZING','FINISHED','ABORTED'])
    def test_workspace_v2_schema_matches_layout(self):
        schema=load('run-workspace.schema.json');layout=json.loads((ROOT/'workspace/layout-v2.json').read_text());validate(layout,schema);self.assertEqual(layout['schema_version'],2);self.assertIn('state/artifact-index.json',layout['required_genesis_files']);self.assertIn('state/run-phase.json',layout['required_genesis_files'])
    def test_removed_overlapping_schemas_are_absent(self):
        for rel in ('runtime-state.schema.json','invocation.schema.json'):
            self.assertFalse((S/rel).exists())
    def test_alpha2_scaffolding_schemas_exist(self):
        for name in ('parameter-resolution.schema.json','strategy-state.schema.json','candidate-snapshot.schema.json','source-activity-event.schema.json','isolation-receipt.schema.json','isolation-packet.schema.json','run-phase.schema.json','artifact-index.schema.json','run-brief.schema.json','completion-gap.schema.json'):
            self.assertTrue((S/name).is_file(),name)

    def test_run_summary_schema_matches_persisted_final_shape(self):
        d=load('run-summary.schema.json')
        self.assertIn('phase',d['required']);self.assertEqual(d['properties']['phase']['const'],'FINISHED')
        self.assertIn('mechanical_checks',d['required']);self.assertIn('mechanical_checks',d['properties'])

    def test_task_startup_still_requires_three_samples(self):
        d=load('task-startup.schema.json');self.assertEqual(d['properties']['clock']['properties']['samples']['minItems'],3)
if __name__=='__main__':unittest.main()
