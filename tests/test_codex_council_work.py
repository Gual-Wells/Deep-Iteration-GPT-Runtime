"""Native work discovery, local return and paid-path identity using only localhost."""
from contextlib import redirect_stdout
from hashlib import sha256
from http.server import BaseHTTPRequestHandler
import io
import json
import unittest
from unittest.mock import patch

import test_codex_council as fixture
from runtime import codex_consult as consult, codex_council as council, codex_council_work as work
from runtime.codex_lifecycle import handle_message, ingest_message
from runtime.codex_session import create_session
from tools.codex_council import main as council_cli

PIN = '1.3.0@' + 'd' * 40
FOLLOWUP = 'The returned source makes the sparse alternative credible. I replace my original choice.\n'


def request_work(task):
    entry = {'work': task, 'informs': 'Which alternative survives the boundary case?'}
    return ('My provisional choice is to use the dense case.\r\n\r\n[[CODEX NATIVE WORK]]\r\n'
            + json.dumps([entry, entry], ensure_ascii=False) + '\r\n[[END CODEX NATIVE WORK]]\r\n')


class WorkHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        with self.server.counter:
            self.server.requests.append(request)
            index = len(self.server.requests)
        body = self.server.answer(request)
        generation = f'gen-native-work-{index}'
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('X-Generation-Id', generation)
        self.end_headers()

        def frame(value):
            self.wfile.write(('data: ' + json.dumps(value, ensure_ascii=False) + '\n\n').encode('utf-8'))
            self.wfile.flush()

        frame({'id': generation, 'model': request['model'], 'choices': [{'index': 0,
            'delta': {'content': body[:30], 'reasoning': 'private synthetic reasoning'}}]})
        frame({'choices': [{'index': 0, 'delta': {'content': body[30:]}}]})
        if not self.server.truncated:
            frame({'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}],
                'usage': {'cost': self.server.cost, 'prompt_tokens': 30, 'completion_tokens': 20}})
            self.wfile.write(b'data: [DONE]\n\n')
            self.wfile.flush()


