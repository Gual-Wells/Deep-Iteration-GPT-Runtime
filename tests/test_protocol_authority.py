import dataclasses
import unittest
from runtime.protocol_authority import ProtocolIdentity, ProtocolAuthority, authority_from_manifest_bytes
from runtime.routing import RouteReceipt, AUTHORITATIVE_REPOSITORY, manifest_sha256

REPO=AUTHORITATIVE_REPOSITORY
SHA='a'*40

def route(sha=SHA,digest='b'*64):
    return RouteReceipt(REPO,'stable',sha,'manifest.json',digest)

class TestProtocolAuthority(unittest.TestCase):
    def test_frozen_run_identity_bound_to_route(self):
        p=ProtocolIdentity('digr-v4.1','4.1.0',REPO,SHA)
        a=ProtocolAuthority(route(),p)
        self.assertEqual(a.P_run.version,'4.1.0')
        self.assertEqual(a.P_run.commit_sha,a.route.pinned_commit)
        with self.assertRaises(dataclasses.FrozenInstanceError): a.P_run=p
        with self.assertRaises(dataclasses.FrozenInstanceError): p.version='5.0.0'

    def test_authority_from_manifest_bytes(self):
        data=b'{"protocol":"digr-v4.1","version":"4.1.0"}'
        a=authority_from_manifest_bytes(route(digest=manifest_sha256(data)),data)
        self.assertEqual(a.P_run.protocol,'digr-v4.1')
        self.assertEqual(a.P_run.version,'4.1.0')
        with self.assertRaises(ValueError): authority_from_manifest_bytes(route(),data)

    def test_route_mismatch_rejected(self):
        p=ProtocolIdentity('digr-v4.1','4.1.0',REPO,SHA)
        with self.assertRaises(ValueError): ProtocolAuthority(route('c'*40),p)

    def test_full_commit_and_exact_repo_required(self):
        with self.assertRaises(ValueError): ProtocolIdentity('digr-v4.1','4.1.0',REPO,'stable')
        with self.assertRaises(ValueError): ProtocolIdentity('digr-v4.1','4.1.0','Other/Repo',SHA)
        with self.assertRaises(ValueError): ProtocolIdentity('','4.1.0',REPO,SHA)

    def test_target_fields_are_not_part_of_routing_authority(self):
        fields={f.name for f in dataclasses.fields(ProtocolAuthority)}
        self.assertEqual(fields,{'route','P_run'})
        self.assertNotIn('target_protocol',fields)
        self.assertNotIn('gate_id',fields)

if __name__=='__main__': unittest.main()
