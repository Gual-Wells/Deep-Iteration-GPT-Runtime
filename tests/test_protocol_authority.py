import dataclasses
import unittest
from runtime.protocol_authority import ProtocolIdentity, ProtocolAuthority, authority_from_route_bytes
from runtime.routing import RouteReceipt, AUTHORITATIVE_REPOSITORY, bytes_sha256

REPO=AUTHORITATIVE_REPOSITORY
SHA='a'*40
MANIFEST=b'{"protocol":"digr-v5.0","version":"5.0.0-alpha.3"}'
VERSION=b'5.0.0-alpha.3\n'

def route(sha=SHA, manifest=MANIFEST, version=VERSION):
    return RouteReceipt(REPO,'stable',sha,'manifest.json',bytes_sha256(manifest),'VERSION',bytes_sha256(version))

class TestProtocolAuthority(unittest.TestCase):
    def test_frozen_run_identity_bound_to_route(self):
        p=ProtocolIdentity('digr-v5.0','5.0.0-alpha.3',REPO,SHA)
        a=ProtocolAuthority(route(),p)
        self.assertEqual(a.P_run.version,'5.0.0-alpha.3')
        self.assertEqual(a.P_run.commit_sha,a.route.pinned_commit)
        with self.assertRaises(dataclasses.FrozenInstanceError): a.P_run=p
        with self.assertRaises(dataclasses.FrozenInstanceError): p.version='5.0.0'

    def test_authority_requires_manifest_and_VERSION_binding(self):
        a=authority_from_route_bytes(route(),MANIFEST,VERSION)
        self.assertEqual(a.P_run.protocol,'digr-v5.0'); self.assertEqual(a.P_run.version,'5.0.0-alpha.3')
        badv=b'4.1.0\n'
        r=route(version=badv)
        with self.assertRaises(ValueError): authority_from_route_bytes(r,MANIFEST,badv)
        with self.assertRaises(ValueError): authority_from_route_bytes(route(),b'{}',VERSION)

    def test_route_mismatch_rejected(self):
        p=ProtocolIdentity('digr-v5.0','5.0.0-alpha.3',REPO,SHA)
        with self.assertRaises(ValueError): ProtocolAuthority(route('c'*40),p)

    def test_full_commit_and_exact_repo_required(self):
        with self.assertRaises(ValueError): ProtocolIdentity('digr-v5.0','5.0.0-alpha.3',REPO,'stable')
        with self.assertRaises(ValueError): ProtocolIdentity('digr-v5.0','5.0.0-alpha.3','Other/Repo',SHA)
        with self.assertRaises(ValueError): ProtocolIdentity('','5.0.0-alpha.3',REPO,SHA)

    def test_target_fields_are_not_part_of_routing_authority(self):
        fields={f.name for f in dataclasses.fields(ProtocolAuthority)}
        self.assertEqual(fields,{'route','P_run'})
        self.assertNotIn('target_protocol',fields); self.assertNotIn('gate_id',fields)

if __name__=='__main__': unittest.main()
