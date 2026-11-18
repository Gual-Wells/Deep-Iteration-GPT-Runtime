import json
from pathlib import Path
import tempfile
import unittest

from runtime.codex_session import create_session
from runtime.codex_usage import build_usage_report, collect_usage
from tests.test_codex_usage import native, tokens


class TurnScopedUsageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='turn-usage-')
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        request = base / 'request.txt'
        request.write_text('DIGR: synthetic accounting replay', encoding='utf-8')
        self.task = base / 'task'
        create_session(self.task, request=request, p_run='0.17.0@' + 'a' * 40)
        self.rollout = base / 'rollout.jsonl'
        self.projection = self.task / 'usage/observations.json'

    def collect(self, rows, *turns, actor='Main'):
        self.rollout.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
        collect_usage(self.task, self.rollout, actor=actor, turn_ids=list(turns))
        return build_usage_report(self.task)['native']

    def context(self, thread, turn, at, model='gpt-6.1-sol', effort='max', speed='standard'):
        return native('turn_context', {'thread_id': thread, 'turn_id': turn,
                      'model': model, 'effort': effort, 'service_tier': speed}, at)

    def response(self, thread, turn, response, at, *, amount=None, cumulative=None, **labels):
        return native('token_usage_record', {'thread_id': thread, 'turn_id': turn,
                      'response_id': response, 'usage': amount or tokens(),
                      'thread_token_usage': cumulative or amount or tokens(), **labels}, at)

    def count(self, thread, turn, at, *, total, last):
        return native('event_msg', {'type': 'token_count', 'thread_id': thread,
                      'turn_id': turn, 'info': {'total_token_usage': total, 'last_token_usage': last}}, at)

    def reroute(self, thread, turn, at, model='gpt-6.2-astra'):
        return {'timestamp': f'2026-11-18T06:{at}Z', 'method': 'model/rerouted',
                'params': {'threadId': thread, 'turnId': turn, 'toModel': model}}

    def observations(self):
        return list(json.loads(self.projection.read_text(encoding='utf-8'))['observations'].values())

    def test_old_turn_alias_and_reroute_are_detached_from_new_turn_and_counter(self):
        old, new = tokens(), tokens(200, 160, 40, 20)
        value = self.collect([
            self.context('thread', 'old', '10:00'),
            self.count('thread', 'old', '10:01', total=old, last=old),
            self.context('thread', 'new', '10:02', 'gpt-6.2-sol', 'high', 'fast'),
            self.count('thread', 'new', '10:03', total=new, last=old),
            self.response('thread', 'old', 'old-late', '10:04'),
            self.reroute('thread', 'old', '10:05'),
            self.response('thread', 'new', 'new-late', '10:06', cumulative=new),
        ], 'old', 'new')
        self.assertEqual(value['responses'], 2)
        self.assertEqual({(group['model'], group['effort'], group['speed']): group['tokens']['total_tokens']
                          for group in value['groups']},
                         {('gpt-6.1-sol', 'max', 'standard'): 120, ('gpt-6.2-sol', 'high', 'fast'): 120})
        self.assertEqual({row['counter_epoch'] for row in self.observations()}, {0})

    def test_active_interval_labels_depend_on_the_turn_named_by_a_reroute(self):
        zero, delta = tokens(0, 0, 0, 0), tokens(40, 0, 40, 10)
        for rerouted_turn, expected_model, expected_weight in (
            ('old', 'gpt-6.2-sol', 12000),
            ('active', None, None),
        ):
            with self.subTest(turn=rerouted_turn):
                value = self.collect([
                    self.context('thread', 'old', '10:00'),
                    self.context('thread', 'active', '10:01', 'gpt-6.2-sol'),
                    self.count('thread', 'active', '10:02', total=zero, last=zero),
                    self.reroute('thread', rerouted_turn, '10:03'),
                    self.count('thread', 'active', '10:04', total=delta, last=delta),
                ], 'active')
                group, = value['groups']
                self.assertEqual((group['model'], group['effort'], group['speed']),
                                 (expected_model, 'max', 'standard'))
                self.assertEqual(group['tokens']['total_tokens'], 80)
                self.assertEqual(group['weight'], expected_weight)

    def test_reopened_old_interval_detects_its_own_reroutes_even_when_endpoint_labels_agree(self):
        zero, delta = tokens(0, 0, 0, 0), tokens(40, 0, 40, 10)
        value = self.collect([
            self.context('thread', 'old', '10:00'),
            self.count('thread', 'old', '10:01', total=zero, last=zero),
            self.context('thread', 'active', '10:02', 'gpt-6.2-sol'),
            self.reroute('thread', 'old', '10:03'),
            self.reroute('thread', 'old', '10:04', 'gpt-6.1-sol'),
            self.count('thread', 'old', '10:05', total=delta, last=delta),
        ], 'old')
        group, = value['groups']
        self.assertIsNone(group['model'])
        self.assertEqual(group['tokens']['total_tokens'], 80)
        self.assertEqual((group['effort'], group['speed']), ('max', 'standard'))

    def test_cumulative_span_across_turns_still_checks_intermediate_model_changes(self):
        zero, delta = tokens(0, 0, 0, 0), tokens(40, 0, 40, 10)
        value = self.collect([
            self.context('thread', 'first', '10:00'),
            self.count('thread', 'first', '10:01', total=zero, last=zero),
            self.context('thread', 'between', '10:02', 'gpt-6.2-astra'),
            self.context('thread', 'last', '10:03'),
            self.count('thread', 'last', '10:04', total=delta, last=delta),
        ], 'first', 'between', 'last')
        group, = value['groups']
        self.assertIsNone(group['model'])
        self.assertEqual(group['tokens']['total_tokens'], 80)
        self.assertEqual((group['effort'], group['speed']), ('max', 'standard'))

    def test_late_old_response_field_conflict_does_not_taint_the_active_interval(self):
        zero, old, interval = tokens(0, 0, 0, 0), tokens(), tokens(40, 0, 40, 10)
        combined = tokens(140, 80, 60, 20)
        value = self.collect([
            self.context('thread', 'old', '10:00'),
            self.context('thread', 'active', '10:01', 'gpt-6.2-sol'),
            self.count('thread', 'active', '10:02', total=old, last=zero),
            self.response('thread', 'old', 'late', '10:03', model='gpt-6.2-astra', speed='fast'),
            self.count('thread', 'active', '10:04', total=combined, last=interval),
        ], 'active')
        group, = value['groups']
        self.assertEqual((group['model'], group['effort'], group['speed']), ('gpt-6.2-sol', 'max', 'standard'))
        self.assertEqual(group['tokens']['total_tokens'], 80)
        self.assertEqual(group['weight'], 12000)

    def test_overlapping_turn_ids_use_their_own_thread_and_unseen_turn_is_unknown(self):
        self.collect([
            self.context('a', 'shared', '10:00'),
            self.context('b', 'shared', '10:01', 'gpt-6.2-sol', 'high', 'fast'),
            self.response('a', 'shared', 'same-response-id', '10:02'),
            self.response('b', 'shared', 'same-response-id', '10:03'),
            self.response('a', 'unseen', 'another-response', '10:04', cumulative=tokens(200, 160, 40, 20)),
        ], 'shared', 'unseen')
        self.assertEqual({(row['thread_id'], row['turn_id']): (row['model'], row['effort'], row['speed'])
                          for row in self.observations()},
                         {('a', 'shared'): ('gpt-6.1-sol', 'max', 'standard'),
                          ('b', 'shared'): ('gpt-6.2-sol', 'high', 'fast'),
                          ('a', 'unseen'): (None, None, None)})

    def test_payload_labels_outrank_reroute_and_stay_stronger_on_reimport(self):
        envelope = self.response('a', 't', 'r', '10:02', model='gpt-6.2-sol',
                                 reasoningEffort='high', serviceTier='fast')
        envelope['type'] = 'event_msg'
        envelope['payload'] = {'type': 'token_usage_record', **envelope['payload']}
        start = [self.context('a', 't', '10:00'), self.reroute('a', 't', '10:01')]
        self.collect(start + [envelope], 't')
        self.collect(start[::-1] + [self.response('a', 't', 'r', '10:02')], 't', actor='D')
        row, = self.observations()
        self.assertEqual((row['model'], row['effort'], row['speed']), ('gpt-6.2-sol', 'high', 'fast'))
        for field in ('model', 'effort', 'speed'):
            self.assertEqual(row['metadata_sources'][field]['basis'], 'response_payload')
        self.assertEqual(row['actors'], ['D', 'Main'])

    def test_same_source_reimport_corrects_legacy_misattribution_without_changing_tokens(self):
        trace = [self.context('a', 'old', '10:00'),
                 self.context('a', 'new', '10:01', 'gpt-6.2-sol', 'high', 'fast'),
                 self.response('a', 'old', 'r', '10:02')]
        self.collect(trace, 'old')
        ledger = json.loads(self.projection.read_text(encoding='utf-8'))
        event_id, = ledger['observations']
        legacy = ledger['observations'][event_id]
        del legacy['label_scope']
        legacy.update(model='gpt-6.2-sol', effort='high', speed='fast', metadata_candidates={
            key: [{'value': value, 'rank': 2}]
            for key, value in {'model': 'gpt-6.2-sol', 'effort': 'high', 'speed': 'fast'}.items()
        })
        ledger['events'][event_id] = legacy
        self.projection.write_text(json.dumps(ledger), encoding='utf-8')
        value = self.collect(trace, 'old', actor='D')
        row, = self.observations()
        self.assertEqual(row['event_id'], event_id)
        self.assertEqual(row['actors'], ['D', 'Main'])
        self.assertEqual((row['model'], row['effort'], row['speed']), ('gpt-6.1-sol', 'max', 'standard'))
        self.assertEqual(value['groups'][0]['tokens']['total_tokens'], 120)

    def test_multiple_exact_records_and_uncovered_tail_conserve_tokens(self):
        zero = tokens(0, 0, 0, 0)
        total = tokens(300, 240, 60, 30)
        value = self.collect([
            self.context('a', 't', '10:00'),
            self.count('a', 't', '10:01', total=zero, last=zero),
            self.response('a', 't', 'r1', '10:02'),
            self.response('a', 't', 'r2', '10:03', cumulative=tokens(200, 160, 40, 20)),
            self.count('a', 't', '10:04', total=total, last=tokens()),
        ], 't')
        self.assertEqual(value['responses'], 3)
        self.assertEqual(value['groups'][0]['tokens']['total_tokens'], 360)
        self.assertEqual(value['groups'][0]['tokens']['cached_input_tokens'], 240)

    def test_reimport_deduplicates_a_response_when_only_later_rows_make_thread_known(self):
        context = self.context('a', 't', '10:00')
        response = self.response('a', 't', 'unbound', '10:01')
        del context['payload']['thread_id']
        del response['payload']['thread_id']
        self.collect([context, response], 't')
        value = self.collect([
            context, response,
            self.response('a', 't', 'bound', '10:02', cumulative=tokens(200, 160, 40, 20)),
        ], 't', actor='D')
        self.assertEqual(value['responses'], 2)
        self.assertEqual(value['groups'][0]['tokens']['total_tokens'], 240)
        self.assertEqual({row['thread_id'] for row in self.observations()}, {'a'})

    def test_later_explicit_model_disagreement_does_not_label_the_cumulative_residual(self):
        zero, one, total = tokens(0, 0, 0, 0), tokens(100, 0, 0, 0), tokens(200, 0, 0, 0)
        value = self.collect([
            self.context('a', 't', '10:00'),
            self.count('a', 't', '10:01', total=zero, last=zero),
            self.count('a', 't', '10:02', total=total, last=one),
            self.response('a', 't', 'late', '10:03', amount=one, cumulative=total, model='gpt-6.2-sol'),
        ], 't')
        self.assertEqual({group['model']: group['tokens']['total_tokens'] for group in value['groups']},
                         {None: 100, 'gpt-6.2-sol': 100})

    def test_conflicting_explicit_speed_keeps_totals_but_disables_the_proxy(self):
        context = self.context('a', 't', '10:00')
        self.collect([context, self.response('a', 't', 'r', '10:01', speed='fast')], 't')
        value = self.collect([context, self.response('a', 't', 'r', '10:01', speed='standard')], 't')
        group, = value['groups']
        self.assertIsNone(group['speed'])
        self.assertIsNone(group['proxy_share_percent'])
        self.assertEqual(group['measured_token_share_percent'], 100)
        self.assertEqual(group['tokens']['total_tokens'], 120)


if __name__ == '__main__':
    unittest.main()
