from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from runtime.codex_session import create_session
from runtime.codex_usage import (build_usage_report, collect_usage, normalize_tokens,
                                record_rate_limits, render_usage_markdown)

ROOT = Path(__file__).resolve().parents[1]
PIN = '0.15.0@' + 'a' * 40


def tokens(input=100, cached=80, output=20, reasoning=10):
    return {'input_tokens': input, 'cached_input_tokens': cached,
            'cache_write_input_tokens': 0, 'output_tokens': output,
            'reasoning_output_tokens': reasoning, 'total_tokens': input + output}


def native(kind, payload, at):
    return {'timestamp': '2026-11-18T06:' + at + '+00:00', 'type': kind, 'payload': payload}


def rates(used, reset=1794985200, minutes=300, plan='plus'):
    return {'limit_id': 'codex', 'plan_type': plan,
            'primary': {'used_percent': used, 'window_minutes': minutes, 'resets_at': reset}}


class UsageTests(unittest.TestCase):
    def setUp(self):
        cache = Path(os.environ.get('DIGR_TEST_TEMP', ROOT / '.cache'))
        cache.mkdir(exist_ok=True, parents=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache, prefix='usage-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        request = self.base / 'request.txt'
        request.write_text('DIGR：计量测试。', encoding='utf-8')
        self.task = self.base / 'task'
        create_session(self.task, request=request, p_run=PIN)
        self.rollout = self.base / 'rollout.jsonl'

    def write(self, events):
        self.rollout.write_text(''.join(json.dumps(event) + '\n' for event in events), encoding='utf-8')

    def context(self, turn='new', effort='max', at='10:00'):
        return native('turn_context', {'turn_id': turn, 'model': 'gpt-6.1-sol', 'effort': effort}, at)

    def response(self, response='r2', turn='new', at='10:01', amount=None, cumulative=None):
        return native('token_usage_record', {'thread_id': 'root', 'turn_id': turn,
            'response_id': response, 'usage': amount or tokens(),
            'thread_token_usage': cumulative or tokens()}, at)

    def count(self, at='10:02', total=None, last=None, quota=None):
        return native('event_msg', {'type': 'token_count', 'info': {
            'total_token_usage': total or tokens(), 'last_token_usage': last or tokens(),
            'last_usage_includes_reasoning': True}, 'rate_limits': quota}, at)

    def test_native_response_and_cumulative_aliases_reimports_and_old_task(self):
        self.write([native('session_meta', {'id': 'root'}, '00:00'),
            self.context('old', 'high', '00:00'),
            self.response('old-r', 'old', '00:01', tokens(200, 150, 40, 20)),
            self.count('00:02', total=tokens(200, 150, 40, 20)),
            self.context(), self.response(cumulative=tokens(300, 230, 60, 30)), self.count(total=tokens(300, 230, 60, 30))])
        first = collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        second = collect_usage(self.task, self.rollout, actor='another-label', turn_ids=['new'])
        self.assertEqual(first['new_events'], 1)
        self.assertEqual(second['new_events'], 0)
        report = build_usage_report(self.task)
        self.assertEqual(report['native']['responses'], 1)
        group = report['native']['groups'][0]
        self.assertEqual(group['tokens']['total_tokens'], 120)
        self.assertEqual(group['effort'], 'max')
        self.assertIsNone(group['speed'])

    def test_real_host_ordinal_prefix_does_not_hide_aggregate_events(self):
        context, response = self.context(), self.response()
        # The actual desktop rollout inserts ordinal between timestamp/type.
        context = {'timestamp': context['timestamp'], 'ordinal': 9, 'type': context['type'], 'payload': context['payload']}
        response = {'timestamp': response['timestamp'], 'ordinal': 12, 'type': response['type'], 'payload': response['payload']}
        self.write([context, response])
        result = collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        self.assertEqual(result['events_total'], 1)

    def test_content_never_persisted_and_explicit_task_boundary_required(self):
        self.write([self.context(), native('response_item', {'type': 'reasoning',
            'content': 'SECRET_HIDDEN_CONTENT'}, '10:01'),
            native('event_msg', {'type': 'agent_message', 'message': 'PRIVATE_BODY'}, '10:01'),
            self.response()])
        with self.assertRaisesRegex(ValueError, 'task start/turn/token baseline'):
            collect_usage(self.task, self.rollout, actor='Main')
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        persisted = (self.task / 'usage' / 'observations.json').read_text(encoding='utf-8')
        self.assertNotIn('SECRET_HIDDEN_CONTENT', persisted)
        self.assertNotIn('PRIVATE_BODY', persisted)
        self.assertNotIn('response_item', persisted)

    def test_cached_and_reasoning_subsets_are_not_added_twice(self):
        normal = normalize_tokens(tokens())
        self.assertEqual(normal['total_tokens'], 120)
        self.write([self.context('one', 'low'), self.response('a', 'one', '10:01'),
            self.context('two', 'max', '11:00'), self.response('b', 'two', '11:01')])
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['one', 'two'])
        groups = build_usage_report(self.task)['native']['groups']
        self.assertEqual([group['proxy_share_percent'] for group in groups], [50, 50])
        with self.assertRaisesRegex(ValueError, 'subset'):
            normalize_tokens(tokens(10, 11))
        with self.assertRaisesRegex(ValueError, 'subset'):
            normalize_tokens(tokens(output=5, reasoning=10))

    def test_legacy_cumulative_notices_deduplicate_and_upgrade_to_responses(self):
        first = [self.context(), self.count('10:01'),
                 self.count('10:02', total=tokens(200, 160, 40, 20)),
                 self.count('10:03', total=tokens(200, 160, 40, 20))]
        self.write(first)
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        self.assertEqual(build_usage_report(self.task)['native']['responses'], 2)
        self.write(first + [self.response('a', at='10:01'),
                            self.response('b', at='10:02', cumulative=tokens(200, 160, 40, 20))])
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        report = build_usage_report(self.task)
        self.assertEqual(report['native']['responses'], 2)
        self.assertEqual(report['native']['groups'][0]['tokens']['total_tokens'], 240)

    def test_different_agent_response_keys_and_models(self):
        self.write([self.context(), self.response()])
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        self.write([native('turn_context', {'turn_id': 'child-turn', 'model': 'gpt-6.2-astra', 'effort': 'high'}, '10:00'),
                    native('token_usage_record', {'thread_id': 'child', 'turn_id': 'child-turn',
                       'response_id': 'r2', 'usage': tokens()}, '10:01')])
        collect_usage(self.task, self.rollout, actor='D', turn_ids=['child-turn'])
        report = build_usage_report(self.task)
        self.assertEqual(report['native']['responses'], 2)
        groups = report['native']['groups']
        self.assertAlmostEqual(sum(group['proxy_share_percent'] for group in groups), 100)
        self.assertNotEqual(groups[0]['proxy_share_percent'], groups[1]['proxy_share_percent'])

    def test_plan_change_slot_move_reset_and_small_marker_jitter(self):
        self.write([self.context(), self.count('10:01', quota=rates(10)),
            self.count('10:02', quota=rates(12, 1794985204)),
            self.count('10:03', quota=rates(0, 1795587517, 10080, 'prolite')),
            self.count('10:04', quota=rates(1, 1795587517, 10080, 'prolite')),
            self.count('10:05', quota=rates(0, 1796192317, 10080, 'prolite')),
            self.count('10:06', quota=rates(2, 1796192317, 10080, 'prolite'))])
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        windows = build_usage_report(self.task)['native']['account_windows']
        self.assertEqual([window['account_delta_pp'] for window in windows], [2, 1, 2])
        self.assertEqual(windows[-1]['segment_reason'], 'usage_decreased_reset_or_adjustment')
        self.assertTrue(all(window['task_interval_pp_approx'] is None for window in windows))
        self.assertTrue(all(window['task_interval_pp_upper_bound'] is None for window in windows))

    def test_zero_and_missing_baseline_do_not_become_zero_consumption_or_upper_bound(self):
        self.write([self.context(), self.count('10:01', quota=rates(0)), self.count('10:02', quota=rates(0))])
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        report = build_usage_report(self.task, account_activity='primary_task')
        window = report['native']['account_windows'][0]
        self.assertEqual(window['account_delta_pp'], 0)
        self.assertIsNone(window['task_interval_pp_approx'])
        self.assertIsNone(window['task_interval_pp_upper_bound'])
        self.assertIn('读数未变化', render_usage_markdown(report))

    def test_snapshot_multi_bucket_does_not_add_compatibility_alias(self):
        bucket = {'limitId': 'codex', 'primary': {'usedPercent': 10,
                    'windowDurationMins': 300, 'resetsAt': 1794985200}}
        data = {'result': {'rateLimits': bucket, 'rateLimitsByLimitId': {'codex': bucket}}}
        record_rate_limits(self.task, data, observed_at='2026-11-18T06:10:00Z', baseline=True)
        windows = build_usage_report(self.task)['native']['account_windows']
        self.assertEqual(len(windows), 1)
        self.assertIsNone(windows[0]['account_delta_pp'])

    def test_token_baseline_and_time_end_exclude_old_and_future_events(self):
        self.write([self.context(), self.response('old', at='10:01', cumulative=tokens()),
            self.count('10:02'), self.response('included', at='10:03', cumulative=tokens(200, 160, 40, 20)),
            self.count('10:04', total=tokens(200, 160, 40, 20)),
            self.response('future', at='10:05', cumulative=tokens(300, 240, 60, 30))])
        collect_usage(self.task, self.rollout, actor='Main', token_baseline=tokens(), end='2026-11-18T06:10:04Z')
        self.assertEqual(build_usage_report(self.task)['native']['responses'], 1)

    def test_unknown_model_still_returns_measured_task_share(self):
        self.write([native('turn_context', {'turn_id': 'new', 'model': 'unknown-model', 'effort': 'high'}, '10:00'), self.response()])
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        group = build_usage_report(self.task)['native']['groups'][0]
        self.assertEqual(group['measured_token_share_percent'], 100)
        self.assertIsNone(group['proxy_share_percent'])

    def test_claude_observed_settled_unknown_and_identity_are_separate(self):
        attempts = [
            {'billing_status': 'KNOWN', 'known_cost_usd': .2, 'reconciled_at': 'actual-readback'},
            {'billing_status': 'KNOWN', 'known_cost_usd': .1},
            {'billing_status': 'UNKNOWN', 'reserved_usd': .3, 'estimated_cost_usd': .05,
             'participation_role': 'council_member', 'council_scope': {'member_id': 'V1', 'cycle_id': 'c1', 'round_id': 'r1'}},
            {'billing_status': 'NOT_ATTEMPTED', 'reserved_usd': 0},
        ]
        for index, attempt in enumerate(attempts):
            folder = self.task / 'consult' / 'exchanges' / str(index)
            folder.mkdir(parents=True)
            (folder / 'attempt.json').write_text(json.dumps(attempt), encoding='utf-8')
        cost = build_usage_report(self.task)['claude']
        self.assertEqual(cost['settled_usd'], .2)
        self.assertEqual(cost['observed_usd'], .1)
        self.assertEqual(cost['unresolved_reserved_usd'], .3)
        self.assertEqual(cost['estimated_usd'], .05)
        self.assertEqual(cost['not_attempted'], 1)
        self.assertEqual(cost['attempts'][2]['member_id'], 'V1')

    def test_unknown_data_and_standalone_cli(self):
        report = build_usage_report(self.task)
        self.assertEqual(report['native']['groups'], [])
        self.assertIn('未知', render_usage_markdown(report))
        process = subprocess.run([sys.executable, str(ROOT / 'tools' / 'codex_usage.py'),
            'report', '--root', str(self.task)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)['native']['responses'], 0)

    def test_shared_wallet_phantom_and_attempt_reservation_count_once(self):
        folder = self.task / 'consult' / 'exchanges' / 'same'
        folder.mkdir(parents=True)
        (folder / 'attempt.json').write_text(json.dumps({'exchange_id': 'same',
            'billing_status': 'UNKNOWN', 'reserved_usd': .3}), encoding='utf-8')
        claims = [
            {'claim_id': 'one', 'exchange_id': 'same', 'state': 'COMMITTED', 'reserved_usd': .3},
            {'claim_id': 'two', 'exchange_id': 'phantom', 'state': 'RESERVED', 'reserved_usd': .4},
            {'claim_id': 'three', 'exchange_id': 'known', 'state': 'KNOWN', 'known_cost_usd': .2},
        ]
        with patch('runtime.codex_wallet.inspect_task', return_value={'status': 'READ', 'claims': claims}):
            report = build_usage_report(self.task)
        cost = report['claude']
        self.assertAlmostEqual(cost['unresolved_reserved_usd'], .7)
        self.assertEqual(cost['observed_usd'], .2)
        self.assertEqual(cost['unknown_attempts'], 2)
        self.assertEqual(len(cost['attempts']), 3)

    def test_claude_estimate_uses_actual_aggregate_and_named_price_bounds(self):
        folder = self.task / 'consult' / 'exchanges' / 'estimated'
        folder.mkdir(parents=True)
        (folder / 'attempt.json').write_text(json.dumps({'billing_status': 'UNKNOWN',
            'reserved_usd': .03, 'usage': {'prompt_tokens': 1000, 'completion_tokens': 200,
                'completion_tokens_details': {'reasoning_tokens': 100}},
            'budget_facts': {'prompt_usd_per_million': 4, 'completion_usd_per_million': 20,
                             'request_usd': 0}}), encoding='utf-8')
        cost = build_usage_report(self.task)['claude']
        self.assertAlmostEqual(cost['estimated_usd'], .008)
        self.assertEqual(cost['unresolved_reserved_usd'], .03)
        self.assertIn('unit-price bounds', cost['attempts'][0]['estimate_basis'])

    def test_task_pp_is_explicit_assumption_and_uses_interval_groups(self):
        self.write([self.context('outside', 'low', '09:00'), self.response('a', 'outside', '09:01'),
            self.context(), self.count('10:01', quota=rates(10)), self.response('b', at='10:02'),
            self.count('10:03', quota=rates(12))])
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['outside', 'new'], limit_ids=['codex'])
        report = build_usage_report(self.task, account_activity='primary_task')
        window = report['native']['account_windows'][0]
        self.assertEqual(window['task_interval_pp_approx'], 2)
        self.assertEqual(window['attribution'], 'primary_task_assumption')
        self.assertEqual([group['effort'] for group in window['groups']], ['max'])
        self.assertAlmostEqual(window['groups'][0]['allocated_pp_approx'], 2)

    def test_partial_exact_reimport_preserves_uncovered_cumulative_usage(self):
        stream = [self.context(), self.count('10:01'),
                  self.count('10:02', total=tokens(200, 160, 40, 20))]
        self.write(stream)
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        before = build_usage_report(self.task)
        self.write(stream + [self.response('only-first', at='10:01')])
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        after = build_usage_report(self.task)
        self.assertEqual(sum(group['tokens']['total_tokens'] for group in before['native']['groups']), 240)
        self.assertEqual(sum(group['tokens']['total_tokens'] for group in after['native']['groups']), 240)
        projection = json.loads((self.task / 'usage' / 'observations.json').read_text(encoding='utf-8'))
        self.assertEqual(len(projection['observations']), 3)
        self.assertEqual(len(projection['events']), 2)

    def test_start_inside_cumulative_interval_marks_gap_and_last_assumption(self):
        self.write([self.context(), self.count('10:00'),
            self.count('10:06', total=tokens(600, 480, 120, 60), last=tokens())])
        collect_usage(self.task, self.rollout, actor='Main', start='2026-11-18T06:10:05Z')
        report = build_usage_report(self.task)
        self.assertEqual(sum(group['tokens']['total_tokens'] for group in report['native']['groups']), 120)
        gap = report['native']['coverage_gaps'][0]
        self.assertEqual(gap['interval_tokens'], 600)
        self.assertEqual(gap['unattributed_interval_tokens'], 480)
        self.assertEqual(report['native']['attribution_assumed_records'], 1)
        self.assertIn('归因缺口', render_usage_markdown(report))

    def test_pp_allocation_requires_same_account_and_known_bucket(self):
        for account, thread, model in [('A', 'thread-A', 'gpt-6.1-sol'),
                                      ('B', 'thread-B', 'gpt-6.2-astra')]:
            self.write([native('session_meta', {'id': thread}, '00:00'),
                        native('turn_context', {'turn_id': 'new', 'model': model, 'effort': 'high'}, '10:00'),
                        native('token_usage_record', {'thread_id': thread, 'turn_id': 'new',
                            'response_id': 'r', 'usage': tokens(), 'thread_token_usage': tokens()}, '10:01')])
            collect_usage(self.task, self.rollout, actor=account, turn_ids=['new'],
                          account=account, limit_ids=['codex'])
            record_rate_limits(self.task, rates(10), observed_at='2026-11-18T06:10:00Z', account=account, baseline=True)
            record_rate_limits(self.task, rates(12), observed_at='2026-11-18T06:10:02Z', account=account)
            # A different metered bucket does not acquire this model's usage.
            other = {'limit_id': 'other', **{key: value for key, value in rates(10).items() if key != 'limit_id'}}
            record_rate_limits(self.task, other, observed_at='2026-11-18T06:10:00Z', account=account, baseline=True)
            other['primary']['used_percent'] = 12
            record_rate_limits(self.task, other, observed_at='2026-11-18T06:10:02Z', account=account)
        report = build_usage_report(self.task, account_activity='exclusive')
        for window in report['native']['account_windows']:
            if window['limit_id'] == 'other':
                self.assertEqual(window['groups'], [])
            else:
                self.assertEqual(len(window['groups']), 1)
                group = window['groups'][0]
                self.assertEqual(group['actors'], [window['account']])
                self.assertEqual(group['allocated_pp_approx'], 2)

    def test_missing_bucket_eligibility_is_not_inferred_from_a_single_window(self):
        self.write([self.context(), self.response()])
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        record_rate_limits(self.task, rates(10), observed_at='2026-11-18T06:10:00Z', baseline=True)
        record_rate_limits(self.task, rates(12), observed_at='2026-11-18T06:10:02Z')
        window = build_usage_report(self.task, account_activity='exclusive')['native']['account_windows'][0]
        self.assertEqual(window['groups'], [])
        self.assertEqual(window['unassigned_bucket_records'], 1)

    def test_payload_model_corrects_context_guess_and_equal_strength_conflict_is_unknown(self):
        self.write([self.context(), self.response()])
        collect_usage(self.task, self.rollout, actor='unidentified', turn_ids=['new'])
        actual = self.response()
        actual['payload']['model'] = 'gpt-6.2-astra'
        self.write([self.context(), actual])
        collect_usage(self.task, self.rollout, actor='actual-D', turn_ids=['new'])
        report = build_usage_report(self.task)
        self.assertEqual(report['native']['groups'][0]['model'], 'gpt-6.2-astra')
        self.assertIn('actual-D', report['native']['groups'][0]['actors'])
        contradictory = self.response()
        contradictory['payload']['model'] = 'gpt-6-astra'
        self.write([self.context(), contradictory])
        collect_usage(self.task, self.rollout, actor='actual-D', turn_ids=['new'])
        report = build_usage_report(self.task)
        self.assertIsNone(report['native']['groups'][0]['model'])
        self.assertIsNone(report['native']['groups'][0]['proxy_share_percent'])
        self.assertTrue(any('contradictory equally strong model' in notice for notice in report['native']['notices']))

    def test_partial_counter_overlap_preserves_scalar_total_without_inventing_categories(self):
        self.write([self.context(), self.count('10:01', total=tokens(100, 0, 0, 0), last=tokens(100, 0, 0, 0)),
            self.response('middle', at='10:01.5', amount=tokens(100, 0, 0, 0), cumulative=tokens(150, 0, 0, 0)),
            self.count('10:02', total=tokens(200, 0, 0, 0), last=tokens(100, 0, 0, 0))])
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        report = build_usage_report(self.task)
        groups = report['native']['groups']
        self.assertEqual(sum(group['tokens']['total_tokens'] for group in groups), 200)
        self.assertTrue(any(group['tokens']['input_tokens'] is None for group in groups))
        self.assertTrue(all(group['proxy_share_percent'] is None for group in groups))
        self.assertTrue(any('residual retained' in notice for notice in report['native']['notices']))

    def test_rerouted_interval_residual_does_not_inherit_its_last_model(self):
        zero = tokens(0, 0, 0, 0)
        self.write([self.context(), self.count('10:00', total=zero, last=zero),
            {'timestamp': '2026-11-18T06:10:02Z', 'method': 'model/rerouted',
             'params': {'threadId': 'root', 'turnId': 'new', 'toModel': 'gpt-6.2-astra'}},
            self.count('10:03', total=tokens(200, 0, 0, 0), last=tokens(100, 0, 0, 0)),
            self.response('last', at='10:03', amount=tokens(100, 0, 0, 0), cumulative=tokens(200, 0, 0, 0))])
        collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        groups = build_usage_report(self.task)['native']['groups']
        actual = {group['model']: group['tokens']['total_tokens'] for group in groups}
        self.assertEqual(actual, {None: 100, 'gpt-6.2-astra': 100})
        self.assertTrue(all(group['proxy_share_percent'] is None for group in groups))

    def test_equal_strength_bucket_conflict_survives_repeating_one_side(self):
        for eligible in (['codex'], ['other'], ['codex']):
            response = self.response()
            response['payload']['metered_limit_ids'] = eligible
            self.write([self.context(), response])
            collect_usage(self.task, self.rollout, actor='Main', turn_ids=['new'])
        record_rate_limits(self.task, rates(10), observed_at='2026-11-18T06:10:00Z', baseline=True)
        record_rate_limits(self.task, rates(12), observed_at='2026-11-18T06:10:02Z')
        report = build_usage_report(self.task, account_activity='exclusive')
        self.assertEqual(report['native']['account_windows'][0]['groups'], [])
        projection = json.loads((self.task / 'usage' / 'observations.json').read_text(encoding='utf-8'))
        exact = next(row for row in projection['observations'].values() if row['basis'] == 'native_response_aggregate')
        self.assertIsNone(exact['metered_limit_ids'])
        self.assertTrue(exact['metered_limit_conflict'])
        self.assertEqual({tuple(item['ids']) for item in exact['metered_limit_candidates']}, {('codex',), ('other',)})


if __name__ == '__main__':
    unittest.main()
