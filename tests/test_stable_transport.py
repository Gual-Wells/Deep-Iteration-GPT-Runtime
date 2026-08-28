import unittest

from runtime.execution_protocol import ProtocolMemberReceipt, execution_set_sha256
from runtime.repository_transport import (
    FRESHNESS_IMMUTABLE, ProtocolLoadAbortError, RepositoryTransportSession,
    RouteAcquisitionError, TransportResponse,
)
from tests.test_repository_transport import FakeFetcher, STABLE_DESCRIPTOR_BYTES


class TestStableTransport(unittest.TestCase):
    def test_execution_set_digest_documented_vector(self):
        members=(
            ProtocolMemberReceipt('core/a.md','a'*64,7),
            ProtocolMemberReceipt('核心/甲.md','b'*64,9),
        )
        self.assertEqual(execution_set_sha256(members),'79a2f680ecb1c8c80f7052e7ef69ef380333ef6dc8b008beeefaff085f9dfb2c')

    def test_pinned_startup_precedes_descriptor_and_execution(self):
        f=FakeFetcher(source_kind='github_connector');session=RepositoryTransportSession(f)
        stable=session.acquire_stable_execution('DIGR：x')
        self.assertEqual(len(f.requests),6)
        self.assertEqual(stable.startup.descriptor['version'],'5.0.0-Berta1')
        self.assertEqual(stable.startup.route_receipt.manifest_path,'manifest.json')
        self.assertEqual(stable.protocol.receipt.manifest_sha256,stable.startup.route_receipt.manifest_sha256)
        self.assertEqual(stable.protocol.receipt.source_mode,'bundle')
        self.assertEqual(
            [r.purpose for r in f.requests],
            ['stable_branch_primary_r1','pinned:manifest.json','pinned:VERSION',
             'pinned:entry/STARTUP.md','pinned:runtime-descriptor.json',
             'pinned:dist/EXECUTION_PROTOCOL.json'],
        )

    def test_direct_mode_always_corroborates_ref(self):
        f=FakeFetcher();session=RepositoryTransportSession(f)
        session.acquire_stable_execution('DIGR：x',paranoid=True)
        self.assertEqual(len(f.requests),7)
        self.assertEqual(f.requests[1].purpose,'stable_ref_corroboration_r1')

    def test_nonexecuting_candidate_is_rejected_only_after_pinned_startup(self):
        for message in ('DIGR/help','DIGR讨论','DIGRAPH','DIGR：'):
            f=FakeFetcher(source_kind='github_connector');session=RepositoryTransportSession(f)
            with self.assertRaises(ValueError): session.acquire_stable_execution(message)
            self.assertEqual(len(f.requests),4,message)
            self.assertFalse(any(r.url.endswith('/runtime-descriptor.json') for r in f.requests))

    def test_descriptor_identity_mismatch_fails_before_bundle(self):
        class BadDescriptor(FakeFetcher):
            def __call__(self,req):
                response=super().__call__(req)
                if req.url.endswith('/runtime-descriptor.json'):
                    bad=__import__('json').loads(STABLE_DESCRIPTOR_BYTES)
                    bad['version']='9.9.9'
                    return TransportResponse(req.url,200,__import__('json').dumps(bad).encode(),self.source_kind,response.freshness)
                return response
        f=BadDescriptor(source_kind='github_connector');session=RepositoryTransportSession(f)
        with self.assertRaises(RouteAcquisitionError): session.acquire_stable_execution('DIGR：x')
        self.assertFalse(any('dist/EXECUTION_PROTOCOL.json' in r.url for r in f.requests))

    def test_descriptor_binds_raw_bundle_bytes_not_only_internal_hashes(self):
        class ReencodedBundle(FakeFetcher):
            def __call__(self,req):
                response=super().__call__(req)
                if req.url.endswith('/dist/EXECUTION_PROTOCOL.json'):
                    return TransportResponse(req.url,200,response.body+b' ',self.source_kind,response.freshness)
                return response
        session=RepositoryTransportSession(ReencodedBundle(source_kind='github_connector'))
        with self.assertRaises(RouteAcquisitionError) as cm:
            session.acquire_stable_execution('DIGR：x')
        self.assertEqual(cm.exception.receipts[-1].purpose,'stable_execution_bundle_validation')

    def test_help_follows_manifest_at_same_pin_without_descriptor(self):
        f=FakeFetcher(source_kind='github_connector')
        artifact=RepositoryTransportSession(f).acquire_stable_help('DIGR/help')
        self.assertEqual(artifact.path,'entry/HELP.md')
        self.assertEqual(len(f.requests),5)
        self.assertEqual(f.requests[-1].purpose,'pinned:entry/HELP.md')
        self.assertFalse(any(r.url.endswith('/runtime-descriptor.json') for r in f.requests))

    def test_abort_failure_is_exposed_not_swallowed(self):
        class BrokenBundle(FakeFetcher):
            def __call__(self,req):
                if 'dist/EXECUTION_PROTOCOL.json' in req.url:
                    self.requests.append(req)
                    return TransportResponse(req.url,503,b'',self.source_kind,FRESHNESS_IMMUTABLE)
                return super().__call__(req)
        class BrokenAbort:
            def abort_protocol_load(self,reason):
                raise OSError('abort persistence failed')

        session=RepositoryTransportSession(BrokenBundle(source_kind='github_connector'))
        startup=session.acquire_startup('DIGR：x')
        with self.assertRaises(ProtocolLoadAbortError) as cm:
            session.load_execution_protocol_for_run(BrokenAbort(),startup)
        self.assertIn('abort persistence failed',str(cm.exception.abort_error))
        self.assertIsNotNone(cm.exception.protocol_error)


if __name__=='__main__': unittest.main()
