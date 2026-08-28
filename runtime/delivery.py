"""Deterministic stable.1 final-delivery binding.

The runtime uses a crash-safe two-phase commit: it may prepare payload,
summary, proof, and envelope artifacts while FINALIZING, but only the later
verified lifecycle transition makes the run DELIVERED.  A crash can therefore
leave a detectable partial/prepared set, never a false success.  The envelope
binds the exact bytes returned by the host, the selected candidate, the run
summary, and the stable proof document.
"""
from __future__ import annotations

from dataclasses import asdict,dataclass
from typing import Any,Mapping

from .validation import require_nonempty_text,require_nonnegative_int
from .workspace import RunWorkspace,canonical_json_bytes,sha256_bytes

DELIVERY_SCHEMA_VERSION=1
DELIVERY_PAYLOAD_PATH='final/delivery.bin'
DELIVERY_SUMMARY_PATH='final/run-summary.json'
DELIVERY_PROOF_PATH='final/stable-proof.json'
DELIVERY_ENVELOPE_PATH='final/delivery-envelope.json'
PREFLIGHT_RECEIPT_PATH='preflight-receipt.json'
CAPABILITY_NEGOTIATION_PATH='capability-negotiation.json'


def _digest(name:str,value:object)->str:
    text=require_nonempty_text(name,value).lower()
    if len(text)!=64 or any(c not in '0123456789abcdef' for c in text):
        raise ValueError(f'{name} must be 64 lowercase hex')
    return text


class DeliveryGateError(RuntimeError):
    """A stable delivery was requested before every mandatory gate passed."""
    def __init__(self,unmet):
        values=tuple(require_nonempty_text('unmet delivery gate',x) for x in unmet)
        if not values:raise ValueError('DeliveryGateError requires at least one unmet gate')
        self.unmet=values
        super().__init__('delivery blocked: ' + ','.join(values))


class HostDeliveryAuthorityError(ValueError):
    """Persisted host evidence cannot authorize canonical delivery."""
    def __init__(self,code:str,message:str):
        self.code=require_nonempty_text('host delivery authority code',code)
        super().__init__(message)


@dataclass(frozen=True)
class HostDeliveryAuthority:
    preflight_receipt_path:str
    preflight_receipt_sha256:str
    capability_negotiation_path:str
    capability_negotiation_sha256:str
    source_tools:bool

    @property
    def binding(self)->dict[str,Any]:
        return {
            'preflight_receipt_path':self.preflight_receipt_path,
            'preflight_receipt_sha256':self.preflight_receipt_sha256,
            'capability_negotiation_path':self.capability_negotiation_path,
            'capability_negotiation_sha256':self.capability_negotiation_sha256,
        }


def _host_authority_error(code:str,message:str,exc:Exception|None=None):
    error=HostDeliveryAuthorityError(code,message)
    if exc is None:raise error
    raise error from exc


