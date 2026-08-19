import base64
import json
import unittest

from runtime.repository_transport import (
    AcquisitionAttemptReceipt,
    FetchRequest,
    RepositoryTransportSession,
    RouteAcquisitionError,
    TransportResponse,
    FRESHNESS_IMMUTABLE,
    FRESHNESS_LIVE_DIRECT,
    FRESHNESS_UNTRUSTED,
    normalize_pinned_file_bytes,
    route_failure_permitted,
)
from runtime.routing import (
    AUTHORITATIVE_BRANCH_API_URL,
    AUTHORITATIVE_REF_API_URL,
    content_api_url,
)
from runtime.protocol_pin import raw_file_url

SHA='a'*40
OTHER='b'*40
MANIFEST={
    'version':'5.0.0-alpha.3',
    'protocol':'digr-v5.0',
    'bootstrap_entry':'bootstrap/BOOTSTRAP.md',
    'entrypoint':'entry/DEEP_ITERATION_ENTRY.md',
    'core':['core/00_RESULT_SOVEREIGNTY.md'],
    'help':'entry/HELP.md',
    'startup_slice':['bootstrap/BOOTSTRAP.md','entry/STARTUP.md'],
}
MANIFEST_BYTES=(json.dumps(MANIFEST,separators=(',',':'))+'\n').encode()
VERSION=b'5.0.0-alpha.3\n'
FILES={
    'manifest.json':MANIFEST_BYTES,
    'VERSION':VERSION,
    'bootstrap/BOOTSTRAP.md':b'# boot\n',
    'entry/STARTUP.md':b'# startup\n',
}


def direct(url,body,status=200,mutable=False):
    return TransportResponse(
        url,status,body,'direct_https',
        FRESHNESS_LIVE_DIRECT if mutable else FRESHNESS_IMMUTABLE,
    )


class FakeFetcher:
    def __init__(self, *, branch_sha=SHA, ref_sha=SHA, raw_fail_paths=(), source_kind='direct_https'):
        self.branch_sha=branch_sha; self.ref_sha=ref_sha
        self.raw_fail_paths=set(raw_fail_paths); self.source_kind=source_kind
        self.requests=[]
    def __call__(self, req:FetchRequest):
        self.requests.append(req)
        freshness=FRESHNESS_LIVE_DIRECT if req.mutable_ref else FRESHNESS_IMMUTABLE
        if req.url==AUTHORITATIVE_REF_API_URL:
            body=json.dumps({'ref':'refs/heads/stable','object':{'type':'commit','sha':self.ref_sha}}).encode()
            return TransportResponse(req.url,200,body,self.source_kind,freshness)
        if req.url==AUTHORITATIVE_BRANCH_API_URL:
            body=json.dumps({'name':'stable','commit':{'sha':self.branch_sha}}).encode()
            return TransportResponse(req.url,200,body,self.source_kind,freshness)
        prefix=f'https://raw.githubusercontent.com/Gual-Wells/Deep-Iteration-GPT-Runtime/{SHA}/'
        if req.url.startswith(prefix):
            path=req.url[len(prefix):]
            if path in self.raw_fail_paths:
                return TransportResponse(req.url,503,b'',self.source_kind,freshness)
            return TransportResponse(req.url,200,FILES[path],self.source_kind,freshness)
        api_prefix='https://api.github.com/repos/Gual-Wells/Deep-Iteration-GPT-Runtime/contents/'
        if req.url.startswith(api_prefix):
            path=req.url[len(api_prefix):].split('?ref=',1)[0]
            body=json.dumps({
                'type':'file','path':path,'encoding':'base64',
                'content':base64.b64encode(FILES[path]).decode(),
            }).encode()
            return TransportResponse(req.url,200,body,self.source_kind,freshness)
        raise AssertionError(req.url)


