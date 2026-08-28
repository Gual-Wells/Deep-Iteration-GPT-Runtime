"""Explicit host capability negotiation for the stable.1 adapter boundary."""
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

    def __post_init__(self) -> None:
        if not isinstance(self.mode, CapabilityMode):
            object.__setattr__(self, 'mode', CapabilityMode(self.mode))
        if not isinstance(self.monotonic_clock, MonotonicClockCapability):
            object.__setattr__(self, 'monotonic_clock', MonotonicClockCapability(self.monotonic_clock))
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
        data['reasons'] = list(self.reasons)
        return data


def negotiate_capabilities(
    capabilities: HostCapabilities,
    parameters: ParameterResolution | None = None,
) -> CapabilityNegotiation:
    """Choose the strongest truthful mode; never infer a final interposer."""
    if not isinstance(capabilities, HostCapabilities):
        raise TypeError('capabilities must be HostCapabilities')
    if parameters is not None and (
        not isinstance(parameters, ParameterResolution)
        or parameters.status is not ResolutionStatus.RESOLVED
    ):
        raise ValueError('parameters must be a resolved ParameterResolution')
    if parameters is not None:
        parameters.require_stable_ready()

    blocking: list[str] = []
    advisory: list[str] = []
    if not capabilities.repository_transport:
        blocking.append('repository transport is unavailable')
    if not capabilities.persistent_workspace:
        blocking.append('persistent run workspace is unavailable')
    if capabilities.monotonic_clock is MonotonicClockCapability.NONE:
        blocking.append('monotonic clock is unavailable')
    elif capabilities.monotonic_clock is MonotonicClockCapability.SESSION_ONLY:
        advisory.append('monotonic clock continuity is session-only')
    if not capabilities.final_gate:
        advisory.append('host has no enforceable final-output interposer')
    if parameters is not None:
        source_required=(
            parameters.source_policy=='required'
            or any((parameters.S.n,parameters.S.t_seconds,parameters.S.r,parameters.S.b))
        )
        if source_required and not capabilities.source_tools:
            blocking.append('required/explicit source work requires source tools')
        if parameters.B == 1 and capabilities.monotonic_clock is not MonotonicClockCapability.CONTINUOUS:
            blocking.append('hard time minimum requires a continuous monotonic clock')
        if parameters.S.b == 1 and capabilities.monotonic_clock is not MonotonicClockCapability.CONTINUOUS:
            blocking.append('hard source-time minimum requires a continuous monotonic clock')
        if parameters.D_s is not None and parameters.D_s > 0 and parameters.L_e > capabilities.isolation_max:
            blocking.append(
                f'requested L{parameters.L_e} exceeds host isolation cap L{capabilities.isolation_max}'
            )
        if parameters.V_o > capabilities.viewpoint_max:
            blocking.append(f'requested V{parameters.V_o} exceeds host viewpoint cap V{capabilities.viewpoint_max}')

    if blocking:
        mode = CapabilityMode.PROMPT_ONLY
        reasons = tuple(blocking + advisory)
    elif advisory:
        mode = CapabilityMode.ADVISORY
        reasons = tuple(advisory)
    else:
        mode = CapabilityMode.ENFORCED
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
    )
