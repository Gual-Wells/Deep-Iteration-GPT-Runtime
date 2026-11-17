"""Apply current-user Claude selection, then derive actual collaboration duties."""
from __future__ import annotations
import re
from typing import Any, Mapping

FORMAT = 'digr-actual-collaboration-1'
SONNET_MODEL = re.compile(r'anthropic/claude-(?:sonnet-[0-9]+(?:\.[0-9]+)*|[0-9]+(?:\.[0-9]+)*-sonnet)(?:-[0-9]{8})?')
CLAUDE_MODEL = re.compile(r'(?:^|/)claude(?:[-/:]|$)', re.IGNORECASE)


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


def requirements(p_run: str, model: str, paper_scope: Mapping[str, Any] | None) -> dict | None:
    if not unified(p_run):
        return None
    sonnet = bool(SONNET_MODEL.fullmatch(model))
    protocols = ['codex/CONSULT.md', 'codex/SPLIT.md', 'codex/PERMISSIONS.md']
    if paper_scope is not None:
        if not sonnet:
            raise ValueError('Selected paper content driving requires the actual canonical Sonnet model')
        protocols += ['paper/PROTOCOL.md', 'paper/DATA.md', 'paper/PDF_DESIGN.md']
    return {'format': FORMAT, 'entrypoint': 'DIGR', 'selection_basis': 'ACTUAL_REQUEST_MODEL_AND_SCOPE',
            'requested_model': model, 'sonnet_selected': sonnet,
            'content_relationship': ('SONNET_NATIVE_PAPER' if paper_scope is not None else
                                     'SONNET_CONTENT_GUIDANCE' if sonnet else 'ORDINARY_CONTENT_COLLABORATION'),
            'paper_scope': dict(paper_scope) if paper_scope is not None else None, 'protocols': protocols,
            'engineering': ['source_preparation', 'native_split', 'public_relay',
                            'budget_and_recovery', 'native_production_and_delivery'],
            'participation_status': 'PREPARED_NOT_SENT', 'fee_authorization': False,
            'scope': 'derived duties; credentials, aliases and a prepared record do not prove actual participation'}
