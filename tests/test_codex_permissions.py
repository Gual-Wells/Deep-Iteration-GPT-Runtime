from __future__ import annotations

import unittest

from runtime.codex_permissions import assess_operation


class TaskAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.context = {'scope': 'Upgrade the delegated Codex project', 'authorized': True}

    def check(self, operation, **kw):
        return assess_operation(self.context, operation, within_task=True, **kw)

    def test_routine_work_continues_under_existing_task_authorization(self):
        result = self.check('push', capability='AVAILABLE')
        self.assertEqual(result['next_action'], 'PROCEED_WITHIN_TASK')
        self.assertFalse(result['host_permissions_changed'])
        self.assertFalse(result['operation_executed'])

    def test_capability_is_separate_from_authorization(self):
        result = self.check('delegate', capability='UNAVAILABLE')
        self.assertEqual(result['authorization'], 'AUTHORIZED')
        self.assertEqual(result['next_action'], 'CAPABILITY_UNAVAILABLE')

    def test_task_grant_does_not_expand_to_another_goal(self):
        result = assess_operation(self.context, 'write', within_task=False)
        self.assertEqual(result['next_action'], 'ESTABLISH_NEW_SCOPE')

    def test_stop_is_not_removed_by_specific_grant(self):
        self.context.update(stopped=True, grants={'deploy': 'user request'})
        self.assertEqual(self.check('deploy')['next_action'], 'STOP')

    def test_specific_grant_allows_already_authorized_external_action(self):
        self.assertEqual(self.check('message_external')['next_action'], 'NEED_SPECIFIC_AUTHORIZATION')
        self.context['grants'] = {'message_external': 'User explicitly requested this message'}
        self.assertEqual(self.check('message_external', capability='AVAILABLE')['next_action'], 'PROCEED_WITHIN_TASK')

    def test_api_authorization_persists_but_unknown_budget_is_not_spent(self):
        self.context['grants'] = {'paid_api': 'Reuse this project API allocation'}
        result = self.check('paid_api', capability='AVAILABLE')
        self.assertEqual(result['authorization'], 'AUTHORIZED')
        self.assertEqual(result['next_action'], 'VERIFY_COST_AND_BUDGET')
        self.context['budget'] = {'remaining': 2.0, 'checked_at': 'observed-now'}
        self.assertEqual(self.check('paid_api', estimated_cost=3)['next_action'], 'BUDGET_EXCEEDED')
        self.assertEqual(self.check('paid_api', capability='AVAILABLE', estimated_cost=.5)['next_action'], 'PROCEED_WITHIN_TASK')

    def test_availability_cannot_create_authorization(self):
        self.context['authorized'] = False
        self.assertEqual(self.check('write', capability='AVAILABLE')['authorization'], 'NOT_ESTABLISHED')

    def test_invalid_budget_and_cost_do_not_become_permission(self):
        self.context.update(grants={'paid_api': 'existing allocation'}, budget={'remaining': True, 'checked_at': 'now'})
        self.assertEqual(self.check('paid_api', estimated_cost=1)['next_action'], 'VERIFY_COST_AND_BUDGET')
        for cost in (True, -1, float('nan'), float('inf')):
            with self.subTest(cost=cost), self.assertRaises(ValueError):
                self.check('paid_api', estimated_cost=cost)
