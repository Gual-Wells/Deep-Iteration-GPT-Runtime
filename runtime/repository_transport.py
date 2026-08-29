"""Host-facing repository transport for DIGR 5.0.0-Berta2.

The transport bridges the version-neutral broad candidate router to pinned
manifest/VERSION/startup bytes without moving DIGR execution semantics into
the local layer.

The transport has four jobs only:

* make an *actual* direct acquisition attempt before route failure is allowed;
* resolve mutable ``stable`` through a repository-native connector branch HEAD or direct GitHub REST observations and reject
  search/index/crawl snapshots as ref authority;
* pin all later reads to the resolved immutable 40-hex commit;
* deliver complete pinned bytes, accepting either raw responses or the GitHub
  Contents API base64 wrapper when a host cannot request the raw media type;
* aggregate the post-genesis logical entrypoint/core transport through the manifest-declared immutable execution bundle when available.

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
from .execution_protocol import (
    ExecutionProtocolBundle, receipt_from_individual_files, verify_execution_bundle,
    verify_descriptor_execution_bundle,
)
from .invocation_surface import InvocationKind, classify_surface
from .routing import (
    AUTHORITATIVE_API_BASE,
    AUTHORITATIVE_REF_API_URL,
    AUTHORITATIVE_BRANCH_API_URL,
    AUTHORITATIVE_REPOSITORY,
    AUTHORITATIVE_REPOSITORY_URL,
    AUTHORITATIVE_REF,
    MANIFEST_PATH,
    RUNTIME_DESCRIPTOR_PATH,
    VERSION_PATH,
    RefResolution,
    RouteReceipt,
    DiscoveryPlan,
    bytes_sha256,
    candidate_route_key,
    route_requires_repository,
    discovery_plan_from_manifest_bytes,
    ref_resolution_from_github_payload,
    ref_resolution_from_branch_payload,
    route_receipt_from_ref_resolution,
)

CONTENTS_RAW_ACCEPT = 'application/vnd.github.raw+json'
GITHUB_JSON_ACCEPT = 'application/vnd.github+json'
USER_AGENT = 'Deep-Iteration-GPT-Runtime/5.0.0-Berta2'
STABLE_DESCRIPTOR_SCHEMA = 'digr-runtime-descriptor/v1'
STABLE_VERSION = '5.0.0-Berta2'
STABLE_PROTOCOL = 'digr-v5.0'

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


@dataclass(frozen=True)
class PinnedStartupFileReceipt:
    path: str
    sha256: str
    byte_length: int

    def __post_init__(self):
        object.__setattr__(self,'path',validate_repo_path(self.path))
        digest=self.sha256
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('startup file sha256 must be 64 lowercase hex')
        if not isinstance(self.byte_length,int) or isinstance(self.byte_length,bool) or self.byte_length<0:
            raise ValueError('startup file byte_length must be a non-negative int')

    def to_dict(self) -> dict[str,Any]:
        return asdict(self)


@dataclass(frozen=True)
class StartupRouteBinding:
    """Auditable transport evidence; never a second protocol-semantic source."""
    schema_version: int
    route: RouteReceipt
    startup_files: tuple[PinnedStartupFileReceipt,...]
    attempts: tuple[AcquisitionAttemptReceipt,...]

    def __post_init__(self):
        if self.schema_version!=1:
            raise ValueError('unsupported startup route binding schema')
        if not isinstance(self.route,RouteReceipt):
            raise TypeError('route must be RouteReceipt')
        object.__setattr__(self,'startup_files',tuple(self.startup_files))
        object.__setattr__(self,'attempts',tuple(self.attempts))
        if not self.startup_files:
            raise ValueError('startup route binding requires pinned startup files')
        if any(not isinstance(x,PinnedStartupFileReceipt) for x in self.startup_files):
            raise TypeError('startup_files must contain PinnedStartupFileReceipt')
        if not route_failure_permitted(self.attempts):
            raise ValueError('startup route binding lacks acquisition evidence')

    def to_dict(self) -> dict[str,Any]:
        return {
            'schema_version':self.schema_version,
            'route':self.route.to_dict(),
            'startup_files':[x.to_dict() for x in self.startup_files],
            'attempts':[x.to_dict() for x in self.attempts],
        }


class RouteAcquisitionError(RuntimeError):
    """Acquisition failure carrying evidence that an attempt actually occurred."""
    def __init__(self, message: str, receipts: tuple[AcquisitionAttemptReceipt, ...]):
        super().__init__(message)
        self.receipts=tuple(receipts)


class ProtocolLoadAbortError(RuntimeError):
    """Both mandatory protocol loading and persistence of ABORTED failed."""
    def __init__(self, protocol_error: Exception, abort_error: Exception):
        self.protocol_error = protocol_error
        self.abort_error = abort_error
        super().__init__(
            'execution protocol load failed and the born run could not be '
            f'aborted: load={protocol_error}; abort={abort_error}'
        )


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
    search/index snapshot. This cannot make an external CDN mathematically
    instantaneous, so Berta2 requires current branch and independent Git-ref
    observations to agree before direct REST accepts the pin.
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
        """Resolve current ``stable`` using transport-specific authority.

        A connected GitHub repository connector may directly expose the current
        branch resource and is accepted from that single repository-native HEAD
        observation. Direct REST corroborates Branches + Git-ref. If a push lands
        between the two live observations, one bounded re-observation is allowed
        before fail-closed consensus is declared. Search/index/crawl provenance
        remains inadmissible.
        """
        last_pair=None
        for observation_round in (1,2):
            branch_req=FetchRequest(AUTHORITATIVE_BRANCH_API_URL,f'stable_branch_primary_r{observation_round}',GITHUB_JSON_ACCEPT,True)
            branch=self._do(branch_req,mutable=True)
            try:
                resolution=ref_resolution_from_branch_payload(branch.body)
            except Exception as exc:
                self._validation_failure(f'stable_branch_primary_validation_r{observation_round}',branch_req.url,exc,freshness=FRESHNESS_LIVE_DIRECT)

            if branch.source_kind == 'github_connector':
                return resolution

            ref_req=FetchRequest(AUTHORITATIVE_REF_API_URL,f'stable_ref_corroboration_r{observation_round}',GITHUB_JSON_ACCEPT,True)
            ref=self._do(ref_req,mutable=True)
            try:
                corroborated=ref_resolution_from_github_payload(ref.body)
            except Exception as exc:
                self._validation_failure(f'stable_ref_corroboration_validation_r{observation_round}',ref_req.url,exc,freshness=FRESHNESS_LIVE_DIRECT)
            if corroborated.commit_sha == resolution.commit_sha:
                return resolution
            last_pair=(resolution.commit_sha,corroborated.commit_sha)

        assert last_pair is not None
        self._receipts.append(AcquisitionAttemptReceipt(
            len(self._receipts)+1,'stable_ref_consensus',AUTHORITATIVE_BRANCH_API_URL,
            'consensus',FRESHNESS_LIVE_DIRECT,200,False,None,None,
            f'branch/ref SHA mismatch after bounded retry: {last_pair[0]} != {last_pair[1]}',
        ))
        raise RouteAcquisitionError('stable ref observations disagree after bounded retry',self.receipts)

    def resolve_stable_head(self, *, paranoid: bool=False) -> RefResolution:
        """Compatibility alias for the always-safe stable resolver.

        Direct REST always corroborates branch and Git-ref observations;
        connector branch resources remain connector-native authority. The
        legacy ``paranoid`` flag is accepted but can no longer weaken this.
        """
        if type(paranoid) is not bool:
            raise TypeError('paranoid must be bool')
        return self.resolve_stable()

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
        candidate_key=candidate_route_key(message)
        if candidate_key is None:
            raise ValueError('message is not a DIGR router candidate')
        if not route_requires_repository(message):
            raise AssertionError('candidate route unexpectedly declined repository acquisition')
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
            resolution,route,manifest_data,version_data,plan,tuple(startup),self.receipts,
            candidate_key,sha256(message.encode('utf-8')).hexdigest(),
        )

    def acquire_stable_descriptor_from_startup(
        self, routing_startup: 'RepositoryStartupBundle', message: str, *, _allow_help: bool=False,
    ) -> 'StableDescriptorStartup':
        """Continue from a manifest-pinned classification without re-reading HEAD."""
        if not isinstance(routing_startup,RepositoryStartupBundle):
            raise TypeError('routing_startup must be RepositoryStartupBundle')
        surface=routing_startup.classify(message)
        allowed=(surface.kind is InvocationKind.EXECUTING
                 or (_allow_help and surface.kind is InvocationKind.HELP))
        if not allowed:
            raise ValueError('stable descriptor continuation requires pinned EXECUTING/HELP classification')
        resolution=routing_startup.resolution
        try:
            manifest=json.loads(bytes(routing_startup.manifest_bytes).decode('utf-8'))
            if not isinstance(manifest,Mapping):
                raise ValueError('pinned manifest root must be an object')
            descriptor_path=validate_repo_path(manifest.get('runtime_descriptor'))
            if descriptor_path!=RUNTIME_DESCRIPTOR_PATH:
                raise ValueError('pinned manifest runtime_descriptor path mismatch')
        except Exception as exc:
            manifest_url=raw_file_url('Gual-Wells','Deep-Iteration-GPT-Runtime',resolution.commit_sha,MANIFEST_PATH)
            self._validation_failure('stable_descriptor_navigation_validation',manifest_url,exc,commit_sha=resolution.commit_sha)
        descriptor_bytes=self.fetch_pinned_file(resolution.commit_sha,descriptor_path)
        descriptor_url=raw_file_url(
            'Gual-Wells','Deep-Iteration-GPT-Runtime',resolution.commit_sha,descriptor_path,
        )
        try:
            descriptor=json.loads(descriptor_bytes.decode('utf-8'))
            if not isinstance(descriptor,dict):
                raise ValueError('runtime descriptor root must be an object')
            if descriptor.get('schema')!=STABLE_DESCRIPTOR_SCHEMA:
                raise ValueError('runtime descriptor schema mismatch')
            if descriptor.get('version')!=STABLE_VERSION:
                raise ValueError('runtime descriptor version mismatch')
            if descriptor.get('protocol')!=STABLE_PROTOCOL:
                raise ValueError('runtime descriptor protocol mismatch')
            manifest_version=bytes(routing_startup.version_bytes).decode('utf-8').strip()
            if descriptor.get('version')!=manifest_version or descriptor.get('version')!=manifest.get('version'):
                raise ValueError('runtime descriptor disagrees with pinned manifest/VERSION')
            if descriptor.get('protocol')!=manifest.get('protocol'):
                raise ValueError('runtime descriptor disagrees with pinned manifest protocol')
            adapter=descriptor.get('minimum_adapter')
            if not isinstance(adapter,Mapping):
                raise ValueError('runtime descriptor minimum_adapter missing')
            if adapter.get('repository')!=AUTHORITATIVE_REPOSITORY or adapter.get('ref')!=AUTHORITATIVE_REF:
                raise ValueError('runtime descriptor repository locator mismatch')
            if adapter.get('descriptor_path')!=RUNTIME_DESCRIPTOR_PATH:
                raise ValueError('runtime descriptor path mismatch')
            artifacts=descriptor.get('artifacts')
            if not isinstance(artifacts,Mapping):
                raise ValueError('runtime descriptor artifacts missing')
            execution_meta=artifacts.get('execution_bundle')
            if not isinstance(execution_meta,Mapping):
                raise ValueError('runtime descriptor execution_bundle metadata missing')
            validate_repo_path(execution_meta.get('path'))
            for name in ('sha256','execution_set_sha256'):
                digest=execution_meta.get(name)
                if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
                    raise ValueError(f'runtime descriptor {name} invalid')
            for name in ('byte_length','member_count'):
                value=execution_meta.get(name)
                if not isinstance(value,int) or isinstance(value,bool) or value<=0:
                    raise ValueError(f'runtime descriptor {name} must be a positive int')
        except Exception as exc:
            self._validation_failure('stable_descriptor_validation',descriptor_url,exc,commit_sha=resolution.commit_sha)
        return StableDescriptorStartup(
            resolution,routing_startup.route_receipt,descriptor_bytes,descriptor,
            self.receipts,routing_startup,
        )

    def acquire_stable_descriptor(self, message: str, *, paranoid: bool=False, _allow_help: bool=False) -> 'StableDescriptorStartup':
        """Compatibility convenience: acquire pinned startup before classification."""
        if type(paranoid) is not bool:
            raise TypeError('paranoid must be bool')
        routing_startup=self.acquire_startup(message)
        return self.acquire_stable_descriptor_from_startup(
            routing_startup,message,_allow_help=_allow_help,
        )

    def acquire_stable_execution_from_startup(
        self, routing_startup: 'RepositoryStartupBundle', message: str,
    ) -> 'StableExecutionStartup':
        """Acquire descriptor + verified bundle at the already pinned SHA."""
        startup=self.acquire_stable_descriptor_from_startup(routing_startup,message)
        path=validate_repo_path(startup.descriptor['artifacts']['execution_bundle']['path'])
        if routing_startup.discovery_plan.execution_bundle_path!=path:
            exc=ValueError('descriptor execution bundle path disagrees with pinned manifest')
            self._validation_failure(
                'stable_execution_navigation_validation',AUTHORITATIVE_REPOSITORY_URL,exc,
                commit_sha=startup.resolution.commit_sha,
            )
        raw=self.fetch_pinned_file(startup.resolution.commit_sha,path)
        try:
            descriptor_protocol=verify_descriptor_execution_bundle(
                raw,commit_sha=startup.resolution.commit_sha,
                descriptor_bytes=startup.descriptor_bytes,
            )
            protocol=verify_execution_bundle(
                raw,commit_sha=startup.resolution.commit_sha,
                manifest_bytes=routing_startup.manifest_bytes,
                expected_paths=routing_startup.discovery_plan.full_protocol_paths,
            )
            if (descriptor_protocol.files!=protocol.files
                    or descriptor_protocol.receipt.container_sha256!=protocol.receipt.container_sha256
                    or descriptor_protocol.receipt.container_byte_length!=protocol.receipt.container_byte_length):
                raise ValueError('descriptor and manifest execution verification disagree')
        except Exception as exc:
            url=raw_file_url('Gual-Wells','Deep-Iteration-GPT-Runtime',startup.resolution.commit_sha,path)
            self._validation_failure('stable_execution_bundle_validation',url,exc,commit_sha=startup.resolution.commit_sha)
        return StableExecutionStartup(startup,protocol,self.receipts)

    def acquire_stable_execution(self, message: str, *, paranoid: bool=False) -> 'StableExecutionStartup':
        """Compatibility convenience: route, classify, then acquire execution."""
        if type(paranoid) is not bool:
            raise TypeError('paranoid must be bool')
        routing_startup=self.acquire_startup(message)
        return self.acquire_stable_execution_from_startup(routing_startup,message)

    def acquire_stable_help_from_startup(
        self, routing_startup: 'RepositoryStartupBundle', message: str='DIGR/help',
    ) -> 'StableHelpArtifact':
        """Acquire manifest-declared Help at the already pinned SHA."""
        if not isinstance(routing_startup,RepositoryStartupBundle):
            raise TypeError('routing_startup must be RepositoryStartupBundle')
        surface=routing_startup.classify(message)
        if surface.kind is not InvocationKind.HELP:
            raise ValueError('stable Help continuation requires pinned HELP classification')
        try:
            path=routing_startup.discovery_plan.help_path
            if path is None:
                raise ValueError('pinned manifest does not declare Help')
            path=validate_repo_path(path)
        except Exception as exc:
            self._validation_failure('stable_help_navigation_validation',AUTHORITATIVE_REPOSITORY_URL,exc,commit_sha=routing_startup.resolution.commit_sha)
        data=self.fetch_pinned_file(routing_startup.resolution.commit_sha,path)
        try:
            data.decode('utf-8')
        except Exception as exc:
            url=raw_file_url('Gual-Wells','Deep-Iteration-GPT-Runtime',routing_startup.resolution.commit_sha,path)
            self._validation_failure('stable_help_validation',url,exc,commit_sha=routing_startup.resolution.commit_sha)
        return StableHelpArtifact(
            routing_startup,path,data,'text/markdown; charset=utf-8',self.receipts,
        )

    def acquire_stable_help(self, message: str='DIGR/help', *, paranoid: bool=False) -> 'StableHelpArtifact':
        """Compatibility convenience: route, classify, then acquire Help."""
        if type(paranoid) is not bool:
            raise TypeError('paranoid must be bool')
        routing_startup=self.acquire_startup(message)
        return self.acquire_stable_help_from_startup(routing_startup,message)


    def acquire_execution_protocol(self, startup: 'RepositoryStartupBundle') -> ExecutionProtocolBundle:
        """Acquire and verify the logical entrypoint/core after Clock Genesis.

        Current manifests use one immutable execution bundle. Older staged
        manifests remain supported through individually pinned logical files.
        Legacy non-staged manifests already carry their full protocol in the
        startup bundle and are normalized into the same load receipt shape.
        """
        if not isinstance(startup,RepositoryStartupBundle):
            raise TypeError('startup must be RepositoryStartupBundle')
        sha=startup.resolution.commit_sha;plan=startup.discovery_plan
        expected=plan.full_protocol_paths
        if plan.execution_bundle_path is not None:
            raw=self.fetch_pinned_file(sha,plan.execution_bundle_path)
            try:
                return verify_execution_bundle(
                    raw,commit_sha=sha,manifest_bytes=startup.manifest_bytes,
                    expected_paths=expected,
                )
            except Exception as exc:
                url=raw_file_url('Gual-Wells','Deep-Iteration-GPT-Runtime',sha,plan.execution_bundle_path)
                self._validation_failure('execution_bundle_validation',url,exc,commit_sha=sha)
        if plan.staged_startup:
            files=tuple((path,self.fetch_pinned_file(sha,path)) for path in expected)
        else:
            by_path=dict(startup.startup_files)
            try: files=tuple((path,by_path[path]) for path in expected)
            except KeyError as exc:
                self._validation_failure('legacy_execution_protocol_missing',AUTHORITATIVE_REPOSITORY_URL,exc,commit_sha=sha)
        try:
            return receipt_from_individual_files(
                commit_sha=sha,manifest_bytes=startup.manifest_bytes,
                expected_paths=expected,files=files,
            )
        except Exception as exc:
            self._validation_failure('individual_execution_protocol_validation',AUTHORITATIVE_REPOSITORY_URL,exc,commit_sha=sha)

    def load_execution_protocol_for_run(self, run, startup: 'RepositoryStartupBundle') -> ExecutionProtocolBundle:
        """Host bridge: post-genesis load either binds a receipt or aborts the born run."""
        try:
            bundle=self.acquire_execution_protocol(startup)
        except Exception as exc:
            try:
                run.abort_protocol_load(f'execution protocol acquisition/validation failed: {exc}')
            except Exception as abort_exc:
                raise ProtocolLoadAbortError(exc, abort_exc) from abort_exc
            raise
        return self.bind_execution_protocol_for_run(run,bundle)

    def bind_execution_protocol_for_run(self, run, bundle: ExecutionProtocolBundle) -> ExecutionProtocolBundle:
        """Bind an already verified bundle without performing repository I/O."""
        if not isinstance(bundle,ExecutionProtocolBundle):
            raise TypeError('bundle must be ExecutionProtocolBundle')
        try:
            run.bind_protocol_load(bundle.receipt)
            return bundle
        except Exception as exc:
            try:
                run.abort_protocol_load(f'execution protocol receipt binding failed: {exc}')
            except Exception as abort_exc:
                raise ProtocolLoadAbortError(exc,abort_exc) from abort_exc
            raise


@dataclass(frozen=True)
class RepositoryStartupBundle:
    resolution: RefResolution
    route_receipt: RouteReceipt
    manifest_bytes: bytes
    version_bytes: bytes
    discovery_plan: DiscoveryPlan
    startup_files: tuple[tuple[str,bytes],...]
    attempts: tuple[AcquisitionAttemptReceipt,...]
    candidate_key: str
    raw_message_sha256: str

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
        if self.candidate_key not in ('DIGR','深度迭代'):
            raise ValueError('startup bundle candidate key is invalid')
        digest=self.raw_message_sha256
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('startup bundle message digest must be 64 lowercase hex')

    def classify(self, message: str):
        """Apply the pinned startup surface only to its exact candidate bytes."""
        if not isinstance(message,str):
            raise TypeError('message must be str')
        if sha256(message.encode('utf-8')).hexdigest()!=self.raw_message_sha256:
            raise ValueError('startup bundle is bound to a different raw message')
        if candidate_route_key(message)!=self.candidate_key:
            raise ValueError('startup bundle candidate key mismatch')
        surface=classify_surface(message)
        if surface is None:
            raise RuntimeError('pinned startup classifier lost a broad candidate')
        return surface

    @property
    def route_binding(self) -> StartupRouteBinding:
        return StartupRouteBinding(
            1,self.route_receipt,
            tuple(PinnedStartupFileReceipt(p,bytes_sha256(b),len(b)) for p,b in self.startup_files),
            self.attempts,
        )


@dataclass(frozen=True)
class StableDescriptorStartup:
    resolution: RefResolution
    route_receipt: RouteReceipt
    descriptor_bytes: bytes
    descriptor: Mapping[str,Any]
    attempts: tuple[AcquisitionAttemptReceipt,...]
    routing_startup: RepositoryStartupBundle

    def __post_init__(self):
        if not isinstance(self.resolution,RefResolution): raise TypeError('resolution')
        if not isinstance(self.route_receipt,RouteReceipt): raise TypeError('route_receipt')
        if self.route_receipt.pinned_commit!=self.resolution.commit_sha: raise ValueError('descriptor pin mismatch')
        if (self.route_receipt.manifest_path,self.route_receipt.version_path)!=(MANIFEST_PATH,VERSION_PATH):
            raise ValueError('descriptor continuation must retain manifest/VERSION route authority')
        if not isinstance(self.descriptor_bytes,(bytes,bytearray)): raise TypeError('descriptor_bytes must be bytes')
        if not isinstance(self.descriptor,Mapping): raise TypeError('descriptor must be a mapping')
        if not route_failure_permitted(self.attempts): raise ValueError('descriptor startup lacks acquisition evidence')
        if not isinstance(self.routing_startup,RepositoryStartupBundle): raise TypeError('routing_startup')
        if self.routing_startup.resolution.commit_sha!=self.resolution.commit_sha:
            raise ValueError('descriptor continuation changed the pinned commit')
        if self.routing_startup.route_receipt!=self.route_receipt:
            raise ValueError('descriptor continuation changed route authority')

    @property
    def descriptor_sha256(self) -> str:
        return bytes_sha256(self.descriptor_bytes)


@dataclass(frozen=True)
class StableExecutionStartup:
    startup: StableDescriptorStartup
    protocol: ExecutionProtocolBundle
    attempts: tuple[AcquisitionAttemptReceipt,...]

    def __post_init__(self):
        if not isinstance(self.startup,StableDescriptorStartup): raise TypeError('startup')
        if not isinstance(self.protocol,ExecutionProtocolBundle): raise TypeError('protocol')
        if self.protocol.receipt.commit_sha!=self.startup.resolution.commit_sha: raise ValueError('execution pin mismatch')
        if self.protocol.receipt.manifest_sha256!=self.startup.route_receipt.manifest_sha256: raise ValueError('descriptor digest mismatch')


@dataclass(frozen=True)
class StableHelpArtifact:
    startup: RepositoryStartupBundle
    path: str
    data: bytes
    media_type: str
    attempts: tuple[AcquisitionAttemptReceipt,...]

    def __post_init__(self):
        if not isinstance(self.startup,RepositoryStartupBundle): raise TypeError('startup')
        object.__setattr__(self,'path',validate_repo_path(self.path))
        if not isinstance(self.data,(bytes,bytearray)): raise TypeError('help data must be bytes')
        object.__setattr__(self,'data',bytes(self.data))
        if not isinstance(self.media_type,str) or not self.media_type: raise ValueError('media_type required')

    @property
    def text(self) -> str:
        return self.data.decode('utf-8')
