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
import re
from typing import Any, Mapping

from .routing import candidate_route_key
from .codex_transport import profile_layout
from .execution_protocol import verify_execution_bundle
from .codex_presets import resolve_defaults, preset_catalog

PROFILE_PROTOCOL = 'digr-codex-native-v24'
PROFILE_CORE = (
    'codex/CONSTITUTION.md',
    'codex/FOUNDATION.md',
    'codex/METHOD.md', 'codex/CHARACTER.md', 'codex/PARAMETERS.md',
    'codex/COLLABORATION.md', 'codex/PERMISSIONS.md',
    'codex/CONSULT.md',
    'codex/SPLIT.md',
    'codex/COUNCIL.md',
    'codex/COURT.md',
    'codex/USAGE.md',
    'codex/CHAT.md',
    'codex/LIVE.md',
    'codex/DELIVERY.md',
    'codex/RETURN.md',
)
PROFILE_FILES = (
    'codex/VERSION',
    'codex/AGENTS.light.md',
    'codex/ROUTER.experimental.txt',
    'codex/STARTUP.md',
    'codex/PROTOCOL.md',
    'codex/CONSTITUTION.md',
    'codex/FOUNDATION.md',
    'codex/METHOD.md',
    'codex/HELP.md',
    'codex/PARAMETERS.md',
    'codex/WORKBENCH.md',
    'codex/CHARACTER.md',
    'codex/COLLABORATION.md',
    'codex/CONSULT.md',
    'codex/SPLIT.md',
    'codex/PERMISSIONS.md',
    'codex/DELIVERY.md',
    'codex/RETURN.md',
    'codex/EXECUTION_PROTOCOL.json',
    'codex/COUNCIL.md',
    'codex/COURT.md',
    'codex/USAGE.md',
    'codex/CHAT.md',
    'codex/CHAT_LIGHT.md',
    'codex/CHAT_DEEP.md',
    'codex/LIVE.md',
)
CAPABILITY_NAMES = (
    'files', 'shell', 'persistent_workspace', 'repository_transport',
    'source_tools', 'monotonic_clock', 'isolated_agents', 'final_output_gate',
)
_DELIVERY_TOKEN = re.compile(r'(?<![A-Za-z0-9_])X(?![A-Za-z0-9_])')
_DELIVERY_TARGET = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}')
_PROFILE_PIN = re.compile(r'(\d+)\.(\d+)\.(\d+)@[0-9a-f]{40}')


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


def _parameter_group_spans(prelude: str) -> list[tuple[int, int]]:
    """Read complete, adjacent header groups without rewriting their bytes."""
    spans = []
    stack = []
    pairs = {')': '(', '）': '（'}
    start = None
    for index, char in enumerate(prelude):
        if char in '(（':
            if not stack:
                start = index
            stack.append(char)
        elif char in ')）':
            if not stack or stack.pop() != pairs[char]:
                raise ValueError('unbalanced parameter parentheses')
            if not stack:
                spans.append((start, index + 1))
        elif not stack and not char.isspace():
            raise ValueError('unexpected text between parameter groups')
    if stack:
        raise ValueError('unclosed parameter parentheses')
    return spans


def _delivery_group(content: str) -> dict[str, Any] | None:
    """Recognize selection syntax, never resolve an account or authorize a send.

    Custom target names are lexical candidates. The task's target registry must
    resolve them before delivery is armed; spelling a slug cannot create a
    destination. Only header punctuation, not task text, is interpreted here.
    """
    content = content.strip()
    if content == 'X':
        return {'mode': 'external', 'target': 'gmail', 'explicit': True}
    selected = re.fullmatch(r'X\s*[=＝]\s*(.*?)\s*', content, flags=re.DOTALL)
    if selected:
        target = selected.group(1)
        if not target:
            raise ValueError('X= requires a nonempty delivery target')
        if not _DELIVERY_TARGET.fullmatch(target):
            raise ValueError('X target must be an ASCII slug of 1 to 64 characters')
        return {'mode': 'external', 'target': target.casefold(), 'explicit': True}
    if _DELIVERY_TOKEN.search(content):
        raise ValueError('X must occupy its own final delivery parameter group')
    return None


