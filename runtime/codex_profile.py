"""Offline Codex profile utilities; not a DIGR executor or host gate.

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
from .codex_transport import profile_layout
from .execution_protocol import verify_execution_bundle

PROFILE_PROTOCOL = 'digr-codex-native-v8'
PROFILE_CORE = (
    'codex/FOUNDATION.md',
    'codex/CHARACTER.md', 'codex/PARAMETERS.md',
    'codex/COLLABORATION.md', 'codex/PERMISSIONS.md',
    'codex/RETURN.md',
)
PROFILE_FILES = (
    'codex/VERSION',
    'codex/AGENTS.light.md',
    'codex/ROUTER.experimental.txt',
    'codex/STARTUP.md',
    'codex/PROTOCOL.md',
    'codex/FOUNDATION.md',
    'codex/HELP.md',
    'codex/PARAMETERS.md',
    'codex/WORKBENCH.md',
    'codex/CHARACTER.md',
    'codex/COLLABORATION.md',
    'codex/PERMISSIONS.md',
    'codex/RETURN.md',
    'codex/EXECUTION_PROTOCOL.json',
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
    lifecycle_status: str

    def __post_init__(self) -> None:
        if not isinstance(self.turn_id, str) or not self.turn_id.strip():
            raise ValueError('active turn_id must be nonempty')
        if self.mode not in ('LIGHT', 'DEEP'):
            raise ValueError('active mode must be LIGHT or DEEP')
        if self.lifecycle_status not in ('ACTIVE', 'PAUSED', 'CLOSED', 'STOPPED', 'CANCELLED'):
            raise ValueError('supply the actual task lifecycle status')


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


def classify_invocation(message: str) -> dict[str, Any]:
    """Classify the versioned call surface AFTER live pinned startup acquisition.

    This is deliberately separate from the thin candidate router. It neither
    fetches a repository nor infers write/publication authority from task words.
    Parameter text and the task are preserved for semantic interpretation.
    """
    if not isinstance(message, str):
        raise TypeError('message must be str')
    text = message.lstrip()
    key = candidate_route_key(message)
    base = {'classification': 'NATIVE', 'route_key': key, 'task': None,
            'parameter_text': None, 'action_scope': 'INTERPRET_SEPARATELY',
            'live_acquisition_performed': False, 'run_started': False}
    if key is None:
        return {**base, 'reason': 'no exact leading candidate prefix'}
    tail = text[len(key):]
    if tail.strip() == '/help':
        return {**base, 'classification': 'HELP', 'reason': 'exact help request'}
    if not tail.strip():
        return {**base, 'classification': 'INVALID', 'reason': 'empty invocation'}
    stack = []
    pairs = {')': '(', '）': '（'}
    separator = None
    for index, char in enumerate(tail):
        if char in '(（':
            stack.append(char)
        elif char in ')）':
            if not stack or stack.pop() != pairs[char]:
                return {**base, 'classification': 'INVALID', 'reason': 'unbalanced parameter parentheses'}
        elif char in ':：' and not stack:
            separator = index
            break
    if separator is None:
        if stack:
            return {**base, 'classification': 'INVALID', 'reason': 'unclosed parameter parentheses'}
        return {**base, 'reason': 'protocol discussion without a complete invocation surface'}
    prelude, task = tail[:separator], tail[separator + 1:]
    if prelude.strip() and not (prelude.strip().startswith(('(', '（')) and prelude.strip().endswith((')', '）'))):
        return {**base, 'reason': 'discussion text before the task separator'}
    if not task.strip():
        return {**base, 'classification': 'INVALID', 'reason': 'empty task'}
    return {**base, 'classification': 'EXECUTING', 'task': task,
            'parameter_text': prelude, 'reason': 'explicit complete DIGR invocation; question/read-only scope does not change mode'}


def decide_boundary(
    event: EventKind | str,
    message: str = '',
    *,
    active: ActiveContext | None = None,
    expected_turn_id: str | None = None,
    goal_changed: bool = False,
) -> BoundaryDecision:
    """Preview a supplied host event without inferring intent or executing it.

    Host turn names do not end an unfinished DEEP task. The caller supplies its
    actual lifecycle status and goal_changed after interpretation; neither a
    turn id nor this preview certifies those facts. Every candidate message
    still requires real acquisition, without replacing the frozen run pin.
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
        if active.lifecycle_status in ('CLOSED', 'STOPPED', 'CANCELLED'):
            raise ValueError('STEER requires an unfinished task; a closed task cannot be revived')
    elif expected_turn_id is not None:
        raise ValueError('expected_turn_id applies only to STEER')

    if event in (EventKind.COMPACTION, EventKind.INTERRUPT):
        if message or goal_changed:
            raise ValueError('control events do not contain a new user message/goal')
        if active is None:
            raise ValueError('control event requires active context')
        if active.lifecycle_status in ('CLOSED', 'STOPPED', 'CANCELLED'):
            return BoundaryDecision('LIGHT', 'PRESERVE_TERMINAL_STATE', False, True, active.turn_id)
        if active.lifecycle_status == 'PAUSED':
            return BoundaryDecision(active.mode, 'PRESERVE_PAUSED_STATE', False, True, active.turn_id)
        action = ('RESTORE_REAL_STATE' if event is EventKind.COMPACTION
                  else 'SUSPEND_ACTIVITY_PRESERVE_TASK')
        return BoundaryDecision(active.mode, action, False, True, active.turn_id)

    unfinished_deep = (active is not None and active.mode == 'DEEP'
                       and active.lifecycle_status in ('ACTIVE', 'PAUSED'))
    continuing = event is EventKind.STEER or unfinished_deep
    preserve = continuing
    continuation = active.turn_id if continuing and active is not None else None
    after_route = 'REALIGN_GOAL' if continuing and goal_changed else (
        'CONTINUE' if continuing else 'CLASSIFY_NEW_INVOCATION'
    )
    if continuing and active is not None and active.lifecycle_status == 'PAUSED':
        after_route = 'HANDLE_SUPPLEMENT_KEEP_PAUSED'
    key = candidate_route_key(message)
    if key is not None:
        return BoundaryDecision(
            'ROUTE_PENDING', 'ACQUIRE_LIVE_PIN_FIRST', True, preserve,
            continuation, key, after_route,
        )
    if continuing:
        assert active is not None
        return BoundaryDecision(
            active.mode, after_route,
            False, preserve, continuation,
        )
    # Completed/cancelled tasks and LIGHT mode do not activate a fresh DIGR task.
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
    if manifest.get('core') != list(PROFILE_CORE):
        raise ValueError('Codex execution must load foundation, character, responsibility, collaboration, permissions and return')
    if manifest.get('startup_slice') != ['codex/STARTUP.md']:
        raise ValueError('unexpected Codex startup slice')
    if manifest.get('help') != 'codex/HELP.md':
        raise ValueError('unexpected Codex help')
    if manifest.get('light_instructions') != 'codex/AGENTS.light.md':
        raise ValueError('unexpected Codex light instructions')
    layout = profile_layout(manifest, version)
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
    # This validates local transport bytes, not a live repository acquisition.
    verify_execution_bundle((root / layout['execution_bundle']).read_bytes(),
        commit_sha='0' * 40, manifest_bytes=(root / 'codex/manifest.json').read_bytes(),
        expected_paths=[manifest['entrypoint'], *manifest['core']])
    return {
        'protocol': manifest['protocol'],
        'version': version,
        'checked_files': len(PROFILE_FILES),
        'verification_scope': 'LOCAL_FILE_INTEGRITY',
        'live_repository_acquisition': False,
        'global_install_performed': False,
        'run_started': False,
    }


