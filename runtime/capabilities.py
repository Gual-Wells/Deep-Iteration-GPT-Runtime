"""Orthogonal Berta2 execution-mode and attestation negotiation."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from .parameter_resolution import ParameterResolution, ResolutionStatus
from .validation import require_isolation_level,require_nonnegative_int


class CapabilityMode(str, Enum):
    ENFORCED = 'ENFORCED'
    ADVISORY = 'ADVISORY'
    PROMPT_ONLY = 'PROMPT_ONLY'


class ExecutionMode(str, Enum):
    MODEL_NATIVE = 'MODEL_NATIVE'
    HOST_ENFORCED = 'HOST_ENFORCED'


class AttestationLevel(str, Enum):
    NONE = 'NONE'
    PARTIAL = 'PARTIAL'
    CANONICAL = 'CANONICAL'


class MonotonicClockCapability(str, Enum):
    CONTINUOUS = 'CONTINUOUS'
    SESSION_ONLY = 'SESSION_ONLY'
    NONE = 'NONE'


@dataclass(frozen=True)
class HostCapabilities:
    """Facts declared by a host; defaults intentionally claim nothing."""
    final_gate: bool = False
    persistent_workspace: bool = False
    monotonic_clock: MonotonicClockCapability = MonotonicClockCapability.NONE
    repository_transport: bool = False
    source_tools: bool = False
    isolation_max: int = 1
    viewpoint_max: int = 0

    def __post_init__(self) -> None:
        for name in ('final_gate', 'persistent_workspace', 'repository_transport', 'source_tools'):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f'{name} must be bool')
        if not isinstance(self.monotonic_clock, MonotonicClockCapability):
            object.__setattr__(self, 'monotonic_clock', MonotonicClockCapability(self.monotonic_clock))
        require_isolation_level('isolation_max', self.isolation_max)
        require_nonnegative_int('viewpoint_max',self.viewpoint_max)


@dataclass(frozen=True)
class CapabilityNegotiation:
    mode: CapabilityMode
    final_gate: bool
    persistent_workspace: bool
    monotonic_clock: MonotonicClockCapability
    repository_transport: bool
    source_tools: bool
    isolation_max: int
    reasons: tuple[str, ...] = ()
    viewpoint_max: int = 0
    execution_mode: ExecutionMode = ExecutionMode.MODEL_NATIVE
    attestation_level: AttestationLevel = AttestationLevel.NONE

    def __post_init__(self) -> None:
        if not isinstance(self.mode, CapabilityMode):
            object.__setattr__(self, 'mode', CapabilityMode(self.mode))
        if not isinstance(self.monotonic_clock, MonotonicClockCapability):
            object.__setattr__(self, 'monotonic_clock', MonotonicClockCapability(self.monotonic_clock))
        if not isinstance(self.execution_mode,ExecutionMode):
            object.__setattr__(self,'execution_mode',ExecutionMode(self.execution_mode))
        if not isinstance(self.attestation_level,AttestationLevel):
            object.__setattr__(self,'attestation_level',AttestationLevel(self.attestation_level))
        for name in ('final_gate', 'persistent_workspace', 'repository_transport', 'source_tools'):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f'{name} must be bool')
        require_isolation_level('isolation_max', self.isolation_max)
        require_nonnegative_int('viewpoint_max',self.viewpoint_max)
        object.__setattr__(self, 'reasons', tuple(self.reasons))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data['mode'] = self.mode.value
        data['monotonic_clock'] = self.monotonic_clock.value
        data['execution_mode'] = self.execution_mode.value
        data['attestation_level'] = self.attestation_level.value
        data['reasons'] = list(self.reasons)
        return data


def negotiate_capabilities(
    capabilities: HostCapabilities,
    parameters: ParameterResolution | None = None,
) -> CapabilityNegotiation:
    """Choose truthful attestation without treating proof gaps as execution denial."""
    if not isinstance(capabilities, HostCapabilities):
        raise TypeError('capabilities must be HostCapabilities')
    if parameters is not None and (
        not isinstance(parameters, ParameterResolution)
        or parameters.status is not ResolutionStatus.RESOLVED
    ):
        raise ValueError('parameters must be a resolved ParameterResolution')
    if parameters is not None:
        parameters.require_stable_ready()

    canonical_gaps: list[str] = []
    if not capabilities.repository_transport:
        canonical_gaps.append('repository transport is unavailable')
    if not capabilities.persistent_workspace:
        canonical_gaps.append('persistent run workspace is unavailable')
    if capabilities.monotonic_clock is MonotonicClockCapability.NONE:
        canonical_gaps.append('monotonic clock is unavailable')
    if not capabilities.final_gate:
        canonical_gaps.append('host has no enforceable final-output interposer')
    if parameters is not None:
        source_required=(
            parameters.source_policy=='required'
            or any((parameters.S.n,parameters.S.t_seconds,parameters.S.r,parameters.S.b))
        )
        if source_required and not capabilities.source_tools:
            canonical_gaps.append('required/explicit source work requires source tools')
        if parameters.B == 1 and capabilities.monotonic_clock is MonotonicClockCapability.NONE:
            canonical_gaps.append('hard time minimum requires a monotonic clock')
        if parameters.S.b == 1 and capabilities.monotonic_clock is MonotonicClockCapability.NONE:
            canonical_gaps.append('hard source-time minimum requires a monotonic clock')
        if parameters.D_s is not None and parameters.D_s > 0 and parameters.L_e > capabilities.isolation_max:
            canonical_gaps.append(
                f'requested L{parameters.L_e} exceeds host isolation cap L{capabilities.isolation_max}'
            )
        # V_o is a semantic-viewpoint minimum. viewpoint_max describes optional
        # physical/agent isolation evidence and never blocks native V work.

    observable=any((
        capabilities.repository_transport,capabilities.persistent_workspace,
        capabilities.monotonic_clock is not MonotonicClockCapability.NONE,
        capabilities.source_tools,capabilities.final_gate,
    ))
    if canonical_gaps:
        mode=CapabilityMode.ADVISORY if observable else CapabilityMode.PROMPT_ONLY
        execution_mode=ExecutionMode.MODEL_NATIVE
        attestation_level=AttestationLevel.PARTIAL if observable else AttestationLevel.NONE
        reasons=tuple(canonical_gaps)
    else:
        mode = CapabilityMode.ENFORCED
        execution_mode=ExecutionMode.HOST_ENFORCED
        attestation_level=AttestationLevel.CANONICAL
        reasons = ()
    return CapabilityNegotiation(
        mode=mode,
        final_gate=capabilities.final_gate,
        persistent_workspace=capabilities.persistent_workspace,
        monotonic_clock=capabilities.monotonic_clock,
        repository_transport=capabilities.repository_transport,
        source_tools=capabilities.source_tools,
        isolation_max=capabilities.isolation_max,
        reasons=reasons,
        viewpoint_max=capabilities.viewpoint_max,
        execution_mode=execution_mode,
        attestation_level=attestation_level,
    )
