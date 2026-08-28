import json,unittest
from pathlib import Path
from runtime.routing import *
SHA='a'*40
MANIFEST=b'{"version":"3.0.0","entrypoint":"entry/E.md","core":["core/A.md"],"help":"entry/H.md"}'
VERSION=b'3.0.0\n'
def receipt(manifest=MANIFEST,version=VERSION): return RouteReceipt(AUTHORITATIVE_REPOSITORY,AUTHORITATIVE_REF,SHA,MANIFEST_PATH,bytes_sha256(manifest),VERSION_PATH,bytes_sha256(version))

class TestRouting(unittest.TestCase):
    def test_candidate_matching_is_broad_but_uppercase_exact(self):
        for text,key in {'DIGR：任务':'DIGR','DIGR/help':'DIGR','  DIGR whatever':'DIGR','\t深度迭代（R=5）：x':'深度迭代','深度迭代的设计呢':'深度迭代'}.items():
            self.assertEqual(candidate_route_key(text),key); self.assertTrue(is_candidate_route(text))
        for text in ('digr/help','Digr：x','DiGr x','我觉得 DIGR 很好','普通对话',''):
            self.assertIsNone(candidate_route_key(text)); self.assertFalse(is_candidate_route(text))
        with self.assertRaises(TypeError): candidate_route_key(None)
    def test_ref_response_must_be_exact_stable_commit(self):
        payload={'ref':'refs/heads/stable','object':{'type':'commit','sha':SHA}}; r=ref_resolution_from_github_payload(payload); self.assertEqual(r.commit_sha,SHA)
        self.assertEqual(ref_resolution_from_github_payload(json.dumps(payload).encode()).commit_sha,SHA)
        for bad in ({'ref':'refs/heads/main','object':{'type':'commit','sha':SHA}},{'ref':'refs/heads/stable','object':{'type':'tag','sha':SHA}},{'ref':'refs/heads/stable','object':{'type':'commit','sha':'short'}},{'ref':'refs/heads/stable'}):
            with self.assertRaises((ValueError,TypeError)): ref_resolution_from_github_payload(bad)
    def test_branch_response_can_be_authoritative_connector_resolution(self):
        payload={'name':'stable','commit':{'sha':SHA}}
        r=ref_resolution_from_branch_payload(payload)
        self.assertEqual(r.commit_sha,SHA); self.assertEqual(r.source_url,AUTHORITATIVE_BRANCH_API_URL)
        with self.assertRaises(ValueError): ref_resolution_from_branch_payload({'name':'main','commit':{'sha':SHA}})

    def test_end_to_end_legacy_route(self):
        rr=route_receipt_from_ref_resolution(ref_resolution_from_github_payload({'ref':'refs/heads/stable','object':{'type':'commit','sha':SHA}}),MANIFEST,VERSION)
        p=discovery_plan_from_manifest_bytes(rr,MANIFEST,VERSION); self.assertTrue(p.legacy_manifest); self.assertEqual(p.initial_paths,('entry/E.md','core/A.md')); self.assertEqual(p.post_startup_paths,())
    def test_alpha2_staged_startup(self):
        m={'bootstrap_entry':'bootstrap/BOOTSTRAP.md','entrypoint':'entry/E.md','core':['core/A.md','core/B.md'],'help':'entry/H.md','startup_slice':['bootstrap/BOOTSTRAP.md','entry/STARTUP.md']}
        p=discovery_plan_from_manifest(m); self.assertFalse(p.legacy_manifest); self.assertTrue(p.staged_startup); self.assertEqual(p.initial_paths,('bootstrap/BOOTSTRAP.md','entry/STARTUP.md')); self.assertEqual(p.post_startup_paths,('entry/E.md','core/A.md','core/B.md')); self.assertEqual(p.optional_paths,('entry/H.md',))
    def test_staged_manifest_execution_bundle_reduces_physical_post_startup_reads(self):
        m={'bootstrap_entry':'bootstrap/BOOTSTRAP.md','entrypoint':'entry/E.md','core':['core/A.md','core/B.md'],'help':'entry/H.md','startup_slice':['bootstrap/BOOTSTRAP.md','entry/STARTUP.md'],'execution_bundle':{'path':'bundle/EXECUTION_PROTOCOL.json','schema':1,'members':['entry/E.md','core/A.md','core/B.md']}}
        p=discovery_plan_from_manifest(m)
        self.assertEqual(p.full_protocol_paths,('entry/E.md','core/A.md','core/B.md'))
        self.assertEqual(p.post_startup_paths,('bundle/EXECUTION_PROTOCOL.json',))
        self.assertEqual(p.execution_bundle_schema,1)

    def test_bootstrap_without_startup_slice_preserves_old_navigation(self):
        m={'bootstrap_entry':'bootstrap/BOOTSTRAP.md','entrypoint':'entry/E.md','core':['core/A.md'],'help':'entry/H.md'}
        p=discovery_plan_from_manifest(m); self.assertFalse(p.legacy_manifest); self.assertFalse(p.staged_startup); self.assertEqual(p.initial_paths,('bootstrap/BOOTSTRAP.md','entry/E.md','core/A.md'))
    def test_exact_locator_constants(self):
        self.assertEqual(AUTHORITATIVE_REPOSITORY,'Gual-Wells/Deep-Iteration-GPT-Runtime'); self.assertEqual(AUTHORITATIVE_REF,'stable'); self.assertEqual(AUTHORITATIVE_REF_API_URL,'https://api.github.com/repos/Gual-Wells/Deep-Iteration-GPT-Runtime/git/ref/heads/stable'); self.assertEqual(AUTHORITATIVE_BRANCH_API_URL,'https://api.github.com/repos/Gual-Wells/Deep-Iteration-GPT-Runtime/branches/stable'); self.assertIn('{SHA}/{PATH}',PINNED_RAW_TEMPLATE); self.assertEqual(content_api_url(SHA,'manifest.json'),f'https://api.github.com/repos/Gual-Wells/Deep-Iteration-GPT-Runtime/contents/manifest.json?ref={SHA}')
    def test_route_receipt_exact_locator_and_two_digests(self):
        r=receipt(); self.assertEqual(r.pinned_commit,SHA)
        with self.assertRaises(ValueError): RouteReceipt('Other/Repo','stable',SHA,'manifest.json','b'*64,'VERSION','c'*64)
        with self.assertRaises(ValueError): RouteReceipt(AUTHORITATIVE_REPOSITORY,'main',SHA,'manifest.json','b'*64,'VERSION','c'*64)
        with self.assertRaises(ValueError): RouteReceipt(AUTHORITATIVE_REPOSITORY,'stable','stable','manifest.json','b'*64,'VERSION','c'*64)
    def test_manifest_version_binding(self):
        r=receipt(); self.assertEqual(load_manifest_for_route(r,MANIFEST)['version'],'3.0.0'); self.assertEqual(load_version_for_route(r,VERSION),'3.0.0'); self.assertEqual(load_route_metadata(r,MANIFEST,VERSION)[1],'3.0.0')
        with self.assertRaises(ValueError): load_manifest_for_route(r,b'{}')
    def test_manifest_routing_metadata_crosscheck(self):
        meta={'candidate_route_keys':['DIGR','深度迭代'],'candidate_match':'lstrip_prefix; DIGR_exact_uppercase; remainder_unvalidated','repository_full_name':AUTHORITATIVE_REPOSITORY,'repository_url':AUTHORITATIVE_REPOSITORY_URL,'requested_ref':'stable','ref_api_url':AUTHORITATIVE_REF_API_URL,'branch_api_url':AUTHORITATIVE_BRANCH_API_URL,'manifest_path':'manifest.json','version_path':'VERSION','content_api_template':CONTENT_API_TEMPLATE,'pinned_raw_template':PINNED_RAW_TEMPLATE,'content_raw_media_type':'application/vnd.github.raw+json','mutable_ref_policy':'connector_branch_head_or_direct_rest_branch_ref_consensus; search_index_forbidden; attempt_required_before_failure'}
        self.assertTrue(validate_manifest_routing_metadata({'routing':meta})); self.assertFalse(validate_manifest_routing_metadata({}))
        bad=dict(meta);bad['candidate_match']='lstrip_prefix; DIGR_ascii_case_insensitive; remainder_unvalidated'
        with self.assertRaises(ValueError):validate_manifest_routing_metadata({'routing':bad})
    def test_current_3_fixture_stays_legacy(self):
        p=discovery_plan_from_manifest(json.loads((Path(__file__).parent/'fixtures/manifest-3.0.json').read_text(encoding='utf-8'))); self.assertTrue(p.legacy_manifest); self.assertEqual(p.entrypoint,'entry/DEEP_ITERATION_ENTRY.md')
    def test_manifest_paths_safe(self):
        with self.assertRaises(ValueError): discovery_plan_from_manifest({'entrypoint':'../x','core':['core/a']})
        with self.assertRaises(ValueError): discovery_plan_from_manifest({'entrypoint':'entry/x','core':[]})
        with self.assertRaises(ValueError): discovery_plan_from_manifest({'entrypoint':'entry/x','core':['../a']})
if __name__=='__main__':unittest.main()