def _invocation_parameters(prelude: str) -> tuple[str, dict[str, Any]]:
    """Separate one execution group from an optional final X delivery group."""
    groups = _parameter_group_spans(prelude)
    selection = {'mode': 'local', 'target': None, 'explicit': False}
    delivery_index = None
    for index, (start, end) in enumerate(groups):
        candidate = _delivery_group(prelude[start + 1:end - 1])
        if candidate is not None:
            if delivery_index is not None:
                raise ValueError('duplicate X delivery parameter groups')
            delivery_index, selection = index, candidate
    if delivery_index is not None and delivery_index != len(groups) - 1:
        raise ValueError('X delivery parameter group must be last')
    if len(groups) - (delivery_index is not None) > 1:
        raise ValueError('only one execution parameter group is allowed before X')
    # Keep the exact normal header prefix (including whitespace); parameter_text
    # separately retains the entire original prelude, including X and suffix.
    execution = prelude if delivery_index is None else prelude[:groups[delivery_index][0]]
    return execution, selection


def _formal_invocation_parameters(prelude: str) -> tuple[str, int | None]:
    """Keep one formal group and an optional compatible standalone X group."""
    groups = _parameter_group_spans(prelude)
    if len(groups) > 2:
        raise ValueError('only one formal parameter group and an optional final X group are allowed')
    if not groups:
        return prelude, None
    start, end = groups[-1]
    content = prelude[start + 1:end - 1].translate(str.maketrans({'（':'(', '）':')', '＝':'='})).strip()
    standalone = re.fullmatch(r'X(?:\s*=\s*(0|1|[Gg][Mm][Aa][Ii][Ll])|\s*\(\s*([01])\s*\))?', content)
    if standalone:
        value = standalone[1] or standalone[2] or '1'
        return prelude[:start], 1 if value.casefold() == 'gmail' else int(value)
    if len(groups) > 1:
        raise ValueError('only a standalone X parameter may follow the formal parameter group')
    return prelude, None


def parse_do_supplement(message: str, *, p_run: str | None = None) -> dict[str, str] | None:
    """Recognize a DO marker in the current user message without interpreting its body."""
    text = message.lstrip()
    if not text.startswith(('DO:', 'DO：')):
        return None
    if p_run is not None:
        version = _PROFILE_PIN.fullmatch(p_run)
        if not version or tuple(map(int, version.groups())) < (0, 17, 0):
            return None
    return {'kind': 'DO', 'prefix': text[:3], 'text': text[3:]}


def classify_invocation(message: str, *, p_run: str | None = None) -> dict[str, Any]:
    """Classify the versioned call surface AFTER live pinned startup acquisition.

    This is deliberately separate from the thin candidate router. It neither
    fetches a repository nor infers write/publication authority from task words.
    Parameter text and the task are preserved for semantic interpretation.
    X controls file delivery only. This preview parses a selection; it does not
    validate a destination registry, transmit files or create extra artifacts.
    """
    if not isinstance(message, str):
        raise TypeError('message must be str')
    text = message.lstrip()
    key = candidate_route_key(message)
    # The thin router stays broad. Only the acquired profile interprets aliases.
    invocation_key = next((alias for alias in ('DIGRC', 'DIGRP')
                           if text.startswith(alias)), key)
    addon_hint = 'paper' if invocation_key == 'DIGRP' else None
    pin = _PROFILE_PIN.fullmatch(p_run) if p_run is not None else None
    version = tuple(map(int, pin.groups())) if pin else ()
    preference_only = p_run is None or version >= (1, 1, 1)
    project_research = p_run is None or version >= (1, 4, 0)
    formal_task_parameters = p_run is None or version >= (1, 5, 0)
    court_mode = p_run is None or version >= (1, 6, 0)
    depth_key = 'depth_preferences' if preference_only else 'depth_defaults'
    base = {'classification': 'NATIVE', 'route_key': key, 'task': None,
            'invocation_key': invocation_key, 'addon_hint': addon_hint,
            'addon_selection': None,
            'parameter_text': None, 'execution_parameter_text': None,
            'consult_selection': False, depth_key: None,
            'delivery_selection': {'mode': 'local', 'target': None, 'explicit': False},
            'action_scope': 'INTERPRET_SEPARATELY',
            'live_acquisition_performed': False, 'run_started': False}
    if key is None:
        supplement = parse_do_supplement(message, p_run=p_run)
        if supplement is not None:
            return {**base, 'supplement': supplement, 'reason': 'explicit same-task supplement'}
        return {**base, 'reason': 'no exact leading candidate prefix'}
    tail = text[len(invocation_key):]
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
    from .codex_collaboration import COUNCIL_ONLY, delimiter_policy, layered_policy
    modern_separator = p_run is None or delimiter_policy(p_run)
    separator_length = 1
    if modern_separator:
        while separator + separator_length < len(tail) and tail[separator + separator_length] in ':：':
            separator_length += 1
    prelude, task = tail[:separator], tail[separator + separator_length:]
    if prelude.strip() and not (prelude.strip().startswith(('(', '（')) and prelude.strip().endswith((')', '）'))):
        return {**base, 'reason': 'discussion text before the task separator'}
    if separator_length > 2:
        return {**base, 'classification': 'INVALID', 'reason': 'use one or two task-separator colons'}
    if not task.strip():
        return {**base, 'classification': 'INVALID', 'reason': 'empty task'}
    try:
        standalone_x = None
        if formal_task_parameters:
            execution_parameters, standalone_x = _formal_invocation_parameters(prelude)
        else:
            execution_parameters, delivery = _invocation_parameters(prelude)
        depth = resolve_defaults(execution_parameters, preference_only=preference_only,
                                 project_research=project_research,
                                 formal_task_parameters=formal_task_parameters, court_mode=court_mode)
        if formal_task_parameters:
            declared = depth['explicit_overrides']
            if standalone_x is not None:
                if 'X' in declared:
                    raise ValueError('duplicate X parameter declarations')
                declared['X'] = standalone_x
            delivery = ({'mode': 'external', 'target': 'gmail', 'explicit': True}
                        if declared.get('X') == 1 else
                        {'mode': 'local', 'target': None, 'explicit': False})
    except ValueError as exc:
        return {**base, 'classification': 'INVALID', 'reason': str(exc)}
    layered = p_run is None or layered_policy(p_run)
    selection = {}
    if modern_separator:
        double = separator_length == 2
        selection = {'task_separator': tail[separator:separator + separator_length],
                     'claude_selection': 'ALLOW' if double else COUNCIL_ONLY if layered else 'DENY'}
        if not layered:
            selection['work_profile'] = 'CLAUDE_GUIDED' if double else 'EXECUTION'
    return {**base, 'classification': 'EXECUTING', 'task': task,
            **selection,
            **({'delivery_explicit': 'X' in depth['explicit_overrides']}
               if formal_task_parameters else {}),
            'parameter_text': prelude, 'execution_parameter_text': execution_parameters,
            'delivery_selection': delivery, 'addon_selection': addon_hint,
            'consult_selection': invocation_key in ('DIGRC', 'DIGRP'),
            depth_key: depth,
            'reason': 'explicit complete ' + invocation_key + ' invocation; question/read-only scope does not change mode'}


