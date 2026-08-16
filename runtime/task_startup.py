"""DIGR 4.1 executing-task startup evidence.

Unlike routing.py, this module is versioned 4.1 protocol support: executing
4.1 tasks require trusted clock readiness before U0/substantive work. Help and
off/invalid candidates never instantiate this record.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .clock_probe import ClockSnapshot, elapsed_ns
from .protocol_authority import ProtocolAuthority

@dataclass(frozen=True)
class ClockReadiness:
    anchor: ClockSnapshot
    probe: ClockSnapshot

    def __post_init__(self):
        if not isinstance(self.anchor, ClockSnapshot) or not isinstance(self.probe, ClockSnapshot):
            raise TypeError('anchor/probe must be ClockSnapshot')
        elapsed_ns(self.anchor, self.probe)

    @property
    def ready(self) -> bool:
        return True

    def to_dict(self) -> dict[str, Any]:
        return {'anchor': self.anchor.to_dict(), 'probe': self.probe.to_dict(), 'ready': True}

@dataclass(frozen=True)
class TaskStartupReceipt:
    authority: ProtocolAuthority
    clock: ClockReadiness
    u0_frozen: bool = False

    def __post_init__(self):
        if not isinstance(self.authority, ProtocolAuthority):
            raise TypeError('authority must be ProtocolAuthority')
        if not isinstance(self.clock, ClockReadiness):
            raise TypeError('clock must be ClockReadiness')
        if not isinstance(self.u0_frozen, bool):
            raise TypeError('u0_frozen must be bool')
        if self.u0_frozen:
            raise ValueError('task startup receipt must be created before U0 freeze')

    def to_dict(self) -> dict[str, Any]:
        return {'authority': self.authority.to_dict(), 'clock': self.clock.to_dict(), 'u0_frozen': False}