def verify_enforced_host_delivery_authority(workspace:RunWorkspace)->HostDeliveryAuthority:
    """Verify the exact persisted host evidence which can interpose delivery."""
    if not isinstance(workspace,RunWorkspace):raise TypeError('workspace must be RunWorkspace')
    try:
        preflight_rec=workspace.require_indexed_artifact(PREFLIGHT_RECEIPT_PATH,kind='preflight-receipt')
        preflight=workspace.read_json(PREFLIGHT_RECEIPT_PATH)
    except (OSError,TypeError,ValueError) as exc:
        _host_authority_error('PREFLIGHT_RECEIPT_INVALID','preflight receipt is missing, unindexed, or drifted',exc)
    if not isinstance(preflight,Mapping):
        _host_authority_error('PREFLIGHT_RECEIPT_INVALID','preflight receipt root must be an object')
    try:
        invocation=workspace.read_json('invocation.json')
        authority=workspace.read_json('authority.json')
        parameters=workspace.read_json('parameter-resolution.json')
    except (OSError,TypeError,ValueError) as exc:
        _host_authority_error('PREFLIGHT_RECEIPT_INVALID','preflight run bindings are unavailable',exc)
    expected_invocation={
        'raw_message_sha256':invocation.get('raw_message_sha256'),
        'kind':invocation.get('kind'),'alias':invocation.get('alias'),
        'task_raw':invocation.get('task_raw'),'parameter_surface':invocation.get('parameter_surface'),
    }
    if (preflight.get('schema_version')!=1 or preflight.get('status')!='READY'
            or preflight.get('startup_acquisition_performed') is not True
            or preflight.get('additional_artifact_fetch_required') is not True
            or preflight.get('native_message') is not None
            or preflight.get('corrections')!=[]
            or any(preflight.get(k)!=v for k,v in expected_invocation.items())
            or preflight.get('source_policy')!=parameters.get('source_policy')):
        _host_authority_error('PREFLIGHT_RECEIPT_INVALID','preflight receipt does not authorize this exact executing invocation')
    warnings=preflight.get('warnings')
    if not isinstance(warnings,list) or any(not isinstance(x,str) or not x for x in warnings):
        _host_authority_error('PREFLIGHT_RECEIPT_INVALID','preflight warnings must be a string list')
    repository_binding=preflight.get('repository_binding')
    if (not isinstance(repository_binding,Mapping) or repository_binding.get('schema_version')!=1
            or repository_binding.get('route')!=authority.get('route')):
        _host_authority_error('PREFLIGHT_RECEIPT_INVALID','preflight repository binding disagrees with run authority')
    startup_files=repository_binding.get('startup_files')
    attempts=repository_binding.get('attempts')
    if (not isinstance(startup_files,list) or not startup_files
            or not isinstance(attempts,list) or not attempts):
        _host_authority_error('PREFLIGHT_RECEIPT_INVALID','preflight repository acquisition evidence is incomplete')
    for item in startup_files:
        if (not isinstance(item,Mapping) or not isinstance(item.get('path'),str) or not item.get('path')
                or not isinstance(item.get('sha256'),str) or len(item['sha256'])!=64
                or any(c not in '0123456789abcdef' for c in item['sha256'])
                or not isinstance(item.get('byte_length'),int) or isinstance(item.get('byte_length'),bool)
                or item['byte_length']<0):
            _host_authority_error('PREFLIGHT_RECEIPT_INVALID','preflight startup file evidence is malformed')
    if any(not isinstance(item,Mapping) for item in attempts):
        _host_authority_error('PREFLIGHT_RECEIPT_INVALID','preflight acquisition attempt evidence is malformed')

    try:
        capability_rec=workspace.require_indexed_artifact(CAPABILITY_NEGOTIATION_PATH,kind='capability-negotiation')
        capability=workspace.read_json(CAPABILITY_NEGOTIATION_PATH)
    except (OSError,TypeError,ValueError) as exc:
        _host_authority_error('CAPABILITY_NEGOTIATION_INVALID','capability negotiation is missing, unindexed, or drifted',exc)
    if not isinstance(capability,Mapping):
        _host_authority_error('CAPABILITY_NEGOTIATION_INVALID','capability negotiation root must be an object')
    required_keys={
        'mode','final_gate','persistent_workspace','monotonic_clock',
        'repository_transport','source_tools','isolation_max','viewpoint_max','reasons',
    }
    if set(capability)!=required_keys:
        _host_authority_error('CAPABILITY_NEGOTIATION_INVALID','capability negotiation has an unexpected shape')
    if (capability.get('mode')!='ENFORCED' or capability.get('final_gate') is not True
            or capability.get('persistent_workspace') is not True
            or capability.get('repository_transport') is not True
            or capability.get('monotonic_clock')!='CONTINUOUS'):
        _host_authority_error('CANONICAL_DELIVERY_NOT_ENFORCED','host cannot enforce canonical final delivery')
    if (type(capability.get('source_tools')) is not bool
            or not isinstance(capability.get('isolation_max'),int)
            or isinstance(capability.get('isolation_max'),bool)
            or capability['isolation_max'] not in (1,2,3)
            or not isinstance(capability.get('viewpoint_max'),int)
            or isinstance(capability.get('viewpoint_max'),bool)
            or capability['viewpoint_max']<0
            or capability.get('reasons')!=[]):
        _host_authority_error('CAPABILITY_NEGOTIATION_INVALID','ENFORCED capability facts are malformed')
    return HostDeliveryAuthority(
        PREFLIGHT_RECEIPT_PATH,preflight_rec.sha256,
        CAPABILITY_NEGOTIATION_PATH,capability_rec.sha256,capability['source_tools'],
    )


