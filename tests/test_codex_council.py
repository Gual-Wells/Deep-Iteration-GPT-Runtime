from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
import io

from runtime import codex_collaboration as collaboration, codex_consult as consult, codex_council as council, codex_io
from runtime.codex_lifecycle import handle_message, ingest_message
from runtime.codex_profile import classify_invocation
from runtime.codex_session import create_session, task_parameters
from tools.codex_council import main as council_cli

ROOT = Path(__file__).resolve().parents[1]
PIN = '0.16.0@' + 'd' * 40
HIDDEN = 'SYNTHETIC_HIDDEN_REASONING_MUST_NOT_PERSIST'


class CouncilHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        with self.server.counter:
            self.server.requests.append(request)
            index = len(self.server.requests)
            self.server.active += 1
            self.server.max_active = max(self.server.max_active, self.server.active)
            if self.server.active >= 2:
                self.server.overlapped.set()
            self.server.entered.set()
        try:
            self.server.release.wait(7)
            if self.server.delay:
                time.sleep(self.server.delay)
            generation = 'gen-council-' + str(index)
            body = 'PUBLIC MEMBER WORK ' + str(index) + '\n条件、反例与研究领域。\n'
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('X-Generation-Id', generation)
            self.end_headers()
            frame = lambda value: ('data: ' + json.dumps(value, ensure_ascii=False) + '\n\n').encode('utf-8')
            self.wfile.write(frame({'id': generation, 'model': request['model'],
                'service_tier': request.get('service_tier'),
                'choices': [{'index': 0, 'delta': {'content': body, 'reasoning': HIDDEN}}]}))
            self.wfile.flush()
            if self.server.truncated or request['model'] in self.server.truncated_models:
                return
            self.wfile.write(frame({'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}],
                'usage': {'cost': .002, 'prompt_tokens': 30, 'completion_tokens': 20}}))
            self.wfile.write(b'data: [DONE]\n\n')
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        finally:
            with self.server.counter:
                self.server.active -= 1


