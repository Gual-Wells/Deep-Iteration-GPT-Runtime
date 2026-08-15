"""Trusted-clock reference helper for DIGR 3.0.

The helper measures facts only. It does not decide what the user meant by T,
what work should be done, or whether a task result is good enough.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import time
from typing import Optional

_BOOT_ID = Path("/proc/sys/kernel/random/boot_id")

@dataclass(frozen=True)
class ClockSnapshot:
    provider: str
    clock_id: Optional[str]
    monotonic_ns: int
    wall_ns: int
    hard_verifiable: bool

    def to_dict(self):
        return asdict(self)

def _linux_boot_id() -> Optional[str]:
    try:
        value = _BOOT_ID.read_text(encoding="utf-8").strip()
        return value or None
    except OSError:
        return None

def snapshot() -> ClockSnapshot:
    boot_id = _linux_boot_id()
    return ClockSnapshot(
        provider="python-monotonic",
        clock_id=f"linux-boot:{boot_id}" if boot_id else None,
        monotonic_ns=time.monotonic_ns(),
        wall_ns=time.time_ns(),
        hard_verifiable=bool(boot_id),
    )

def elapsed_seconds(start: ClockSnapshot, end: ClockSnapshot) -> float:
    if not start.hard_verifiable or not end.hard_verifiable:
        raise ValueError("hard elapsed time is not verifiable with these snapshots")
    if start.provider != end.provider or start.clock_id != end.clock_id:
        raise ValueError("clock identity changed; hard elapsed time is unverifiable")
    delta = end.monotonic_ns - start.monotonic_ns
    if delta < 0:
        raise ValueError("monotonic clock moved backwards")
    return delta / 1_000_000_000

if __name__ == "__main__":
    print(json.dumps(snapshot().to_dict(), ensure_ascii=False, sort_keys=True))
