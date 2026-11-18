"""Stable foundation boundary fixtures. No model inference or payment."""
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from runtime import codex_consult as consult, codex_foundation as foundation, codex_guidance as guidance
from runtime.codex_lifecycle import handle_message, ingest_message, load_lifecycle
from runtime.codex_session import create_line, create_session


PIN = '1.0.0@' + 'c' * 40
COMMISSION = 'Implement the fixed synthetic specification within the existing task.'
PUBLIC = 'Synthetic completed guidance. This choice stays within the original delegated scope.'
PARAMETERS = {'N': 2, 'T': 0, 'R': 1, 'B': 0, 'S': {'n': 0, 't': 0, 'r': 0, 'b': 0},
              'D': 0, 'V': 0, 'L': 3}


class LayeredFoundationTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[1] / '.cache'
        cache.mkdir(exist_ok=True)
        scratch = tempfile.TemporaryDirectory(prefix='layered-foundation-', dir=cache)
        self.addCleanup(scratch.cleanup)
        self.base = Path(scratch.name)

    def create(self, separator='::'):
        self.root = self.base / 'session'
        request = self.base / 'request.txt'
        request.write_text('DIGR' + separator + ' ' + COMMISSION, encoding='utf-8')
        self.session = create_session(self.root, request=request, p_run=PIN)

    def propose(self, **changes):
        proposal = {'brief': {key: 'Synthetic fixed ' + key for key in foundation.BRIEF_FIELDS},
                    'questions': [], **changes}
        return foundation.propose_foundation(self.root, proposal, reason='Synthetic scoped decision')

    def adopt(self, brief, **changes):
        supplied = {'revision': brief['revision'],
                    'commission_source': self.session['request_origin'],
                    'commission_sha256': self.session['request_sha256'],
                    'commission_scope_quote': COMMISSION,
                    'explicit_execution_commission': True, 'no_new_user_choice': True,
                    'reason': 'Use original synthetic delegation', **changes}
        return foundation.adopt_commission(self.root, supplied)

    def supplement(self, text, action='continue'):
        path = self.base / (f'reply-{load_lifecycle(self.root)["message_id"]}.txt')
        path.write_text(text, encoding='utf-8')
        value = ingest_message(self.root, source=path, source_ref=str(path),
                               route_pin=PIN if text.startswith('DIGR') else None)
        handle_message(self.root, message_id=value['message_id'], action=action,
                       reason='Synthetic user follow-up consequence')
        return load_lifecycle(self.root)['current_message']['source']

    def complete_guidance(self, exchange_id):
        instruction = self.base / 'instruction.txt'
        instruction.write_text('Synthetic material for a formal content question.', encoding='utf-8')
        consult.prepare_request(self.root, input_path=instruction, exchange_id=exchange_id, max_tokens=64)
        directory = self.root / 'consult' / 'exchanges' / exchange_id
        body = PUBLIC.encode('utf-8')
        (directory / 'public.md').write_bytes(body)
        attempt = consult._read(directory / 'attempt.json')
        attempt.update(transport_status='RESPONDED', public_status='COMPLETE', finish_reason='stop',
                       response_model=consult.DEFAULT_MODEL, http_status=200,
                       public_sha256=sha256(body).hexdigest(), public_byte_length=len(body),
                       billing_status='KNOWN', known_cost_usd=0, synthetic_fixture=True)
        consult._write(directory / 'attempt.json', attempt)
        return {'exchange_id': exchange_id, 'public_sha256': attempt['public_sha256']}

    def test_delimiter_alone_never_requires_formal_guidance(self):
        for separator in (':', '::'):
            with self.subTest(separator=separator):
                self.base = self.base / 'variant'
                self.base.mkdir()
                self.create(separator)
                proposal = self.propose(questions=[{'id': 'optional', 'question': 'Optional?',
                                                   'why': 'A drafting preference'}])
                self.assertFalse(proposal['guidance_required'])
                accepted = self.adopt(proposal)
                self.assertEqual(accepted['confirmation']['kind'], 'STANDING_COMMISSION')
                self.assertFalse(accepted['confirmation']['user_saw_this_plan'])
                self.assertIsNone(accepted['confirmation']['user_confirmed_revision'])
                displayed = foundation.foundation_packet(self.root)
                self.assertIn('## 可选意见', displayed)
                self.assertNotIn('## 需要用户决定', displayed)
                self.assertEqual(foundation.require_foundation_ready(self.root)['status'], 'CONFIRMED')

    def test_new_content_waits_while_accepted_line_continues(self):
        self.create()
        self.adopt(self.propose())
        create_line(self.root, 'M01', parameters=PARAMETERS, owner='Fixture')
        self.supplement('Consider a second-layer product choice while continuing the fixed source work.')
        pending = self.propose(guidance_required=True, unaffected_lines={'M01': 'Original fixed source work'})
        self.assertEqual(pending['status'], 'AWAITING_GUIDANCE')
        self.assertEqual(foundation.require_foundation_ready(self.root, owner='M01')['status'],
                         'CONFIRMED_UNCHANGED_SCOPE')
        with self.assertRaisesRegex(ValueError, 'complete formal guidance'):
            foundation.require_foundation_ready(self.root)
        answered = self.propose(guidance=self.complete_guidance('actual-content'))
        self.assertTrue(answered['guidance_required'])
        accepted = self.adopt(answered, continue_existing_commission=True, commission_scope_unchanged=True,
                              guidance_no_new_choice_quote=PUBLIC, input_ref=guidance.input_ref(load_lifecycle(self.root)))
        self.assertEqual(accepted['confirmation']['kind'], 'STANDING_COMMISSION_WITH_CLAUDE_GUIDANCE')
        self.assertEqual(foundation.require_foundation_ready(self.root)['guidance']['exchange_id'], 'actual-content')

    def test_budget_only_reply_neither_reanchors_content_nor_confirms_brief(self):
        self.create()
        before = guidance.input_ref(load_lifecycle(self.root))
        proposal = self.propose(questions=[{'id': 'label', 'question': 'Change the title?', 'why': 'Optional fixture'}])
        reply = self.supplement('I approve the cost ceiling only.', action='budget')
        self.assertEqual(guidance.input_ref(load_lifecycle(self.root)), before)
        for command in ('answer', 'confirm'):
            with self.subTest(command=command), self.assertRaisesRegex(ValueError, 'budget-only reply'):
                if command == 'confirm':
                    foundation.confirm_foundation(self.root, revision=proposal['revision'],
                                                  user_text=reply['text'], source=reply['source_ref'])
                else:
                    foundation.answer_foundation(self.root, 'label', revision=proposal['revision'],
                                                 user_text=reply['text'], source=reply['source_ref'], effect='Synthetic')
        completed = self.complete_guidance('payer-separate')
        self.assertEqual(guidance.public_receipt(self.root, completed)['input_ref'], before)
        earlier = self.adopt(proposal)
        coverage = {'kind': 'DIRECT_USER_DECISION', 'input_ref': before,
                    'previous_brief_sha256': earlier['brief_sha256'],
                    'no_new_substantive_prior': True, 'no_new_user_choice': True,
                    'reason': 'Apply only the explicit cost ceiling.',
                    'sources': [{'kind': 'CURRENT_USER_INPUT', 'quote': reply['text']}]}
        with self.assertRaisesRegex(ValueError, 'can cover resource limits only'):
            self.propose(brief={**earlier['brief'], 'goal': 'Invented content'},
                         covered_change={**coverage, 'changed_fields': ['goal']})
        applied = self.propose(brief={**earlier['brief'], 'resources': 'Explicit user cost ceiling'},
                               covered_change={**coverage, 'changed_fields': ['resources']})
        self.assertEqual(applied['status'], 'CONFIRMED')
        self.assertFalse(applied['guidance_required'])
        self.assertEqual(applied['covered_change']['sources'][0]['input_ref']['message_id'], 1)
        self.assertIn('DIRECT_USER_DECISION', foundation.foundation_packet(self.root))

    def test_current_single_colon_cannot_attach_new_formal_content_dependency(self):
        self.create()
        receipt = self.complete_guidance('not-adopted')
        self.supplement('DIGR: Continue the original fixed specification with a council perspective.')
        with self.assertRaisesRegex(ValueError, 'does not allow a new formal content'):
            self.propose(guidance=receipt)
        accepted = self.adopt(self.propose())
        self.assertFalse(accepted['guidance_required'])

    def test_changed_u0_needs_actual_new_authority_and_keeps_explicitly_unchanged_work(self):
        self.create()
        earlier = self.adopt(self.propose())
        create_line(self.root, 'M01', parameters=PARAMETERS, owner='Fixture')
        change = 'DO: Expand the product and implement it with the original source work intact.'
        source = self.supplement(change, action='revise')
        self.assertEqual(foundation.load_foundation(self.root)['status'], 'REVISION_REQUIRED')
        with self.assertRaisesRegex(ValueError, 'awaits.*confirmation'):
            foundation.require_foundation_ready(self.root, owner='M01')
        pending = self.propose(brief={**earlier['brief'], 'results': 'Expanded product'},
                               unaffected_lines={'M01': 'The original sources still apply.'})
        self.assertEqual(foundation.require_foundation_ready(self.root, owner='M01')['status'],
                         'CONFIRMED_UNCHANGED_SCOPE')
        with self.assertRaisesRegex(ValueError, 'scope change needs its own user decision'):
            self.adopt(pending)
        with self.assertRaisesRegex(ValueError, 'current handled material scope instruction'):
            self.adopt(pending, commission_message_id=0)
        self.supplement('Update me on progress.', action='ordinary')
        decided = self.adopt(pending, commission_message_id=1, commission_source=source['source_ref'],
                             commission_sha256=source['sha256'], commission_scope_quote=change)
        confirmation = decided['confirmation']
        self.assertEqual(confirmation['source_message_id'], 1)
        self.assertFalse(confirmation['user_saw_this_plan'])
        self.assertEqual(foundation.require_foundation_ready(self.root)['brief']['results'], 'Expanded product')

    def test_withdrawn_scope_cannot_reappear_through_another_proposal(self):
        self.create()
        self.adopt(self.propose())
        create_line(self.root, 'M01', parameters=PARAMETERS, owner='Fixture')
        actual = self.supplement('Withdraw the original authorization.')
        foundation.revoke_foundation(self.root, user_text=actual['text'], source=actual['source_ref'],
                                     reason='Actual fixture withdrawal')
        pending = self.propose()
        with self.assertRaisesRegex(ValueError, 'withdrawn decision'):
            self.adopt(pending)
        with self.assertRaisesRegex(ValueError, 'revoked authority'):
            self.propose(unaffected_lines={'M01': 'This would revive withdrawn work.'})