class CouncilNativeWorkTests(unittest.TestCase):
    stop_server = fixture.CouncilRuntimeTests.stop_server
    file = fixture.CouncilRuntimeTests.file
    facts = fixture.CouncilRuntimeTests.facts
    jobs = fixture.CouncilRuntimeTests.jobs
    native_return = fixture.CouncilRuntimeTests.native_return

    def setUp(self):
        fixture.CouncilRuntimeTests.setUp(self)
        self.root = self.task('single', allow=False)
        self.server.RequestHandlerClass = WorkHandler
        self.server.answer = lambda request: (FOLLOWUP if 'ROUND: NATIVE_WORK_RETURN' in
            request['messages'][-1]['content'] else request_work('Extract the boundary equation.'))
        self.server.cost = .002

    def task(self, name, *, allow, pin=PIN):
        request = self.file(name + '-user.txt', ('DIGR::' if allow else 'DIGR:') + ' Compare the boundary cases.')
        root = self.folder / name
        create_session(root, request=request, p_run=pin)
        return root

    def initial(self, *, first_opinion=True, effort=None):
        council.create_council(self.root, council_id='one', native_actors=['native-1'], enable_claude=True,
            first_opinion='Which case sets the decisive comparison?' if first_opinion else None)
        return council.prepare_round(self.root, 'one', max_tokens=100, effort=effort)

    def run_prepared(self, prepared, *, ceiling=.04, events=None):
        jobs = self.jobs(prepared)
        for job in jobs.values():
            job['ceiling_usd'] = ceiling
        return self.dispatch(prepared, jobs, events=events)

    def dispatch(self, prepared, jobs, *, events=None):
        return council.run_round(self.root, 'one', round_id=prepared['rounds'][-1]['round_id'], jobs=jobs,
                                 on_public_event=events.append if events is not None else None)

    def current_work(self, actor='Main'):
        return council.read_native_work(self.root, 'one', actor=actor)['jobs']

    def return_work(self, work_id, output_path, **kwargs):
        return council.submit_native_work(self.root, 'one', actor='Main', work_id=work_id,
                                          output_path=output_path, **kwargs)

    def prepare_return(self, **kwargs):
        return council.prepare_round(self.root, 'one', kind=work.ROUND_KIND, **kwargs)

    def test_first_opinion_uses_observed_work_and_actual_same_member_history(self):
        events = []
        initial = self.initial()
        observed = self.run_prepared(initial, events=events)
        source_exchange = observed['rounds'][0]['jobs']['member-1']['exchange_id']
        body = ''.join(event['text'] for event in events if event['event'] == 'public_delta')
        self.assertEqual(body, request_work('Extract the boundary equation.'))
        self.assertEqual(observed['cycle']['members']['member-1']['status'], 'AWAITING_NATIVE_WORK')
        with self.assertRaisesRegex(ValueError, 'initial work before seeing'):
            self.current_work('native-1')
        with self.assertRaisesRegex(ValueError, 'local Codex actor'):
            self.current_work('member-1')
        self.assertEqual(self.native_return()['phase'], 'INITIAL')
        (work_id, job), = self.current_work().items()
        self.assertEqual(job['source']['exchange_id'], source_exchange)
        self.assertEqual(job['source']['public_sha256'], sha256(body.encode('utf-8')).hexdigest())
        self.assertEqual(job['request']['work'], 'Extract the boundary equation.')
        with self.assertRaisesRegex(ValueError, 'native work results'):
            self.prepare_return()
        output = self.file('actual-local-output.txt', 'Checked the original at Eq. 9.\r\nx* = 0.\r\n')
        original = self.file('eq9-window.txt', '完整原式 x* = 0 仅当 θ = 1。\r\n')
        cli_output = io.StringIO()
        with redirect_stdout(cli_output):
            status = council_cli(['native-work-return', '--root', str(self.root), '--council-id', 'one',
                '--work-id', work_id, '--input', str(output), '--source', str(original)])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(cli_output.getvalue())['result']['outcome'], 'COMPLETE')
        with self.assertRaisesRegex(ValueError, 'already has a recorded result'):
            self.return_work(work_id, output)
        with self.assertRaisesRegex(ValueError, 'uses high effort'):
            self.prepare_return(effort='low')
        with self.assertRaisesRegex(ValueError, 'requesting Claude member'):
            self.prepare_return(model='anthropic/claude-sonnet-4.5')
        with self.assertRaisesRegex(ValueError, 'one independent round'):
            council.prepare_round(self.root, 'one')
        prepared = self.prepare_return(max_tokens=110)
        round_record = prepared['rounds'][-1]
        exchange = round_record['jobs']['member-1']['exchange_id']
        scope = round_record['jobs']['member-1']['scope']
        with self.assertRaisesRegex(ValueError, 'scope differs'):
            council.require_member_scope(self.root, {**scope, 'first_opinion_exchange_id': 'invented'})
        attempt = consult.inspect_exchange(self.root, exchange)['exchange']
        self.assertEqual(attempt['parent_exchange'], source_exchange)
        jobs = self.jobs(prepared)
        job = jobs['member-1']
        with patch('runtime.codex_consult_budget.first_opinion_quote',
                   return_value={'facts': job['facts'], 'ceiling_usd': .04}) as quote:
            quoted = council.first_opinion_plan(self.root, 'one', round_id=round_record['round_id'],
                split_path=job['split_path'], config_path=self.config)
        quote.assert_called_once()
        final = self.dispatch(prepared, quoted)
        self.assertEqual(final['phase'], 'REDELIBERATION', final['rounds'][-1])
        self.assertEqual(len(self.server.requests), 2)
        sent = self.server.requests[-1]
        self.assertEqual(sent['model'], self.server.requests[0]['model'])
        self.assertEqual(sent['reasoning']['effort'], 'high')
        self.assertEqual(sent['messages'][-2], {'role': 'assistant', 'content': body})
        self.assertIn(output.read_bytes().decode('utf-8'), sent['messages'][-1]['content'])
        self.assertIn(original.read_bytes().decode('utf-8'), sent['messages'][-1]['content'])
        self.assertIn(sha256(original.read_bytes()).hexdigest(), sent['messages'][-1]['content'])
        self.assertNotIn(original.as_posix(), sent['messages'][-1]['content'])
        claim = consult.inspect_exchange(self.root, exchange)['exchange']['wallet_claim']
        self.assertAlmostEqual(claim['layer_available_before_usd']['COUNCIL'], .198)
        self.assertEqual(len(consult.inspect_exchange(self.root)['shared_wallet']['claims']), 2)
        with self.assertRaisesRegex(ValueError, 'cannot be replayed'):
            self.dispatch(prepared, quoted)

    def test_normal_council_returns_material_to_one_member_and_handles_unavailable_work(self):
        self.root = self.task('ordinary', allow=True)
        self.server.answer = lambda request: (FOLLOWUP if 'ROUND: NATIVE_WORK_RETURN' in
            request['messages'][-1]['content'] else request_work('Extract for member 2.' if
            'round-1-member-2-input.txt' in request['messages'][-1]['content'] else 'Extract for member 1.'))
        self.run_prepared(self.initial(first_opinion=False, effort='xhigh'))
        entries = {job['source']['scope']['member_id']: identity for identity, job in self.current_work().items()}
        exclusive = self.file('private-to-one.txt', 'EXCLUSIVE RAW RESULT TO MEMBER ONE.')
        self.return_work(entries['member-1'], exclusive)
        with self.assertRaisesRegex(ValueError, 'recorded results'):
            self.prepare_return(members=['member-2'])
        self.run_prepared(self.prepare_return())
        self.assertIn(exclusive.read_text(), self.server.requests[-1]['messages'][-1]['content'])
        self.assertEqual(self.server.requests[-1]['reasoning']['effort'], 'xhigh')
        self.assertEqual(list(self.current_work()), [entries['member-2']])
        unavailable = self.file('unavailable.txt', 'Searched the original tables and appendices. Eq. 9 is missing.')
        self.return_work(entries['member-2'], unavailable, outcome='UNAVAILABLE')
        self.run_prepared(self.prepare_return())
        sent = self.server.requests[-1]
        self.assertNotIn(exclusive.read_text(), json.dumps(sent))
        self.assertIn('UNAVAILABLE by Main', sent['messages'][-1]['content'])
        self.assertIn(unavailable.read_text(), sent['messages'][-1]['content'])
        self.assertEqual(self.current_work(), {})

    def test_truncated_return_keeps_actual_partial_transport_and_never_replays(self):
        self.run_prepared(self.initial())
        self.native_return()
        work_id, = self.current_work()
        self.return_work(work_id, self.file('local-proof.txt', 'Actual source proof.'))
        prepared = self.prepare_return()
        jobs = self.jobs(prepared)
        jobs['member-1']['ceiling_usd'] = .04
        self.server.truncated = True
        outcome = self.dispatch(prepared, jobs)
        round_record = outcome['rounds'][-1]['jobs']['member-1']
        self.assertEqual(round_record['public_status'], 'PARTIAL')
        self.assertEqual(round_record['transport_status'], 'OUTCOME_UNKNOWN')
        self.assertEqual(round_record['billing_status'], 'UNKNOWN')
        self.assertEqual(outcome['cycle']['barrier']['reason'], 'EXPLICIT_ABNORMAL_TERMINALS')
        self.assertEqual(outcome['native_work'][work_id]['return_exchange_id'], round_record['exchange_id'])
        with self.assertRaisesRegex(ValueError, 'cannot be replayed'):
            self.dispatch(prepared, jobs)
        self.assertEqual(len(self.server.requests), 2)

    def test_remaining_budget_and_changed_result_are_unsent_then_current_input_fences_return(self):
        self.server.cost = .16
        self.run_prepared(self.initial(), ceiling=.17)
        work_id, = self.current_work()
        output = self.file('local-proof.txt', 'Actual source proof.')
        result = self.return_work(work_id, output)['result']
        stored = self.root / 'councils' / 'one' / result['path']
        prepared = self.prepare_return()
        jobs = self.jobs(prepared)
        jobs['member-1']['ceiling_usd'] = .05
        with self.assertRaisesRegex(ValueError, 'remaining COUNCIL'):
            self.dispatch(prepared, jobs)
        jobs['member-1']['ceiling_usd'] = .03
        exact = stored.read_bytes()
        stored.write_bytes(exact + b'changed')
        with self.assertRaisesRegex(ValueError, 'Sealed council public artifact changed'):
            self.dispatch(prepared, jobs)
        stored.write_bytes(exact)
        self.assertEqual(council.inspect_council(self.root, 'one')['rounds'][-1]['status'], 'PREPARED')
        message = self.file('revision.txt', 'DO: Change the decisive comparison to a different model.')
        pending = ingest_message(self.root, source=message, source_ref='revision')
        handle_message(self.root, message_id=pending['message_id'], action='continue', reason='Changed fixture scope')
        with self.assertRaisesRegex(ValueError, 'current active council input'):
            self.current_work()
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.dispatch(prepared, jobs)
        self.assertEqual(len(self.server.requests), 1)

    def test_partial_body_and_old_pin_cannot_issue_work(self):
        self.server.truncated = True
        observed = self.run_prepared(self.initial())
        self.assertEqual(observed['rounds'][0]['jobs']['member-1']['public_status'], 'PARTIAL')
        self.assertEqual(self.current_work(), {})
        self.root = self.task('old', allow=False, pin='1.2.2@' + 'd' * 40)
        self.server.truncated = False
        prior = self.run_prepared(self.initial())
        self.assertNotIn('native_work', prior)
        self.assertEqual(prior['cycle']['members']['member-1']['status'], 'COMPLETE')
        self.assertNotIn('[[CODEX NATIVE WORK]]', self.server.requests[-1]['messages'][0]['content'])

    def test_only_valid_terminal_public_block_counts(self):
        genuine = request_work('Check the article’s result.')
        self.assertEqual(len(work.requests_from_body(genuine)), 1)
        self.assertEqual(work.requests_from_body('```text\n' + genuine), [])
        self.assertEqual(work.requests_from_body(genuine + '\nThen I explain it.'), [])
        self.assertEqual(work.requests_from_body(genuine.replace('informs', 'command')), [])


if __name__ == '__main__':
    unittest.main()
