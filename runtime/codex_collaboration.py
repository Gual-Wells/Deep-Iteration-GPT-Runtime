"""Apply current-user Claude selection, then derive actual collaboration duties."""
from __future__ import annotations
import re
from typing import Any, Mapping

FORMAT = 'digr-actual-collaboration-1'
SONNET_MODEL = re.compile(r'anthropic/claude-(?:sonnet-[0-9]+(?:\.[0-9]+)*|[0-9]+(?:\.[0-9]+)*-sonnet)(?:-[0-9]{8})?')
CLAUDE_MODEL = re.compile(r'(?:^|/)claude(?:[-/:]|$)', re.IGNORECASE)


def council_enabled(p_run: str) -> bool:
    version = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)@[0-9a-f]{40}', p_run)
    return bool(version and tuple(map(int, version.groups())) >= (0, 16, 0))


def delimiter_policy(p_run: str) -> bool:
    version = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)@[0-9a-f]{40}', p_run)
    return bool(version and tuple(map(int, version.groups())) >= (0, 15, 0))


def require_claude_permission(p_run: str, model: str, lifecycle: Mapping[str, Any]) -> None:
    """No credentials, reservations or transport before a current allow choice.

    Local source-bound records are not user authentication or a budget grant.
    Old pinned tasks retain their original admission rules.
    """
    if delimiter_policy(p_run) and CLAUDE_MODEL.search(model):
        if lifecycle.get('claude_policy', {}).get('mode') != 'ALLOW':
            raise ValueError('Claude is disabled by the current task choice; DIGR:: permits Claude, DIGR: does not')


def unified(p_run: str) -> bool:
    version = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)@[0-9a-f]{40}', p_run)
    return bool(version and tuple(map(int, version.groups())) >= (0, 14, 0))


def requirements(p_run: str, model: str, paper_scope: Mapping[str, Any] | None, *,
                 participation_role: str = 'consult_guidance',
                 council_scope: Mapping[str, Any] | None = None) -> dict | None:
    if participation_role not in {'consult_guidance', 'council_member'}:
        raise ValueError('Unknown collaboration participation role')
    if participation_role == 'council_member':
        if not council_enabled(p_run) or paper_scope is not None or not isinstance(council_scope, Mapping):
            raise ValueError('Council members require the current council profile and a member scope')
    elif council_scope is not None:
        raise ValueError('Formal Consult cannot inherit a council member identity')
    if not unified(p_run):
        return None
    sonnet = bool(SONNET_MODEL.fullmatch(model))
    protocols = ['codex/CONSULT.md', 'codex/SPLIT.md', 'codex/PERMISSIONS.md']
    if participation_role == 'council_member':
        protocols = ['codex/COUNCIL.md', 'codex/COLLABORATION.md', 'codex/SPLIT.md', 'codex/PERMISSIONS.md']
    if paper_scope is not None:
        if not sonnet:
            raise ValueError('Selected paper content driving requires the actual canonical Sonnet model')
        protocols += ['paper/PROTOCOL.md', 'paper/DATA.md', 'paper/PDF_DESIGN.md']
    result = {'format': FORMAT, 'entrypoint': 'DIGR', 'selection_basis': 'ACTUAL_REQUEST_MODEL_AND_SCOPE',
            'requested_model': model, 'sonnet_selected': sonnet,
            'content_relationship': ('COUNCIL_MEMBER_RESEARCH' if participation_role == 'council_member' else
                                     'SONNET_NATIVE_PAPER' if paper_scope is not None else
                                     'SONNET_CONTENT_GUIDANCE' if sonnet else 'ORDINARY_CONTENT_COLLABORATION'),
            'paper_scope': dict(paper_scope) if paper_scope is not None else None, 'protocols': protocols,
            'engineering': ['source_preparation', 'native_split', 'public_relay',
                            'budget_and_recovery', 'native_production_and_delivery'],
            'participation_status': 'PREPARED_NOT_SENT', 'fee_authorization': False,
            'scope': 'derived duties; credentials, aliases and a prepared record do not prove actual participation'}
    if council_enabled(p_run):
        result['participation_role'] = participation_role
        result['council_scope'] = dict(council_scope) if council_scope is not None else None
        result['subjective_guidance_priority'] = participation_role == 'consult_guidance' and sonnet
    return result
