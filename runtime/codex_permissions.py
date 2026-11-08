"""Task-scoped authorization advice; this does not change host permissions.

The caller supplies the user's real authorization and the operation's relation
to the task. Research material, a model's own TODO, and availability flags are
not authorization sources. No operation is executed by this module.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


ROUTINE = frozenset({
    'read', 'research', 'write', 'shell', 'install', 'configure', 'repair',
    'verify', 'delegate', 'commit', 'push', 'merge', 'deploy',
})
EXPLICIT = frozenset({'purchase', 'message_external', 'irreversible_bulk_delete'})


def assess_operation(
    context: Mapping[str, Any], operation: str, *, within_task: bool,
    capability: str = 'UNKNOWN', estimated_cost: float | None = None,
) -> dict[str, Any]:
    """Separate declared authorization, available capability and next action.

    `within_task` is a semantic judgment supplied by the operator, not inferred
    from matching words or paths. A nonempty grant is the caller's reference to
    an actual user instruction, not an authenticated permission receipt.
    """
    if not isinstance(context, Mapping):
        raise TypeError('authorization context must be a mapping')
    scope = context.get('scope')
    if not isinstance(scope, str) or not scope.strip():
        raise ValueError('authorization context needs the real task scope')
    if not isinstance(operation, str) or not operation.strip():
        raise ValueError('operation must be nonempty')
    if type(within_task) is not bool:
        raise TypeError('within_task must be an explicit boolean judgment')
    if capability not in ('AVAILABLE', 'UNAVAILABLE', 'UNKNOWN'):
        raise ValueError('capability must be AVAILABLE, UNAVAILABLE or UNKNOWN')
    for key in ('authorized', 'stopped'):
        if key in context and type(context[key]) is not bool:
            raise TypeError(f'{key} must be boolean')
    grants = context.get('grants', {})
    if not isinstance(grants, Mapping) or any(
        not isinstance(k, str) or not isinstance(v, str) or not v.strip()
        for k, v in grants.items()
    ):
        raise ValueError('grants must map operation names to actual authorization references')
    if estimated_cost is not None and (
        isinstance(estimated_cost, bool) or not isinstance(estimated_cost, (int, float))
        or not 0 <= estimated_cost < float('inf')
    ):
        raise ValueError('estimated_cost must be finite and nonnegative')

    authorization, action, reason = 'NOT_ESTABLISHED', 'CHECK_SCOPE', ''
    explicit = grants.get(operation)
    if context.get('stopped', False):
        authorization, action = 'STOPPED', 'STOP'
        reason = 'The current user stop applies; no automatic resume.'
    elif not within_task:
        action, reason = 'ESTABLISH_NEW_SCOPE', 'Existing task authorization does not cover another goal.'
    elif operation in EXPLICIT and not explicit:
        action, reason = 'NEED_SPECIFIC_AUTHORIZATION', 'This operation needs its own user authorization.'
    elif not context.get('authorized', False) and not explicit:
        action, reason = 'ESTABLISH_AUTHORIZATION', 'Task authorization has not been supplied.'
    elif operation == 'paid_api':
        if not explicit:
            action, reason = 'ESTABLISH_API_SCOPE', 'Reuse the actual existing API grant; no new budget is implied.'
        else:
            authorization = 'AUTHORIZED'
            budget = context.get('budget')
            remaining = budget.get('remaining') if isinstance(budget, Mapping) else None
            valid = (
                isinstance(remaining, (int, float)) and not isinstance(remaining, bool)
                and 0 <= remaining < float('inf')
                and isinstance(budget.get('checked_at'), str) and bool(budget['checked_at'].strip())
            )
            if not valid or estimated_cost is None:
                action, reason = 'VERIFY_COST_AND_BUDGET', 'Authorization persists; current cost/budget is not established.'
            elif estimated_cost > remaining:
                action, reason = 'BUDGET_EXCEEDED', 'The estimate exceeds the supplied remaining budget.'
            else:
                action, reason = 'PROCEED_WITHIN_TASK', explicit
    elif operation in ROUTINE or explicit:
        authorization, action = 'AUTHORIZED', 'PROCEED_WITHIN_TASK'
        reason = explicit or 'The user authorized this goal and its necessary task work.'
    else:
        action, reason = 'USE_TASK_JUDGMENT', 'Classify this operation by its real scope and existing authorization.'

    if action == 'PROCEED_WITHIN_TASK' and capability != 'AVAILABLE':
        action = 'RESOLVE_CAPABILITY' if capability == 'UNKNOWN' else 'CAPABILITY_UNAVAILABLE'
    return {
        'scope': scope, 'operation': operation, 'within_task': within_task,
        'authorization': authorization, 'capability': capability,
        'next_action': action, 'basis': reason,
        'evidence_scope': 'CALLER_SUPPLIED_TASK_CONTEXT',
        'host_permissions_changed': False, 'operation_executed': False,
    }
