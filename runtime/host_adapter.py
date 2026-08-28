"""Thin stable.1 host adapter: broad local capture, then pinned preflight."""
from __future__ import annotations

from dataclasses import dataclass,field
from enum import Enum
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable, Mapping

from .capabilities import (
    CapabilityMode, CapabilityNegotiation, HostCapabilities,
    negotiate_capabilities,
)
from .clock_probe import ClockSnapshot, snapshot
from .execution_protocol import ExecutionProtocolBundle
from .invocation_surface import InvocationKind
from .parameter_resolution import (
    ParameterResolution, ResolutionStatus, parameter_profile,
    resolve_stable_parameter_surface,
)
from .protocol_authority import authority_from_route_bytes
from .repository_transport import (
    RepositoryStartupBundle,RepositoryTransportSession,StableDescriptorStartup,
    StartupRouteBinding,
)
from .routing import candidate_route_key


class PreflightStatus(str, Enum):
    READY = 'READY'
    NATIVE = 'NATIVE'
    HELP = 'HELP'
    INVALID = 'INVALID'
    NEEDS_CORRECTION = 'NEEDS_CORRECTION'
    ADVISORY = 'ADVISORY'
    UNSUPPORTED = 'UNSUPPORTED'


@dataclass(frozen=True)
class PreflightReceipt:
    schema_version: int
    status: PreflightStatus
    raw_message_sha256: str
    kind: InvocationKind
    alias: str
    task_raw: str | None
    parameter_surface: str | None
    profile: str | None
    corrections: tuple[str, ...]
    warnings: tuple[str, ...]
    startup_acquisition_performed: bool
    additional_artifact_fetch_required: bool
    repository_binding: StartupRouteBinding
    native_message: str | None
    source_policy: str | None = None
    parameters: ParameterResolution | None = None
    startup: RepositoryStartupBundle | None = field(default=None,repr=False,compare=False)
    capability: CapabilityNegotiation | None = field(default=None,repr=False,compare=False)

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError('unsupported preflight schema')
        if not isinstance(self.status, PreflightStatus):
            object.__setattr__(self, 'status', PreflightStatus(self.status))
        if not isinstance(self.kind, InvocationKind):
            object.__setattr__(self, 'kind', InvocationKind(self.kind))
        object.__setattr__(self, 'corrections', tuple(self.corrections))
        object.__setattr__(self, 'warnings', tuple(self.warnings))
        if type(self.startup_acquisition_performed) is not bool:
            raise TypeError('startup_acquisition_performed must be bool')
        if not self.startup_acquisition_performed:
            raise ValueError('candidate preflight requires completed pinned startup acquisition')
        if type(self.additional_artifact_fetch_required) is not bool:
            raise TypeError('additional_artifact_fetch_required must be bool')
        expected_additional_fetch = self.status in (PreflightStatus.READY,PreflightStatus.HELP)
        if self.additional_artifact_fetch_required != expected_additional_fetch:
            raise ValueError('only READY/HELP preflight requires post-classification artifact fetches')
        if self.source_policy not in (None,'auto','required','off'):
            raise ValueError('source_policy must be auto/required/off when present')
        if not isinstance(self.repository_binding,StartupRouteBinding):
            raise TypeError('repository_binding must be StartupRouteBinding')
        if not isinstance(self.startup,RepositoryStartupBundle):
            raise TypeError('preflight receipt requires its verified repository startup')
        if self.startup.route_binding!=self.repository_binding:
            raise ValueError('preflight repository binding disagrees with startup evidence')
        if self.startup.raw_message_sha256!=self.raw_message_sha256:
            raise ValueError('preflight startup is bound to a different raw message')
        if self.status is PreflightStatus.NATIVE:
            if not isinstance(self.native_message,str):
                raise ValueError('NATIVE preflight must return the original message')
            from hashlib import sha256
            if sha256(self.native_message.encode('utf-8')).hexdigest()!=self.raw_message_sha256:
                raise ValueError('NATIVE passthrough message digest mismatch')
        elif self.native_message is not None:
            raise ValueError('only NATIVE preflight may carry native_message')
        if self.capability is not None and not isinstance(self.capability,CapabilityNegotiation):
            raise TypeError('capability must be CapabilityNegotiation when present')

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'status': self.status.value,
            'raw_message_sha256': self.raw_message_sha256,
            'kind': self.kind.value,
            'alias': self.alias,
            'task_raw': self.task_raw,
            'parameter_surface': self.parameter_surface,
            'profile': self.profile,
            'corrections': list(self.corrections),
            'warnings': list(self.warnings),
            'startup_acquisition_performed': self.startup_acquisition_performed,
            'additional_artifact_fetch_required': self.additional_artifact_fetch_required,
            'repository_binding': self.repository_binding.to_dict(),
            'native_message': self.native_message,
            'source_policy': self.source_policy,
        }