class CouncilRuntimeTests(unittest.TestCase):
    def setUp(self):
        cache = Path(os.environ.get('DIGR_TEST_TMPDIR', str(ROOT / '.cache'))).resolve()
        cache.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='council-runtime-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.environment = patch.dict(os.environ, {'CODEX_HOME': str(self.folder / 'codex-home'),
            'DIGR_COUNCIL_TEST_KEY': 'LOCALHOST_ONLY_NOT_A_REAL_CREDENTIAL'})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.root = self.task('task', allow=True)
        self.native = self.file('native.txt', 'NATIVE INITIAL OPINION must stay off the Claude first phase.\n')
        self.redeliberation = self.file('redeliberation.txt', 'Native council chooses its domains and handles the strong alternative with reasons.\n')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), CouncilHandler)
        self.server.counter = threading.Lock()
        self.server.requests = []
        self.server.active = 0
        self.server.max_active = 0
        self.server.overlapped = threading.Event()
        self.server.entered = threading.Event()
        self.server.release = threading.Event()
        self.server.release.set()
        self.server.delay = 0
        self.server.truncated = False
        self.server.truncated_models = set()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.config = self.file('private.json', json.dumps({
            'endpoint': f'http://127.0.0.1:{self.server.server_port}/members',
            'api_key_env': 'DIGR_COUNCIL_TEST_KEY', 'wallet_id': 'synthetic-one-account',
            'timeout_seconds': 3}))

    def stop_server(self):
        self.server.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)

    def file(self, name, text):
        path = self.folder / name
        path.write_text(text, encoding='utf-8', newline='')
        return path

    def task(self, name, *, allow):
        request = self.file(name + '-user.txt', ('DIGR::' if allow else 'DIGR:') + ' Research this synthetic localhost task.')
        root = self.folder / name
        create_session(root, request=request, p_run=PIN)
        return root

    def create(self, *, enable=True, deadline=300):
        return council.create_council(self.root, council_id='one', native_actors=['native-1'],
                                     enable_claude=enable, deadline_seconds=deadline)

    def prepare(self, kind='INDEPENDENT', members=None):
        return council.prepare_round(self.root, 'one', kind=kind, members=members, max_tokens=100)

    def facts(self):
        return {'authorization_ref': 'Synthetic localhost-only fixture, no external paid authority',
            'checked_at': datetime.now(timezone.utc).isoformat(), 'model': consult.DEFAULT_MODEL,
            'pricing_ref': 'Constructed fixture prices', 'budget_total_usd': 20,
            'outside_spent_usd': 0, 'wallet_remaining_usd': 20,
            'prompt_usd_per_million': 2, 'completion_usd_per_million': 10,
            'input_tokens_upper_bound': 10000, 'input_bound_basis': 'Constructed complete-fixture bound'}

    def jobs(self, prepared):
        record = prepared['rounds'][-1]
        result = {}
        for member_id, job in record['jobs'].items():
            if job['status'] != 'PREPARED':
                self.fail('Preparation failed: ' + json.dumps(record))
            brief = consult.split_brief(self.root, job['exchange_id'])
            decision = {'decision': 'Native source and identity preparation completed; preserve independent research.',
                'local_work': [{'task': 'Inspect complete prepared common input', 'result': 'Actual packet has source identities and no native initial opinions.'}],
                'claude_value': 'Independent problem representation and domain research.',
                'context_decision': 'Supply exact sources, own public history, and all public peer work for this round.'}
            note = self.file(job['exchange_id'] + '-decision.json', json.dumps(decision))
            plan = self.folder / (job['exchange_id'] + '-split.json')
            consult.bind_split_decision(self.root, job['exchange_id'], input_path=note, output=plan)
            self.assertEqual(brief['binding']['request_sha256'], consult.inspect_exchange(self.root, job['exchange_id'])['exchange']['request_sha256'])
            facts = {**self.facts(), 'model': job.get('model', consult.DEFAULT_MODEL)}
            cap = .1 if collaboration.parallel_external_policy(prepared['P_run']) else .2
            result[member_id] = {'facts': facts, 'ceiling_usd': cap,
                                 'split_path': plan, 'config_path': self.config}
        return result

    def run_prepared(self, prepared, *, events=None):
        return council.run_round(self.root, 'one', round_id=prepared['rounds'][-1]['round_id'],
                                 jobs=self.jobs(prepared), on_public_event=events.append if events is not None else None)

    def assert_complete_round(self, result):
        record = result['rounds'][-1]
        observed = {'round': record, 'cycle': result['cycle'], 'attempts': {}}
        for member_id, job in record['jobs'].items():
            observed['attempts'][member_id] = consult.inspect_exchange(self.root, job['exchange_id'])['exchange']
        self.assertTrue(all(job['status'] == 'COMPLETE' for job in record['jobs'].values()),
                        'Actual member round failed: ' + json.dumps(observed, ensure_ascii=False, indent=2))

    def native_return(self, version=1):
        return council.submit_native_initial(self.root, 'one', actor='native-1',
                                             output_path=self.native, input_version=version)

    def foundation_intent_task(self, name, delimiter=':', *, version='1.7.0'):
        request = self.file(name + '-input.txt', 'DIGR' + delimiter + ' Follow the specified scope.')
        self.root = self.folder / name
        create_session(self.root, request=request, p_run=version + '@' + 'e' * 40)
        return request

    def foundation_intent_proposal(self, identity='u0-0'):
        from runtime.codex_foundation import BRIEF_FIELDS
        return {'brief': {key: 'Source-bound actual ' + key for key in BRIEF_FIELDS},
                'intent_council': identity}

    def test_binary_u_preserves_default_and_existing_non_u0_council(self):
        pin = '1.8.0@' + 'e' * 40
        for malformed in ('U=2', 'U', 'U=1,U=0', 'S(U=1)'):
            with self.subTest(malformed=malformed):
                self.assertEqual(classify_invocation(f'DIGR({malformed}): Test.', p_run=pin)['classification'],
                                 'INVALID')
        self.foundation_intent_task('u0-default-closed', version='1.8.0')
        self.assertEqual(task_parameters(self.root)['parameters']['U'], 0)
        with self.assertRaisesRegex(ValueError, 'requires U=1'):
            council.create_council(self.root, council_id='u0-0', native_actors=['native-1'],
                                   foundation_intent=True)
        first = council.create_council(self.root, council_id='opinion', native_actors=['native-1'],
                                       first_opinion='Find a better way to meet this goal.')
        self.assertEqual({member['model'] for member in first['members'].values()},
                         set(collaboration.external_models(pin).values()))

    def test_new_u0_dispatches_three_models_with_hydrogen_flex_only(self):
        self.foundation_intent_task('u0-flex', '(U=1):', version='1.8.0')
        self.assertEqual(task_parameters(self.root)['parameters']['U'], 1)
        council.create_council(self.root, council_id='u0-0', native_actors=['native-1'],
                               foundation_intent=True)
        prepared = council.prepare_round(self.root, 'u0-0', kind='INDEPENDENT', max_tokens=100)
        jobs = self.jobs(prepared)
        for job in jobs.values():
            job['ceiling_usd'] = 0.05  # Covers this 100-token request, within the shared layer cap.
        completed = council.run_round(self.root, 'u0-0', round_id=1, jobs=jobs)
        self.assert_complete_round(completed)
        requests = {request['model']: request for request in self.server.requests}
        self.assertEqual(set(requests), {collaboration.SONNET_5_5, collaboration.GEMINI_HYDROGEN,
                                         collaboration.GROK_4_7})
        hydrogen = requests[collaboration.GEMINI_HYDROGEN]
        self.assertEqual(hydrogen['service_tier'], 'flex')
        self.assertEqual(hydrogen['provider']['only'], ['google-ai-studio/flex'])
        self.assertIs(hydrogen['provider']['allow_fallbacks'], False)
        self.assertEqual(requests[collaboration.SONNET_5_5]['service_tier'], 'default')
        self.assertEqual(requests[collaboration.GROK_4_7]['service_tier'], 'default')
        for job in completed['rounds'][-1]['jobs'].values():
            _, attempt, request = consult._load(self.root, job['exchange_id'])
            self.assertEqual(attempt['response_service_tier'], request['service_tier'])

    def test_u0_revocation_blocks_existing_prepared_round(self):
        self.foundation_intent_task('u0-revoked', '(U=1):', version='1.8.0')
        council.create_council(self.root, council_id='u0-0', native_actors=['native-1'],
                               foundation_intent=True)
        prepared = council.prepare_round(self.root, 'u0-0', max_tokens=100)
        jobs = self.jobs(prepared)
        message = self.file('u0-turn-off.txt', 'DO: Turn off the U0 model council.')
        pending = ingest_message(self.root, source=message, source_ref='latest-u0-decision')
        handle_message(self.root, message_id=pending['message_id'], action='ordinary',
                       reason='The user revoked U0 council use', u0_council=0)
        self.assertEqual(task_parameters(self.root)['U_source']['source_ref'], 'latest-u0-decision')
        with self.assertRaisesRegex(ValueError, 'requires U=1'):
            council.run_round(self.root, 'u0-0', round_id=1, jobs=jobs)
        self.assertFalse(self.server.requests)
        followup = self.file('u0-inherit.txt', 'DO: Continue the task as agreed.')
        pending = ingest_message(self.root, source=followup, source_ref='continue-without-u0')
        handle_message(self.root, message_id=pending['message_id'], action='ordinary',
                       reason='Continue with the saved choice')
        self.assertEqual(task_parameters(self.root)['parameters']['U'], 0)

    def test_parallel_foundation_uses_first_layer_before_confirmation_under_both_delimiters(self):
        from runtime.codex_foundation import propose_foundation

        for i, delimiter in enumerate((':', '::')):
            with self.subTest(delimiter=delimiter):
                self.foundation_intent_task('u0-input-' + str(i), delimiter)
                identity = 'u0-0'
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(council_cli(['create', '--root', str(self.root),
                        '--council-id', identity, '--foundation-intent', '--native-actor', 'native-1']), 0)
                self.assertFalse((self.root / 'foundation.json').exists())
                prepared = council.prepare_round(self.root, identity, kind='INDEPENDENT', max_tokens=100)
                jobs = self.jobs(prepared)
                by_model = {job['facts']['model']: job for job in jobs.values()}
                def quoted(request, **options):
                    self.assertEqual(options['layer_ceiling'], .25)
                    job = by_model[request['model']]
                    return {'facts': job['facts'], 'ceiling_usd': job['ceiling_usd']}
                with patch('runtime.codex_consult_budget.claude_council_quote', side_effect=quoted) as quote:
                    kind, jobs = council.automatic_round_plan(
                        self.root, identity, round_id=1,
                        split_paths={key: job['split_path'] for key, job in jobs.items()},
                        config_path=self.config)
                self.assertEqual(kind, 'foundation_intent_quote')
                self.assertEqual(quote.call_count, 2)
                self.server.entered.clear()
                self.server.overlapped.clear()
                self.server.release.clear()
                events = []
                with ThreadPoolExecutor(max_workers=1) as pool:
                    sender = pool.submit(council.run_round, self.root, identity, round_id=1,
                                         jobs=jobs, on_public_event=events.append)
                    try:
                        self.assertTrue(self.server.overlapped.wait(5))
                        self.assertEqual(council.read_packet(self.root, identity, actor='native-1')['public_work'], [])
                        sent = self.server.requests[-2:]
                        self.assertEqual({r['model'] for r in sent}, set(collaboration.EXTERNAL_MODELS.values()))
                        self.assertEqual(sent[0]['messages'], sent[1]['messages'])
                        for request in sent:
                            body = json.dumps(request, ensure_ascii=False)
                            self.assertIn('Independently extract the user intent', body)
                            self.assertIn('Follow the specified scope', body)
                            self.assertIn('Return one complete public U0 draft', request['messages'][0]['content'])
                            self.assertNotIn('[[CODEX NATIVE WORK]]', body)
                            self.assertNotIn('NATIVE INITIAL OPINION', body)
                            self.assertNotIn('PUBLIC MEMBER WORK', body)
                        council.submit_native_initial(self.root, identity, actor='native-1',
                                                      output_path=self.native, input_version=1)
                    finally:
                        self.server.release.set()
                    result = sender.result(timeout=8)
                self.assert_complete_round(result)
                packet = council.read_packet(self.root, identity, actor='native-1', stage='REDELIBERATION')
                self.assertEqual({x['source'] for x in packet['public_work']},
                                 {'native_initial', 'claude_sonnet', 'gemini_carbon'})
                self.assertEqual({e['source'] for e in events if e.get('event') == 'public_delta'},
                                 {'claude_sonnet', 'gemini_carbon'})
                council.submit_redeliberation(self.root, identity, actor='native-1',
                                              output_path=self.redeliberation, input_version=1)
                proposal = propose_foundation(self.root, self.foundation_intent_proposal(), reason='Compare actual U0 drafts.')
                self.assertEqual(proposal['intent_review']['basis'], 'EXTERNAL_INTENT_PRIORITY')
                self.assertEqual(set(proposal['intent_review']['completed_collaborators']), {'sonnet', 'carbon'})
                self.assertEqual(proposal['status'], 'AWAITING_USER')
                self.assertEqual(proposal['intent_review']['input_ref']['message_id'], 0)
                self.assertTrue(council.completion_status(self.root)['complete'])
                with self.assertRaisesRegex(ValueError, 'already exists'):
                    council.create_council(self.root, council_id=identity, native_actors=['native-1'],
                                           foundation_intent=True)

    def test_foundation_intent_partial_and_new_input_keep_separate_evidence(self):
        from runtime.codex_foundation import propose_foundation

        self.foundation_intent_task('u0-partial')
        self.server.truncated = True
        council.create_council(self.root, council_id='u0-0', native_actors=['native-1'],
                               foundation_intent=True)
        prepared = council.prepare_round(self.root, 'u0-0', kind='INDEPENDENT', max_tokens=100)
        council.submit_native_initial(self.root, 'u0-0', actor='native-1',
                                      output_path=self.native, input_version=1)
        result = council.run_round(self.root, 'u0-0', round_id=1, jobs=self.jobs(prepared))
        self.assertEqual(result['phase'], 'REDELIBERATION')
        council.submit_redeliberation(self.root, 'u0-0', actor='native-1',
                                      output_path=self.redeliberation, input_version=1)
        fallback = propose_foundation(self.root, self.foundation_intent_proposal(), reason='Actual fallback.')
        self.assertEqual(fallback['intent_review']['basis'], 'NATIVE_FALLBACK')
        self.assertEqual({d['status'] for d in fallback['intent_review']['external_drafts'].values()}, {'PARTIAL'})

        revision = self.file('u0-change.txt', 'DO: Replace the task scope with a new output.')
        message = ingest_message(self.root, source=revision, source_ref=revision.as_posix())
        handle_message(self.root, message_id=message['message_id'], action='revise', reason='Material scope changed.')
        with self.assertRaisesRegex(ValueError, 'earlier user input'):
            propose_foundation(self.root, self.foundation_intent_proposal(), reason='Stale scope.')
        with self.assertRaisesRegex(ValueError, 'fresh independent council'):
            council.publish_event(self.root, 'u0-0', input_path=revision, kind='USER_CORRECTION')
        council.create_council(self.root, council_id='u0-1', native_actors=['native-1'],
                               foundation_intent=True)
        packet = council.read_packet(self.root, 'u0-1', actor='native-1')
        self.assertEqual(packet['public_work'], [])
        self.assertIn('Replace the task scope', json.dumps(packet['common_input']))

    def test_parallel_first_opinion_dispatch_claims_both_member_slots(self):
        from runtime import codex_wallet

        self.foundation_intent_task('paired-first-opinion')
        identity = 'paired-first'
        council.create_council(self.root, council_id=identity, native_actors=['native-1'],
                               first_opinion='Which design choice is still open?')
        prepared = council.prepare_round(self.root, identity, max_tokens=100)
        council.submit_native_initial(self.root, identity, actor='native-1', output_path=self.native, input_version=1)
        result = council.run_round(self.root, identity, round_id=1, jobs=self.jobs(prepared))
        self.assert_complete_round(result)
        _, session, _ = consult._task(self.root, active=False)
        wallet = codex_wallet.inspect_task(self.root, session)
        self.assertEqual(set(wallet['first_opinion_claims']), {'sonnet', 'carbon'})
        self.assertAlmostEqual(wallet['totals']['known_cost_usd'], .004)

    def test_carbon_complete_u0_has_priority_when_sonnet_is_partial(self):
        from runtime.codex_foundation import propose_foundation

        self.foundation_intent_task('u0-carbon-complete')
        self.server.truncated_models.add(collaboration.SONNET_5_5)
        council.create_council(self.root, council_id='u0-0', native_actors=['native-1'], foundation_intent=True)
        prepared = council.prepare_round(self.root, 'u0-0', max_tokens=100)
        council.submit_native_initial(self.root, 'u0-0', actor='native-1', output_path=self.native, input_version=1)
        council.run_round(self.root, 'u0-0', round_id=1, jobs=self.jobs(prepared))
        council.submit_redeliberation(self.root, 'u0-0', actor='native-1',
                                      output_path=self.redeliberation, input_version=1)
        review = propose_foundation(self.root, self.foundation_intent_proposal(), reason='Use complete U0.')
        self.assertEqual(review['intent_review']['basis'], 'EXTERNAL_INTENT_PRIORITY')
        self.assertEqual(review['intent_review']['completed_collaborators'], ['carbon'])

    def test_foundation_intent_only_runs_for_initial_or_material_input(self):
        self.foundation_intent_task('u0-ordinary')
        reply = self.file('same-scope.txt', 'DO: Continue the same scope.')
        message = ingest_message(self.root, source=reply, source_ref=reply.as_posix())
        handle_message(self.root, message_id=message['message_id'], action='continue',
                       reason='The currently commissioned scope still applies.')
        with self.assertRaisesRegex(ValueError, 'material change'):
            council.create_council(self.root, council_id='u0-1', native_actors=['native-1'],
                                   foundation_intent=True)
        self.assertEqual(self.server.requests, [])

    def test_late_foundation_intent_does_not_reopen_or_block_fallback(self):
        from runtime.codex_foundation import propose_foundation

        self.foundation_intent_task('u0-late')
        council.create_council(self.root, council_id='u0-0', native_actors=['native-1'],
                               foundation_intent=True)
        prepared = council.prepare_round(self.root, 'u0-0', kind='INDEPENDENT', max_tokens=100)
        council.submit_native_initial(self.root, 'u0-0', actor='native-1',
                                      output_path=self.native, input_version=1)
        jobs = self.jobs(prepared)
        self.server.release.clear()
        with ThreadPoolExecutor(max_workers=1) as pool:
            sender = pool.submit(council.run_round, self.root, 'u0-0', round_id=1, jobs=jobs)
            try:
                self.assertTrue(self.server.entered.wait(4))
                deadline = datetime.fromisoformat(prepared['cycle']['deadline_at'])
                barrier = council.advance_barrier(self.root, 'u0-0', now=deadline + timedelta(seconds=1))
                self.assertEqual(barrier['phase'], 'REDELIBERATION')
                council.submit_redeliberation(self.root, 'u0-0', actor='native-1',
                                              output_path=self.redeliberation, input_version=1)
            finally:
                self.server.release.set()
            result = sender.result(timeout=8)
        self.assertEqual(result['late_results'][0]['status'], 'RETAINED')
        self.assertTrue(council.completion_status(self.root)['complete'])
        fallback = propose_foundation(self.root, self.foundation_intent_proposal(), reason='Actual deadline fallback.')
        self.assertEqual(fallback['intent_review']['basis'], 'NATIVE_FALLBACK')

    def test_foundation_intent_refuses_old_pin_and_zero_wallet(self):
        self.foundation_intent_task('u0-legacy', version='1.6.1')
        with self.assertRaisesRegex(ValueError, '1.7.0'):
            council.create_council(self.root, council_id='u0-0', native_actors=['native-1'],
                                   foundation_intent=True)
        self.foundation_intent_task('u0-zero')
        council.create_council(self.root, council_id='u0-0', native_actors=['native-1'],
                               foundation_intent=True)
        prepared = council.prepare_round(self.root, 'u0-0', kind='INDEPENDENT', max_tokens=100)
        jobs = self.jobs(prepared)
        for job in jobs.values():
            job['facts']['wallet_remaining_usd'] = 0
        result = council.run_round(self.root, 'u0-0', round_id=1, jobs=jobs)
        self.assertEqual({j['status'] for j in result['rounds'][0]['jobs'].values()}, {'FAILED'})
        self.assertEqual(self.server.requests, [])


    def test_native_only_single_colon_context_gate_and_complete_chunks(self):
        self.root = self.task('denied', allow=False)
        self.create(enable=False)
        with self.assertRaisesRegex(ValueError, 'after the barrier'):
            council.read_packet(self.root, 'one', actor='native-1', stage='REDELIBERATION')
        with self.assertRaisesRegex(ValueError, 'assigned'):
            council.read_packet(self.root, 'one', actor='Main')
        initial = council.read_packet(self.root, 'one', actor='native-1')
        self.assertEqual(initial['public_work'], [])
        result = self.native_return()
        self.assertEqual(result['phase'], 'REDELIBERATION')
        self.assertFalse(council.completion_status(self.root)['complete'])
        packet = council.read_packet(self.root, 'one', actor='native-1', stage='REDELIBERATION', chunk_chars=7)
        self.assertEqual(''.join(chunk['text'] for chunk in packet['public_work'][0]['chunks']), self.native.read_text())
        council.submit_redeliberation(self.root, 'one', actor='native-1', output_path=self.redeliberation, input_version=1)
        self.assertTrue(council.completion_status(self.root)['complete'])
        self.assertEqual(len(self.server.requests), 0)

    def test_single_colon_never_prepares_claude(self):
        self.root = self.task('denied', allow=False)
        with self.assertRaisesRegex(ValueError, 'disabled'):
            self.create(enable=True)
        self.create(enable=False)
        with self.assertRaisesRegex(ValueError, 'disabled'):
            self.prepare()
        self.assertFalse((self.root / 'consult' / 'exchanges').exists())

    def test_two_members_three_real_rounds_parallel_relay_and_native_decision(self):
        self.create()
        self.native_return()
        first = self.prepare()
        for job in first['rounds'][0]['jobs'].values():
            info = consult.inspect_exchange(self.root, job['exchange_id'])
            request = json.loads(Path(info['request_path']).read_text())
            self.assertNotIn('NATIVE INITIAL OPINION', json.dumps(request))
            self.assertNotIn('has priority over Main', request['messages'][0]['content'])
            self.assertEqual(info['exchange']['participation_role'], 'council_member')
        self.server.release.clear()
        events = []
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.run_prepared, first, events=events)
            try:
                self.assertTrue(self.server.overlapped.wait(3), 'member POSTs did not actually overlap')
            finally:
                self.server.release.set()
            result = future.result(4)
        self.assert_complete_round(result)
        self.assertEqual(result['phase'], 'INITIAL')
        self.assertGreaterEqual(self.server.max_active, 2)
        self.assertTrue(any(event.get('event') == 'public_delta' for event in events))
        cross = self.prepare('CROSS')
        for job in cross['rounds'][-1]['jobs'].values():
            text = Path(consult.inspect_exchange(self.root, job['exchange_id'])['request_path']).read_text()
            self.assertIn('PUBLIC MEMBER WORK 1', text)
            self.assertIn('PUBLIC MEMBER WORK 2', text)
        self.assert_complete_round(self.run_prepared(cross))
        result = self.run_prepared(self.prepare('FINAL'))
        self.assert_complete_round(result)
        self.assertEqual(len(self.server.requests), 6)
        self.assertEqual(result['phase'], 'REDELIBERATION')
        self.assertTrue(result['cycle']['barrier']['research_complete'])
        self.assertFalse(council.completion_status(self.root)['complete'])
        packet = council.read_packet(self.root, 'one', actor='native-1', stage='REDELIBERATION', chunk_chars=3)
        self.assertEqual(len([item for item in packet['public_work'] if item['source'] == 'claude_subcouncil']), 6)
        council.submit_redeliberation(self.root, 'one', actor='native-1', output_path=self.redeliberation, input_version=1)
        self.assertTrue(council.completion_status(self.root)['complete'])
        self.assertAlmostEqual(consult.inspect_exchange(self.root)['totals']['known_cost_usd'], .012)
        for path in self.root.rglob('*'):
            if path.is_file() and path.suffix in {'.json', '.jsonl', '.md', '.txt'}:
                self.assertNotIn(HIDDEN, path.read_text(encoding='utf-8-sig'))

    def test_full_cross_round_reads_a_coherent_attempt_when_peer_finalizes_its_request(self):
        self.create()
        self.native_return()
        self.assert_complete_round(self.run_prepared(self.prepare()))
        cross = self.prepare('CROSS')
        jobs = self.jobs(cross)
        peer = cross['rounds'][-1]['jobs']['member-2']['exchange_id']
        old_attempt_seen, new_request_written = threading.Event(), threading.Event()
        original_load, original_read, original_replace = consult._load, codex_io.read_bytes, codex_io.replace

        def load(root, exchange_id, **kwargs):
            if threading.current_thread().name.endswith('_1') and exchange_id == peer:
                self.assertTrue(old_attempt_seen.wait(5), 'reader never reached the exact old attempt snapshot')
            return original_load(root, exchange_id, **kwargs)

        def read(path):
            raw = original_read(path)
            if (threading.current_thread().name.endswith('_0') and Path(path).name == 'attempt.json'
                    and Path(path).parent.name == peer and not old_attempt_seen.is_set()):
                observed = json.loads(raw)
                self.assertEqual(observed['transport_status'], 'PREPARED')
                self.assertNotIn('pending_request_sha256', observed)
                old_attempt_seen.set()
                self.assertTrue(new_request_written.wait(5), 'peer did not finalize the request between the actual reads')
            return raw

        def replace(source, target, **kwargs):
            result = original_replace(source, target, **kwargs)
            if (threading.current_thread().name.endswith('_1') and Path(target).name == 'request.json'
                    and Path(target).parent.name == peer):
                new_request_written.set()
            return result

        # This forces the old production failure with two real POSTs, rather
        # than retrying a failed inference or relaxing the sealed-member rule.
        with patch.object(consult, '_load', side_effect=load), patch.object(codex_io, 'read_bytes', side_effect=read), \
                patch.object(codex_io, 'replace', side_effect=replace):
            result = council.run_round(self.root, 'one', round_id=2, jobs=jobs)
        self.assertTrue(old_attempt_seen.is_set())
        self.assertTrue(new_request_written.is_set())
        self.assert_complete_round(result)
        self.assertTrue(all(side['status'] == 'PENDING' for side in result['cycle']['members'].values()))
        final = self.run_prepared(self.prepare('FINAL'))
        self.assert_complete_round(final)
        self.assertEqual(final['phase'], 'REDELIBERATION')
        self.assertEqual(len(self.server.requests), 6)

    def test_same_research_line_actually_reenters_on_relevant_new_material(self):
        self.create()
        self.run_prepared(self.prepare())
        for member in ('member-1', 'member-2'):
            council.seal_member(self.root, 'one', member_id=member, status='COMPLETE')
        self.native_return()
        council.submit_redeliberation(self.root, 'one', actor='native-1', output_path=self.redeliberation, input_version=1)
        before = council.inspect_council(self.root, 'one')['members']['member-1']['exchanges'][-1]
        event = self.file('event.txt', 'New candidate: retain the rejected condition and investigate it in the same domain.')
        reopened = council.publish_event(self.root, 'one', input_path=event, kind='RELATED_CANDIDATE', members=['member-1'])
        self.assertFalse(reopened['pending_events'][0]['research_reentry_performed'])
        prepared = self.prepare('REENTRY')
        member_job = prepared['rounds'][-1]['jobs']['member-1']
        info = consult.inspect_exchange(self.root, member_job['exchange_id'])
        self.assertEqual(info['exchange']['parent_exchange'], before)
        self.assertEqual(info['exchange']['council_scope']['line_id'], 'one/member-1')
        result = self.run_prepared(prepared)
        self.assertTrue(result['pending_events'][0]['research_reentry_performed'])
        self.assertEqual(result['members']['member-1']['last_researched_input_version'], 2)
        self.assertEqual(result['members']['member-2']['last_researched_input_version'], 1)
        council.seal_member(self.root, 'one', member_id='member-1', status='COMPLETE')
        self.native_return(version=2)
        council.submit_redeliberation(self.root, 'one', actor='native-1', output_path=self.redeliberation, input_version=2)
        self.assertTrue(council.completion_status(self.root)['complete'])

    def test_truncated_public_work_keeps_unknown_cost_and_never_auto_retries(self):
        self.create()
        self.server.truncated = True
        prepared = self.prepare()
        jobs = self.jobs(prepared)
        result = council.run_round(self.root, 'one', round_id=1, jobs=jobs)
        self.assertTrue(all(side['status'] == 'PARTIAL' for side in result['cycle']['members'].values()))
        self.native_return()
        info = council.inspect_council(self.root, 'one')
        self.assertFalse(info['cycle']['barrier']['research_complete'])
        self.assertGreater(consult.inspect_exchange(self.root)['totals']['unresolved_reserved_usd'], 0)
        with self.assertRaisesRegex(ValueError, 'attempted batch'):
            council.run_round(self.root, 'one', round_id=1, jobs=jobs)
        self.assertEqual(len(self.server.requests), 2)

    def test_input_correction_revokes_old_prepared_scope_before_network(self):
        self.create()
        prepared = self.prepare()
        jobs = self.jobs(prepared)
        source = self.file('correction.txt', 'Use the corrected original source and keep Claude permission.')
        message = ingest_message(self.root, source=source, source_ref='correction')
        handle_message(self.root, message_id=message['message_id'], action='continue', reason='Synthetic current input correction')
        with self.assertRaisesRegex(ValueError, 'stale|current-input'):
            council.run_round(self.root, 'one', round_id=1, jobs=jobs)
        self.assertEqual(len(self.server.requests), 0)
        council.publish_event(self.root, 'one', input_path=source, kind='USER_CORRECTION')
        reentry = self.prepare('REENTRY')
        self.assertEqual(reentry['input_version'], 2)
        self.assertEqual(reentry['rounds'][0]['status'], 'SUPERSEDED_NOT_SENT')

    def test_deadline_releases_phase_without_waiting_for_late_body_or_rewriting_packet(self):
        self.create()
        self.native_return()
        prepared = self.prepare()
        self.server.release.clear()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.run_prepared, prepared)
            try:
                self.assertTrue(self.server.overlapped.wait(3))
                council.advance_barrier(self.root, 'one', now=datetime.now(timezone.utc) + timedelta(seconds=600))
                packet_before = council.read_packet(self.root, 'one', actor='native-1', stage='REDELIBERATION')
            finally:
                self.server.release.set()
            future.result(4)
        result = council.inspect_council(self.root, 'one')
        self.assertEqual(len(result['late_results']), 2)
        self.assertTrue(all(side['status'] == 'TIMEOUT' for side in result['cycle']['members'].values()))
        packet_after = council.read_packet(self.root, 'one', actor='native-1', stage='REDELIBERATION')
        self.assertEqual(packet_before, packet_after)
        self.assertFalse(council.completion_status(self.root)['complete'])
        late_exchange = result['late_results'][0]['exchange_id']
        updated = council.reenter_late_result(self.root, 'one', exchange_id=late_exchange)
        self.assertEqual(updated['cycle_id'], 2)
        self.assertEqual(len(self.server.requests), 2, 'reenter-late must not resend the old request')

    def test_real_short_deadline_returns_with_explicit_timeout(self):
        self.create(deadline=1)
        self.native_return()
        self.server.delay = 1.5
        prepared = self.prepare()
        started = time.monotonic()
        result = self.run_prepared(prepared)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 1.4)
        self.assertEqual(result['phase'], 'REDELIBERATION')
        self.assertFalse(result['cycle']['barrier']['research_complete'])
        # Let capped HTTP calls finish recording before deleting their task.
        until = time.monotonic() + 3
        while council.completion_status(self.root)['active_councils'] and time.monotonic() < until:
            time.sleep(.02)
        self.assertFalse(council.completion_status(self.root)['active_councils'])

    def test_scope_cannot_cross_member_or_formal_consult_and_packets_are_immutable(self):
        self.create()
        prepared = self.prepare()
        jobs = prepared['rounds'][0]['jobs']
        scope = dict(jobs['member-1']['scope'])
        scope['line_id'] = 'one/member-2'
        with self.assertRaisesRegex(ValueError, 'research line'):
            council.require_member_scope(self.root, scope)
        packet_path = self.root / 'councils' / 'one' / 'packet-1.json'
        packet_path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'packet changed'):
            council.read_packet(self.root, 'one', actor='native-1')

    def test_explicit_close_preserves_unfinished_scope_and_cli_has_no_implicit_send(self):
        self.create(enable=False)
        council.close_council(self.root, 'one', reason='User stops this specific research scope before redeliberation.')
        status = council.completion_status(self.root)
        self.assertTrue(status['complete'])
        self.assertFalse(status['councils'][0]['closure']['pending_work_completed'])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(council_cli(['inspect', '--root', str(self.root), '--council-id', 'one']), 0)
        self.assertEqual(len(self.server.requests), 0)

    def test_deadline_cannot_be_retroactively_filled_by_a_late_native_return(self):
        self.create(enable=False)
        council.advance_barrier(self.root, 'one', now=datetime.now(timezone.utc) + timedelta(seconds=600))
        with self.assertRaisesRegex(ValueError, 'initial actor'):
            self.native_return()
        info = council.inspect_council(self.root, 'one')
        self.assertEqual(info['cycle']['native']['native-1']['status'], 'TIMEOUT')
        self.assertFalse(info['cycle']['barrier']['research_complete'])

    def test_closing_unsent_prepared_round_does_not_claim_a_paid_attempt_or_native_completion(self):
        self.create()
        self.prepare()
        council.close_council(self.root, 'one', reason='Explicit synthetic stop before any inference.')
        info = council.inspect_council(self.root, 'one')
        self.assertEqual(info['rounds'][0]['status'], 'CANCELLED_NOT_SENT')
        status = council.completion_status(self.root)
        self.assertTrue(status['complete'])
        self.assertFalse(status['councils'][0]['complete'])
        self.assertEqual(status['councils'][0]['native_redeliberations'], [])
        self.assertEqual(len(self.server.requests), 0)

    def _two_native_actors(self):
        council.create_council(self.root, council_id='one', native_actors=['native-a', 'native-b'])

    def _return_actor(self, actor, version, *, reconsider=False):
        if reconsider:
            return council.submit_redeliberation(self.root, 'one', actor=actor,
                output_path=self.redeliberation, input_version=version)
        return council.submit_native_initial(self.root, 'one', actor=actor,
            output_path=self.native, input_version=version)

    def test_new_cycle_migrates_unfinished_initial_actor_outside_event_scope(self):
        self._two_native_actors()
        self._return_actor('native-a', 1)
        event = self.file('narrow-event.txt', 'Relevant candidate for A; B still owes independent work.')
        info = council.publish_event(self.root, 'one', input_path=event, kind='CANDIDATE',
                                     native_actors=['native-a'], members=[])
        self.assertEqual(set(info['cycle']['native']), {'native-a', 'native-b'})
        self.assertEqual(info['cycle_history'][0]['resolution']['native_actors'], ['native-a', 'native-b'])
        self._return_actor('native-a', 2)
        self.assertFalse(council.completion_status(self.root)['complete'])
        with self.assertRaisesRegex(ValueError, 'current assigned'):
            self._return_actor('native-a', 2, reconsider=True)
        self._return_actor('native-b', 2)
        self._return_actor('native-a', 2, reconsider=True)
        self.assertFalse(council.completion_status(self.root)['complete'])
        self._return_actor('native-b', 2, reconsider=True)
        self.assertTrue(council.completion_status(self.root)['complete'])

    def test_new_cycle_migrates_missing_redeliberation_but_not_already_returned_unrelated_actor(self):
        self._two_native_actors()
        for actor in ('native-a', 'native-b'):
            self._return_actor(actor, 1)
        self._return_actor('native-a', 1, reconsider=True)
        event = self.file('b-event.txt', 'Only B is newly affected; B also owes the previous reconsideration.')
        info = council.publish_event(self.root, 'one', input_path=event, kind='CANDIDATE',
                                     native_actors=['native-b'], members=[])
        self.assertEqual(set(info['cycle']['native']), {'native-b'})
        self.assertEqual(info['cycle_history'][0]['resolution']['native_actors'], ['native-b'])
        self._return_actor('native-b', 2)
        self.assertFalse(council.completion_status(self.root)['complete'])
        self._return_actor('native-b', 2, reconsider=True)
        self.assertTrue(council.completion_status(self.root)['complete'])
        # An unrelated, fully returned B must not be revived from cycle one's
        # historical missing-entry record after its duty was validly migrated.
        info = council.publish_event(self.root, 'one', input_path=event, kind='NEW_A_MATERIAL',
                                     native_actors=['native-a'], members=[])
        self.assertEqual(set(info['cycle']['native']), {'native-a'})

    def test_new_cycle_keeps_unsealed_member_lines_even_when_event_names_only_one(self):
        self.create()
        event = self.file('member-event.txt', 'A new source for one member cannot discard the other unfinished line.')
        info = council.publish_event(self.root, 'one', input_path=event, kind='SOURCE',
                                     members=['member-1'])
        self.assertEqual(set(info['cycle']['members']), {'member-1', 'member-2'})
        resolution = info['cycle_history'][0]['resolution']
        self.assertEqual(resolution['members'], ['member-1', 'member-2'])
        self.assertFalse(council.completion_status(self.root)['complete'])

    @unittest.skipUnless(os.name == 'nt', 'Windows delete-sharing race')
    def test_atomic_council_write_waits_for_an_actual_concurrent_windows_reader(self):
        self.create(enable=False)
        path = self.root / 'councils' / 'one' / 'council.json'
        original_bytes = path.read_bytes()
        value = json.loads(original_bytes)
        value['reader_race_test'] = 'Only this exact local replacement may be retried.'
        sharing_denied = threading.Event()
        original_replace = Path.replace

        def observed_replace(source, target):
            try:
                return original_replace(source, target)
            except OSError as error:
                if getattr(error, 'winerror', None) in {5, 32, 33}:
                    sharing_denied.set()
                raise

        with patch.object(Path, 'replace', observed_replace):
            with ThreadPoolExecutor(1) as pool:
                with path.open('rb') as reader:
                    future = pool.submit(council._write, path, value)
                    self.assertTrue(sharing_denied.wait(.8), 'fixture did not exercise an actual Windows sharing denial')
                    self.assertEqual(reader.read(), original_bytes)
                future.result(2)
        self.assertEqual(json.loads(path.read_text())['reader_race_test'], value['reader_race_test'])
        self.assertEqual(len(self.server.requests), 0)

    def test_atomic_council_write_does_not_retry_permanent_permission_failure(self):
        target = self.file('permanent.json', '{"old": true}\n')
        with patch.object(Path, 'replace', side_effect=PermissionError('permanent non-sharing permission failure')) as replace:
            with self.assertRaises(PermissionError):
                council._write(target, {'new': True})
        self.assertEqual(replace.call_count, 1)
        self.assertEqual(json.loads(target.read_text()), {'old': True})


if __name__ == '__main__':
    unittest.main()
