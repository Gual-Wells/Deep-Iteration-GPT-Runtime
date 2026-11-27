"""Apply current-user Claude selection, then derive actual collaboration duties."""
from __future__ import annotations
import re
from typing import Any, Mapping

FORMAT = 'digr-actual-collaboration-1'
SONNET_MODEL = re.compile(r'anthropic/claude-(?:sonnet-[0-9]+(?:\.[0-9]+)*|[0-9]+(?:\.[0-9]+)*-sonnet)(?:-[0-9]{8})?')
CLAUDE_MODEL = re.compile(r'(?:^|/)claude(?:[-/:]|$)', re.IGNORECASE)
COUNCIL_ONLY = 'COUNCIL_ONLY'
CLAUDE_LAYER_BY_ROLE = {'council_member': 'COUNCIL', 'consult_guidance': 'CONTENT'}
DOUBLE_COLON_LAYER_CEILINGS_USD = {'COUNCIL': 0.20, 'CONTENT': 1.00}
FOUNDATION_INTENT_PURPOSE = 'foundation_intent'
FIRST_OPINION_PURPOSE = 'first_opinion'
FIRST_OPINION_NATIVE_WORK_RETURN_PURPOSE = 'first_opinion_native_work_return'
FIRST_OPINION_CEILING_USD = 0.20
FIRST_OPINION_OUTPUT_TOKENS = 16_000
_PIN_VERSION = re.compile(r'(\d+)\.(\d+)\.(\d+)@[0-9a-f]{40}')


def _since(p_run: str, introduced: tuple[int, int, int]) -> bool:
    matched = _PIN_VERSION.fullmatch(p_run)
    return bool(matched and tuple(map(int, matched.groups())) >= introduced)


def council_enabled(p_run: str) -> bool:
    return _since(p_run, (0, 16, 0))


def delimiter_policy(p_run: str) -> bool:
    return _since(p_run, (0, 15, 0))


def layered_policy(p_run: str) -> bool:
    return _since(p_run, (1, 0, 0))


def first_opinion_policy(p_run: str) -> bool:
    return _since(p_run, (1, 2, 0))


def double_colon_layer_budget_policy(p_run: str) -> bool:
    return _since(p_run, (1, 2, 1))


def standing_claude_budget_policy(p_run: str) -> bool:
    return _since(p_run, (1, 3, 0))


def native_work_policy(p_run: str) -> bool:
    return _since(p_run, (1, 3, 0))


def foundation_intent_policy(p_run: str) -> bool:
    return _since(p_run, (1, 7, 0))


def require_first_opinion_permission(lifecycle: Mapping[str, Any]) -> None:
    if not first_opinion_policy(lifecycle['P_run']):
        raise ValueError('The first-opinion opportunity requires a frozen Codex 1.2.0+ task')
    if lifecycle.get('claude_policy', {}).get('mode') != COUNCIL_ONLY:
        raise ValueError('The first-opinion opportunity requires the current single-colon choice')


def allowed_selections(p_run: str) -> set[str]:
    return {'ALLOW', 'DENY', COUNCIL_ONLY} if layered_policy(p_run) else {'ALLOW', 'DENY'}


def require_council_permission(lifecycle: Mapping[str, Any]) -> None:
    mode = lifecycle.get('claude_policy', {}).get('mode')
    if mode == 'ALLOW' or (layered_policy(lifecycle['P_run']) and mode == COUNCIL_ONLY):
        return
    raise ValueError('Claude council members are disabled by the current task choice; native council remains usable')


def require_claude_permission(p_run: str, model: str, lifecycle: Mapping[str, Any], *,
                              participation_role: str = 'consult_guidance') -> None:
    """No credentials, reservations or transport before a current allow choice.

    Local source-bound records are not user authentication. Send admission
    also checks the budget policy of the frozen task.
    """
    if layered_policy(p_run):
        if participation_role == 'council_member':
            require_council_permission(lifecycle)
            if lifecycle['claude_policy']['mode'] == COUNCIL_ONLY and not CLAUDE_MODEL.search(model):
                raise ValueError('The council-only wallet grant covers Claude members')
        elif participation_role != 'consult_guidance' or lifecycle.get('claude_policy', {}).get('mode') != 'ALLOW':
            raise ValueError('Formal content participation requires the current two-layer DIGR:: choice')
        if standing_claude_budget_policy(p_run) and not re.fullmatch(r'anthropic/claude-[a-z0-9][a-z0-9._:-]*', model):
            raise ValueError('Standing layer authority covers configured Anthropic Claude models')
    elif delimiter_policy(p_run) and CLAUDE_MODEL.search(model):
        if lifecycle.get('claude_policy', {}).get('mode') != 'ALLOW':
            raise ValueError('Claude is disabled by the current task choice; DIGR:: permits Claude, DIGR: does not')


def unified(p_run: str) -> bool:
    return _since(p_run, (0, 14, 0))


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
    if layered_policy(p_run):
        result['claude_layer'] = CLAUDE_LAYER_BY_ROLE[participation_role]
    return result