def refresh_distribution(root: Path) -> dict[str, Any]:
    """Explicitly regenerate the local execution bundle and declared hashes."""
    root = Path(root).resolve()
    path = root / 'codex/manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    version = (root / 'codex/VERSION').read_text(encoding='utf-8').strip()
    if manifest.get('protocol') != PROFILE_PROTOCOL or manifest.get('version') != version:
        raise ValueError('Codex manifest/VERSION identity mismatch')
    expected = ['codex/PROTOCOL.md', *PROFILE_CORE]
    if manifest.get('core') != list(PROFILE_CORE) or manifest.get('execution_bundle') != {
        'path': 'codex/EXECUTION_PROTOCOL.json', 'schema': 1, 'members': expected,
    }:
        raise ValueError('unexpected local execution bundle layout')
    members = []
    for rel in expected:
        raw = (root / rel).read_bytes()
        members.append({'path': rel, 'sha256': sha256(raw).hexdigest(),
                        'byte_length': len(raw), 'content': raw.decode('utf-8')})
    bundle = {'schema_version': 1, 'version': version, 'protocol': PROFILE_PROTOCOL, 'members': members}
    (root / 'codex/EXECUTION_PROTOCOL.json').write_text(
        json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n',
        encoding='utf-8', newline='\n')
    manifest['file_sha256'] = {rel: sha256((root / rel).read_bytes()).hexdigest() for rel in PROFILE_FILES}
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    return verify_distribution(root)


def instruction_text(root: Path, layer: str) -> str:
    verify_distribution(root)
    if layer == 'codex-agents':
        # A ready-to-merge thin host layer. Choosing/exporting this text does
        # not install it, and it carries no deep execution semantics.
        return ((Path(root) / 'codex/ROUTER.experimental.txt').read_text(encoding='utf-8').rstrip()
                + '\n\n' + (Path(root) / 'codex/AGENTS.light.md').read_text(encoding='utf-8'))
    paths = {
        'light': 'codex/AGENTS.light.md',
        'experimental-router': 'codex/ROUTER.experimental.txt',
    }
    if layer not in paths:
        raise ValueError('layer must be light, experimental-router or codex-agents')
    return (Path(root) / paths[layer]).read_text(encoding='utf-8')


def depth_preferences(root: Path) -> dict[str, Any]:
    """Return the user's declared investment policy, not a workload scheduler."""
    verify_distribution(root)
    manifest = json.loads((Path(root) / 'codex/manifest.json').read_text(encoding='utf-8'))
    return manifest['depth_preferences']