def preflight_invocation(
    message: str,
    *,
    startup: RepositoryStartupBundle | None = None,
    capabilities: HostCapabilities | None = None,
    semantic_normalizations: Mapping[str, str] | None = None,
) -> PreflightReceipt | None:
    """Classify only through an exact-message, repository-verified startup.

    This public helper cannot acquire the repository itself.  For a candidate,
    callers must supply the bundle returned by ``acquire_startup(message)``;
    therefore it cannot be used to bypass the pin-before-classification gate.
    """
    if candidate_route_key(message) is None:
        return None
    if not isinstance(startup,RepositoryStartupBundle):
        raise ValueError('candidate preflight requires a verified repository startup')
    surface=startup.classify(message)
    binding=startup.route_binding
    common = dict(
        schema_version=1,
        raw_message_sha256=surface.raw_message_sha256,
        kind=surface.kind,
        alias=surface.alias,
        task_raw=surface.task_raw,
        parameter_surface=surface.parameter_surface,
        repository_binding=binding,
        native_message=message if surface.kind is InvocationKind.NATIVE else None,
        startup_acquisition_performed=True,
        startup=startup,
    )
    if surface.kind is InvocationKind.NATIVE:
        return PreflightReceipt(status=PreflightStatus.NATIVE, profile=None, corrections=(), warnings=(), additional_artifact_fetch_required=False, **common)
    if surface.kind is InvocationKind.HELP:
        return PreflightReceipt(status=PreflightStatus.HELP, profile=None, corrections=(), warnings=(), additional_artifact_fetch_required=True, **common)
    if surface.kind is InvocationKind.INVALID:
        return PreflightReceipt(status=PreflightStatus.INVALID, profile=None, corrections=(surface.reason or 'invalid invocation surface',), warnings=(), additional_artifact_fetch_required=False, **common)

    profile = parameter_profile(surface.parameter_surface)
    parameters = resolve_stable_parameter_surface(surface.parameter_surface, semantic_normalizations)
    if parameters.status is not ResolutionStatus.RESOLVED:
        return PreflightReceipt(
            status=PreflightStatus.NEEDS_CORRECTION,
            profile=profile,
            corrections=parameters.diagnostics or ('parameter surface is not uniquely resolvable',),
            warnings=(), additional_artifact_fetch_required=False, parameters=parameters, **common,
        )
    warnings = tuple(
        item for item in parameters.diagnostics
        if not item.startswith('profile:') and not item.startswith('time-policy:') and not item.startswith('source-policy:')
    )
    negotiation=None
    if capabilities is not None:
        negotiation = negotiate_capabilities(capabilities, parameters)
        if negotiation.mode is CapabilityMode.PROMPT_ONLY:
            return PreflightReceipt(
                status=PreflightStatus.UNSUPPORTED, profile=profile,
                corrections=negotiation.reasons, warnings=warnings,
                additional_artifact_fetch_required=False, source_policy=parameters.source_policy,
                parameters=parameters,capability=negotiation,**common,
            )
        if negotiation.mode is CapabilityMode.ADVISORY:
            return PreflightReceipt(
                status=PreflightStatus.ADVISORY, profile=profile,
                corrections=(), warnings=warnings + negotiation.reasons,
                additional_artifact_fetch_required=False, source_policy=parameters.source_policy,
                parameters=parameters,capability=negotiation,**common,
            )
    return PreflightReceipt(
        status=PreflightStatus.READY, profile=profile,
        corrections=(), warnings=warnings, additional_artifact_fetch_required=True,
        source_policy=parameters.source_policy, parameters=parameters,
        capability=negotiation,**common,
    )


class PreflightBlockedError(RuntimeError):
    def __init__(self, receipt: PreflightReceipt):
        self.receipt = receipt
        super().__init__(f'preflight blocked: {receipt.status.value}')


@dataclass(frozen=True)
class HostStartResult:
    preflight: PreflightReceipt
    capability: CapabilityNegotiation
    startup: StableDescriptorStartup
    run: Any
    protocol: ExecutionProtocolBundle

    @property
    def route_binding(self) -> StartupRouteBinding:
        return self.preflight.repository_binding


