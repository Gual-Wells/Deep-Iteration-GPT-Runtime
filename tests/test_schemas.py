import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'schemas'
def load(name): return json.loads((S/name).read_text(encoding='utf-8'))

class TestSchemas(unittest.TestCase):
    def test_all_json_load_and_ids(self):
        for p in S.glob('*.json'):
            d=json.loads(p.read_text(encoding='utf-8'))
            self.assertEqual(d['$schema'],'https://json-schema.org/draft/2020-12/schema')
            self.assertTrue(d['$id'].endswith('/'+p.name))

    def test_invocation_has_no_auto(self):
        d=load('invocation.schema.json'); text=json.dumps(d)
        self.assertNotIn('"auto"',text.lower()); self.assertIn('task',text)

    def test_effective_contract_closed(self):
        d=load('effective-contract.schema.json')
        self.assertFalse(d['additionalProperties']); self.assertFalse(d['properties']['S']['additionalProperties'])
        self.assertIn('D_s',d['properties']); self.assertIn('L_e',d['properties'])

    def test_route_receipt_schema(self):
        d=load('route-receipt.schema.json')
        self.assertEqual(d['properties']['repository_full_name']['const'],'Gual-Wells/Deep-Iteration-GPT-Runtime')
        self.assertEqual(d['properties']['requested_ref']['const'],'stable')
        self.assertEqual(d['properties']['manifest_path']['const'],'manifest.json')
        self.assertNotIn('clock',json.dumps(d).lower())

    def test_authority_binds_route_and_P_run_only(self):
        d=load('protocol-authority.schema.json')
        self.assertEqual(set(d['required']),{'route','P_run'})
        self.assertNotIn('target_protocol',json.dumps(d)); self.assertNotIn('gate_id',json.dumps(d))
        self.assertFalse(d['additionalProperties'])

    def test_task_startup_schema(self):
        d=load('task-startup.schema.json')
        self.assertEqual(set(d['required']),{'authority','clock','u0_frozen'})
        self.assertEqual(d['properties']['u0_frozen']['const'],False)
        self.assertEqual(d['properties']['clock']['properties']['ready']['const'],True)

    def test_runtime_requires_task_startup_not_bootstrap_gate(self):
        d=load('runtime-state.schema.json')
        self.assertIn('task_startup',d['required']); self.assertNotIn('bootstrap_gate',d['required'])
        self.assertEqual(d['properties']['task_startup']['$ref'],'task-startup.schema.json')
        self.assertNotIn('authority',d['required']); self.assertNotIn('authority',d['properties'])
        time=d['properties']['time']
        for name in ('timing_ready','T_hard_verified','t_hard_verified','T_actual_ns','t_actual_ns'): self.assertIn(name,time['required'])

    def test_manifest_has_repository_bootstrap_not_preprotocol_gate(self):
        d=load('manifest.schema.json')
        self.assertIn('bootstrap_entry',d['required']); self.assertEqual(d['properties']['bootstrap_entry']['const'],'bootstrap/BOOTSTRAP.md')
        self.assertNotIn('repository_gate',d['properties']); self.assertNotIn('repository_loader',d['properties'])

    def test_draft202012_behavior_when_jsonschema_available(self):
        try:
            from jsonschema import Draft202012Validator
            from referencing import Registry, Resource
        except Exception:
            self.skipTest('jsonschema/referencing unavailable')
        schemas={p.name:load(p.name) for p in S.glob('*.json')}
        registry=Registry()
        for d in schemas.values(): registry=registry.with_resource(d['$id'],Resource.from_contents(d))
        def validate(name,instance): Draft202012Validator(schemas[name],registry=registry).validate(instance)

        invocation={'enabled':True,'kind':'task','alias':'DIGR','task_raw':'x','explicit':{}}
        validate('invocation.schema.json',invocation)
        with self.assertRaises(Exception): validate('invocation.schema.json',{'enabled':True,'kind':'task','alias':'DIGR','task_raw':'','explicit':{}})

        route={'repository_full_name':'Gual-Wells/Deep-Iteration-GPT-Runtime','requested_ref':'stable','pinned_commit':'a'*40,'manifest_path':'manifest.json','manifest_sha256':'b'*64}
        validate('route-receipt.schema.json',route)
        authority={'route':route,'P_run':{'protocol':'digr-v4.1','version':'4.1.0','repository_full_name':'Gual-Wells/Deep-Iteration-GPT-Runtime','commit_sha':'a'*40}}
        validate('protocol-authority.schema.json',authority)
        with self.assertRaises(Exception):
            bad=json.loads(json.dumps(authority)); bad['P_run']['commit_sha']='stable'; validate('protocol-authority.schema.json',bad)

        snap={'provider':'test','session_id':'s','boot_id':None,'monotonic_ns':1,'wall_ns':1}
        probe={'provider':'test','session_id':'s','boot_id':None,'monotonic_ns':2,'wall_ns':2}
        startup={'authority':authority,'clock':{'anchor':snap,'probe':probe,'ready':True},'u0_frozen':False}
        validate('task-startup.schema.json',startup)
        with self.assertRaises(Exception):
            bad=dict(startup); bad['u0_frozen']=True; validate('task-startup.schema.json',bad)

        contract={'N':1,'T_seconds':0,'R':0,'B':0,'S':{'n':0,'t_seconds':0,'r':0,'b':0},'D_s':0,'L_e':1}
        runtime={'task_startup':startup,'U0':'x','contract':contract,
                 'main':{'N_actual':1,'R_actual':0,'est_snapshot':None,'current_result_state':None},
                 'sources':[],'dictator':{'D_actual':0,'L_actual':1,'d_state_summary':None},
                 'time':{'timing_ready':True,'formal_started':False,'finished':True,'foreground_state':None,'intervals':[],
                         'T_actual_seconds':0,'t_actual_seconds':0,'T_actual_ns':0,'t_actual_ns':0,
                         'T_hard_verified':False,'t_hard_verified':False}}
        validate('runtime-state.schema.json',runtime)

if __name__=='__main__': unittest.main()
