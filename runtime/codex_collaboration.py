"""Derive duties from the actual request, without an alias or fee gate."""
from __future__ import annotations
import re
from typing import Any, Mapping

FORMAT = 'digr-actual-collaboration-1'
SONNET_MODEL = re.compile(r'anthropic/claude-(?:sonnet-[0-9]+(?:\.[0-9]+)*|[0-9]+(?:\.[0-9]+)*-sonnet)(?:-[0-9]{8})?')


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
