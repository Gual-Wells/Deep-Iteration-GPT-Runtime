from __future__ import annotations

from datetime import datetime, timezone, timedelta
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import base64
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from runtime import codex_consult as consult
from runtime import codex_paper as paper
from runtime.codex_lifecycle import handle_message, ingest_message, terminate_message
from runtime.codex_session import create_session
from tools.codex_consult import main as consult_cli

ROOT = Path(__file__).resolve().parents[1]
PIN = '0.10.0@' + 'b' * 40
SECRET = 'FAKE_LOCALHOST_KEY_NEVER_PERSIST'
HIDDEN = 'HIDDEN_REASONING_SENTINEL_NEVER_PERSIST'
PUBLIC = '先让读者看完整系统图，再沿一次真实请求解释符号。\r\nKeep this exact draft.\n'


class ConsultFaultHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.get_calls.append(self.path)
        raw = json.dumps({'data': {'id': self.server.reconcile_id, 'total_cost': .02,
                                   'reasoning': HIDDEN}}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        label = self.path.strip('/')
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.post_calls.append({'label': label, 'request': request})
        self.assert_auth_header = self.headers.get('Authorization')
        if label == 'redirect':
            self.send_response(307)
            self.send_header('Location', '/redirect-target')
            self.end_headers()
            return
        self.send_response(400 if label == 'rejected' else 200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('X-Generation-Id', 'gen-local-' + label)
        if label == 'disconnect':
            self.send_header('Content-Length', '99999')
            self.end_headers()
            self.wfile.flush()
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        response = {'id': 'gen-local-' + label, 'model': 'actual/provider-model', 'provider': 'localhost',
                    'choices': [{'finish_reason': 'stop', 'message': {'content': PUBLIC,
                        'reasoning': HIDDEN, 'reasoning_details': [{'text': HIDDEN}]}}],
                    'usage': {'cost': .03, 'prompt_tokens': 100, 'completion_tokens': 200,
                              'completion_tokens_details': {'reasoning_tokens': 100, 'unknown_private': HIDDEN}},
                    'arbitrary_hidden_state': HIDDEN}
        if label == 'no-cost':
            response['usage'].pop('cost')
        elif label == 'reasoning-only':
            response['choices'][0]['message']['content'] = ''
            response['choices'][0]['finish_reason'] = 'length'
        elif label == 'body-error':
            response['error'] = {'code': 502, 'message': SECRET + HIDDEN}
            response['choices'][0]['finish_reason'] = 'error'
        elif label == 'over-ceiling':
            response['usage']['cost'] = .75
        elif label == 'conflicting-id':
            response['id'] = 'gen-not-the-header'
        elif label == 'rejected':
            response = {'error': {'code': 400, 'message': SECRET + HIDDEN}}
        elif label == 'invalid-cost':
            response['usage']['cost'] = True
        elif label == 'paper-model-confirmed':
            response['model'] = consult.DEFAULT_MODEL
        elif label == 'paper-model-missing':
            response.pop('model')
        elif label == 'paper-model-different-sonnet':
            response['model'] = 'anthropic/claude-sonnet-4.6'
        raw = json.dumps(response, ensure_ascii=False).encode('utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class ConsultPublicRuntimeTests(unittest.TestCase):
    def setUp(self):
        cache = (ROOT / '.cache').resolve()
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='codex-consult-test-', dir=cache)
        self.folder = Path(self.temp.name).resolve()
        if not self.folder.is_relative_to(cache) or not self.folder.name.startswith('codex-consult-test-'):
            raise RuntimeError('refusing cleanup outside the intended task cache')
        self.addCleanup(self.temp.cleanup)
        self.root = self.folder / 'task'
        self.original = self.file('user.txt', 'DIGRC：做有完整原件依据的内容与设计。\n')
        create_session(self.root, request=self.original, p_run=PIN)
        self.input = self.file('input.txt', '请发展一份可用的解释；原始约束见本条真实输入。\n')
        self.material = self.file('source.txt', 'Original source: A routes to B.\n')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), ConsultFaultHandler)
        self.server.post_calls = []
        self.server.get_calls = []
        self.server.reconcile_id = 'gen-local-disconnect'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def file(self, name, text):
        path = self.folder / name
        path.write_text(text, encoding='utf-8', newline='')
        return path

    def config(self, label):
        return self.file('private-' + label + '.json', json.dumps({
            'endpoint': f'http://127.0.0.1:{self.server.server_port}/' + label,
            'api_key_env': 'DIGR_TEST_CONSULT_KEY', 'timeout_seconds': 2}))

    def facts(self, *, total=1, wallet=10, **kw):
        result = {'authorization_ref': 'Constructed localhost-only test; no real paid API scope',
                  'checked_at': datetime.now(timezone.utc).isoformat(), 'model': consult.DEFAULT_MODEL,
                  'pricing_ref': 'Constructed rates for fake HTTP provider',
                  'budget_total_usd': total, 'outside_spent_usd': 0, 'wallet_remaining_usd': wallet,
                  'prompt_usd_per_million': 2, 'completion_usd_per_million': 10,
                  'input_tokens_upper_bound': 1000, 'input_bound_basis': 'Constructed all-message test upper bound'}
        result.update(kw)
        return result

    def prepare(self, label, **kw):
        kw.setdefault('max_tokens', 16000)  # Explicit bounded localhost fixture, not a model capability default.
        return consult.prepare_request(self.root, input_path=self.input, materials=[self.material],
                                       exchange_id=label, **kw)

    def test_stale_cost_facts_never_send_a_generation(self):
        self.prepare('stale')
        facts = self.facts(checked_at=(datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat())
        with self.assertRaisesRegex(ValueError, 'Refresh actual'):
            with patch.dict(os.environ, {'DIGR_TEST_CONSULT_KEY': SECRET}):
                consult.call_once(self.root, 'stale', facts=facts, ceiling_usd=.20,
                                  config_path=self.config('normal'))
        self.assertEqual(self.server.post_calls, [])

    def test_explicit_proxy_is_used_without_persisting_private_config(self):
        self.prepare('proxy')
        config = self.file('proxy-config.json', json.dumps({
            'endpoint': 'http://127.0.0.1:9/normal',
            'proxy_url': f'http://127.0.0.1:{self.server.server_port}',
            'api_key_env': 'DIGR_TEST_CONSULT_KEY', 'timeout_seconds': 2}))
        with patch.dict(os.environ, {'DIGR_TEST_CONSULT_KEY': SECRET}), patch('urllib.request.proxy_bypass', return_value=False):
            result = consult.call_once(self.root, 'proxy', facts=self.facts(), ceiling_usd=.20,
                                       config_path=config)
        self.assertEqual(len(self.server.post_calls), 1)
        self.assertIn('127.0.0.1:9/normal', self.server.post_calls[0]['label'])
        self.assertEqual(result['exchange']['public_status'], 'COMPLETE')

    def call(self, label, *, facts=None, ceiling=.2):
        with patch.dict(os.environ, {'DIGR_TEST_CONSULT_KEY': SECRET}):
            return consult.call_once(self.root, label, facts=facts or self.facts(), ceiling_usd=ceiling,
                                      config_path=self.config(label))

    def public_files(self):
        return [path for path in (self.root / 'consult').rglob('*') if path.is_file() and path.name != '.writer.lock']

    def authoring_fixture(self, label='authoring', *, invocation='DIGRP', same_user_text=False):
        folder = self.folder / label
        folder.mkdir()
        original = folder / 'actual-user.txt'
        original.write_text(invocation + '：保留完整论文，以一次真实请求讲清给初学读者。\n', encoding='utf-8')
        task = folder / 'task'
        pin = '0.11.0@' + 'd' * 40
        create_session(task, request=original, p_run=pin, visits_path=folder / 'visits', run_id=label)
        selection = folder / 'actual-paper-selection.txt'
        if same_user_text:
            selection.write_bytes(original.read_bytes())
        else:
            selection.write_text('这两篇各自完整处理；允许各篇发展自己的讲法。\n', encoding='utf-8')
        batch = folder / 'batch'
        paper.initialize(batch, p_run=pin, authorization=selection, source_ref=label + '-paper-choice', task_root=task)
        parameters = {'N': 2, 'T': '0min', 'R': 1, 'B': 0,
                      'S': {'n': 0, 't': '0min', 'r': 0, 'b': 0}, 'D': 0, 'V': 0, 'L': 3}
        roots = []
        for paper_id, title, line, sentinel in (
                ('first', 'First selected source identity', 'M01', 'FIRST_ORIGINAL_NOT_SENT_BY_INVENTORY'),
                ('second', 'OTHER_PAPER_TITLE_MUST_STAY_OUT', 'M02', 'OTHER_PAPER_CONTENT_MUST_STAY_OUT')):
            selected = Path(paper.add_paper(batch, paper_id=paper_id, title=title, line=line,
                owner='synthetic-native-host', parameters=parameters)['paper_root'])
            source = folder / (paper_id + '-original.txt')
            source.write_text(sentinel, encoding='utf-8')
            paper.register_source(selected, {'id': paper_id + '-source', 'path': str(source),
                'pages': 3, 'identity': title}, expected_revision=0, operation_id=paper_id + '-source')
            roots.append(selected)
        return task, batch, roots

    def authoring_call(self, task, exchange_id):
        with patch.dict(os.environ, {'DIGR_TEST_CONSULT_KEY': SECRET}):
            return consult.call_once(task, exchange_id, facts=self.facts(), ceiling_usd=.2,
                                     config_path=self.config(exchange_id))

    def test_actual_sources_are_prepared_then_transmitted_and_public_draft_is_byte_exact(self):
        prepared = self.prepare('complete', input_revision='revision-one')
        self.assertEqual(prepared['exchange']['sources'][1]['transmission'], 'PREPARED_NOT_SENT')
        self.assertEqual(self.server.post_calls, [])
        result = self.call('complete')
        record = result['exchange']
        self.assertEqual(record['transport_status'], 'RESPONDED')
        self.assertEqual(record['public_status'], 'COMPLETE')
        self.assertEqual(record['billing_status'], 'KNOWN')
        self.assertEqual(record['response_model'], 'actual/provider-model')
        self.assertEqual(Path(result['public_path']).read_bytes(), PUBLIC.encode('utf-8'))
        body = self.server.post_calls[0]['request']
        self.assertIn('Original source: A routes to B.', body['messages'][-1]['content'])
        self.assertEqual(body['reasoning'], {'effort': 'high', 'exclude': True})
        self.assertEqual(body['provider']['max_price']['completion'], 10)
        self.assertEqual(record['sources'][1]['sha256'], sha256(self.material.read_bytes()).hexdigest())
        self.assertTrue(all(s['transmission'] == 'RESPONSE_OBSERVED' for s in record['sources']))
        serialized = '\n'.join(path.read_text(encoding='utf-8') for path in self.public_files())
        self.assertNotIn(SECRET, serialized)
        self.assertNotIn(HIDDEN, serialized)
        self.assertFalse(record['native_responsibility_credit'])

    def test_cost_unknown_does_not_discard_good_public_guidance_or_turn_into_zero_cost(self):
        self.prepare('no-cost')
        result = self.call('no-cost')
        self.assertEqual(result['exchange']['public_status'], 'COMPLETE')
        self.assertEqual(result['exchange']['billing_status'], 'UNKNOWN')
        self.assertEqual(result['totals']['known_cost_usd'], 0)
        self.assertEqual(result['totals']['unresolved_reserved_usd'], .2)
        self.assertEqual(Path(result['public_path']).read_bytes(), PUBLIC.encode('utf-8'))
        with self.assertRaisesRegex(ValueError, 'already started'):
            self.call('no-cost')
        self.assertEqual(len(self.server.post_calls), 1)

    def test_http200_reasoning_only_and_body_error_have_distinct_content_and_bill_facts(self):
        self.prepare('reasoning-only')
        empty = self.call('reasoning-only')['exchange']
        self.assertEqual(empty['public_status'], 'ABSENT')
        self.assertEqual(empty['known_cost_usd'], .03)
        self.assertEqual(empty['finish_reason'], 'length')
        self.prepare('body-error')
        error = self.call('body-error')['exchange']
        self.assertEqual(error['http_status'], 200)
        self.assertEqual(error['public_status'], 'PARTIAL')
        self.assertEqual(error['provider_error_code'], 502)
        self.assertNotIn('message', error)

    def test_disconnect_preserves_header_id_and_cost_get_cannot_fabricate_lost_advice(self):
        self.prepare('disconnect')
        result = self.call('disconnect')
        self.assertEqual(result['exchange']['generation_id'], 'gen-local-disconnect')
        self.assertEqual(result['exchange']['transport_status'], 'OUTCOME_UNKNOWN')
        with patch.dict(os.environ, {'DIGR_TEST_CONSULT_KEY': SECRET}):
            recovered = consult.reconcile_cost(self.root, 'disconnect', config_path=self.config('disconnect'))
        self.assertEqual(recovered['exchange']['known_cost_usd'], .02)
        self.assertEqual(recovered['exchange']['public_status'], 'ABSENT')
        self.assertIsNone(recovered['public_path'])
        self.assertEqual(recovered['exchange']['transport_status'], 'OUTCOME_UNKNOWN')
        self.assertEqual(len(self.server.post_calls), 1)
        self.assertEqual(len(self.server.get_calls), 1)

    def test_public_history_survives_fresh_reads_and_copies_only_observed_public_messages(self):
        self.prepare('complete')
        completed = self.call('complete')
        self.input.write_text('用户新纠正：保留系统图，先解释用途。\n', encoding='utf-8')
        second = self.prepare('followup', continue_from='complete', input_revision='revision-two')
        with open(second['request_path'], encoding='utf-8') as stream:
            messages = json.load(stream)['messages']
        self.assertEqual(messages[-2], {'role': 'assistant', 'content': PUBLIC})
        self.assertEqual(len(messages), 4)
        self.assertIn('用户新纠正', messages[-1]['content'])
        self.assertEqual(completed['exchange']['public_sha256'],
                         sha256(Path(completed['public_path']).read_bytes()).hexdigest())
        self.assertNotIn(HIDDEN, json.dumps(messages))
        Path(completed['public_path']).write_text('accidental overwrite', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'public output changed'):
            self.prepare('bad-history', continue_from='complete')

    def test_all_task_exchanges_reserve_budget_and_allow_a_distinct_call_only_when_it_fits(self):
        self.prepare('no-cost')
        self.call('no-cost', facts=self.facts(total=.35))
        self.prepare('complete')
        with self.assertRaisesRegex(ValueError, 'remaining task/wallet'):
            self.call('complete', facts=self.facts(total=.35))
        self.assertEqual(len(self.server.post_calls), 1)
        # A genuinely different call can proceed if its ceiling still fits,
        # without auto-repeating the unresolved one.
        result = self.call('complete', facts=self.facts(total=.5))
        self.assertEqual(result['totals']['unresolved_reserved_usd'], .2)
        self.assertEqual(result['totals']['known_cost_usd'], .03)

    def test_process_exit_keeps_public_conversation_and_reservations_for_the_next_process(self):
        self.prepare('no-cost')
        facts = self.file('cost-facts.json', json.dumps(self.facts()))
        config = self.config('no-cost')
        child = subprocess.run([sys.executable, '-B', str(ROOT / 'tools' / 'codex_consult.py'),
            'call', '--root', str(self.root), '--exchange-id', 'no-cost', '--facts', str(facts),
            '--ceiling-usd', '.2', '--config', str(config)], capture_output=True, text=True,
            encoding='utf-8', env={**os.environ, 'DIGR_TEST_CONSULT_KEY': SECRET},
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, check=False)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertNotIn(SECRET, child.stdout + child.stderr)
        self.assertNotIn(HIDDEN, child.stdout + child.stderr)
        recovered = consult.inspect_exchange(self.root, 'no-cost')
        self.assertEqual(recovered['totals']['unresolved_reserved_usd'], .2)
        self.input.write_text('新事实：这张图的标签已经校正。', encoding='utf-8')
        followup = self.prepare('followup', continue_from='no-cost')
        messages = json.loads(Path(followup['request_path']).read_text(encoding='utf-8'))['messages']
        self.assertEqual(messages[-2]['content'], PUBLIC)
        with self.assertRaisesRegex(ValueError, 'already started'):
            self.call('no-cost')
        self.assertEqual(len(self.server.post_calls), 1)

    def test_report_real_cost_above_ceiling_and_reject_next_over_budget_call(self):
        self.prepare('over-ceiling')
        result = self.call('over-ceiling', facts=self.facts(total=.8))
        self.assertTrue(result['exchange']['call_ceiling_exceeded'])
        self.assertEqual(result['totals']['known_cost_usd'], .75)
        self.prepare('complete')
        with self.assertRaisesRegex(ValueError, 'remaining task/wallet'):
            self.call('complete', facts=self.facts(total=.8))

    def test_later_actual_cost_readback_updates_budget_without_erasing_original_usage(self):
        self.prepare('complete')
        self.call('complete')
        result = consult.reconcile_cost(self.root, 'complete', metadata={'id': 'gen-local-complete', 'total_cost': .8})
        self.assertEqual(result['exchange']['usage']['cost'], .03)
        self.assertEqual(result['exchange']['known_cost_usd'], .8)
        self.assertTrue(result['exchange']['cost_changed_on_readback'])
        self.assertTrue(result['exchange']['call_ceiling_exceeded'])
        self.prepare('next')
        with self.assertRaisesRegex(ValueError, 'remaining task/wallet'):
            self.call('next', facts=self.facts(total=.9))

    def test_missing_or_wrong_price_facts_never_make_a_post(self):
        self.prepare('complete')
        for facts in (self.facts(model='wrong/model'), self.facts(wallet_remaining_usd=.01),
                      self.facts(input_tokens_upper_bound=True), self.facts(authorization_ref=''),
                      self.facts(completion_usd_per_million=1000)):
            with self.subTest(facts=facts), self.assertRaises(ValueError):
                self.call('complete', facts=facts)
        self.assertEqual(self.server.post_calls, [])
        self.assertEqual(consult.inspect_exchange(self.root, 'complete')['exchange']['transport_status'], 'PREPARED')

    def test_current_user_stop_fences_generation_but_allows_history_and_cost_readback(self):
        self.prepare('no-cost')
        self.call('no-cost')
        self.prepare('next')
        source = self.file('stop.txt', '停止这个任务。\n')
        terminate_message(self.root, action='stop', reason='Actual constructed stop',
                          source=source, source_ref='test-stop')
        with self.assertRaisesRegex(ValueError, 'STOPPED'):
            self.call('next')
        result = consult.reconcile_cost(self.root, 'no-cost', metadata={'data': {'id': 'gen-local-no-cost', 'total_cost': .02}})
        self.assertEqual(result['task_status'], 'STOPPED')
        self.assertEqual(len(self.server.post_calls), 1)

    def test_pending_user_correction_is_visible_and_cannot_be_silently_ignored_by_new_call(self):
        self.prepare('complete')
        source = self.file('correction.txt', '保留原图；不要重写成另一篇内容。\n')
        ingest_message(self.root, source=source, source_ref='test-correction')
        self.assertTrue(consult.inspect_exchange(self.root, 'complete')['newer_user_input_since_prepare'])
        with self.assertRaisesRegex(ValueError, 'pending'):
            self.call('complete')
        self.assertEqual(self.server.post_calls, [])

    def test_generation_id_conflict_keeps_cost_unknown_and_rejects_wrong_reconciliation(self):
        self.prepare('conflicting-id')
        record = self.call('conflicting-id')['exchange']
        self.assertTrue(record['generation_id_mismatch'])
        self.assertEqual(record['billing_status'], 'UNKNOWN')
        with self.assertRaisesRegex(ValueError, 'Conflicting generation'):
            consult.reconcile_cost(self.root, 'conflicting-id', metadata={'id': 'gen-local-conflicting-id', 'total_cost': .02})

    def test_redirect_does_not_forward_credential_or_repeat_post(self):
        self.prepare('redirect')
        result = self.call('redirect')
        self.assertEqual(result['exchange']['transport_status'], 'OUTCOME_UNKNOWN')
        self.assertEqual([item['label'] for item in self.server.post_calls], ['redirect'])

    def test_explicit_rejection_without_cost_keeps_unknown_reservation_and_no_public_draft(self):
        self.prepare('rejected')
        result = self.call('rejected')
        self.assertEqual(result['exchange']['http_status'], 400)
        self.assertEqual(result['exchange']['billing_status'], 'UNKNOWN')
        self.assertIsNone(result['public_path'])
        self.prepare('invalid-cost')
        invalid = self.call('invalid-cost')['exchange']
        self.assertEqual(invalid['billing_status'], 'UNKNOWN')

    def test_cli_composes_prepare_and_inspect_without_secret_or_network(self):
        output = io.StringIO()
        with patch('sys.stdout', output):
            code = consult_cli(['prepare', '--root', str(self.root), '--input', str(self.input),
                                '--material', str(self.material), '--exchange-id', 'cli'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['exchange']['exchange_id'], 'cli')
        output = io.StringIO()
        with patch('sys.stdout', output):
            code = consult_cli(['inspect', '--root', str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(self.server.post_calls, [])

    def test_nonsecret_default_locator_references_synthetic_private_json_without_copying_secret(self):
        self.prepare('complete')
        host_home = self.folder / 'synthetic-codex-home'
        locator_directory = host_home / 'digr-codex'
        locator_directory.mkdir(parents=True)
        credential = self.folder / 'synthetic-credential.json'
        credential.write_text(json.dumps({'apiKey': SECRET, 'unused': HIDDEN}), encoding='utf-8')
        locator = locator_directory / 'consult.json'
        locator.write_text(json.dumps({'endpoint': f'http://127.0.0.1:{self.server.server_port}/complete',
            'api_key_file': str(credential), 'api_key_field': 'apiKey'}), encoding='utf-8')
        with patch.dict(os.environ, {'CODEX_HOME': str(host_home), 'DIGR_CONSULT_CONFIG': ''}):
            result = consult.call_once(self.root, 'complete', facts=self.facts(), ceiling_usd=.2)
        self.assertEqual(result['exchange']['billing_status'], 'KNOWN')
        self.assertEqual(len(result['public_outputs']), 1)
        self.assertFalse(result['public_outputs'][0]['guidance_implementation_verified'])
        self.assertEqual(result['local_path'], (self.root / 'consult').as_posix())
        self.assertNotIn(SECRET, json.dumps(result))
        serialized = '\n'.join(path.read_text(encoding='utf-8') for path in self.public_files())
        self.assertNotIn(SECRET, serialized)
        self.assertNotIn(HIDDEN, serialized)

    def test_selected_image_bytes_are_actually_in_the_public_request(self):
        raw = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+yjX8AAAAASUVORK5CYII=')
        image = self.folder / 'original.png'
        image.write_bytes(raw)
        result = consult.prepare_request(self.root, input_path=self.input, images=[image], exchange_id='image')
        request = json.loads(Path(result['request_path']).read_text(encoding='utf-8'))
        transmitted = request['messages'][-1]['content'][-1]['image_url']['url']
        self.assertEqual(base64.b64decode(transmitted.split(',', 1)[1]), raw)
        self.assertEqual(result['exchange']['sources'][-1]['sha256'], sha256(raw).hexdigest())
        self.assertEqual(self.server.post_calls, [])

    def test_process_crash_releases_the_os_writer_lock_without_a_stale_permission_state(self):
        code = ('from pathlib import Path\nimport os, sys\n'
                'from runtime.codex_consult import _writer\n'
                'with _writer(Path(sys.argv[1])):\n    os._exit(17)\n')
        child = subprocess.run([sys.executable, '-B', '-c', code, str(self.root)], cwd=ROOT,
            capture_output=True, text=True, encoding='utf-8', check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        self.assertEqual(child.returncode, 17, child.stderr)
        self.assertEqual(self.prepare('after-crash')['exchange']['transport_status'], 'PREPARED')

    def test_interrupted_unsent_request_finalization_can_resume_without_replaying_inference(self):
        self.prepare('complete')
        original_write = consult._write_bytes
        def crash_after_request_file(path, raw, *, new=False):
            original_write(path, raw, new=new)
            if path.name == 'request.json':
                raise SystemExit('Constructed process interruption before any durable send intent')
        with patch.object(consult, '_write_bytes', crash_after_request_file):
            with self.assertRaises(SystemExit):
                self.call('complete')
        self.assertEqual(self.server.post_calls, [])
        self.assertEqual(consult.inspect_exchange(self.root, 'complete')['exchange']['transport_status'], 'PREPARED')
        self.assertEqual(self.call('complete')['exchange']['transport_status'], 'RESPONDED')
        self.assertEqual(len(self.server.post_calls), 1)

    def test_native_and_old_pinned_sessions_do_not_silently_gain_consult(self):
        request = self.file('native.txt', 'DIGR：保留普通原生工作。\n')
        native = self.folder / 'native'
        create_session(native, request=request, p_run=PIN)
        with self.assertRaisesRegex(ValueError, 'explicitly initialized'):
            consult.prepare_request(native, input_path=self.input)
        old = self.folder / 'old-paper'
        paper_request = self.file('paper.txt', 'DIGRP：只处理这个旧任务的论文。\n')
        create_session(old, request=paper_request, p_run='0.9.0@' + 'c' * 40)
        with self.assertRaisesRegex(ValueError, 'explicitly initialized'):
            consult.prepare_request(old, input_path=self.input)

    def test_native_parent_real_selected_paper_addon_enables_only_verified_new_pin_scope(self):
        request = self.file('native-paper-task.txt', 'DIGR：按DIGRP处理这篇论文。\n')
        native = self.folder / 'native-paper-parent'
        metadata = create_session(native, request=request, p_run=PIN)
        self.assertEqual(metadata['execution_profile']['mode'], 'NATIVE')
        with self.assertRaisesRegex(ValueError, 'verified selected paper'):
            consult.prepare_request(native, input_path=self.input)
        batch = self.folder / 'actual-selected-paper-batch'
        selection = self.file('paper-selection.txt', '明确选择DIGRP处理这篇论文，保留原生父任务。\n')
        value = paper.initialize(batch, p_run=PIN, authorization=selection,
                                  source_ref='actual-paper-choice', task_root=native)
        parent = json.loads((native / 'session.json').read_text(encoding='utf-8'))
        self.assertEqual(parent['execution_profile']['mode'], 'NATIVE')
        prepared = consult.prepare_request(native, input_path=self.input, exchange_id='paper-scope', max_tokens=16000)
        self.assertEqual(prepared['exchange']['selected_paper_scopes'][0]['authorization_source_ref'], 'actual-paper-choice')
        self.assertEqual(parent['initial_invocation']['invocation_key'], 'DIGR')
        with patch.dict(os.environ, {'DIGR_TEST_CONSULT_KEY': SECRET}):
            called = consult.call_once(native, 'paper-scope', facts=self.facts(), ceiling_usd=.2,
                                       config_path=self.config('native-paper'))
        self.assertEqual(called['exchange']['public_status'], 'COMPLETE')
        self.assertEqual(json.loads((native / 'session.json').read_text(encoding='utf-8'))['execution_profile']['mode'], 'NATIVE')
        for key, changed in (('P_run', '0.10.0@' + 'a' * 40), ('task_root', str(self.folder / 'wrong-parent')),
                             ('consult_enabled', False), ('authorization_source_ref', 'different-selection')):
            invalid = dict(value, **{key: changed})
            (batch / 'batch.json').write_text(json.dumps(invalid), encoding='utf-8')
            with self.subTest(changed=key), self.assertRaisesRegex(ValueError, 'verified selected paper'):
                consult.prepare_request(native, input_path=self.input)
        (batch / 'batch.json').write_text(json.dumps(value), encoding='utf-8')
        parent.pop('consult_addons')
        (native / 'session.json').write_text(json.dumps(parent), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'verified selected paper'):
            consult.prepare_request(native, input_path=self.input)
        old = self.folder / 'old-native-with-forged-addon'
        old_pin = '0.9.0@' + 'e' * 40
        old_parent = create_session(old, request=request, p_run=old_pin)
        old_parent['consult_addons'] = [{'addon': 'paper', 'version': '0.4.0', 'batch': str(batch),
                                         'authorization_source_ref': 'actual-paper-choice'}]
        (old / 'session.json').write_text(json.dumps(old_parent), encoding='utf-8')
        (batch / 'batch.json').write_text(json.dumps(dict(value, P_run=old_pin, task_root=str(old))), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'verified selected paper'):
            consult.prepare_request(old, input_path=self.input)
        self.assertEqual(len(self.server.post_calls), 1)

    def test_paper_author_gets_actual_user_snapshots_and_only_selected_paper_inventory(self):
        task, _, papers = self.authoring_fixture()
        correction = self.file('author-correction.txt', '先解释原图里的排队时刻；不要照搬统一章节。\n')
        selected = ingest_message(task, source=correction, source_ref='author-correction')
        handle_message(task, message_id=selected['message_id'], action='continue', reason='Constructed relevant reader correction')
        correction.write_text('CHANGED_LOCATOR_IS_NOT_THE_CURRENT_MESSAGE', encoding='utf-8')
        prepared = consult.prepare_request(task, input_path=self.input, paper_root=papers[0],
                                           exchange_id='paper-author', max_tokens=16000)
        body = json.loads(Path(prepared['request_path']).read_text(encoding='utf-8'))
        system = body['messages'][0]['content']
        content = body['messages'][-1]['content']
        self.assertNotEqual(system, consult._SYSTEM)
        self.assertIn('author and content driver', system)
        for private in ('N/R/D/V', 'm1', 'mapping_contract', 'P_run', 'M01'):
            self.assertNotIn(private, system)
        self.assertIn('保留完整论文，以一次真实请求讲清给初学读者', content)
        self.assertIn('这两篇各自完整处理', content)
        self.assertIn('先解释原图里的排队时刻', content)
        self.assertNotIn('CHANGED_LOCATOR_IS_NOT_THE_CURRENT_MESSAGE', content)
        self.assertIn('HISTORICAL USER INPUT', content)
        self.assertIn('CURRENT MANAGED TASK USER MESSAGE', content)
        self.assertIn('First selected source identity', content)
        self.assertIn('NOT_TRANSMITTED_BY_INVENTORY', content)
        self.assertNotIn('FIRST_ORIGINAL_NOT_SENT_BY_INVENTORY', content)
        self.assertNotIn('OTHER_PAPER_TITLE_MUST_STAY_OUT', content)
        self.assertNotIn('OTHER_PAPER_CONTENT_MUST_STAY_OUT', content)
        scope = prepared['exchange']['authoring_scope']
        self.assertEqual(scope['paper_root'], papers[0].as_posix())
        self.assertEqual(scope['paper_id'], 'first')
        self.assertEqual(scope['authoring_contract'], 'sonnet-native-v1')
        self.assertEqual(body['user'], 'digr-paper-' + prepared['exchange']['authoring_scope_sha256'])
        self.assertEqual(self.server.post_calls, [])

    def test_paper_first_exchange_requires_explicit_selection_and_cli_expands_actual_content(self):
        task, batch, papers = self.authoring_fixture()
        with self.assertRaisesRegex(ValueError, 'explicit --paper-root'):
            consult.prepare_request(task, input_path=self.input)
        output = io.StringIO()
        source = batch.parent / 'first-original.txt'
        with patch('sys.stdout', output):
            code = consult_cli(['prepare', '--root', str(task), '--input', str(self.input),
                '--paper-root', str(papers[0]), '--material', str(source), '--exchange-id', 'paper-cli'])
        self.assertEqual(code, 0)
        prepared = json.loads(output.getvalue())
        body = json.loads(Path(prepared['request_path']).read_text(encoding='utf-8'))
        self.assertIn('FIRST_ORIGINAL_NOT_SENT_BY_INVENTORY', body['messages'][-1]['content'])
        self.assertEqual(self.server.post_calls, [])

    def test_author_continuation_replays_actual_public_work_without_cross_paper_or_generic_switch(self):
        task, _, papers = self.authoring_fixture(invocation='DIGRC')
        first = consult.prepare_request(task, input_path=self.input, paper_root=papers[0],
                                        exchange_id='paper-first', max_tokens=16000)
        self.authoring_call(task, 'paper-first')
        self.input.write_text('已取得你要的原图，下面只补图与一个确定事实。', encoding='utf-8')
        followup = consult.prepare_request(task, input_path=self.input, continue_from='paper-first',
                                           exchange_id='paper-next', max_tokens=16000)
        previous = json.loads(Path(first['request_path']).read_text(encoding='utf-8'))['messages']
        continued = json.loads(Path(followup['request_path']).read_text(encoding='utf-8'))['messages']
        self.assertEqual(continued[:-2], previous)
        self.assertEqual(continued[-2], {'role': 'assistant', 'content': PUBLIC})
        self.assertEqual(followup['exchange']['authoring_scope'], first['exchange']['authoring_scope'])
        with self.assertRaisesRegex(ValueError, 'another paper'):
            consult.prepare_request(task, input_path=self.input, continue_from='paper-first', paper_root=papers[1])
        generic = consult.prepare_request(task, input_path=self.input, exchange_id='generic-stays-generic', max_tokens=16000)
        body = json.loads(Path(generic['request_path']).read_text(encoding='utf-8'))
        self.assertEqual(body['messages'][0], {'role': 'system', 'content': consult._SYSTEM})
        self.assertNotIn('authoring_scope', generic['exchange'])
        self.authoring_call(task, 'generic-stays-generic')
        with self.assertRaisesRegex(ValueError, 'generic Consult'):
            consult.prepare_request(task, input_path=self.input, continue_from='generic-stays-generic', paper_root=papers[0])
        self.assertEqual(len(self.server.post_calls), 2)

    def test_handled_user_correction_fences_prepared_author_context_until_reprepared(self):
        task, _, papers = self.authoring_fixture()
        consult.prepare_request(task, input_path=self.input, paper_root=papers[0],
                                exchange_id='stale-paper', max_tokens=16000)
        correction = self.file('handled-paper-correction.txt', '保留我新选的图，撤销上一版配图决定。')
        selected = ingest_message(task, source=correction, source_ref='handled-paper-correction')
        handle_message(task, message_id=selected['message_id'], action='continue', reason='Constructed correction already handled by host')
        with self.assertRaisesRegex(ValueError, 'New user input'):
            self.authoring_call(task, 'stale-paper')
        self.assertEqual(self.server.post_calls, [])
        prepared = consult.prepare_request(task, input_path=self.input, paper_root=papers[0],
                                           exchange_id='current-paper', max_tokens=16000)
        body = json.loads(Path(prepared['request_path']).read_text(encoding='utf-8'))
        self.assertIn('撤销上一版配图决定', body['messages'][-1]['content'])

    def test_native_paper_history_remains_readable_when_current_selection_is_unavailable(self):
        task, batch, papers = self.authoring_fixture(invocation='DIGR')
        with self.assertRaisesRegex(ValueError, 'explicit --paper-root'):
            consult.prepare_request(task, input_path=self.input)
        consult.prepare_request(task, input_path=self.input, paper_root=papers[0],
                                exchange_id='native-paper-history', max_tokens=16000)
        value = json.loads((batch / 'batch.json').read_text(encoding='utf-8'))
        value['authoring_contract'] = 'not-the-selected-contract'
        (batch / 'batch.json').write_text(json.dumps(value), encoding='utf-8')
        observed = consult.inspect_exchange(task, 'native-paper-history')
        self.assertEqual(observed['exchange']['authoring_scope']['paper_id'], 'first')
        with self.assertRaisesRegex(ValueError, 'verified selected paper'):
            self.authoring_call(task, 'native-paper-history')
        self.assertEqual(self.server.post_calls, [])
        parent = json.loads((task / 'session.json').read_text(encoding='utf-8'))
        self.assertEqual(parent['execution_profile']['mode'], 'NATIVE')

    def test_old_paper_prompt_is_not_promoted_and_authoring_scope_edits_are_detected(self):
        old_batch = self.folder / 'old-consult-batch'
        paper.initialize(old_batch, p_run=PIN, authorization=self.original,
                         source_ref='old-consult-paper', task_root=self.root)
        prepared = self.prepare('old-paper-is-generic')
        body = json.loads(Path(prepared['request_path']).read_text(encoding='utf-8'))
        self.assertEqual(body['messages'][0], {'role': 'system', 'content': consult._SYSTEM})
        self.assertNotIn('authoring_scope', prepared['exchange'])
        with self.assertRaisesRegex(ValueError, 'registered paper 0.5'):
            consult.prepare_request(self.root, input_path=self.input, paper_root=old_batch / 'papers' / 'fake')
        task, _, papers = self.authoring_fixture()
        native = consult.prepare_request(task, input_path=self.input, paper_root=papers[0],
                                         exchange_id='scope-edited', max_tokens=16000)
        attempt_path = Path(native['request_path']).with_name('attempt.json')
        attempt = json.loads(attempt_path.read_text(encoding='utf-8'))
        attempt['authoring_scope']['paper_id'] = 'second'
        attempt['authoring_scope_sha256'] = sha256(consult._json_bytes(attempt['authoring_scope'])).hexdigest()
        attempt_path.write_text(json.dumps(attempt), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'authoring scope'):
            consult.inspect_exchange(task, 'scope-edited')

    def test_paper_model_requires_exact_observed_selected_sonnet_without_losing_paid_public_work(self):
        task, _, papers = self.authoring_fixture()
        for model in ('openai/gpt-5.5', 'anthropic/claude-opus-5.5', 'sonnet',
                      'anthropic/claude-sonnet-5.5:unverified-alias'):
            with self.subTest(requested=model), self.assertRaisesRegex(ValueError, 'canonical Anthropic Sonnet'):
                consult.prepare_request(task, input_path=self.input, paper_root=papers[0], model=model)
        generic = consult.prepare_request(self.root, input_path=self.input, model='openai/explicit-other-model',
                                           exchange_id='generic-other-model')
        generic_request = json.loads(Path(generic['request_path']).read_text(encoding='utf-8'))
        self.assertEqual(generic_request['model'], 'openai/explicit-other-model')
        self.assertNotIn('paper_model_identity', generic)
        for label, expected in (('paper-model-confirmed', 'CONFIRMED'),
                                ('paper-model-missing', 'UNCONFIRMED'),
                                ('paper-model-different-sonnet', 'UNCONFIRMED'),
                                ('paper-model-other-family', 'UNCONFIRMED')):
            prepared = consult.prepare_request(task, input_path=self.input, paper_root=papers[0],
                                               exchange_id=label, max_tokens=16000)
            self.assertEqual(prepared['paper_model_identity']['status'], 'UNCONFIRMED')
            result = self.authoring_call(task, label)
            with self.subTest(observed=label):
                self.assertEqual(result['paper_model_identity']['status'], expected)
                self.assertEqual(result['paper_model_identity']['requested_model'], consult.DEFAULT_MODEL)
                self.assertEqual(result['exchange']['public_status'], 'COMPLETE')
                self.assertEqual(result['exchange']['known_cost_usd'], .03)
                self.assertEqual(Path(result['public_path']).read_bytes(), PUBLIC.encode('utf-8'))
                with self.assertRaisesRegex(ValueError, 'already started'):
                    self.authoring_call(task, label)
        self.assertEqual(len(self.server.post_calls), 4)

    def test_identical_paper_user_bodies_expand_once_but_keep_all_three_source_roles(self):
        task, _, papers = self.authoring_fixture(same_user_text=True)
        prepared = consult.prepare_request(task, input_path=self.input, paper_root=papers[0],
                                           exchange_id='one-user-body', max_tokens=16000)
        body = json.loads(Path(prepared['request_path']).read_text(encoding='utf-8'))['messages'][-1]['content']
        original = (task / 'REQUEST.txt').read_bytes().decode('utf-8-sig')
        self.assertEqual(body.count(original), 1)
        sources = prepared['exchange']['sources'][:3]
        self.assertEqual([item['kind'] for item in sources],
                         ['ORIGINAL_TASK_INPUT', 'PAPER_SELECTION_INPUT', 'CURRENT_USER_INPUT_SNAPSHOT'])
        self.assertEqual([item['content_representation'] for item in sources],
                         ['INLINE', 'EXACT_BODY_REFERENCE', 'EXACT_BODY_REFERENCE'])
        self.assertTrue(all(item['public_body_sha256'] == sha256(original.encode('utf-8')).hexdigest()
                            and item['sha256'] for item in sources))
        self.assertIn('RECORDED PAPER SELECTION - HISTORICAL USER INPUT', body)
        self.assertIn('CURRENT MANAGED TASK USER MESSAGE', body)
        self.assertIn('message_id=0', body)
        self.assertIn('also the current user message', body)
        correction_text = '改为从原图的排队时刻进入；原先完整范围仍保留。\n'
        correction = self.file('distinct-user-body.txt', correction_text)
        selected = ingest_message(task, source=correction, source_ref='distinct-user-body')
        handle_message(task, message_id=selected['message_id'], action='continue', reason='Constructed distinct current correction')
        current = consult.prepare_request(task, input_path=self.input, paper_root=papers[0],
                                          exchange_id='distinct-current-body', max_tokens=16000)
        content = json.loads(Path(current['request_path']).read_text(encoding='utf-8'))['messages'][-1]['content']
        self.assertEqual(content.count(original), 1)
        self.assertEqual(content.count(correction_text), 1)
        self.assertEqual(current['exchange']['sources'][2]['content_representation'], 'INLINE')
        self.assertEqual(current['exchange']['sources'][2]['message_id'], 1)
        self.assertIn('message_id=1', content)
        self.assertEqual(self.server.post_calls, [])


if __name__ == '__main__':
    unittest.main()