class TestRepositoryTransport(unittest.TestCase):
    def test_actual_acquisition_precedes_startup(self):
        f=FakeFetcher(); s=RepositoryTransportSession(f)
        bundle=s.acquire_startup('DIGR/help')
        self.assertEqual(bundle.resolution.commit_sha,SHA)
        self.assertEqual(bundle.version_bytes,VERSION)
        self.assertEqual(tuple(p for p,_ in bundle.startup_files),('bootstrap/BOOTSTRAP.md','entry/STARTUP.md'))
        self.assertEqual([r.purpose for r in bundle.attempts[:2]],['stable_ref_primary','stable_ref_corroboration'])
        self.assertTrue(all(r.success for r in bundle.attempts))
        self.assertTrue(route_failure_permitted(bundle.attempts))

    def test_no_attempt_is_not_route_failure(self):
        self.assertFalse(route_failure_permitted(()))
        r=AcquisitionAttemptReceipt(1,'x',AUTHORITATIVE_REF_API_URL,'unknown',FRESHNESS_UNTRUSTED,0,False,None,None,'x')
        self.assertTrue(route_failure_permitted((r,)))
        off=AcquisitionAttemptReceipt(1,'x','https://example.invalid','unknown',FRESHNESS_UNTRUSTED,0,False,None,None,'x')
        self.assertFalse(route_failure_permitted((off,)))

    def test_search_or_index_transport_is_rejected(self):
        s=RepositoryTransportSession(FakeFetcher(source_kind='search_index'))
        with self.assertRaises(RouteAcquisitionError) as cm:
            s.acquire_startup('DIGR/help')
        self.assertTrue(route_failure_permitted(cm.exception.receipts))
        self.assertEqual(cm.exception.receipts[0].purpose,'stable_ref_primary')
        self.assertFalse(cm.exception.receipts[0].success)

    def test_ref_branch_disagreement_fails_closed(self):
        s=RepositoryTransportSession(FakeFetcher(branch_sha=OTHER))
        with self.assertRaises(RouteAcquisitionError) as cm:
            s.resolve_stable()
        self.assertEqual(cm.exception.receipts[-1].purpose,'stable_ref_consensus')
        self.assertIn('mismatch',cm.exception.receipts[-1].failure)

    def test_contents_base64_wrapper_is_decoded(self):
        payload=json.dumps({'type':'file','path':'VERSION','encoding':'base64','content':base64.b64encode(VERSION).decode()}).encode()
        self.assertEqual(normalize_pinned_file_bytes(payload,'VERSION'),VERSION)
        self.assertEqual(normalize_pinned_file_bytes(VERSION,'VERSION'),VERSION)

    def test_raw_failure_falls_back_to_contents_raw_contract(self):
        f=FakeFetcher(raw_fail_paths={'manifest.json'})
        s=RepositoryTransportSession(f)
        b=s.acquire_startup('DIGR/help')
        self.assertEqual(b.manifest_bytes,MANIFEST_BYTES)
        purposes=[r.purpose for r in b.attempts]
        self.assertIn('pinned-fallback:manifest.json',purposes)
        fallback_req=next(r for r in f.requests if r.purpose=='pinned-fallback:manifest.json')
        self.assertEqual(fallback_req.accept,'application/vnd.github.raw+json')
        self.assertEqual(fallback_req.url,content_api_url(SHA,'manifest.json'))


    def test_malformed_direct_ref_is_wrapped_with_attempt_evidence(self):
        class BadRef(FakeFetcher):
            def __call__(self,req):
                if req.url==AUTHORITATIVE_REF_API_URL:
                    self.requests.append(req)
                    return TransportResponse(req.url,200,b"{}",'direct_https',FRESHNESS_LIVE_DIRECT)
                return super().__call__(req)
        sess=RepositoryTransportSession(BadRef())
        with self.assertRaises(RouteAcquisitionError) as cm:
            sess.resolve_stable()
        self.assertEqual(cm.exception.receipts[-1].purpose,'stable_ref_primary_validation')
        self.assertTrue(route_failure_permitted(cm.exception.receipts))

    def test_manifest_version_integrity_error_is_route_acquisition_error(self):
        class BadVersion(FakeFetcher):
            def __call__(self,req):
                response=super().__call__(req)
                marker=f'https://raw.githubusercontent.com/Gual-Wells/Deep-Iteration-GPT-Runtime/{SHA}/VERSION'
                if req.url==marker:
                    return TransportResponse(req.url,200,b'9.9.9\n','direct_https',FRESHNESS_IMMUTABLE)
                return response
        sess=RepositoryTransportSession(BadVersion())
        with self.assertRaises(RouteAcquisitionError) as cm:
            sess.acquire_startup('DIGR/help')
        self.assertEqual(cm.exception.receipts[-1].purpose,'pinned_route_metadata_validation')
        self.assertTrue(route_failure_permitted(cm.exception.receipts))

    def test_non_candidate_never_starts_repository_acquisition(self):
        f=FakeFetcher(); s=RepositoryTransportSession(f)
        with self.assertRaises(ValueError): s.acquire_startup('ordinary chat')
        self.assertEqual(f.requests,[])

    def test_pinned_raw_urls_are_immutable_sha_urls(self):
        self.assertEqual(
            raw_file_url('Gual-Wells','Deep-Iteration-GPT-Runtime',SHA,'VERSION'),
            f'https://raw.githubusercontent.com/Gual-Wells/Deep-Iteration-GPT-Runtime/{SHA}/VERSION'
        )

if __name__=='__main__': unittest.main()
