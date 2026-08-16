import unittest
from runtime.routing import (
    AUTHORITATIVE_REPOSITORY, AUTHORITATIVE_REF, MANIFEST_PATH,
    RouteReceipt, discovery_plan_from_manifest, discovery_plan_from_manifest_bytes, load_manifest_for_route, manifest_sha256,
)

SHA='a'*40

class TestRouting(unittest.TestCase):
    def receipt(self):
        return RouteReceipt(AUTHORITATIVE_REPOSITORY,AUTHORITATIVE_REF,SHA,MANIFEST_PATH,'b'*64)

    def test_route_receipt_exact_locator(self):
        r=self.receipt()
        self.assertEqual(r.repository_full_name,AUTHORITATIVE_REPOSITORY)
        self.assertEqual(r.requested_ref,'stable')
        self.assertEqual(r.pinned_commit,SHA)
        with self.assertRaises(ValueError): RouteReceipt('Other/Repo','stable',SHA,'manifest.json','b'*64)
        with self.assertRaises(ValueError): RouteReceipt(AUTHORITATIVE_REPOSITORY,'main',SHA,'manifest.json','b'*64)
        with self.assertRaises(ValueError): RouteReceipt(AUTHORITATIVE_REPOSITORY,'stable','stable','manifest.json','b'*64)
        with self.assertRaises(ValueError): RouteReceipt(AUTHORITATIVE_REPOSITORY,'stable',SHA,'../manifest.json','b'*64)

    def test_manifest_digest(self):
        self.assertEqual(len(manifest_sha256(b'{}')),64)
        with self.assertRaises(TypeError): manifest_sha256('{}')

    def test_raw_manifest_is_bound_to_receipt_digest(self):
        data=b'{"entrypoint":"entry/E.md","core":["core/A.md"]}'
        r=RouteReceipt(AUTHORITATIVE_REPOSITORY,AUTHORITATIVE_REF,SHA,MANIFEST_PATH,manifest_sha256(data))
        self.assertEqual(load_manifest_for_route(r,data)['entrypoint'],'entry/E.md')
        self.assertTrue(discovery_plan_from_manifest_bytes(r,data).legacy_manifest)
        with self.assertRaises(ValueError): load_manifest_for_route(r,b'{}')

    def test_4_1_manifest_uses_bootstrap(self):
        m={'bootstrap_entry':'bootstrap/BOOTSTRAP.md','entrypoint':'entry/E.md','core':['core/A.md'],'help':'entry/H.md'}
        p=discovery_plan_from_manifest(m)
        self.assertFalse(p.legacy_manifest)
        self.assertEqual(p.load_paths,('bootstrap/BOOTSTRAP.md','entry/E.md','core/A.md','entry/H.md'))

    def test_legacy_manifest_routes_entry_core_without_inventing_bootstrap(self):
        m={'entrypoint':'entry/DEEP_ITERATION_ENTRY.md','core':['core/00.md','core/10.md'],'help':'entry/HELP.md'}
        p=discovery_plan_from_manifest(m)
        self.assertTrue(p.legacy_manifest)
        self.assertIsNone(p.bootstrap_entry)
        self.assertEqual(p.load_paths[0],'entry/DEEP_ITERATION_ENTRY.md')
        self.assertNotIn('bootstrap/BOOTSTRAP.md',p.load_paths)

    def test_current_3_0_fixture_discovers_only_repository_entry_core(self):
        import json
        from pathlib import Path
        fixture=Path(__file__).parent/'fixtures/manifest-3.0.json'
        m=json.loads(fixture.read_text(encoding='utf-8'))
        p=discovery_plan_from_manifest(m)
        self.assertTrue(p.legacy_manifest)
        self.assertNotIn('bootstrap/LOCAL_FALLBACK_CORE.md',p.load_paths)
        self.assertEqual(p.entrypoint,'entry/DEEP_ITERATION_ENTRY.md')

    def test_manifest_paths_are_safe(self):
        with self.assertRaises(ValueError): discovery_plan_from_manifest({'entrypoint':'../x','core':['core/a']})
        with self.assertRaises(ValueError): discovery_plan_from_manifest({'entrypoint':'entry/x','core':[]})
        with self.assertRaises(ValueError): discovery_plan_from_manifest({'entrypoint':'entry/x','core':['../a']})

if __name__=='__main__': unittest.main()
