"""Exercise both new role paths through a local HTTP fixture and existing tools."""
import json
from pathlib import Path
import unittest

import test_codex_council as fixture
from runtime import codex_consult as consult, codex_consult_budget as budget, codex_council as council
from runtime import codex_allot as allot
from runtime.codex_lifecycle import handle_message, ingest_message, load_lifecycle
from runtime.codex_session import create_session


PIN = '1.0.0@' + 'a' * 40


class LayeredInteropTests(unittest.TestCase):
    setUp = fixture.CouncilRuntimeTests.setUp
    stop_server = fixture.CouncilRuntimeTests.stop_server
    file = fixture.CouncilRuntimeTests.file
    create = fixture.CouncilRuntimeTests.create
    prepare = fixture.CouncilRuntimeTests.prepare
    facts = fixture.CouncilRuntimeTests.facts
    jobs = fixture.CouncilRuntimeTests.jobs
    native_return = fixture.CouncilRuntimeTests.native_return

    def task(self, name, *, allow):
        request = self.file(name + '-request.txt', ('DIGR::' if allow else 'DIGR:') + ' Local fixture work')
        root = self.folder / name
        create_session(root, request=request, p_run=PIN)
        return root

    def handle(self, name, text, action, selection=None):
        source = self.file(name + '.txt', text)
        pending = ingest_message(self.root, source=source, source_ref=name)
        return handle_message(self.root, message_id=pending['message_id'], action=action,
                              claude_selection=selection, reason='Apply actual fixture input')

    def round(self, prepared, jobs):
        return council.run_round(self.root, 'one', round_id=prepared['rounds'][-1]['round_id'], jobs=jobs)

    def test_single_keeps_first_layer_in_council_and_other_member_runs_after_local_stop(self):
        self.root = self.task('single', allow=False)
        self.assertEqual(load_lifecycle(self.root)['claude_policy']['mode'], 'COUNCIL_ONLY')
        self.assertEqual(json.loads((self.root / 'session.json').read_bytes())['execution_profile']['native_model_selection'],
                         'ACTIVE_CODEX_SETTINGS')
        with self.assertRaisesRegex(ValueError, 'Allot is retired'):
            allot.inspect(self.root)
        with self.assertRaisesRegex(ValueError, 'Formal content participation'):
            consult.prepare_request(self.root, input_path=self.native, exchange_id='not-a-council-member', max_tokens=100)
        self.create()
        prepared = self.prepare()
        jobs = self.jobs(prepared)
        first = prepared['rounds'][-1]['jobs']['member-1']['exchange_id']
        with self.assertRaisesRegex(ValueError, 'registered council run-round'):
            consult.call_once(self.root, first, **jobs['member-1'])
        self.assertEqual(self.server.requests, [])
        council.seal_member(self.root, 'one', member_id='member-1', status='CANCELLED')
        job = jobs['member-2']
        job['facts'].pop('authorization_ref')
        job['facts'].pop('budget_total_usd')
        finished = self.round(prepared, {'member-2': job})
        second = finished['rounds'][-1]['jobs']['member-2']['exchange_id']
        attempt = consult.inspect_exchange(self.root, second)['exchange']
        self.assertEqual(len(self.server.requests), 1)
        self.assertEqual(attempt['budget_facts']['authorization_evidence']['kind'], 'SINGLE_COLON_WALLET_ONLY')
        self.assertIsNone(attempt['budget_facts']['budget_total_usd'])
        self.assertEqual(attempt['public_status'], 'COMPLETE')
        self.assertEqual(finished['cycle']['members']['member-1']['status'], 'CANCELLED')
        council.seal_member(self.root, 'one', member_id='member-2', status='COMPLETE')
        self.assertEqual(self.native_return()['phase'], 'REDELIBERATION')

    def test_double_budget_approval_preserves_prepared_round_and_withdrawal_breaks_reuse(self):
        self.root = self.task('double', allow=True)
        planned = {'planned_council_member': {'model': consult.DEFAULT_MODEL, 'max_tokens': 100,
                    'purpose': 'One independent technical perspective'}, 'facts': self.facts(), 'ceiling_usd': .5}
        view = budget.preview(self.root, jobs=[planned], scope='one independent council question',
                              wallet_id='synthetic-one-account', task_ceiling_usd=.5)
        self.assertFalse((self.root / 'councils').exists())
        preview = self.file('offer.json', json.dumps(view))
        self.create()
        prepared = self.prepare()
        jobs = self.jobs(prepared)
        with self.assertRaisesRegex(ValueError, 'recorded user budget approval'):
            self.round(prepared, jobs)
        self.assertEqual(council.inspect_council(self.root, 'one')['rounds'][-1]['status'], 'PREPARED')
        self.assertEqual(self.server.requests, [])
        text = 'DO: Approve the quoted scope up to fifty cents.'
        self.handle('fee-only', text, 'budget')
        budget.approve(self.root, preview_path=preview, user_text=text, source='fee-only', quote=text)
        result = self.round(prepared, jobs)
        self.assertEqual(len(self.server.requests), 2)
        self.assertEqual(result['rounds'][-1]['status'], 'FINISHED')
        self.handle('withdraw', 'Stop Claude and withdraw the fee decision.', 'continue', 'DENY')
        state = self.handle('reopen', 'Enable both roles for future work.', 'continue', 'ALLOW')
        exchange = prepared['rounds'][-1]['jobs']['member-1']['exchange_id']
        _, session, _ = consult._task(self.root, active=True)
        _, attempt, _ = consult._load(self.root, exchange)
        with self.assertRaisesRegex(ValueError, 'recorded user budget approval'):
            budget.resolve(self.root, session, state, attempt, self.facts(), 'synthetic-one-account')
        self.assertEqual(len(self.server.requests), 2)