@dataclass(frozen=True)
class DeliveryEnvelope:
    schema_version:int
    run_id:str
    status:str
    payload_path:str
    payload_sha256:str
    payload_byte_length:int
    media_type:str
    candidate_revision:int
    candidate_digest:str
    candidate_payload_path:str
    preflight_receipt_path:str
    preflight_receipt_sha256:str
    capability_negotiation_path:str
    capability_negotiation_sha256:str
    run_summary_path:str
    run_summary_sha256:str
    stable_proof_path:str
    stable_proof_sha256:str

    def __post_init__(self):
        if self.schema_version!=DELIVERY_SCHEMA_VERSION:raise ValueError('unsupported delivery envelope schema')
        object.__setattr__(self,'run_id',require_nonempty_text('run_id',self.run_id))
        if self.status!='DELIVERED':raise ValueError('delivery envelope status must be DELIVERED')
        if self.payload_path!=DELIVERY_PAYLOAD_PATH:raise ValueError('unexpected delivery payload path')
        if self.run_summary_path!=DELIVERY_SUMMARY_PATH:raise ValueError('unexpected run summary path')
        if self.stable_proof_path!=DELIVERY_PROOF_PATH:raise ValueError('unexpected stable proof path')
        if self.preflight_receipt_path!=PREFLIGHT_RECEIPT_PATH:raise ValueError('unexpected preflight receipt path')
        if self.capability_negotiation_path!=CAPABILITY_NEGOTIATION_PATH:raise ValueError('unexpected capability negotiation path')
        object.__setattr__(self,'payload_sha256',_digest('payload_sha256',self.payload_sha256))
        object.__setattr__(self,'run_summary_sha256',_digest('run_summary_sha256',self.run_summary_sha256))
        object.__setattr__(self,'stable_proof_sha256',_digest('stable_proof_sha256',self.stable_proof_sha256))
        object.__setattr__(self,'preflight_receipt_sha256',_digest('preflight_receipt_sha256',self.preflight_receipt_sha256))
        object.__setattr__(self,'capability_negotiation_sha256',_digest('capability_negotiation_sha256',self.capability_negotiation_sha256))
        object.__setattr__(self,'candidate_digest',_digest('candidate_digest',self.candidate_digest))
        candidate_path=require_nonempty_text('candidate_payload_path',self.candidate_payload_path)
        expected_candidate_path=f'state/candidate-payloads/{self.payload_sha256}.bin'
        if candidate_path!=expected_candidate_path:
            raise ValueError('candidate payload path is not content-addressed by payload_sha256')
        object.__setattr__(self,'candidate_payload_path',candidate_path)
        require_nonnegative_int('payload_byte_length',self.payload_byte_length)
        if self.payload_byte_length==0:raise ValueError('delivered payload must not be empty')
        require_nonnegative_int('candidate_revision',self.candidate_revision)
        object.__setattr__(self,'media_type',require_nonempty_text('media_type',self.media_type))

    def to_dict(self)->dict[str,Any]:return asdict(self)

    @classmethod
    def from_dict(cls,d:Mapping[str,Any])->'DeliveryEnvelope':
        return cls(
            d['schema_version'],d['run_id'],d['status'],d['payload_path'],
            d['payload_sha256'],d['payload_byte_length'],d['media_type'],
            d['candidate_revision'],d['candidate_digest'],d['candidate_payload_path'],
            d['preflight_receipt_path'],d['preflight_receipt_sha256'],
            d['capability_negotiation_path'],d['capability_negotiation_sha256'],
            d['run_summary_path'],d['run_summary_sha256'],d['stable_proof_path'],d['stable_proof_sha256'],
        )

    @property
    def digest(self)->str:return sha256_bytes(canonical_json_bytes(self.to_dict()))

    @property
    def final_binding(self)->dict[str,Any]:
        return {
            'payload_sha256':self.payload_sha256,
            'payload_byte_length':self.payload_byte_length,
            'media_type':self.media_type,
            'candidate_revision':self.candidate_revision,
            'candidate_digest':self.candidate_digest,
            'candidate_payload_path':self.candidate_payload_path,
            'preflight_receipt_path':self.preflight_receipt_path,
            'preflight_receipt_sha256':self.preflight_receipt_sha256,
            'capability_negotiation_path':self.capability_negotiation_path,
            'capability_negotiation_sha256':self.capability_negotiation_sha256,
        }

    def verify_payload(self,payload:bytes)->bool:
        if not isinstance(payload,(bytes,bytearray)):raise TypeError('delivery payload must be bytes')
        raw=bytes(payload)
        if len(raw)!=self.payload_byte_length or sha256_bytes(raw)!=self.payload_sha256:
            raise ValueError('delivered payload bytes do not match delivery envelope')
        return True