class HostAdapter:
    """Host boundary which requires explicit, enforceable capabilities."""
    def __init__(self, transport: RepositoryTransportSession, capabilities: HostCapabilities):
        if not isinstance(transport, RepositoryTransportSession):
            raise TypeError('transport must be RepositoryTransportSession')
        if not isinstance(capabilities, HostCapabilities):
            raise TypeError('capabilities must be HostCapabilities')
        self.transport = transport
        self.capabilities = capabilities

    def preflight(self, message: str, *, semantic_normalizations: Mapping[str, str] | None = None) -> PreflightReceipt | None:
        # This is the only local decision: exact broad-prefix candidate capture.
        if candidate_route_key(message) is None:
            return None
        startup=self.transport.acquire_startup(message)
        return preflight_invocation(
            message, startup=startup,capabilities=self.capabilities,
            semantic_normalizations=semantic_normalizations,
        )

    def start(
        self, message: str, *, workspace_parent: Path | None = None,
        snapshot_fn: Callable[[], ClockSnapshot] = snapshot,
        run_id: str | None = None,
        semantic_normalizations: Mapping[str, str] | None = None,
    ) -> HostStartResult:
        receipt = self.preflight(message, semantic_normalizations=semantic_normalizations)
        if receipt is None:
            raise ValueError('message is not a DIGR candidate')
        if receipt.status is not PreflightStatus.READY:
            raise PreflightBlockedError(receipt)

        routing_startup=receipt.startup
        if routing_startup is None:
            raise RuntimeError('READY preflight lacks pinned repository startup')
        stable = self.transport.acquire_stable_execution_from_startup(routing_startup,message)
        startup=stable.startup;protocol=stable.protocol
        authority=authority_from_route_bytes(
            routing_startup.route_receipt,
            routing_startup.manifest_bytes,
            routing_startup.version_bytes,
        )
        # Descriptor, version/protocol identity, bundle, member hashes and
        # parameter uniqueness are all verified before Genesis.  Build the
        # initial workspace below a private staging parent, then publish the
        # protocol-ready/parameter-bound run with one same-filesystem rename.
        # A crash before that rename cannot expose a half-born canonical run.
        from .run_session import LiveDIGRRun
        resolved=receipt.parameters
        if resolved is None or resolved.status is not ResolutionStatus.RESOLVED:
            raise RuntimeError('READY preflight lacks resolved stable parameters')
        resolved.require_stable_ready()
        capability=receipt.capability
        if capability is None:
            capability=negotiate_capabilities(self.capabilities,resolved)
        if capability.mode is not CapabilityMode.ENFORCED:
            raise PreflightBlockedError(receipt)

        parent=(Path(workspace_parent) if workspace_parent is not None
                else Path(tempfile.gettempdir())/'.digr-runs').resolve()
        parent.mkdir(parents=True,exist_ok=True)
        if run_id is not None and (parent/run_id).exists():
            raise FileExistsError(parent/run_id)
        stage_parent=Path(tempfile.mkdtemp(prefix='.digr-genesis-',dir=str(parent))).resolve()
        if parent not in stage_parent.parents:
            raise RuntimeError('staged Genesis directory escaped workspace parent')
        published=False
        try:
            run=LiveDIGRRun.start(
                authority,message,stage_parent,snapshot_fn,run_id,
            )
            self.transport.bind_execution_protocol_for_run(run,protocol)
            # Stable parameters were already resolved before Genesis. Persist
            # the exact receipt instead of invoking the legacy parser again.
            run.workspace.write_json(
                'preflight-receipt.json',receipt.to_dict(),kind='preflight-receipt',
            )
            run.workspace.write_json(
                'capability-negotiation.json',capability.to_dict(),kind='capability-negotiation',
            )
            run.bind_preflight_parameters(resolved)
            final_root=(parent/run.run_id).resolve()
            if final_root.exists():
                raise FileExistsError(final_root)
            if parent not in final_root.parents:
                raise RuntimeError('published Genesis directory escaped workspace parent')
            os.replace(run.workspace.root,final_root)
            published=True
        finally:
            # stage_parent is generated under the validated parent and never
            # aliases the final run path. Removal is limited to this one
            # private staging directory.
            if stage_parent.exists():
                shutil.rmtree(stage_parent)

        if not published:
            raise RuntimeError('stable Genesis was not published')
        # Re-open through the ordinary verifier. The same-process clock bridge
        # also proves that no unaccounted execution occurred during staging.
        try:
            run=LiveDIGRRun.resume(final_root,run.run_id,snapshot_fn)
        except Exception:
            # Publication is provisional until ordinary recovery succeeds. A
            # failed reopen must not leave a canonical-looking partial run.
            if final_root.exists():
                if parent not in final_root.parents:
                    raise RuntimeError('failed published run escaped workspace parent')
                shutil.rmtree(final_root)
            raise
        return HostStartResult(receipt, capability, startup, run, protocol)

    def help(self, message: str='DIGR/help'):
        """Fetch verified manifest-declared Help without creating a run."""
        receipt=self.preflight(message)
        if receipt is None:
            raise ValueError('message is not a DIGR candidate')
        if receipt.status is not PreflightStatus.HELP:
            raise PreflightBlockedError(receipt)
        if receipt.startup is None:
            raise RuntimeError('HELP preflight lacks pinned repository startup')
        return self.transport.acquire_stable_help_from_startup(receipt.startup,message)