def decide_boundary(
    event: EventKind | str,
    message: str = '',
    *,
    active: ActiveContext | None = None,
    expected_turn_id: str | None = None,
    goal_changed: bool = False,
    p_run: str | None = None,
) -> BoundaryDecision:
    """Preview a supplied host event without inferring intent or executing it.

    Host turn names do not end an unfinished DEEP task. The caller supplies its
    actual lifecycle status and goal_changed after interpretation; neither a
    turn id nor this preview certifies those facts. Supply the frozen pin for
    version-specific continuation. Every candidate message still requires real
    acquisition, without replacing the frozen run pin.
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
    if parse_do_supplement(message, p_run=p_run) is not None:
        if not unfinished_deep:
            return BoundaryDecision('LIGHT', 'SUPPLEMENT_NEEDS_TASK', False, False, None)
        if after_route == 'CONTINUE':
            after_route = 'HANDLE_SUPPLEMENT'
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
    catalog = preset_catalog()
    manifest['depth_preferences']['presets'] = catalog['presets']
    manifest['depth_preferences']['task_defaults'] = catalog['task_defaults']
    manifest['depth_preferences']['task_parameters'] = catalog['task_parameters']
    manifest['depth_preferences']['task_defaults_scope'] = catalog['task_defaults_scope']
    manifest['depth_preferences']['implicit_deep'] = dict(catalog['presets']['Default'])
    manifest['depth_preferences']['preset_aliases'] = {'standard': 'Light'}
    manifest['depth_preferences']['default_preset'] = 'Default'
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
        'chat-light': 'codex/CHAT_LIGHT.md',
        'chat-deep': 'codex/CHAT_DEEP.md',
    }
    if layer not in paths:
        raise ValueError('layer must be light, experimental-router or codex-agents')
    return (Path(root) / paths[layer]).read_text(encoding='utf-8')


def depth_preferences(root: Path) -> dict[str, Any]:
    """Return the versioned preference baselines and task-inference policy."""
    verify_distribution(root)
    manifest = json.loads((Path(root) / 'codex/manifest.json').read_text(encoding='utf-8'))
    return manifest['depth_preferences']
