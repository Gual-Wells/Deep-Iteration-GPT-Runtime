"""Trusted monotonic-clock facts for DIGR 5.0.0-Berta1.

Two notions are intentionally separated:

* observed monotonic duration: a non-negative delta from the same provider;
* hard-verifiable duration: the same delta plus continuity identity proof.

Every executing DIGR 5.0 task must establish repository-defined task-clock readiness
after invocation classification and before U0/substantive work. Soft T/t may then report honest observed duration.
Hard T/t may only claim a number when continuity is additionally verified
across the formal intervals used for the claim.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import time
import uuid
from typing import Optional
from .validation import require_nonempty_text, require_nonnegative_int

_BOOT_ID = Path('/proc/sys/kernel/random/boot_id')
_SESSION_ID = uuid.uuid4().hex
_PROVIDER = 'python-monotonic-ns'

@dataclass(frozen=True)
class ClockSnapshot:
    provider: str
    session_id: str
    boot_id: Optional[str]
    monotonic_ns: int
    wall_ns: int

    def __post_init__(self):
        object.__setattr__(self, 'provider', require_nonempty_text('provider', self.provider))
        object.__setattr__(self, 'session_id', require_nonempty_text('session_id', self.session_id))
        if self.boot_id is not None:
            object.__setattr__(self, 'boot_id', require_nonempty_text('boot_id', self.boot_id))
        require_nonnegative_int('monotonic_ns', self.monotonic_ns)
        require_nonnegative_int('wall_ns', self.wall_ns)

    def to_dict(self):
        return asdict(self)


def _linux_boot_id() -> Optional[str]:
    try:
        value = _BOOT_ID.read_text(encoding='utf-8').strip()
        return value or None
    except OSError:
        return None


def snapshot() -> ClockSnapshot:
    return ClockSnapshot(
        provider=_PROVIDER,
        session_id=_SESSION_ID,
        boot_id=_linux_boot_id(),
        monotonic_ns=time.monotonic_ns(),
        wall_ns=time.time_ns(),
    )


def observed_elapsed_ns(start: ClockSnapshot, end: ClockSnapshot) -> int:
    """Return a best-effort monotonic delta without claiming hard continuity."""
    if not isinstance(start, ClockSnapshot) or not isinstance(end, ClockSnapshot):
        raise TypeError('start/end must be ClockSnapshot')
    if start.provider != end.provider:
        raise ValueError('clock provider changed; observed monotonic delta is unavailable')
    if start.session_id == end.session_id:
        # Same-process identity is sufficient, but an explicit contradictory
        # boot fact still fails closed.
        if start.boot_id is not None and end.boot_id is not None and start.boot_id != end.boot_id:
            raise ValueError('clock boot identity changed within one session')
    else:
        # Alpha2 tightens cross-process timing: provider equality alone is not
        # evidence that two monotonic counters share an epoch. Both boot IDs
        # must be present and equal even for soft/observed continuity.
        if start.boot_id is None or end.boot_id is None or start.boot_id != end.boot_id:
            raise ValueError('cross-session monotonic continuity requires equal non-empty boot_id')
    delta = end.monotonic_ns - start.monotonic_ns
    if delta < 0:
        raise ValueError('monotonic clock moved backwards or changed epoch')
    return delta


def continuity_kind(start: ClockSnapshot, end: ClockSnapshot) -> str:
    observed_elapsed_ns(start, end)
    if start.session_id == end.session_id:
        return 'same-process-session'
    if start.boot_id is not None and start.boot_id == end.boot_id:
        return 'same-boot-cross-process'
    raise ValueError('clock continuity identity changed; hard elapsed time is unverifiable')


def elapsed_ns(start: ClockSnapshot, end: ClockSnapshot) -> int:
    """Return hard-verifiable monotonic delta or fail closed."""
    continuity_kind(start, end)
    return observed_elapsed_ns(start, end)


def elapsed_seconds(start: ClockSnapshot, end: ClockSnapshot) -> float:
    return elapsed_ns(start, end) / 1_000_000_000


def pair_is_hard_verifiable(start: ClockSnapshot, end: ClockSnapshot) -> bool:
    try:
        elapsed_ns(start, end)
        return True
    except (TypeError, ValueError):
        return False


if __name__ == '__main__':
    print(json.dumps(snapshot().to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False))
