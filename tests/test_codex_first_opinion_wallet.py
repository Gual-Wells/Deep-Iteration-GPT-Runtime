"""Exercise first-opinion authorization and the shared ledger entirely offline."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from io import BytesIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Barrier
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from runtime import codex_collaboration as collaboration, codex_consult as consult
from runtime import codex_consult_budget as authority, codex_wallet as wallet
from runtime.codex_lifecycle import handle_message, ingest_message, load_lifecycle
from runtime.codex_session import create_session

PIN = '1.2.0@' + 'a' * 40
OLD_PIN = '1.1.1@' + 'b' * 40


class FirstOpinionQuoteTests(unittest.TestCase):
    def setUp(self):
        self.config = {'endpoint': consult.DEFAULT_ENDPOINT, 'wallet_id': 'quote-fixture', 'timeout_seconds': 8}
        self.secret = 'mock-credential-only'
        self.opener = Mock()
        config = patch.object(consult, '_config', return_value=(self.config, self.secret))
        opener = patch.object(consult, '_opener', return_value=self.opener)
        config.start()
        self.make_opener = opener.start()
        self.addCleanup(config.stop)
        self.addCleanup(opener.stop)
        coverage = patch.object(wallet, 'confirmed_coverage', return_value={})
        coverage.start()
        self.addCleanup(coverage.stop)
        self.request = {'model': consult.DEFAULT_MODEL, 'messages': [{'role': 'system', 'content': 'Research independently.'},
                        {'role': 'user', 'content': '请核对代价与可行性。'}], 'provider': {'require_parameters': True},
                        'reasoning': {'effort': 'high', 'exclude': True}, 'max_tokens': 16_000}

    def catalog(self, **prices):
        data = {'data': [{'id': 'anthropic/unrelated', 'pricing': {'prompt': '0', 'completion': '0'}},
                         {'id': self.request['model'], 'pricing': prices}]}
        return BytesIO(json.dumps(data).encode('utf-8'))

    def test_startup_prices_use_no_credential_wallet_or_prepared_request(self):
        data = [{'id': collaboration.SONNET_5_5, 'pricing': {'prompt': '0.000002', 'completion': '0.00001'}},
                {'id': collaboration.GEMINI_CARBON, 'pricing': {'prompt': '0.000004', 'completion': '0.00002'}}]
        self.opener.open.return_value = BytesIO(json.dumps({'data': data}).encode('utf-8'))
        with patch.object(authority, 'build_opener', return_value=self.opener), \
                patch.object(wallet, 'ledger_path', side_effect=AssertionError('price display read the ledger')):
            quotes = list(authority.startup_collaboration_quotes())
        self.opener.open.assert_called_once()
        request = self.opener.open.call_args.args[0]
        self.assertEqual((request.full_url, request.get_method(), request.data, request.get_header('Authorization')),
                         ('https://openrouter.ai/api/v1/models', 'GET', None, None))
        self.assertEqual({q['participant']: float(q['output_usd_per_million']) for q in quotes},
                         {'sonnet': 10, 'carbon': 20})
        self.assertTrue(all(q['scope'] == 'DISPLAY_ONLY' and q['status'] == 'QUOTED' for q in quotes))

    def test_auto_quote_reads_official_sources_and_bounds_the_full_priced_request(self):
        prices = {'prompt': '0.000002', 'completion': '0.00001', 'request': '0.002'}
        self.opener.open.side_effect = [self.catalog(**prices), BytesIO(b'{"data":{"total_credits":9.9,"total_usage":7.8}}')]
        quoted = authority.first_opinion_quote(self.request)
        self.make_opener.assert_called_once_with(self.config)
        model_call, credits_call = self.opener.open.call_args_list
        models, credits = model_call.args[0], credits_call.args[0]
        self.assertEqual((models.full_url, models.get_method(), models.data),
                         ('https://openrouter.ai/api/v1/models', 'GET', None))
        self.assertEqual((credits.full_url, credits.get_method(), credits.data),
                         ('https://openrouter.ai/api/v1/credits', 'GET', None))
        self.assertIsNone(models.get_header('Authorization'))
        self.assertEqual(credits.get_header('Authorization'), 'Bearer ' + self.secret)
        self.assertNotIn(self.secret, json.dumps(quoted))
        facts = quoted['facts']
        self.assertEqual(facts['wallet_id'], self.config['wallet_id'])
        self.assertEqual(facts['wallet_remaining_usd'], 2.1)
        self.assertEqual((facts['prompt_usd_per_million'], facts['completion_usd_per_million'], facts['request_usd']),
                         (2, 10, .002))
        priced = {**self.request, 'provider': {**self.request['provider'],
                  'max_price': {'prompt': 2.0, 'completion': 10.0, 'request': .002}}}
        self.assertGreater(facts['input_tokens_upper_bound'], len(consult._json_bytes(priced)))
        expected = facts['input_tokens_upper_bound'] * .000002 + 16_000 * .00001 + .002
        self.assertGreaterEqual(quoted['ceiling_usd'] + 1e-12, expected)
        self.assertLessEqual(quoted['ceiling_usd'], min(.2, expected + .000001))
        self.assertNotIn('max_price', self.request['provider'])

    def test_auto_quote_rejects_nonofficial_endpoint_before_opening_connections(self):
        self.config['endpoint'] = 'https://openrouter.ai.example.com/api/v1/chat/completions'
        with self.assertRaisesRegex(ValueError, 'official OpenRouter HTTPS.*--plan'):
            authority.first_opinion_quote(self.request)
        self.make_opener.assert_not_called()

    def test_credits_permission_error_offers_plan_without_provider_error_text(self):
        read_denied = HTTPError('https://openrouter.ai/api/v1/credits', 403, self.secret, {}, None)
        self.opener.open.side_effect = [self.catalog(prompt='0.000002', completion='0.00001'), read_denied]
        with self.assertRaisesRegex(ValueError, 'credits read returned HTTP 403.*--plan') as caught:
            authority.first_opinion_quote(self.request)
        self.assertNotIn(self.secret, str(caught.exception))

    def test_quote_over_cap_stops_before_reading_credits(self):
        self.opener.open.return_value = self.catalog(prompt='0.000002', completion='0.00002')
        with self.assertRaisesRegex(ValueError, 'exceeds its USD 0.20 ceiling'):
            authority.first_opinion_quote(self.request)
        self.opener.open.assert_called_once()


class FirstOpinionWalletTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[1] / '.cache'
        cache.mkdir(exist_ok=True)
        temporary = TemporaryDirectory(prefix='codex-first-opinion-wallet-', dir=cache)
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.ledger = self.folder / 'wallet.sqlite3'
        replacement = patch.object(wallet, 'ledger_path', return_value=self.ledger)
        replacement.start()
        self.addCleanup(replacement.stop)
        self.root = self.folder / 'task'
        request = self.write('request.txt', 'DIGR: Assess the proposed result from an independent perspective.')
        self.session = create_session(self.root, request=request, p_run=PIN)

    def write(self, filename, text):
        path = self.folder / filename
        path.write_text(text, encoding='utf-8')
        return path

    def reserve(self, exchange, *, root=None, wallet_id='wallet-one', ceiling=.2,
                wallet_remaining=1, session=None, purpose=None, snapshot=None):
        budget = {'budget_total_usd': None, 'outside_spent_usd': 0, 'outside_reserved_usd': 0,
                  'wallet_remaining_usd': wallet_remaining, 'ceiling_usd': ceiling}
        if snapshot is not None:
            budget['wallet_snapshot'] = snapshot
        return wallet.reserve(root or self.root, session or self.session, exchange_id=exchange,
                              request_sha256='c' * 64, wallet_id=wallet_id, budget=budget, purpose=purpose)

    def reserve_first(self, exchange, **kwargs):
        return self.reserve(exchange, purpose=collaboration.FIRST_OPINION_PURPOSE, **kwargs)

    def test_two_external_models_share_layers_and_each_has_one_first_opinion(self):
        root = self.folder / 'paired'
        session = create_session(root, request=self.write('paired.txt', 'DIGR:: A shared task.'),
                                 p_run='1.7.0@' + 'e' * 40)

        def reserve(name, *, role, amount, participant=None):
            current_purpose = collaboration.FIRST_OPINION_PURPOSE if participant else None
            label = 'wallet-' + name
            layer = collaboration.CLAUDE_LAYER_BY_ROLE[role]
            evidence = {'kind': 'STANDING_CLAUDE_LAYER_LIMIT', 'role': role, 'layer': layer,
                        'wallet_id': label, 'purpose': current_purpose, 'first_opinion_participant': participant}
            return wallet.reserve(root, session, exchange_id=name, request_sha256='d' * 64, wallet_id=label,
                                  budget={'budget_total_usd': None, 'ceiling_usd': amount, 'wallet_remaining_usd': 20,
                                          'outside_spent_usd': 0, 'outside_reserved_usd': 0,
                                          'authorization_evidence': evidence})

        reserve('first-sonnet', role='council_member', amount=.13, participant='sonnet')
        with self.assertRaisesRegex(ValueError, 'COUNCIL layer budget.*0.25'):
            reserve('large-carbon', role='council_member', amount=.13, participant='carbon')
        reserve('first-carbon', role='council_member', amount=.12, participant='carbon')
        with self.assertRaisesRegex(ValueError, 'already claimed'):
            reserve('repeat-carbon', role='council_member', amount=.01, participant='carbon')
        reserve('content-sonnet', role='consult_guidance', amount=.7)
        with self.assertRaisesRegex(ValueError, 'CONTENT layer budget.*1.25'):
            reserve('large-content-carbon', role='consult_guidance', amount=.56)
        reserve('content-carbon', role='consult_guidance', amount=.55)
        paired = wallet.inspect_task(root, session)
        self.assertEqual(set(paired['first_opinion_claims']), {'carbon', 'sonnet'})
        self.assertAlmostEqual(paired['totals']['unresolved_reserved_usd'], 1.5)

    def test_first_opinion_claim_is_atomic_across_wallets_exchanges_and_restored_roots(self):
        gate = Barrier(2, timeout=5)

        def reserve(exchange):
            gate.wait()
            return self.reserve_first(exchange, root=self.folder / ('restore-' + exchange), wallet_id=exchange)

        with ThreadPoolExecutor(max_workers=2) as executor:
            contenders = [executor.submit(reserve, exchange) for exchange in ('first', 'second')]
        admitted = [job.result() for job in contenders if job.exception() is None]
        denied = [job.exception() for job in contenders if job.exception() is not None]
        self.assertEqual(len(admitted), 1)
        self.assertEqual(len(denied), 1)
        self.assertIsInstance(denied[0], ValueError)
        self.assertIn('already claimed its first Claude opinion', str(denied[0]))
        ledger = wallet.inspect_task(self.root, self.session)
        self.assertEqual(len(ledger['claims']), 1)
        claim = ledger['first_opinion_claim']
        self.assertEqual(claim['claim_id'], admitted[0]['claim_id'])
        self.assertEqual((claim['state'], claim['ceiling_usd']), ('RESERVED', .2))

    def test_insufficient_wallet_balance_does_not_claim_first_opinion(self):
        with self.assertRaisesRegex(ValueError, 'Shared wallet reservation exceeds'):
            self.reserve_first('first', wallet_remaining=.19)
        self.assertIsNone(wallet.inspect_task(self.root, self.session).get('first_opinion_claim'))
        self.reserve_first('first', wallet_remaining=.2)

    def test_auto_quote_reuses_confirmed_cost_but_counts_later_revision_and_pending_hold(self):
        billed = self.reserve('settled')
        initial = wallet.update(billed, state='KNOWN', cost=.16, cost_observed_at='2026-01-01T00:00:00+00:00')
        snapshot = {'snapshot_id': 'verified-provider-balance', 'wallet_id': 'wallet-one',
                    'covered_claims': {billed['claim_id']: {'cost_revision': initial['cost_revision'],
                                                          'covered_cost_usd': .16}}}
        self.reserve('pending', ceiling=.025, wallet_remaining=.35, snapshot=snapshot)
        wallet.update(billed, state='KNOWN', cost=.18, cost_observed_at='2026-01-02T00:00:00+00:00')

        model = consult.DEFAULT_MODEL
        request = {'model': model, 'messages': [{'role': 'user', 'content': 'Review the claim.'}],
                   'provider': {'require_parameters': True}, 'max_tokens': 3200}
        config = {'endpoint': consult.DEFAULT_ENDPOINT, 'wallet_id': 'wallet-one', 'timeout_seconds': 8}
        catalog = [{'id': model, 'pricing': {'prompt': '0.000002', 'completion': '0.00001'}}]
        with patch.object(consult, '_config', return_value=(config, 'mock-credential-only')), \
                patch.object(authority, '_quote_data', side_effect=[catalog, {'total_credits': 1.0, 'total_usage': .89}]):
            quote = authority.first_opinion_quote(request)
        facts = quote['facts']
        self.assertEqual(facts['wallet_snapshot']['covered_claims'], snapshot['covered_claims'])
        args = {'ceiling': quote['ceiling_usd'], 'wallet_remaining': facts['wallet_remaining_usd']}
        with self.assertRaisesRegex(ValueError, 'Shared wallet reservation exceeds'):
            self.reserve_first('first-opinion', **args)
        receipt = self.reserve_first('first-opinion', snapshot=facts['wallet_snapshot'], **args)
        self.assertAlmostEqual(receipt['known_uncovered_usd'], .02)
        self.assertAlmostEqual(receipt['wallet_available_before_usd'], .11 - .02 - .025)

    def test_proven_unsent_release_frees_the_slot_and_committed_or_zero_cost_does_not(self):
        unsent = self.reserve_first('unsent')
        wallet.update(unsent, state='ABORTED')
        self.assertIsNone(wallet.inspect_task(self.root, self.session).get('first_opinion_claim'))
        with self.assertRaisesRegex(ValueError, 'already claimed this exchange'):
            self.reserve_first('unsent')
        next_claim = self.reserve_first('replacement', wallet_id='new-wallet')
        wallet.update(next_claim, state='COMMITTED')
        with self.assertRaisesRegex(ValueError, 'proven unsent'):
            wallet.update(next_claim, state='ABORTED')
        with self.assertRaisesRegex(ValueError, 'already claimed its first Claude opinion'):
            self.reserve_first('while-outcome-unknown')
        wallet.update(next_claim, state='KNOWN', cost=0, cost_observed_at='2026-01-01T00:00:00+00:00')
        with self.assertRaisesRegex(ValueError, 'already claimed its first Claude opinion'):
            self.reserve_first('settled-without-charge')
        claim = wallet.inspect_task(self.root, self.session)['first_opinion_claim']
        self.assertEqual((claim['exchange_id'], claim['state'], claim['known_cost_usd']), ('replacement', 'KNOWN', 0))

    def test_migration_keeps_old_claims_and_the_old_insert_contract(self):
        insert = '''INSERT INTO claims
            (claim_id,task_id,wallet_id,exchange_id,request_sha256,state,ceiling_usd,reserved_at,account_authorization_ref)
            VALUES (?,?,?,?,?,'RESERVED',?,?,?)'''
        with closing(sqlite3.connect(self.ledger)) as db:
            db.execute('''CREATE TABLE claims (
                claim_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, wallet_id TEXT NOT NULL,
                exchange_id TEXT NOT NULL, request_sha256 TEXT NOT NULL,
                state TEXT NOT NULL, ceiling_usd REAL NOT NULL, known_cost_usd REAL,
                reserved_at TEXT NOT NULL, cost_observed_at TEXT, committed_at TEXT,
                account_authorization_ref TEXT, cost_revision INTEGER NOT NULL DEFAULT 0,
                cost_first_observed_at TEXT, last_cost_checked_at TEXT)''')
            old_task = wallet.task_id(self.root, self.session)
            db.execute(insert, ('previous', old_task, 'wallet-one', 'ordinary-before', 'c' * 64, .1, '1', None))
            db.commit()
        original = wallet.inspect_task(self.root, self.session)
        self.assertEqual(len(original['claims']), 1)
        self.assertIsNone(original.get('first_opinion_claim'))
        self.reserve_first('first-opinion')
        with closing(sqlite3.connect(self.ledger)) as db:
            db.execute(insert, ('historical', old_task, 'wallet-two', 'legacy-shape', 'd' * 64, .1, '2', None))
            db.commit()
        migrated = wallet.inspect_task(self.root, self.session)
        self.assertEqual(len(migrated['claims']), 3)
        self.assertAlmostEqual(migrated['totals']['unresolved_reserved_usd'], .4)
        self.assertEqual(migrated['first_opinion_claim']['exchange_id'], 'first-opinion')

    def test_ordinary_and_historical_reservations_can_still_exceed_first_opinion_cap(self):
        with self.assertRaisesRegex(ValueError, 'USD 0.20 ceiling'):
            self.reserve_first('too-high', ceiling=.201)
        self.assertFalse(self.ledger.exists())
        self.reserve_first('first')
        self.reserve('ordinary', ceiling=.6)
        previous = {**self.session, 'P_run': OLD_PIN}
        with self.assertRaisesRegex(ValueError, 'this task profile'):
            self.reserve_first('unsupported', session=previous)
        self.reserve('historically-allowed', session=previous, wallet_id='wallet-two', ceiling=.6)

    def authorize(self, *, ceiling, purpose=True, session=None, role='council_member', **facts):
        scope = {'purpose': collaboration.FIRST_OPINION_PURPOSE} if purpose else {}
        attempt = {'participation_role': role, 'council_scope': scope,
                   'collaboration_contract': {'requested_model': consult.DEFAULT_MODEL}}
        return authority.resolve(self.root, session or self.session, load_lifecycle(self.root), attempt, facts,
                                 'wallet-one', ceiling_usd=ceiling)

    def handle(self, text, *, action, selection=None):
        ref = action + '-reply'
        message = ingest_message(self.root, source=self.write(ref + '.txt', text), source_ref=ref)
        handle_message(self.root, message_id=message['message_id'], action=action,
                       reason='Record actual fixture decision.', claude_selection=selection)
        return {'user_text': text, 'source': ref, 'quote': text}

    def test_first_opinion_authority_is_canonical_and_per_submission(self):
        paid = self.authorize(ceiling=.2)
        self.assertEqual(paid['authorization_evidence']['purpose'], collaboration.FIRST_OPINION_PURPOSE)
        self.assertIsNone(paid['budget_total_usd'])
        self.assertFalse(self.ledger.exists())
        with self.assertRaisesRegex(ValueError, 'different wallet configuration'):
            self.authorize(ceiling=.2, wallet_id='changed-wallet')
        with self.assertRaisesRegex(ValueError, 'USD 0.20 ceiling'):
            self.authorize(ceiling=.2001)
        with self.assertRaisesRegex(ValueError, 'Wallet-only authority'):
            self.authorize(ceiling=.2, role='consult_guidance')
        regular = self.authorize(ceiling=.6, purpose=False, authorization_evidence={'purpose': 'first_opinion'})
        self.assertNotIn('purpose', regular['authorization_evidence'])
        self.assertIsNone(regular['budget_total_usd'])
        previous = self.authorize(ceiling=.6, session={**self.session, 'P_run': OLD_PIN})
        self.assertNotIn('purpose', previous['authorization_evidence'])
        self.handle('Allow both roles from here.', action='continue', selection='ALLOW')
        with self.assertRaisesRegex(ValueError, 'current single-colon choice'):
            self.authorize(ceiling=.2)

    def test_narrower_user_budget_limit_still_applies_to_first_opinion(self):
        reply = self.handle('Set an eight-cent limit for the whole task.', action='budget')
        with self.assertRaisesRegex(ValueError, 'latest fee-only decision'):
            self.authorize(ceiling=.08)
        authority.record_limit(self.root, task_ceiling_usd=.08, **reply)
        with self.assertRaisesRegex(ValueError, 'current task budget ceiling'):
            self.authorize(ceiling=.081)
        self.assertAlmostEqual(self.authorize(ceiling=.08)['budget_total_usd'], .08)


if __name__ == '__main__':
    unittest.main()
