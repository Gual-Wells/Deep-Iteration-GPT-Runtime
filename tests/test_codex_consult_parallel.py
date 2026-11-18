from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

from runtime import codex_consult as consult, codex_wallet as wallet
from runtime.codex_lifecycle import ingest_message, handle_message
from runtime.codex_session import create_session
import test_codex_consult as fixtures

PIN = '0.16.0@' + 'f' * 40


class ParallelHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        with self.server.counter_lock:
            self.server.requests.append(request)
            if len(self.server.requests) >= self.server.expected:
                self.server.entered.set()
        self.server.first_entered.set()
        label = self.path.strip('/')
        if label == 'inspect-partial':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('X-Generation-Id', 'gen-inspect-partial')
            self.end_headers()
            first = {'id': 'gen-inspect-partial', 'model': consult.DEFAULT_MODEL,
                     'choices': [{'index': 0, 'delta': {'content': 'An actual partial public answer.\n'}}]}
            self.wfile.write(('data: ' + json.dumps(first) + '\n\n').encode())
            self.wfile.flush()
            self.server.release.wait(5)
            last = {'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}], 'usage': {'cost': .03}}
            self.wfile.write(('data: ' + json.dumps(last) + '\n\ndata: [DONE]\n\n').encode())
            self.wfile.flush()
            return
        self.server.release.wait(5)
        if label in {'deadline', 'slow-byte'}:
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('X-Generation-Id', 'gen-' + label)
            self.end_headers()
            if label == 'slow-byte':
                raw = ('data: ' + json.dumps({'id': 'gen-slow-byte', 'model': consult.DEFAULT_MODEL,
                       'choices': [{'index': 0, 'delta': {'content': 'Late public body'}}]}) + '\n\n').encode()
                try:
                    for byte in raw[:60]:
                        self.wfile.write(bytes([byte]))
                        self.wfile.flush()
                        time.sleep(.05)
                    self.wfile.write(raw[60:])
                except ConnectionError:
                    pass
                return
            for index in range(40):
                try:
                    value = {'id': 'gen-deadline', 'model': consult.DEFAULT_MODEL,
                             'choices': [{'delta': {'content': 'Part ' + str(index) + '\n'}, 'index': 0}]}
                    self.wfile.write(('data: ' + json.dumps(value) + '\n\n').encode())
                    self.wfile.flush()
                except ConnectionError:
                    break
                time.sleep(.05)
            return
        response = {'id': 'gen-' + label, 'model': consult.DEFAULT_MODEL,
            'choices': [{'finish_reason': 'stop', 'message': {'content': 'Public ' + label,
                'reasoning': fixtures.HIDDEN}}], 'usage': {'cost': .03}}
        if label == 'unknown':
            response['usage'] = {}
        raw = json.dumps(response).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('X-Generation-Id', 'gen-' + label)
        self.end_headers()
        self.wfile.write(raw)


class ParallelConsultTests(unittest.TestCase):
    file = fixtures.ConsultPublicRuntimeTests.file
    facts = fixtures.ConsultPublicRuntimeTests.facts

    def setUp(self):
        cache = fixtures.ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        import tempfile
        self.temp = tempfile.TemporaryDirectory(prefix='parallel-consult-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.env = patch.dict(os.environ, {'CODEX_HOME': str(self.folder / 'codex-home'),
                                          'DIGR_TEST_CONSULT_KEY': fixtures.SECRET})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.input = self.file('input.txt', 'Explore the actual supplied problem independently.')
        self.root = self.task('first')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), ParallelHandler)
        self.server.counter_lock = threading.Lock()
        self.server.requests = []
        self.server.expected = 1
        self.server.entered = threading.Event()
        self.server.first_entered = threading.Event()
        self.server.release = threading.Event()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def task(self, name):
        original = self.file(name + '-user.txt', 'DIGR:: Explore this synthetic localhost-only task.')
        root = self.folder / name
        create_session(root, request=original, p_run=PIN)
        return root

    def config(self, label, *, wallet_id='synthetic-shared-account'):
        value = {'endpoint': f'http://127.0.0.1:{self.server.server_port}/' + label,
                 'api_key_env': 'DIGR_TEST_CONSULT_KEY', 'timeout_seconds': 3}
        if wallet_id is not None:
            value['wallet_id'] = wallet_id
        return self.file('config-' + label + '.json', json.dumps(value))

    def prepare(self, label, *, root=None):
        root = root or self.root
        consult.prepare_request(root, input_path=self.input, exchange_id=label, max_tokens=200)
        brief = consult.split_brief(root, label)
        plan = {'format': consult.codex_split.CONTRACT, 'binding': brief['binding'],
            'decision': 'Local extraction complete; request independent content.',
            'local_work': [], 'local_work_reason': 'Synthetic transport test has no source extraction.',
            'claude_value': 'Independent reasoning from the supplied problem.',
            'context_decision': 'The actual task and working question are sufficient.'}
        return self.file(root.name + '-' + label + '-split.json', json.dumps(plan))

    def call(self, label, plan, *, root=None, facts=None, ceiling=.2, config=None):
        return consult.call_once(root or self.root, label, facts=facts or self.facts(),
            ceiling_usd=ceiling, split_path=plan, config_path=config or self.config(label))

    def test_same_task_distinct_exchanges_enter_network_together(self):
        plans = [self.prepare(label) for label in ('a', 'b')]
        self.server.expected = 2
        with ThreadPoolExecutor(2) as pool:
            jobs = [pool.submit(self.call, label, plan) for label, plan in zip(('a', 'b'), plans)]
            try:
                self.assertTrue(self.server.entered.wait(3), 'network calls were serialized by a task lock')
            finally:
                self.server.release.set()
            results = [job.result(3) for job in jobs]
        self.assertEqual(len(self.server.requests), 2)
        self.assertTrue(all(item['exchange']['public_status'] == 'COMPLETE' for item in results))
        self.assertAlmostEqual(consult.inspect_exchange(self.root)['totals']['known_cost_usd'], .06)

    def test_two_processes_use_the_same_short_wallet_transaction_and_overlap_http(self):
        labels = ('process-a', 'process-b')
        plans = [self.prepare(label) for label in labels]
        configs = [self.config(label) for label in labels]
        facts = self.file('process-facts.json', json.dumps(self.facts()))
        script = ('import json,sys; from pathlib import Path; from runtime.codex_consult import call_once; '
                  'r=call_once(Path(sys.argv[1]),sys.argv[2],facts=json.loads(Path(sys.argv[3]).read_text()),'
                  'ceiling_usd=.2,config_path=Path(sys.argv[4]),split_path=Path(sys.argv[5])); '
                  'print(r["exchange"]["public_status"])')
        self.server.expected = 2
        processes = [subprocess.Popen([sys.executable, '-c', script, str(self.root), label, str(facts),
                     str(config), str(plan)], cwd=fixtures.ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     text=True) for label, config, plan in zip(labels, configs, plans)]
        try:
            self.assertTrue(self.server.entered.wait(4), 'cross-process transports did not overlap')
        finally:
            self.server.release.set()
        for process in processes:
            out, error = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, error)
            self.assertIn('COMPLETE', out)
        self.assertEqual(len(self.server.requests), 2)

    def test_same_exchange_has_at_most_one_physical_post(self):
        plan = self.prepare('one')
        with ThreadPoolExecutor(1) as pool:
            job = pool.submit(self.call, 'one', plan)
            try:
                self.assertTrue(self.server.first_entered.wait(3))
                with self.assertRaisesRegex(ValueError, 'writer owns this exchange'):
                    self.call('one', plan)
                with self.assertRaisesRegex(ValueError, 'writer owns this exchange'):
                    consult.reconcile_cost(self.root, 'one', metadata={'data': {'id': 'gen-one', 'total_cost': .03}})
            finally:
                self.server.release.set()
            job.result(3)
        with self.assertRaisesRegex(ValueError, 'already started'):
            self.call('one', plan)
        self.assertEqual(len(self.server.requests), 1)

    def test_consistent_raw_snapshot_survives_exact_old_attempt_new_request_interleaving(self):
        from runtime import codex_io
        self.prepare('snapshot-race')
        directory = self.root / 'consult' / 'exchanges' / 'snapshot-race'
        attempt_path, request_path = directory / 'attempt.json', directory / 'request.json'
        old_seen, new_written = threading.Event(), threading.Event()
        read = codex_io.read_bytes

        def interleaved(path):
            raw = read(path)
            if (threading.current_thread().name.startswith('snapshot-reader')
                    and Path(path) == attempt_path and not old_seen.is_set()):
                old_seen.set()
                if not new_written.wait(2):
                    raise AssertionError('writer never reached the forced new request boundary')
            return raw

        with ThreadPoolExecutor(1, thread_name_prefix='snapshot-reader') as pool, \
                patch.object(codex_io, 'read_bytes', side_effect=interleaved):
            job = pool.submit(consult._load, self.root, 'snapshot-race')
            try:
                self.assertTrue(old_seen.wait(1))
                attempt, request = consult._read(attempt_path), consult._read(request_path)
                request['provider']['max_price'] = {'prompt': 2, 'completion': 10, 'request': 0}
                raw = consult._json_bytes(request)
                attempt['pending_request_sha256'] = consult._hash(raw)
                with consult._exchange_writer(self.root, 'snapshot-race'):
                    consult._write(attempt_path, attempt)
                    consult._write_bytes(request_path, raw)
            finally:
                new_written.set()
            _, loaded_attempt, loaded_request = job.result(2)
        self.assertEqual(loaded_attempt['pending_request_sha256'], consult._hash(consult._json_bytes(loaded_request)))
        self.assertEqual(loaded_request['provider']['max_price']['completion'], 10)
        self.assertEqual(self.server.requests, [])

    def test_consistent_snapshot_still_rejects_a_stable_unbound_request_change(self):
        self.prepare('corrupt-request')
        path = self.root / 'consult' / 'exchanges' / 'corrupt-request' / 'request.json'
        request = consult._read(path)
        request['max_tokens'] += 1
        consult._write_bytes(path, consult._json_bytes(request))
        with self.assertRaisesRegex(ValueError, 'request/attempt identity changed'):
            consult._load(self.root, 'corrupt-request')
        self.assertEqual(self.server.requests, [])

    def test_inspection_returns_partial_bytes_without_waiting_for_the_network_owner(self):
        plan = self.prepare('inspect-partial')
        partial = threading.Event()
        with ThreadPoolExecutor(1) as pool:
            job = pool.submit(consult.call_once, self.root, 'inspect-partial', facts=self.facts(),
                ceiling_usd=.2, split_path=plan, config_path=self.config('inspect-partial'),
                on_public_event=lambda event: partial.set() if event['event'] == 'public_delta' else None)
            try:
                self.assertTrue(partial.wait(3))
                self.assertFalse(job.done())
                started = time.monotonic()
                observed = consult.inspect_exchange(self.root, 'inspect-partial')
                self.assertLess(time.monotonic() - started, .5)
                self.assertEqual(observed['exchange']['public_status'], 'PARTIAL')
                self.assertIn('actual partial public answer', Path(observed['public_path']).read_text())
                self.assertFalse(job.done())
            finally:
                self.server.release.set()
            result = job.result(3)
        self.assertEqual(result['exchange']['public_status'], 'COMPLETE')
        self.assertEqual(len(self.server.requests), 1)

    def test_shared_wallet_prevents_two_roots_spending_the_same_balance(self):
        second = self.task('second')
        plan1, plan2 = self.prepare('a'), self.prepare('b', root=second)
        same_snapshot = self.facts(wallet=.30)
        with ThreadPoolExecutor(1) as pool:
            job = pool.submit(self.call, 'a', plan1, facts=same_snapshot)
            try:
                self.assertTrue(self.server.first_entered.wait(3))
                with self.assertRaisesRegex(ValueError, 'Shared wallet reservation'):
                    self.call('b', plan2, root=second, facts=same_snapshot)
            finally:
                self.server.release.set()
            job.result(3)
        self.assertEqual(len(self.server.requests), 1)

    def test_shared_task_budget_also_applies_across_different_wallets(self):
        plans = [self.prepare(label) for label in ('a', 'b')]
        facts = self.facts(total=.30)
        with ThreadPoolExecutor(1) as pool:
            job = pool.submit(self.call, 'a', plans[0], facts=facts)
            try:
                self.assertTrue(self.server.first_entered.wait(3))
                with self.assertRaisesRegex(ValueError, 'budget'):
                    self.call('b', plans[1], facts=facts, config=self.config('b', wallet_id='another-account'))
            finally:
                self.server.release.set()
            job.result(3)
        self.assertEqual(len(self.server.requests), 1)

    def test_missing_wallet_identity_never_falls_back_to_a_task_local_budget(self):
        plan = self.prepare('no-wallet')
        with self.assertRaisesRegex(ValueError, 'wallet_id'):
            self.call('no-wallet', plan, config=self.config('no-wallet', wallet_id=None))
        self.assertEqual(self.server.requests, [])
        self.assertEqual(consult.inspect_exchange(self.root, 'no-wallet')['exchange']['transport_status'], 'PREPARED')

    def test_crash_before_attempt_intent_preserves_claim_and_explicit_unsent_recovery(self):
        plan = self.prepare('pre-intent')
        write = consult._write
        def crash(path, value, **kwargs):
            if path.name == 'attempt.json' and value.get('transport_status') == 'ATTEMPTED':
                raise OSError('synthetic pre-intent interruption')
            return write(path, value, **kwargs)
        with patch.object(consult, '_write', side_effect=crash):
            with self.assertRaisesRegex(OSError, 'synthetic'):
                self.call('pre-intent', plan)
        current = consult.inspect_exchange(self.root, 'pre-intent')
        self.assertEqual(current['exchange']['transport_status'], 'PREPARED')
        self.assertAlmostEqual(current['totals']['unresolved_reserved_usd'], .2)
        with self.assertRaisesRegex(ValueError, 'already claimed'):
            self.call('pre-intent', plan)
        recovered = consult.recover_preflight(self.root, 'pre-intent')
        self.assertAlmostEqual(recovered['totals']['unresolved_reserved_usd'], 0)
        self.assertFalse(recovered['exchange']['preflight_recovery']['exchange_reusable'])
        self.assertEqual(self.server.requests, [])

    def test_unknown_invoice_remains_reserved_then_reconciles_without_a_second_post(self):
        plan = self.prepare('unknown')
        self.server.release.set()
        observed = self.call('unknown', plan)
        self.assertEqual(observed['exchange']['billing_status'], 'UNKNOWN')
        self.assertAlmostEqual(observed['totals']['unresolved_reserved_usd'], .2)
        with self.assertRaisesRegex(ValueError, 'committed attempt'):
            consult.recover_preflight(self.root, 'unknown')
        settled = consult.reconcile_cost(self.root, 'unknown', metadata={'data': {'id': 'gen-unknown', 'total_cost': .04}})
        self.assertAlmostEqual(settled['totals']['known_cost_usd'], .04)
        self.assertAlmostEqual(settled['totals']['unresolved_reserved_usd'], 0)
        self.assertEqual(len(self.server.requests), 1)

    def test_permission_revocation_during_reservation_prevents_send(self):
        plan = self.prepare('revoke')
        reserve = wallet.reserve
        def revoke(*args, **kwargs):
            receipt = reserve(*args, **kwargs)
            source = self.file('revoke.txt', 'DIGR: Disable Claude for this task now.')
            message = ingest_message(self.root, source=source, source_ref='synthetic-revocation', route_pin=PIN)
            handle_message(self.root, message_id=message['message_id'], action='continue', reason='Apply actual choice')
            return receipt
        with patch.object(wallet, 'reserve', side_effect=revoke):
            with self.assertRaisesRegex(ValueError, 'disabled'):
                self.call('revoke', plan)
        self.assertEqual(self.server.requests, [])
        current = consult.inspect_exchange(self.root, 'revoke')
        self.assertEqual(current['exchange']['transport_status'], 'PREPARED')
        self.assertAlmostEqual(current['totals']['unresolved_reserved_usd'], .2)

    def test_wallet_snapshot_does_not_double_subtract_earlier_settled_costs(self):
        self.server.release.set()
        first = self.prepare('old')
        prior = self.call('old', first)['exchange']
        second_root = self.task('fresh')
        second = self.prepare('new', root=second_root)
        coverage = {'snapshot_id': 'confirmed-old-bill', 'wallet_id': 'synthetic-shared-account',
                    'covered_claims': {prior['wallet_claim']['claim_id']: {
                        'cost_revision': prior['cost_revision'], 'covered_cost_usd': prior['known_cost_usd']}}}
        result = self.call('new', second, root=second_root, facts=self.facts(wallet=.21, wallet_snapshot=coverage))
        self.assertGreaterEqual(result['exchange']['wallet_claim']['wallet_available_before_usd'], .21)

    def test_settlements_after_snapshot_and_shared_account_grant_remain_bounded(self):
        self.server.release.set()
        old_snapshot = self.facts(wallet=.21)
        self.call('a', self.prepare('a'), facts=old_snapshot)
        other = self.task('other')
        with self.assertRaisesRegex(ValueError, 'Shared wallet reservation'):
            self.call('b', self.prepare('b', root=other), root=other, facts=old_snapshot)
        # A new wallet snapshot restores the balance fact, but a separately
        # scoped shared authorization is still enforced across task roots.
        grant = self.facts(account_authorization_ref='synthetic-global-grant', account_budget_total_usd=.21)
        self.call('c', self.prepare('c'), facts=grant)
        with self.assertRaisesRegex(ValueError, 'Shared wallet reservation'):
            self.call('d', self.prepare('d', root=other), root=other, facts=grant)

    def test_public_files_and_wallet_never_contain_credentials_or_hidden_reasoning(self):
        self.server.release.set()
        self.call('clean', self.prepare('clean'))
        files = list((self.root / 'consult').rglob('*')) + list((self.folder / 'codex-home').rglob('*'))
        for path in files:
            if path.is_file():
                raw = path.read_bytes()
                self.assertNotIn(fixtures.SECRET.encode(), raw, path)
                self.assertNotIn(fixtures.HIDDEN.encode(), raw, path)

    def test_real_registered_member_has_no_guidance_priority_and_cannot_spawn_extra_jobs(self):
        from runtime import codex_council as council
        council.create_council(self.root, council_id='identity', native_actors=['native-1'],
                               enable_claude=True, member_count=2)
        state = council.prepare_round(self.root, 'identity', max_tokens=200)
        jobs = state['rounds'][-1]['jobs']
        first = jobs['member-1']
        prepared = consult.inspect_exchange(self.root, first['exchange_id'])
        self.assertEqual(prepared['collaboration']['content_relationship'], 'COUNCIL_MEMBER_RESEARCH')
        self.assertFalse(prepared['collaboration']['subjective_guidance_priority'])
        request = json.loads(Path(prepared['request_path']).read_text())
        self.assertEqual(request['messages'][0]['content'], consult._COUNCIL_MEMBER_SYSTEM)
        with self.assertRaisesRegex(ValueError, 'exchange'):
            consult.prepare_request(self.root, input_path=self.input, exchange_id='unregistered-extra',
                participation_role='council_member', council_scope=first['scope'])
        with self.assertRaisesRegex(ValueError, 'exchange_id'):
            consult.prepare_request(self.root, input_path=self.input,
                participation_role='council_member', council_scope=first['scope'])
        with self.assertRaisesRegex(ValueError, 'across member and formal Consult roles'):
            consult.prepare_request(self.root, input_path=self.input, continue_from=first['exchange_id'])
        self.assertEqual(self.server.requests, [])

    def test_continuous_sse_stops_at_actual_member_deadline_and_preserves_unknown_cost(self):
        from runtime import codex_council as council
        council.create_council(self.root, council_id='timed', native_actors=['native-1'],
            enable_claude=True, member_count=1, deadline_seconds=1)
        state = council.prepare_round(self.root, 'timed', max_tokens=200)
        job = state['rounds'][-1]['jobs']['member-1']
        label = job['exchange_id']
        brief = consult.split_brief(self.root, label)
        plan = self.file('timed-split.json', json.dumps({'format': consult.codex_split.CONTRACT,
            'binding': brief['binding'], 'decision': 'Synthetic deadline transport experiment.',
            'local_work': [], 'local_work_reason': 'The localhost server supplies public chunks.',
            'claude_value': 'Produce a synthetic public stream.', 'context_decision': 'Actual test packet is complete.'}))
        self.server.release.set()
        started = time.monotonic()
        result = self.call(label, plan, config=self.config('deadline'))
        self.assertLess(time.monotonic() - started, 1.8)
        self.assertEqual(result['exchange']['transport_status'], 'OUTCOME_UNKNOWN')
        self.assertEqual(result['exchange']['public_status'], 'PARTIAL')
        self.assertEqual(result['exchange']['billing_status'], 'UNKNOWN')
        self.assertAlmostEqual(result['totals']['unresolved_reserved_usd'], .2)
        self.assertEqual(len(self.server.requests), 1)

    def timed_job(self):
        from runtime import codex_council as council
        council.create_council(self.root, council_id='slow', native_actors=['native-1'],
            enable_claude=True, member_count=1, deadline_seconds=1)
        state = council.prepare_round(self.root, 'slow', max_tokens=200)
        job = state['rounds'][-1]['jobs']['member-1']
        brief = consult.split_brief(self.root, job['exchange_id'])
        plan = self.file('slow-plan.json', json.dumps({'format': consult.codex_split.CONTRACT,
            'binding': brief['binding'], 'decision': 'Absolute deadline on a slow-byte synthetic stream.',
            'local_work': [], 'local_work_reason': 'Constructed HTTP input needs no extraction.',
            'claude_value': 'Synthetic public reply.', 'context_decision': 'Actual complete test packet supplied.'}))
        return job, plan

    def test_slow_bytes_without_a_newline_cannot_extend_the_absolute_deadline(self):
        job, plan = self.timed_job()
        self.server.release.set()
        start = time.monotonic()
        result = self.call(job['exchange_id'], plan, config=self.config('slow-byte'))
        self.assertLess(time.monotonic() - start, 1.8)
        self.assertEqual(result['exchange']['transport_status'], 'OUTCOME_UNKNOWN')
        self.assertEqual(result['exchange']['billing_status'], 'UNKNOWN')
        self.assertAlmostEqual(result['totals']['unresolved_reserved_usd'], .2)
        self.assertEqual(len(self.server.requests), 1)

    def test_round_process_exits_promptly_after_slow_byte_deadline(self):
        config = self.config('slow-byte')
        facts = self.file('slow-facts.json', json.dumps(self.facts()))
        # Start the actual one-second council inside the child. Python startup
        # must not consume the fixture's deadline before any POST can begin.
        script = '''import json,sys,time
from pathlib import Path
from runtime import codex_council as c, codex_consult as t
root=Path(sys.argv[1])
s=time.monotonic()
c.create_council(root,council_id='slow',native_actors=['native-1'],enable_claude=True,member_count=1,deadline_seconds=1)
state=c.prepare_round(root,'slow',max_tokens=200)
job=state['rounds'][-1]['jobs']['member-1']
brief=t.split_brief(root,job['exchange_id'])
plan=root/'slow-child-plan.json'
plan.write_text(json.dumps({'format':t.codex_split.CONTRACT,'binding':brief['binding'],
 'decision':'Synthetic absolute read deadline.','local_work':[],
 'local_work_reason':'Localhost fixture.','claude_value':'Constructed public stream.',
 'context_decision':'Actual test packet supplied.'}),encoding='utf-8')
r=c.run_round(root,'slow',round_id=1,jobs={'member-1':{'facts':json.loads(Path(sys.argv[2]).read_text()),
 'ceiling_usd':.2,'config_path':Path(sys.argv[3]),'split_path':plan}})
print(json.dumps({'elapsed':time.monotonic()-s,'phase':r['phase']}),flush=True)
'''
        self.server.release.set()
        start = time.monotonic()
        process = subprocess.Popen([sys.executable, '-c', script, str(self.root), str(facts), str(config)],
            cwd=fixtures.ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, error = process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0, error)
        self.assertLess(time.monotonic() - start, 2.5)
        self.assertEqual(len(self.server.requests), 1)

    def test_repeated_reconciliation_and_corrected_invoice_use_confirmed_snapshot_deltas(self):
        self.server.release.set()
        old = self.call('bill', self.prepare('bill'))['exchange']
        first = consult.reconcile_cost(self.root, 'bill', metadata={'data': {'id': 'gen-bill', 'total_cost': .2}})['exchange']
        snapshot = {'snapshot_id': 'balance-after-point-two', 'wallet_id': 'synthetic-shared-account',
            'covered_claims': {first['wallet_claim']['claim_id']: {'cost_revision': first['cost_revision'],
                                                               'covered_cost_usd': .2}}}
        same = consult.reconcile_cost(self.root, 'bill', metadata={'data': {'id': 'gen-bill', 'total_cost': .2}})['exchange']
        self.assertEqual(same['cost_observed_at'], first['cost_observed_at'])
        self.assertEqual(same['cost_revision'], first['cost_revision'])
        revised = consult.reconcile_cost(self.root, 'bill', metadata={'data': {'id': 'gen-bill', 'total_cost': .25}})['exchange']
        self.assertEqual(revised['cost_revision'], first['cost_revision'] + 1)
        result = self.call('after-revision', self.prepare('after-revision'), ceiling=.7,
            facts=self.facts(wallet=.8, wallet_snapshot=snapshot))
        self.assertAlmostEqual(result['exchange']['wallet_claim']['wallet_available_before_usd'], .75)


class WalletSnapshotTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        cache = fixtures.ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='wallet-snapshot-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {'CODEX_HOME': str(self.folder / 'codex-home')})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.session = {'P_run': PIN, 'request_sha256': 'a' * 64, 'task_uuid': 'stable-synthetic-task'}

    def budget(self, **kwargs):
        value = {'budget_total_usd': 10, 'outside_spent_usd': 0, 'outside_reserved_usd': 0,
            'wallet_remaining_usd': 1, 'ceiling_usd': .2, 'checked_at': datetime.now(timezone.utc).isoformat(),
            'authorization_ref': 'synthetic-grant'}
        value.update(kwargs)
        return value

    def reserve(self, label, budget=None, *, root='original', wallet_id='shared-wallet'):
        return wallet.reserve(self.folder / root, self.session, exchange_id=label,
            request_sha256='b' * 64, wallet_id=wallet_id, budget=budget or self.budget())

    def test_confirmed_snapshot_same_invoice_is_idempotent_and_revision_only_deducts_delta(self):
        first = self.reserve('old')
        wallet.update(first, state='COMMITTED')
        at = datetime.now(timezone.utc) - timedelta(seconds=5)
        initial = wallet.update(first, state='KNOWN', cost=.2, cost_observed_at=at.isoformat())
        snapshot = {'snapshot_id': 'confirmed-after-old-fee', 'wallet_id': 'shared-wallet',
            'covered_claims': {first['claim_id']: {'cost_revision': initial['cost_revision'], 'covered_cost_usd': .2}}}
        data = self.budget(wallet_remaining_usd=.8, ceiling_usd=.7, wallet_snapshot=snapshot)
        baseline = self.reserve('baseline', data)
        self.assertAlmostEqual(baseline['wallet_available_before_usd'], .8)
        wallet.update(baseline, state='ABORTED')
        same = wallet.update(first, state='KNOWN', cost=.2,
                             cost_observed_at=(at + timedelta(seconds=10)).isoformat())
        self.assertEqual(same['cost_observed_at'], at.isoformat())
        self.assertEqual(same['cost_revision'], initial['cost_revision'])
        after = self.reserve('same-bill', data)
        self.assertAlmostEqual(after['wallet_available_before_usd'], .8)
        wallet.update(after, state='ABORTED')
        revised = wallet.update(first, state='KNOWN', cost=.25,
                                cost_observed_at=(at + timedelta(seconds=11)).isoformat())
        delta = self.reserve('delta', data)
        self.assertAlmostEqual(delta['wallet_available_before_usd'], .75)
        self.assertEqual(revised['cost_revision'], initial['cost_revision'] + 1)
        self.assertEqual(revised['cost_first_observed_at'], initial['cost_first_observed_at'])

    def test_missing_snapshot_coverage_is_conservative_and_snapshot_identity_is_immutable(self):
        first = self.reserve('old')
        wallet.update(first, state='KNOWN', cost=.2, cost_observed_at=datetime.now(timezone.utc).isoformat())
        no_coverage = self.reserve('unconfirmed', self.budget(wallet_remaining_usd=.8, ceiling_usd=.1))
        self.assertAlmostEqual(no_coverage['wallet_available_before_usd'], .6)
        wallet.update(no_coverage, state='ABORTED')
        snapshot = {'snapshot_id': 'fixed', 'wallet_id': 'shared-wallet', 'covered_claims': {}}
        one = self.reserve('fixed', self.budget(wallet_snapshot=snapshot))
        wallet.update(one, state='ABORTED')
        with self.assertRaisesRegex(ValueError, 'immutable wallet snapshot'):
            self.reserve('changed', self.budget(wallet_remaining_usd=2, wallet_snapshot=snapshot))

    def test_task_identity_and_budget_survive_root_copy_or_restore(self):
        grant = self.budget(budget_total_usd=.3, wallet_remaining_usd=100)
        first = self.reserve('one', grant)
        with self.assertRaisesRegex(ValueError, 'already claimed'):
            self.reserve('one', grant, root='restored')
        with self.assertRaisesRegex(ValueError, 'Shared wallet reservation'):
            self.reserve('different-exchange', grant, root='restored', wallet_id='different-wallet')
        self.assertEqual(wallet.task_id(self.folder / 'original', self.session),
                         wallet.task_id(self.folder / 'restored', self.session))
        legacy = dict(self.session)
        legacy.pop('task_uuid')
        legacy.update(created_wall_ns=1234, request_origin='/frozen/request.txt')
        self.assertEqual(wallet.task_id(self.folder / 'original', legacy),
                         wallet.task_id(self.folder / 'restored', legacy))


if __name__ == '__main__':
    unittest.main()