def verify_delivery_artifacts(workspace:RunWorkspace,envelope:DeliveryEnvelope)->bool:
    """Re-read every exact artifact bound by a delivery envelope."""
    if not isinstance(workspace,RunWorkspace):raise TypeError('workspace must be RunWorkspace')
    if not isinstance(envelope,DeliveryEnvelope):raise TypeError('envelope must be DeliveryEnvelope')
    if workspace.run_id!=envelope.run_id:raise ValueError('delivery envelope run_id mismatch')
    host_authority=verify_enforced_host_delivery_authority(workspace)
    if host_authority.binding!={
            'preflight_receipt_path':envelope.preflight_receipt_path,
            'preflight_receipt_sha256':envelope.preflight_receipt_sha256,
            'capability_negotiation_path':envelope.capability_negotiation_path,
            'capability_negotiation_sha256':envelope.capability_negotiation_sha256,
        }:
        raise ValueError('delivery envelope host authority binding drift')
    payload_rec=workspace.require_indexed_artifact(envelope.payload_path,kind='final-delivery-payload')
    candidate_rec=workspace.require_indexed_artifact(envelope.candidate_payload_path,kind='candidate-payload')
    summary_rec=workspace.require_indexed_artifact(envelope.run_summary_path,kind='run-summary')
    proof_rec=workspace.require_indexed_artifact(envelope.stable_proof_path,kind='stable-proof')
    if payload_rec.sha256!=envelope.payload_sha256:
        raise ValueError('indexed delivery payload digest disagrees with envelope')
    if candidate_rec.sha256!=envelope.payload_sha256:
        raise ValueError('candidate payload is not the exact delivered payload')
    if summary_rec.sha256!=envelope.run_summary_sha256:
        raise ValueError('indexed run summary digest disagrees with envelope')
    if proof_rec.sha256!=envelope.stable_proof_sha256:
        raise ValueError('indexed stable proof digest disagrees with envelope')
    envelope.verify_payload(workspace.path(envelope.payload_path).read_bytes())

    # Hashes alone are insufficient when an attacker or buggy recovery path can
    # rewrite and re-index several files together.  Close the cross-artifact
    # shape here so summary/proof still describe this exact delivery envelope.
    summary=workspace.read_json(envelope.run_summary_path)
    if (not isinstance(summary,Mapping) or summary.get('run_id')!=envelope.run_id
            or summary.get('phase')!='DELIVERED' or summary.get('delivery_ready') is not True
            or summary.get('final')!=envelope.final_binding):
        raise ValueError('run summary does not describe the delivery envelope')
    proof=workspace.read_json(envelope.stable_proof_path)
    if (not isinstance(proof,Mapping) or proof.get('schema_version')!=1
            or proof.get('run_id')!=envelope.run_id or proof.get('status')!='DELIVERED'
            or proof.get('delivery')!=envelope.final_binding or not isinstance(proof.get('proof'),Mapping)):
        raise ValueError('stable proof does not describe the delivery envelope')
    if workspace.path(DELIVERY_ENVELOPE_PATH).is_file():
        persisted=DeliveryEnvelope.from_dict(workspace.read_json(DELIVERY_ENVELOPE_PATH))
        if persisted!=envelope:raise ValueError('persisted delivery envelope drift')
        workspace.require_indexed_artifact(DELIVERY_ENVELOPE_PATH,kind='delivery-envelope')
    return True
