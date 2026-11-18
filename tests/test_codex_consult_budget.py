"""Versioned approval and ledger arithmetic, entirely against local fixtures."""
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from runtime import codex_consult as consult, codex_consult_budget as authority, codex_wallet as wallet
from runtime import codex_council as council
from runtime.codex_lifecycle import handle_message, ingest_message, load_lifecycle
from runtime.codex_session import create_session

PIN = '1.0.0@' + 'e' * 40
WALLET = 'local-offline-wallet'


class LayeredBudgetTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[1] / '.cache'
        cache.mkdir(exist_ok=True)
        temp = TemporaryDirectory(prefix='codex-layered-budget-', dir=cache)
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.ledger = self.folder / 'wallet.sqlite3'
        replaced = patch.object(wallet, 'ledger_path', return_value=self.ledger)
        replaced.start()
        self.addCleanup(replaced.stop)
        self.root, self.session = self.task('first', 'DIGR:: Prepare an offline example')
        self.work = self.file('example.txt', 'Prepare a compact example from this supplied text.')
        self.inference_guard = patch.object(consult, '_opener', side_effect=AssertionError('No provider send allowed'))
        self.inference_guard.start()
        self.addCleanup(self.inference_guard.stop)

    def file(self, label, text):
        path = self.folder / label
        path.write_text(text, encoding='utf-8')
        return path

    def task(self, label, request):
        root = self.folder / label
        return root, create_session(root, request=self.file(label + '.txt', request), p_run=PIN)

    def message(self, label, user_text, *, action='budget', selection=None, root=None):
        root = root or self.root
        selected = ingest_message(root, source=self.file(label + '.txt', user_text), source_ref=label)
        handle_message(root, message_id=selected['message_id'], action=action,
                       reason='Process a selected fixture source', claude_selection=selection)
        return {'user_text': user_text, 'source': label, 'quote': user_text}

    def facts(self, **overrides):
        return {'model': consult.DEFAULT_MODEL, 'checked_at': datetime.now(timezone.utc).isoformat(),
                'pricing_ref': 'fixture price sheet', 'input_bound_basis': 'fixture exact input bound',
                'outside_spent_usd': 0, 'wallet_remaining_usd': 1, 'prompt_usd_per_million': 10,
                'completion_usd_per_million': 20, 'input_tokens_upper_bound': 1000, **overrides}

    def prepare_guidance(self, label='guide'):
        return consult.prepare_request(self.root, input_path=self.work, exchange_id=label, max_tokens=100)

    def prepare_council(self):
        council.create_council(self.root, council_id='review', native_actors=['V01'], enable_claude=True,
                               member_count=1)
        result = council.prepare_round(self.root, 'review', max_tokens=100)
        job = result['rounds'][-1]['jobs']['member-1']
        self.assertEqual(job['status'], 'PREPARED', result['rounds'][-1].get('prepare_errors'))
        return job['exchange_id']

    def selected(self, exchange, *, root=None):
        return consult._load(root or self.root, exchange)[1]

    def view(self, exchanges, *, total=.5, **pricing):
        return authority.preview(self.root, jobs=[{'exchange_id': exchange, 'facts': self.facts(**pricing),
                                                   'ceiling_usd': .2} for exchange in exchanges],
                                 task_ceiling_usd=total, scope='actual example and independent council question',
                                 wallet_id=WALLET)

    def save_preview(self, value):
        return self.file('offer.json', json.dumps(value))

    def resolve(self, exchange, *, root=None, session=None, wallet_id=WALLET, **facts):
        root = root or self.root
        return authority.resolve(root, session or self.session, load_lifecycle(root),
                                 self.selected(exchange, root=root), self.facts(**facts), wallet_id)

    def reservation(self, session, *, total=None, ceiling=.2, wallet_remaining=1, label='test-hold'):
        return wallet.reserve(self.root, session, exchange_id=label, request_sha256='b' * 64, wallet_id=WALLET,
                              budget={'budget_total_usd': total, 'outside_spent_usd': 0, 'outside_reserved_usd': 0,
                                      'wallet_remaining_usd': wallet_remaining, 'ceiling_usd': ceiling})

    def test_single_colon_resolves_wallet_authority_without_an_artificial_total(self):
        self.root, self.session = self.task('single', 'DIGR: Check one external perspective')
        exchange = self.prepare_council()
        admitted = self.resolve(exchange)
        self.assertIsNone(admitted['budget_total_usd'])
        self.assertEqual(admitted['authorization_evidence']['kind'], 'SINGLE_COLON_WALLET_ONLY')
        first = self.reservation(self.session, total=admitted['budget_total_usd'], ceiling=.6)
        with self.assertRaisesRegex(ValueError, 'Shared wallet reservation'):
            self.reservation(self.session, ceiling=.5, label='too-much-while-unresolved')
        wallet.update(first, state='ABORTED')
        self.reservation(self.session, ceiling=.5, label='fits-after-proven-unsent')

    def test_double_colon_both_roles_require_source_bound_approval(self):
        self.prepare_guidance()
        member = self.prepare_council()
        for exchange in ('guide', member):
            with self.assertRaisesRegex(ValueError, 'recorded user budget approval'):
                self.resolve(exchange, authorization_ref='invented')
        view = self.view(['guide', member])
        self.assertAlmostEqual(view['prepared_reservation_upper_usd'], .4)
        self.assertFalse(self.ledger.exists(), 'an estimate never reserves or creates the ledger')
        original_input = consult._input_ref(load_lifecycle(self.root))
        reply = self.message('real-user-reply', 'I approve $0.45 for the two prepared roles.')
        self.assertEqual(consult._input_ref(load_lifecycle(self.root)), original_input)
        decision = authority.approve(self.root, preview_path=self.save_preview(view), task_ceiling_usd=.45, **reply)
        for exchange in ('guide', member):
            allowed = self.resolve(exchange, authorization_ref='invented', budget_total_usd=90)
            self.assertEqual(allowed['budget_total_usd'], .45)
            self.assertEqual(allowed['authorization_evidence']['decision_id'], decision['decision_id'])
            self.assertNotEqual(allowed['authorization_ref'], 'invented')
        with self.assertRaisesRegex(ValueError, 'outside the approved budget scope'):
            self.resolve('guide', wallet_id='different-wallet')
        self.message('ordinary-supplement', 'DO: Use the existing facts.', action='continue')
        self.prepare_guidance('fresh-guide')
        self.assertEqual(self.resolve('fresh-guide')['budget_total_usd'], .45)
        self.message('new-u0', 'DO: Replace the commissioned product with a different one.', action='revise')
        self.prepare_guidance('new-product')
        with self.assertRaisesRegex(ValueError, 'material task revision'):
            self.resolve('new-product')

    def test_scope_change_and_other_task_require_actual_fresh_authority(self):
        self.prepare_guidance()
        offered = self.save_preview(self.view(['guide']))
        with self.assertRaisesRegex(ValueError, 'does not match'):
            authority.approve(self.root, preview_path=offered, user_text='fabricated', source='empty', quote='yes')
        self.message('real-correction', 'DO: replace the earlier question.', action='continue')
        reply = self.message('late-fee-reply', 'Yes to the older offer.')
        with self.assertRaisesRegex(ValueError, 'earlier scoped preview'):
            authority.approve(self.root, preview_path=offered, **reply)
        second, _ = self.task('second', 'DIGR:: Prepare an offline example')
        reply = self.message('second-fee-reply', 'Yes to this amount.', root=second)
        with self.assertRaisesRegex(ValueError, 'earlier scoped preview'):
            authority.approve(second, preview_path=offered, **reply)

    def test_explicit_limit_and_pending_fee_apply_after_switch_to_single_colon(self):
        self.prepare_guidance()
        offered = self.save_preview(self.view(['guide']))
        approved = self.message('approve', 'Approve the fifty-cent cap.')
        authority.approve(self.root, preview_path=offered, **approved)
        self.message('switch', 'Use just the first layer now.', action='continue', selection='COUNCIL_ONLY')
        member = self.prepare_council()
        self.assertEqual(self.resolve(member)['budget_total_usd'], .5)
        self.message('open-both', 'Allow both roles now.', action='continue', selection='ALLOW')
        self.prepare_guidance('after-narrowing')
        with self.assertRaisesRegex(ValueError, 'recorded user budget approval'):
            self.resolve('after-narrowing')
        self.message('only-council', 'Keep the council role only.', action='continue', selection='COUNCIL_ONLY')
        narrower = self.message('narrower', 'Spend no more than $0.10 on this task.')
        with self.assertRaisesRegex(ValueError, 'latest fee-only decision'):
            self.resolve(member)
        authority.record_limit(self.root, task_ceiling_usd=.10, **narrower)
        self.assertEqual(self.resolve(member)['budget_total_usd'], .10)
        with self.assertRaisesRegex(ValueError, 'Shared wallet reservation'):
            self.reservation(self.session, total=self.resolve(member)['budget_total_usd'], ceiling=.11)

    def test_preview_respects_shared_unresolved_holds_and_the_combined_ceiling(self):
        self.prepare_guidance()
        member = self.prepare_council()
        _, other = self.task('second', 'DIGR: Check an independent fact')
        hold = self.reservation(other, ceiling=.75)
        with self.assertRaisesRegex(ValueError, 'combined task envelope'):
            self.view(['guide', member], total=.4)
        wallet.update(hold, state='ABORTED')
        with self.assertRaisesRegex(ValueError, 'combined task envelope'):
            self.view(['guide', member], total=.3)
        self.assertAlmostEqual(self.view(['guide', member], total=.4)['available_to_reserve_usd'], 1.)


if __name__ == '__main__':
    unittest.main()
