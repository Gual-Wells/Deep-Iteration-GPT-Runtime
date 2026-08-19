"""Host-facing repository transport for DIGR 5.0.0-alpha.3.

Alpha 2 deliberately kept ``runtime.routing`` free of network I/O, but the
production personalization path then had no executable bridge between a route
obligation and the bytes consumed by the deterministic verifier.  Alpha 3
closes that boundary without moving DIGR execution semantics into the local
layer.

The transport has four jobs only:

* make an *actual* direct acquisition attempt before route failure is allowed;
* resolve mutable ``stable`` through direct GitHub REST observations and reject
  search/index/crawl snapshots as ref authority;
* pin all later reads to the resolved immutable 40-hex commit;
* deliver complete pinned bytes, accepting either raw responses or the GitHub
  Contents API base64 wrapper when a host cannot request the raw media type.

The module includes a standard-library HTTPS fetcher for ordinary Python hosts.
ChatGPT integrations may instead provide a connector-backed ``fetch`` callable,
but they must preserve the provenance/freshness fields in ``TransportResponse``.
No N/T/R/S/D/L, invocation-surface, clock, stop or proof semantics live here.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any, Callable, Mapping, NoReturn
import base64
import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

from .protocol_pin import raw_file_url, validate_commit_sha, validate_repo_path
from .routing import (
    AUTHORITATIVE_API_BASE,
    AUTHORITATIVE_REF_API_URL,
    AUTHORITATIVE_BRANCH_API_URL,
    AUTHORITATIVE_REPOSITORY,
    AUTHORITATIVE_REF,
    MANIFEST_PATH,
    VERSION_PATH,
    RefResolution,
    RouteReceipt,
    DiscoveryPlan,
    bytes_sha256,
    candidate_route_key,
    discovery_plan_from_manifest_bytes,
    ref_resolution_from_github_payload,
    route_receipt_from_ref_resolution,
)

CONTENTS_RAW_ACCEPT = 'application/vnd.github.raw+json'
GITHUB_JSON_ACCEPT = 'application/vnd.github+json'
USER_AGENT = 'Deep-Iteration-GPT-Runtime/5.0.0-alpha.3'

LIVE_SOURCE_KINDS = frozenset({'direct_https', 'github_connector'})
FRESHNESS_LIVE_DIRECT = 'live_direct'
FRESHNESS_IMMUTABLE = 'immutable_sha'
FRESHNESS_UNTRUSTED = 'untrusted'


@dataclass(frozen=True)
class FetchRequest:
    url: str
    purpose: str
    accept: str
    mutable_ref: bool = False

    def __post_init__(self):
        if not isinstance(self.url, str) or not self.url.startswith('https://'):
            raise ValueError('transport request URL must be absolute HTTPS')
        if not isinstance(self.purpose, str) or not self.purpose:
            raise ValueError('transport request purpose required')
        if not isinstance(self.accept, str) or not self.accept:
            raise ValueError('transport request Accept media type required')
        if not isinstance(self.mutable_ref, bool):
            raise TypeError('mutable_ref must be bool')


@dataclass(frozen=True)
class TransportResponse:
    request_url: str
    status: int
    body: bytes
    source_kind: str
    freshness: str
    headers: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if not isinstance(self.request_url, str) or not self.request_url.startswith('https://'):
            raise ValueError('response request_url must be absolute HTTPS')
        if not isinstance(self.status, int) or self.status < 0:
            raise ValueError('response status must be a non-negative int')
        if not isinstance(self.body, (bytes, bytearray)):
            raise TypeError('response body must be bytes')
        object.__setattr__(self, 'body', bytes(self.body))
        if not isinstance(self.source_kind, str) or not self.source_kind:
            raise ValueError('source_kind required')
        if self.freshness not in (FRESHNESS_LIVE_DIRECT, FRESHNESS_IMMUTABLE, FRESHNESS_UNTRUSTED):
            raise ValueError('invalid freshness value')
        norm=[]
        for k,v in self.headers:
            if not isinstance(k,str) or not isinstance(v,str):
                raise TypeError('headers must be string pairs')
            norm.append((k.lower(),v))
        object.__setattr__(self,'headers',tuple(norm))

    @property
    def direct(self) -> bool:
        return self.source_kind in LIVE_SOURCE_KINDS

    @property
    def body_sha256(self) -> str:
        return sha256(self.body).hexdigest()


@dataclass(frozen=True)
class AcquisitionAttemptReceipt:
    seq: int
    purpose: str
    request_url: str
    source_kind: str
    freshness: str
    status: int
    success: bool
    response_sha256: str | None = None
    commit_sha: str | None = None
    failure: str | None = None

    def __post_init__(self):
        if not isinstance(self.seq,int) or self.seq < 1:
            raise ValueError('attempt seq must be >=1')
        for name,val in (('purpose',self.purpose),('request_url',self.request_url),('source_kind',self.source_kind),('freshness',self.freshness)):
            if not isinstance(val,str) or not val:
                raise ValueError(f'{name} required')
        if not self.request_url.startswith('https://'):
            raise ValueError('attempt request_url must be HTTPS')
        if self.freshness not in (FRESHNESS_LIVE_DIRECT,FRESHNESS_IMMUTABLE,FRESHNESS_UNTRUSTED):
            raise ValueError('invalid attempt freshness')
        if not isinstance(self.status,int) or self.status < 0:
            raise ValueError('attempt status must be non-negative int')
        if not isinstance(self.success,bool):
            raise TypeError('attempt success must be bool')
        if self.response_sha256 is not None:
            d=self.response_sha256.lower()
            if len(d)!=64 or any(c not in '0123456789abcdef' for c in d):
                raise ValueError('response_sha256 must be 64 hex')
            object.__setattr__(self,'response_sha256',d)
        if self.commit_sha is not None:
            object.__setattr__(self,'commit_sha',validate_commit_sha(self.commit_sha))
        if self.failure is not None and (not isinstance(self.failure,str) or not self.failure):
            raise ValueError('failure must be non-empty text when present')

    def to_dict(self) -> dict[str,Any]:
        return asdict(self)


class RouteAcquisitionError(RuntimeError):
    """Acquisition failure carrying evidence that an attempt actually occurred."""
    def __init__(self, message: str, receipts: tuple[AcquisitionAttemptReceipt, ...]):
        super().__init__(message)
        self.receipts=tuple(receipts)


def _canonical_repository_url(url: str) -> bool:
    try:
        p=urlparse(url)
    except Exception:
        return False
    if p.scheme != 'https':
        return False
    if p.netloc == 'api.github.com':
        return p.path.startswith('/repos/Gual-Wells/Deep-Iteration-GPT-Runtime/')
    if p.netloc == 'raw.githubusercontent.com':
        return p.path.startswith('/Gual-Wells/Deep-Iteration-GPT-Runtime/')
    return False


def route_failure_permitted(receipts: tuple[AcquisitionAttemptReceipt, ...] | list[AcquisitionAttemptReceipt]) -> bool:
    """Necessary precondition for the fixed route-failure response.

    At least one canonical repository acquisition must have actually been
    attempted during this turn.  The caller must *also* have a real current-stage
    acquisition/integrity failure; this helper intentionally does not invent one.
    """
    if not receipts:
        return False
    return any(
        isinstance(r,AcquisitionAttemptReceipt) and _canonical_repository_url(r.request_url)
        for r in receipts
    )


class UrllibDirectFetcher:
    """Concrete direct HTTPS fetcher for public GitHub resources.

    Mutable-ref requests ask intermediaries to revalidate instead of serving a
    search/index snapshot.  This cannot make an external CDN mathematically
    instantaneous, so Alpha 3 also corroborates ``stable`` with the independent
    Branches endpoint before accepting the pin.
    """
    def __init__(self, timeout: float = 15.0):
        self.timeout=float(timeout)
        if self.timeout <= 0:
            raise ValueError('timeout must be positive')

    def __call__(self, request: FetchRequest) -> TransportResponse:
        headers={'Accept':request.accept,'User-Agent':USER_AGENT}
        if request.mutable_ref:
            headers['Cache-Control']='no-cache'
            headers['Pragma']='no-cache'
        req=urllib.request.Request(request.url,headers=headers,method='GET')
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as resp:
                body=resp.read()
                hs=tuple((k,v) for k,v in resp.headers.items())
                return TransportResponse(
                    request.url,
                    int(getattr(resp,'status',200)),
                    body,
                    'direct_https',
                    FRESHNESS_LIVE_DIRECT if request.mutable_ref else FRESHNESS_IMMUTABLE,
                    hs,
                )
        except urllib.error.HTTPError as exc:
            try: body=exc.read()
            except Exception: body=b''
            hs=tuple((k,v) for k,v in exc.headers.items()) if exc.headers else ()
            return TransportResponse(
                request.url,int(exc.code),body,'direct_https',
                FRESHNESS_LIVE_DIRECT if request.mutable_ref else FRESHNESS_IMMUTABLE,hs,
            )


def _response_ok(request: FetchRequest, response: TransportResponse, *, mutable: bool) -> None:
    if response.request_url != request.url:
        raise ValueError('transport response URL does not match request')
    if response.status != 200:
        raise ValueError(f'HTTP status {response.status}')
    if not response.direct:
        raise ValueError('search/index/crawl response is not admissible repository transport')
    if mutable and response.freshness != FRESHNESS_LIVE_DIRECT:
        raise ValueError('mutable stable ref requires live direct freshness provenance')
    if not mutable and response.freshness not in (FRESHNESS_LIVE_DIRECT,FRESHNESS_IMMUTABLE):
        raise ValueError('pinned resource provenance is untrusted')


def _branch_sha(payload: bytes | Mapping[str,Any]) -> str:
    if isinstance(payload,(bytes,bytearray)):
        try: payload=json.loads(bytes(payload).decode('utf-8'))
        except (UnicodeDecodeError,json.JSONDecodeError) as exc:
            raise ValueError('GitHub branch response is not valid UTF-8 JSON') from exc
    if not isinstance(payload,Mapping):
        raise TypeError('GitHub branch response must be a mapping or bytes')
    if payload.get('name') != 'stable':
        raise ValueError('GitHub branch response is not stable')
    commit=payload.get('commit')
    if not isinstance(commit,Mapping):
        raise ValueError('GitHub branch response missing commit')
    return validate_commit_sha(commit.get('sha'))


def _contents_wrapper_bytes(body: bytes, expected_path: str | None = None) -> bytes | None:
    """Decode GitHub Contents API object responses; return None for non-wrapper raw bytes."""
    stripped=body.lstrip()
    if not stripped.startswith(b'{'):
        return None
    try: obj=json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError,json.JSONDecodeError):
        return None
    if not isinstance(obj,Mapping) or 'content' not in obj or 'encoding' not in obj:
        return None
    if obj.get('type') != 'file':
        return None
    if expected_path is not None and obj.get('path') not in (None,expected_path):
        raise ValueError('GitHub Contents response path mismatch')
    encoding=obj.get('encoding')
    content=obj.get('content')
    if encoding != 'base64' or not isinstance(content,str):
        raise ValueError('GitHub Contents file body is not base64 encoded')
    try:
        return base64.b64decode(content,validate=True)
    except Exception as exc:
        # GitHub inserts newlines in base64; validate after removing ASCII whitespace.
        try:
            compact=''.join(content.split())
            return base64.b64decode(compact,validate=True)
        except Exception:
            raise ValueError('invalid base64 content in GitHub Contents response') from exc


def normalize_pinned_file_bytes(body: bytes, expected_path: str | None = None) -> bytes:
    """Return complete file bytes from raw media or GitHub Contents JSON."""
    if not isinstance(body,(bytes,bytearray)):
        raise TypeError('pinned response body must be bytes')
    raw=bytes(body)
    decoded=_contents_wrapper_bytes(raw,expected_path)
    return decoded if decoded is not None else raw


FetchCallable = Callable[[FetchRequest],TransportResponse]


class RepositoryTransportSession:
    """Deterministic acquisition orchestration around a host-provided fetcher."""
    def __init__(self, fetch: FetchCallable):
        if not callable(fetch):
            raise TypeError('fetch must be callable')
        self.fetch=fetch
        self._receipts: list[AcquisitionAttemptReceipt]=[]

    @property
    def receipts(self) -> tuple[AcquisitionAttemptReceipt,...]:
        return tuple(self._receipts)

    def _do(self, request: FetchRequest, *, mutable: bool, commit_sha: str | None=None) -> TransportResponse:
        seq=len(self._receipts)+1
        try:
            response=self.fetch(request)
            if not isinstance(response,TransportResponse):
                raise TypeError('fetcher must return TransportResponse')
            _response_ok(request,response,mutable=mutable)
            receipt=AcquisitionAttemptReceipt(
                seq,request.purpose,request.url,response.source_kind,response.freshness,response.status,True,
                response.body_sha256,commit_sha,None,
            )
            self._receipts.append(receipt)
            return response
        except Exception as exc:
            status=0; source='unknown'; freshness=FRESHNESS_UNTRUSTED; digest=None
            if 'response' in locals() and isinstance(response,TransportResponse):
                status=response.status; source=response.source_kind; freshness=response.freshness; digest=response.body_sha256
            self._receipts.append(AcquisitionAttemptReceipt(
                seq,request.purpose,request.url,source,freshness,status,False,digest,commit_sha,str(exc),
            ))
            raise RouteAcquisitionError(str(exc),self.receipts) from exc

    def _validation_failure(self, purpose: str, request_url: str, exc: Exception, *, commit_sha: str | None=None, freshness: str=FRESHNESS_IMMUTABLE) -> 'NoReturn':
        self._receipts.append(AcquisitionAttemptReceipt(
            len(self._receipts)+1,purpose,request_url,'validation',freshness,200,False,None,commit_sha,str(exc),
        ))
        raise RouteAcquisitionError(str(exc),self.receipts) from exc

    def resolve_stable(self) -> RefResolution:
        primary_req=FetchRequest(AUTHORITATIVE_REF_API_URL,'stable_ref_primary',GITHUB_JSON_ACCEPT,True)
        primary=self._do(primary_req,mutable=True)
        try:
            resolution=ref_resolution_from_github_payload(primary.body)
        except Exception as exc:
            self._validation_failure('stable_ref_primary_validation',primary_req.url,exc,freshness=FRESHNESS_LIVE_DIRECT)

        branch_req=FetchRequest(AUTHORITATIVE_BRANCH_API_URL,'stable_ref_corroboration',GITHUB_JSON_ACCEPT,True)
        branch=self._do(branch_req,mutable=True)
        try:
            corroborated=_branch_sha(branch.body)
        except Exception as exc:
            self._validation_failure('stable_ref_corroboration_validation',branch_req.url,exc,freshness=FRESHNESS_LIVE_DIRECT)
        if corroborated != resolution.commit_sha:
            # Add an explicit failed consensus receipt rather than silently picking one.
            self._receipts.append(AcquisitionAttemptReceipt(
                len(self._receipts)+1,'stable_ref_consensus',AUTHORITATIVE_REF_API_URL,
                'consensus',FRESHNESS_LIVE_DIRECT,200,False,None,None,
                f'ref/branch SHA mismatch: {resolution.commit_sha} != {corroborated}',
            ))
            raise RouteAcquisitionError('stable ref observations disagree',self.receipts)
        return resolution

    def fetch_pinned_file(self, commit_sha: str, path: str) -> bytes:
        sha=validate_commit_sha(commit_sha); rel=validate_repo_path(path)
        raw_url=raw_file_url('Gual-Wells','Deep-Iteration-GPT-Runtime',sha,rel)
        req=FetchRequest(raw_url,f'pinned:{rel}','application/octet-stream',False)
        raw_failed=False
        try:
            response=self._do(req,mutable=False,commit_sha=sha)
            try:
                return normalize_pinned_file_bytes(response.body,rel)
            except Exception as exc:
                self._receipts.append(AcquisitionAttemptReceipt(
                    len(self._receipts)+1,f'pinned-validation:{rel}',req.url,'validation',FRESHNESS_IMMUTABLE,200,False,response.body_sha256,sha,str(exc),
                ))
                raw_failed=True
        except RouteAcquisitionError:
            raw_failed=True
        if raw_failed:
            # One standards-compliant fallback closes the Alpha2 Contents-API/raw-bytes gap.
            from .routing import content_api_url
            api_url=content_api_url(sha,rel)
            api_req=FetchRequest(api_url,f'pinned-fallback:{rel}',CONTENTS_RAW_ACCEPT,False)
            response=self._do(api_req,mutable=False,commit_sha=sha)
            try:
                return normalize_pinned_file_bytes(response.body,rel)
            except Exception as exc:
                self._validation_failure(f'pinned-fallback-validation:{rel}',api_req.url,exc,commit_sha=sha)
        raise AssertionError('unreachable pinned transport state')

    def acquire_startup(self, message: str) -> 'RepositoryStartupBundle':
        if candidate_route_key(message) is None:
            raise ValueError('message is not a DIGR router candidate')
        resolution=self.resolve_stable()
        manifest_data=self.fetch_pinned_file(resolution.commit_sha,MANIFEST_PATH)
        version_data=self.fetch_pinned_file(resolution.commit_sha,VERSION_PATH)
        try:
            route=route_receipt_from_ref_resolution(resolution,manifest_data,version_data)
            plan=discovery_plan_from_manifest_bytes(route,manifest_data,version_data)
        except Exception as exc:
            manifest_url=raw_file_url('Gual-Wells','Deep-Iteration-GPT-Runtime',resolution.commit_sha,MANIFEST_PATH)
            self._validation_failure('pinned_route_metadata_validation',manifest_url,exc,commit_sha=resolution.commit_sha)
        startup=[]
        for path in plan.initial_paths:
            startup.append((path,self.fetch_pinned_file(resolution.commit_sha,path)))
        return RepositoryStartupBundle(
            resolution,route,manifest_data,version_data,plan,tuple(startup),self.receipts
        )


@dataclass(frozen=True)
class RepositoryStartupBundle:
    resolution: RefResolution
    route_receipt: RouteReceipt
    manifest_bytes: bytes
    version_bytes: bytes
    discovery_plan: DiscoveryPlan
    startup_files: tuple[tuple[str,bytes],...]
    attempts: tuple[AcquisitionAttemptReceipt,...]

    def __post_init__(self):
        if not isinstance(self.resolution,RefResolution): raise TypeError('resolution')
        if not isinstance(self.route_receipt,RouteReceipt): raise TypeError('route_receipt')
        if self.route_receipt.pinned_commit != self.resolution.commit_sha:
            raise ValueError('startup bundle pin mismatch')
        for data_name,data in (('manifest_bytes',self.manifest_bytes),('version_bytes',self.version_bytes)):
            if not isinstance(data,(bytes,bytearray)): raise TypeError(f'{data_name} must be bytes')
        expected=self.discovery_plan.initial_paths
        paths=tuple(p for p,_ in self.startup_files)
        if paths != expected: raise ValueError('startup_files do not match discovery plan initial_paths')
        for p,b in self.startup_files:
            validate_repo_path(p)
            if not isinstance(b,(bytes,bytearray)): raise TypeError('startup file bytes required')
        if not route_failure_permitted(self.attempts):
            raise ValueError('startup bundle lacks acquisition evidence')
