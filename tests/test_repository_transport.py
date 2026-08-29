import base64
import json
import unittest
from pathlib import Path

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
from runtime.protocol_authority import authority_from_route_bytes
from runtime.run_session import LiveDIGRRun
from runtime.run_lifecycle import RunPhase
from tests.helpers import FakeClock

SHA='a'*40
OTHER='b'*40
MANIFEST={
    'version':'5.0.0-Berta2',
    'protocol':'digr-v5.0',
    'runtime_descriptor':'runtime-descriptor.json',
    'bootstrap_entry':'entry/STARTUP.md',
    'entrypoint':'entry/DEEP_ITERATION_ENTRY.md',
    'core':['core/00_RESULT_SOVEREIGNTY.md'],
    'help':'entry/HELP.md',
    'startup_slice':['entry/STARTUP.md'],
    'execution_bundle':{
        'path':'dist/EXECUTION_PROTOCOL.json','schema':1,
        'members':['entry/DEEP_ITERATION_ENTRY.md','core/00_RESULT_SOVEREIGNTY.md'],
    },
}
MANIFEST_BYTES=(json.dumps(MANIFEST,separators=(',',':'))+'\n').encode()
VERSION=b'5.0.0-Berta2\n'
LOGICAL={
    'entry/DEEP_ITERATION_ENTRY.md':b'# entry\n',
    'core/00_RESULT_SOVEREIGNTY.md':b'# core\n',
}
BUNDLE_BYTES=(json.dumps({
    'schema_version':1,'version':'5.0.0-Berta2','protocol':'digr-v5.0',
    'members':[
        {'path':p,'sha256':__import__('hashlib').sha256(b).hexdigest(),'byte_length':len(b),'content':b.decode()}
        for p,b in LOGICAL.items()
    ],
},sort_keys=True,separators=(',',':'))+'\n').encode()
STABLE_MEMBERS=[
    {'path':p,'sha256':__import__('hashlib').sha256(b).hexdigest(),'byte_length':len(b),'content':b.decode()}
    for p,b in LOGICAL.items()
]
STABLE_BUNDLE_BYTES=(json.dumps({
    'schema_version':1,'version':'5.0.0-Berta2','protocol':'digr-v5.0',
    'members':STABLE_MEMBERS,
},sort_keys=True,separators=(',',':'))+'\n').encode()
STABLE_HELP_BYTES='# DIGR Help\n\nVerified stable help.\n'.encode()
STABLE_EXECUTION_SET=[{k:item[k] for k in ('path','sha256','byte_length')} for item in STABLE_MEMBERS]
STABLE_EXECUTION_SET_BYTES=json.dumps(STABLE_EXECUTION_SET,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
STABLE_DESCRIPTOR={
    'schema':'digr-runtime-descriptor/v1','protocol':'digr-v5.0','version':'5.0.0-Berta2',
    'minimum_adapter':{
        'repository':'Gual-Wells/Deep-Iteration-GPT-Runtime','ref':'stable',
        'descriptor_path':'runtime-descriptor.json',
    },
    'artifacts':{'execution_bundle':{
        'path':'dist/EXECUTION_PROTOCOL.json',
        'sha256':__import__('hashlib').sha256(STABLE_BUNDLE_BYTES).hexdigest(),
        'byte_length':len(STABLE_BUNDLE_BYTES),'member_count':len(STABLE_MEMBERS),
        'execution_set_sha256':__import__('hashlib').sha256(STABLE_EXECUTION_SET_BYTES).hexdigest(),
    },'help':{
        'path':'dist/HELP.zh-CN.md','sha256':__import__('hashlib').sha256(STABLE_HELP_BYTES).hexdigest(),
        'byte_length':len(STABLE_HELP_BYTES),'media_type':'text/markdown; charset=utf-8',
    }},
}
STABLE_DESCRIPTOR_BYTES=(json.dumps(STABLE_DESCRIPTOR,separators=(',',':'))+'\n').encode()
FILES={
    'manifest.json':MANIFEST_BYTES,
    'VERSION':VERSION,
    'bootstrap/BOOTSTRAP.md':b'# boot\n',
    'entry/STARTUP.md':b'# startup\n',
    'entry/HELP.md':STABLE_HELP_BYTES,
    **LOGICAL,
    'bundle/EXECUTION_PROTOCOL.json':BUNDLE_BYTES,
    'runtime-descriptor.json':STABLE_DESCRIPTOR_BYTES,
    'dist/EXECUTION_PROTOCOL.json':STABLE_BUNDLE_BYTES,
    'dist/HELP.zh-CN.md':STABLE_HELP_BYTES,
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
    def test_real_release_files_complete_stable_execution_acquisition(self):
        root=Path(__file__).resolve().parents[1]
        prefix=f'https://raw.githubusercontent.com/Gual-Wells/Deep-Iteration-GPT-Runtime/{SHA}/'
        class RealReleaseFetcher(FakeFetcher):
            def __init__(self):
                super().__init__(source_kind='github_connector')
            def __call__(self,req):
                if req.url.startswith(prefix):
                    self.requests.append(req)
                    rel=req.url[len(prefix):]
                    return TransportResponse(
                        req.url,200,(root/rel).read_bytes(),self.source_kind,FRESHNESS_IMMUTABLE,
                    )
                return super().__call__(req)
        fetcher=RealReleaseFetcher();stable=RepositoryTransportSession(fetcher).acquire_stable_execution('DIGR：诗创作')
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        expected=(manifest['entrypoint'],*manifest['core'])
        self.assertEqual(stable.protocol.receipt.member_paths,expected)
        self.assertEqual(len(stable.protocol.files),len(expected))
        self.assertEqual(
            [request.purpose for request in fetcher.requests],
            ['stable_branch_primary_r1','pinned:manifest.json','pinned:VERSION',
             'pinned:entry/STARTUP.md','pinned:runtime-descriptor.json',
             'pinned:dist/EXECUTION_PROTOCOL.json'],
        )

    def test_actual_acquisition_precedes_startup(self):
        f=FakeFetcher(); s=RepositoryTransportSession(f)
        bundle=s.acquire_startup('DIGR：x')
        self.assertEqual(bundle.resolution.commit_sha,SHA)
        self.assertEqual(bundle.version_bytes,VERSION)
        self.assertEqual(tuple(p for p,_ in bundle.startup_files),('entry/STARTUP.md',))
        self.assertEqual([r.purpose for r in bundle.attempts[:2]],['stable_branch_primary_r1','stable_ref_corroboration_r1'])
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
            s.acquire_startup('DIGR：x')
        self.assertTrue(route_failure_permitted(cm.exception.receipts))
        self.assertEqual(cm.exception.receipts[0].purpose,'stable_branch_primary_r1')
        self.assertFalse(cm.exception.receipts[0].success)


    def test_connected_connector_uses_branch_head_without_ref_endpoint(self):
        class ConnectorFetcher(FakeFetcher):
            def __init__(self):
                super().__init__(source_kind='github_connector')
            def __call__(self,req):
                if req.url==AUTHORITATIVE_REF_API_URL:
                    raise AssertionError('connector mode must not require Git-ref endpoint')
                return super().__call__(req)
        f=ConnectorFetcher();s=RepositoryTransportSession(f)
        b=s.acquire_startup('DIGR：x')
        self.assertEqual(b.resolution.commit_sha,SHA)
        self.assertEqual(b.resolution.source_url,AUTHORITATIVE_BRANCH_API_URL)
        self.assertEqual(b.attempts[0].purpose,'stable_branch_primary_r1')
        self.assertFalse(any(r.purpose.startswith('stable_ref_corroboration') for r in b.attempts))

    def test_ref_branch_disagreement_fails_closed(self):
        s=RepositoryTransportSession(FakeFetcher(branch_sha=OTHER))
        with self.assertRaises(RouteAcquisitionError) as cm:
            s.resolve_stable()
        self.assertEqual(cm.exception.receipts[-1].purpose,'stable_ref_consensus')
        self.assertIn('mismatch',cm.exception.receipts[-1].failure)

    def test_execution_protocol_uses_one_bundle_fetch_after_startup(self):
        f=FakeFetcher(source_kind='github_connector');s=RepositoryTransportSession(f)
        startup=s.acquire_startup('DIGR：x')
        before=len(f.requests)
        protocol=s.acquire_execution_protocol(startup)
        after=f.requests[before:]
        self.assertEqual(protocol.receipt.source_mode,'bundle')
        self.assertEqual(protocol.receipt.member_paths,('entry/DEEP_ITERATION_ENTRY.md','core/00_RESULT_SOVEREIGNTY.md'))
        self.assertEqual(len(after),1)
        self.assertIn('/dist/EXECUTION_PROTOCOL.json',after[0].url)

    def test_execution_bundle_corruption_fails_closed(self):
        class Corrupt(FakeFetcher):
            def __call__(self,req):
                r=super().__call__(req)
                if req.url.endswith('/dist/EXECUTION_PROTOCOL.json'):
                    bad=json.loads(r.body.decode());bad['members'][0]['content']='tampered\n'
                    return TransportResponse(req.url,200,json.dumps(bad).encode(),self.source_kind,r.freshness)
                return r
        sess=RepositoryTransportSession(Corrupt(source_kind='github_connector'));startup=sess.acquire_startup('DIGR：x')
        with self.assertRaises(RouteAcquisitionError) as cm:
            sess.acquire_execution_protocol(startup)
        self.assertEqual(cm.exception.receipts[-1].purpose,'execution_bundle_validation')

    def test_direct_rest_consensus_allows_one_bounded_retry(self):
        class Racing(FakeFetcher):
            def __init__(self): super().__init__();self.branch_reads=0
            def __call__(self,req):
                if req.url==AUTHORITATIVE_BRANCH_API_URL:
                    self.requests.append(req);self.branch_reads+=1
                    sha=OTHER if self.branch_reads==1 else SHA
                    body=json.dumps({'name':'stable','commit':{'sha':sha}}).encode()
                    return TransportResponse(req.url,200,body,'direct_https',FRESHNESS_LIVE_DIRECT)
                return super().__call__(req)
        sess=RepositoryTransportSession(Racing())
        self.assertEqual(sess.resolve_stable().commit_sha,SHA)
        self.assertEqual(sum(r.purpose.startswith('stable_branch_primary') for r in sess.receipts),2)

    def test_standard_post_genesis_bridge_aborts_when_bundle_cannot_load(self):
        class BrokenBundle(FakeFetcher):
            def __call__(self,req):
                if 'dist/EXECUTION_PROTOCOL.json' in req.url:
                    self.requests.append(req)
                    freshness=FRESHNESS_IMMUTABLE
                    return TransportResponse(req.url,503,b'',self.source_kind,freshness)
                return super().__call__(req)
        f=BrokenBundle(source_kind='github_connector');sess=RepositoryTransportSession(f);startup=sess.acquire_startup('DIGR：x')
        authority=authority_from_route_bytes(startup.route_receipt,startup.manifest_bytes,startup.version_bytes)
        with __import__('tempfile').TemporaryDirectory() as td:
            run=LiveDIGRRun.start(authority,'DIGR：x',__import__('pathlib').Path(td),FakeClock(),run_id='digr-12345678')
            with self.assertRaises(RouteAcquisitionError):sess.load_execution_protocol_for_run(run,startup)
            self.assertEqual(run.phase.phase,RunPhase.ABORTED)

    def test_contents_base64_wrapper_is_decoded(self):
        payload=json.dumps({'type':'file','path':'VERSION','encoding':'base64','content':base64.b64encode(VERSION).decode()}).encode()
        self.assertEqual(normalize_pinned_file_bytes(payload,'VERSION'),VERSION)
        self.assertEqual(normalize_pinned_file_bytes(VERSION,'VERSION'),VERSION)

    def test_raw_failure_falls_back_to_contents_raw_contract(self):
        f=FakeFetcher(raw_fail_paths={'manifest.json'})
        s=RepositoryTransportSession(f)
        b=s.acquire_startup('DIGR：x')
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
        self.assertEqual(cm.exception.receipts[-1].purpose,'stable_ref_corroboration_validation_r1')
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
            sess.acquire_startup('DIGR：x')
        self.assertEqual(cm.exception.receipts[-1].purpose,'pinned_route_metadata_validation')
        self.assertTrue(route_failure_permitted(cm.exception.receipts))

    def test_non_candidate_never_starts_repository_acquisition(self):
        f=FakeFetcher(); s=RepositoryTransportSession(f)
        with self.assertRaises(ValueError): s.acquire_startup('ordinary chat')
        self.assertEqual(f.requests,[])

    def test_every_candidate_acquires_before_pinned_classification(self):
        for message in ('DIGR/help','DIGR讨论','DIGRAPH','DIGR：'):
            f=FakeFetcher(source_kind='github_connector'); s=RepositoryTransportSession(f)
            startup=s.acquire_startup(message)
            self.assertEqual(len(f.requests),4,message)
            self.assertEqual(
                [r.purpose for r in f.requests],
                ['stable_branch_primary_r1','pinned:manifest.json','pinned:VERSION','pinned:entry/STARTUP.md'],
            )
            self.assertEqual(startup.raw_message_sha256,__import__('hashlib').sha256(message.encode()).hexdigest())

    def test_pinned_startup_cannot_classify_different_message(self):
        startup=RepositoryTransportSession(FakeFetcher(source_kind='github_connector')).acquire_startup('DIGRAPH')
        with self.assertRaisesRegex(ValueError,'different raw message'):
            startup.classify('DIGR是什么？')

    def test_direct_native_candidate_uses_branch_ref_consensus_before_classification(self):
        f=FakeFetcher();startup=RepositoryTransportSession(f).acquire_startup('DIGRAPH')
        self.assertEqual(startup.classify('DIGRAPH').kind.value,'NATIVE')
        self.assertEqual(len(f.requests),5)
        self.assertEqual(
            [r.purpose for r in f.requests],
            ['stable_branch_primary_r1','stable_ref_corroboration_r1',
             'pinned:manifest.json','pinned:VERSION','pinned:entry/STARTUP.md'],
        )

    def test_pinned_raw_urls_are_immutable_sha_urls(self):
        self.assertEqual(
            raw_file_url('Gual-Wells','Deep-Iteration-GPT-Runtime',SHA,'VERSION'),
            f'https://raw.githubusercontent.com/Gual-Wells/Deep-Iteration-GPT-Runtime/{SHA}/VERSION'
        )

if __name__=='__main__': unittest.main()
