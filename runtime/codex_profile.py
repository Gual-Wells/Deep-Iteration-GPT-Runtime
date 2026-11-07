"""Small, offline Codex profile utilities; not a DIGR executor or host gate.

The active router still has to acquire a live immutable repository pin. This
module neither acquires one nor treats local file hashes/capability declarations
as a run receipt. Task interpretation remains model-owned.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from .routing import candidate_route_key

PROFILE_PROTOCOL = 'digr-codex-native-v4'
PROFILE_FILES = (
    'codex/VERSION',
    'codex/AGENTS.light.md',
    'codex/ROUTER.experimental.txt',
    'codex/STARTUP.md',
    'codex/PROTOCOL.md',
    'codex/HELP.md',
    'codex/PARAMETERS.md',
    'codex/WORKBENCH.md',
)
CAPABILITY_NAMES = (
    'files', 'shell', 'persistent_workspace', 'repository_transport',
    'source_tools', 'monotonic_clock', 'isolated_agents', 'final_output_gate',
)


class EventKind(str, Enum):
    NEW_TURN = 'NEW_TURN'
    STEER = 'STEER'
    COMPACTION = 'COMPACTION'
    INTERRUPT = 'INTERRUPT'


@dataclass(frozen=True)
class ActiveContext:
    turn_id: str
    mode: str

    def __post_init__(self) -> None:
        if not isinstance(self.turn_id, str) or not self.turn_id.strip():
            raise ValueError('active turn_id must be nonempty')
        if self.mode not in ('LIGHT', 'DEEP'):
            raise ValueError('active mode must be LIGHT or DEEP')


@dataclass(frozen=True)
class BoundaryDecision:
    mode: str
    action: str
    route_required: bool
    preserve_task: bool
    continuation_of: str | None
    route_key: str | None = None
    after_route: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def decide_boundary(
    event: EventKind | str,
    message: str = '',
    *,
    active: ActiveContext | None = None,
    expected_turn_id: str | None = None,
    goal_changed: bool = False,
) -> BoundaryDecision:
    """Preview a supplied host event without inferring intent or executing it.

    STEER needs an active turn and its expected id, like App Server. The caller
    supplies goal_changed after semantic interpretation; this helper cannot
    decide whether a user's correction replaces the goal. Every candidate user
    message, including a steer, still requires real routing before interpretation.
    A route requirement is never an EXECUTING decision.
    """
    event = EventKind(event)
    if not isinstance(message, str):
        raise TypeError('message must be str')
    if type(goal_changed) is not bool:
        raise TypeError('goal_changed must be bool')
    if active is not None and not isinstance(active, ActiveContext):
        raise TypeError('active must be ActiveContext or None')

    if event is EventKind.STEER:
        if active is None or expected_turn_id != active.turn_id:
            raise ValueError('STEER requires the matching active expected_turn_id')
    elif expected_turn_id is not None:
        raise ValueError('expected_turn_id applies only to STEER')

    if event in (EventKind.COMPACTION, EventKind.INTERRUPT):
        if message or goal_changed:
            raise ValueError('control events do not contain a new user message/goal')
        if active is None:
            raise ValueError('control event requires active context')
        action = 'RESTORE_REAL_STATE' if event is EventKind.COMPACTION else 'STOP'
        return BoundaryDecision(active.mode, action, False, True, active.turn_id)

    continuing = event is EventKind.STEER
    preserve = continuing and not goal_changed
    continuation = active.turn_id if continuing and active is not None else None
    after_route = 'REALIGN_GOAL' if continuing and goal_changed else (
        'CONTINUE' if continuing else 'CLASSIFY_NEW_INVOCATION'
    )
    key = candidate_route_key(message)
    if key is not None:
        return BoundaryDecision(
            'ROUTE_PENDING', 'ACQUIRE_LIVE_PIN_FIRST', True, preserve,
            continuation, key, after_route,
        )
    if continuing:
        assert active is not None
        return BoundaryDecision(
            active.mode, 'REALIGN_GOAL' if goal_changed else 'CONTINUE',
            False, preserve, continuation,
        )
    # A previous DEEP context does not make an ordinary new turn sticky.
    return BoundaryDecision('LIGHT', 'HANDLE_ORDINARY_TASK', False, False, None)


def capability_report(observations: Mapping[str, str]) -> dict[str, Any]:
    """Describe caller-supplied availability, never certify a run from flags."""
    if not isinstance(observations, Mapping):
        raise TypeError('observations must be a mapping')
    unknown = set(observations) - set(CAPABILITY_NAMES)
    if unknown:
        raise ValueError(f'unknown capabilities: {sorted(unknown)}')
    facts = dict.fromkeys(CAPABILITY_NAMES, 'UNKNOWN')
    for name, value in observations.items():
        if value not in ('AVAILABLE', 'UNAVAILABLE', 'UNKNOWN'):
            raise ValueError(f'{name} must be AVAILABLE, UNAVAILABLE or UNKNOWN')
        facts[name] = value
    return {
        'capabilities': facts,
        'execution_mode': 'MODEL_NATIVE',
        'attestation_level': 'NONE',
        'note': 'Availability declarations are not execution/delivery evidence. '
                'This helper cannot issue CANONICAL attestation.',
    }


def verify_distribution(root: Path) -> dict[str, Any]:
    """Check local profile identity and bytes, not live GitHub authority."""
    root = Path(root).resolve()
    manifest = json.loads((root / 'codex/manifest.json').read_text(encoding='utf-8'))
    version = (root / 'codex/VERSION').read_text(encoding='utf-8').strip()
    if manifest.get('protocol') != PROFILE_PROTOCOL or manifest.get('version') != version:
        raise ValueError('Codex manifest/VERSION identity mismatch')
    if manifest.get('entrypoint') != 'codex/PROTOCOL.md':
        raise ValueError('unexpected Codex entrypoint')
    if manifest.get('core') != ['codex/PARAMETERS.md']:
        raise ValueError('Codex execution must load parameter responsibility semantics')
    if manifest.get('startup_slice') != ['codex/STARTUP.md']:
        raise ValueError('unexpected Codex startup slice')
    if manifest.get('help') != 'codex/HELP.md':
        raise ValueError('unexpected Codex help')
    if manifest.get('light_instructions') != 'codex/AGENTS.light.md':
        raise ValueError('unexpected Codex light instructions')
    hashes = manifest.get('file_sha256', {})
    if not isinstance(hashes, dict) or set(hashes) != set(PROFILE_FILES):
        raise ValueError('profile hash set must exactly cover the declared instruction files')
    for rel in PROFILE_FILES:
        path = (root / rel).resolve()
        if root not in path.parents:
            raise ValueError(f'profile file escapes distribution root: {rel}')
        raw = path.read_bytes()
        raw.decode('utf-8')
        if sha256(raw).hexdigest() != hashes[rel]:
            raise ValueError(f'profile file hash mismatch: {rel}')
    return {
        'protocol': manifest['protocol'],
        'version': version,
        'checked_files': len(PROFILE_FILES),
        'verification_scope': 'LOCAL_FILE_INTEGRITY',
        'live_repository_acquisition': False,
        'global_install_performed': False,
        'run_started': False,
    }


def instruction_text(root: Path, layer: str) -> str:
    verify_distribution(root)
    paths = {
        'light': 'codex/AGENTS.light.md',
        'experimental-router': 'codex/ROUTER.experimental.txt',
    }
    if layer not in paths:
        raise ValueError('layer must be light or experimental-router')
    return (Path(root) / paths[layer]).read_text(encoding='utf-8')


def depth_preferences(root: Path) -> dict[str, Any]:
    """Return the user's declared investment policy, not a workload scheduler."""
    verify_distribution(root)
    manifest = json.loads((Path(root) / 'codex/manifest.json').read_text(encoding='utf-8'))
    return manifest['depth_preferences']
