"""DIGR 5.0 executing-task genesis with multi-sample clock readiness."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from .clock_probe import ClockSnapshot, elapsed_ns, snapshot, continuity_kind
from .invocation_surface import InvocationSurface, InvocationKind
from .protocol_authority import ProtocolAuthority
from .validation import require_nonnegative_int


@dataclass(frozen=True)
class ClockReadiness:
    samples: tuple[ClockSnapshot, ...]

    def __post_init__(self):
        samples = tuple(self.samples)
        if len(samples) < 3:
            raise ValueError('clock readiness requires at least three samples')
        if any(not isinstance(x, ClockSnapshot) for x in samples):
            raise TypeError('all clock samples must be ClockSnapshot')
        # Verify every adjacent edge and the full anchor->probe span.
        for a, b in zip(samples, samples[1:]):
            elapsed_ns(a, b)
        elapsed_ns(samples[0], samples[-1])
        object.__setattr__(self, 'samples', samples)

    @property
    def anchor(self) -> ClockSnapshot: return self.samples[0]
    @property
    def probe(self) -> ClockSnapshot: return self.samples[-1]
    @property
    def ready(self) -> bool: return True
    @property
    def continuity_kind(self) -> str: return continuity_kind(self.anchor, self.probe)
    @property
    def sample_count(self) -> int: return len(self.samples)

    def to_dict(self) -> dict[str, Any]:
        return {
            'samples': [x.to_dict() for x in self.samples],
            'ready': True,
            'continuity_kind': self.continuity_kind,
            'sample_count': self.sample_count,
        }


@dataclass(frozen=True)
class TaskStartupReceipt:
    authority: ProtocolAuthority
    invocation: InvocationSurface
    clock: ClockReadiness
    u0_frozen: bool = False

    def __post_init__(self):
        if not isinstance(self.authority, ProtocolAuthority): raise TypeError('authority must be ProtocolAuthority')
        if not isinstance(self.invocation, InvocationSurface): raise TypeError('invocation must be InvocationSurface')
        if self.invocation.kind is not InvocationKind.EXECUTING: raise ValueError('task startup requires EXECUTING invocation')
        if not isinstance(self.clock, ClockReadiness): raise TypeError('clock must be ClockReadiness')
        if type(self.u0_frozen) is not bool: raise TypeError('u0_frozen must be bool')
        if self.u0_frozen: raise ValueError('task startup receipt must be created before U0 freeze')

    def to_dict(self) -> dict[str, Any]:
        return {'authority': self.authority.to_dict(),'invocation': self.invocation.to_dict(),'clock': self.clock.to_dict(),'u0_frozen': False}


def start_task(authority: ProtocolAuthority, invocation: InvocationSurface, snapshot_fn: Callable[[], ClockSnapshot] = snapshot, *, sample_count: int = 3) -> TaskStartupReceipt:
    """Cross the task-start boundary by opening and validating the clock first."""
    if not callable(snapshot_fn): raise TypeError('snapshot_fn must be callable')
    if not isinstance(invocation, InvocationSurface) or invocation.kind is not InvocationKind.EXECUTING:
        raise ValueError('only an EXECUTING surface can start a DIGR task')
    sample_count = require_nonnegative_int('sample_count', sample_count)
    if sample_count < 3: raise ValueError('sample_count must be >= 3')
    readiness = ClockReadiness(tuple(snapshot_fn() for _ in range(sample_count)))
    return TaskStartupReceipt(authority, invocation, readiness, False)
