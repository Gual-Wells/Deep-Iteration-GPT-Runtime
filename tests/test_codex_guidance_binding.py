"""Offline structural fixtures, never actual Claude returns or user consent."""
from copy import deepcopy
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from runtime import codex_consult as consult, codex_foundation as foundation, codex_guidance as guidance, codex_wallet as wallet
from runtime.codex_lifecycle import ingest_message, handle_message, load_lifecycle
from runtime.codex_session import create_session


PIN = '0.18.0@' + 'e' * 40
OLD_PIN = '0.17.0@' + 'd' * 40
RULE = 'Existing applicable guidance may be reused for direct user constraints and uniquely locked execution.'
NO_CHOICE = 'This delegated implementation introduces no new user choice.'
PUBLIC = '# SYNTHETIC OFFLINE SOURCE\nNo paid model call occurred.\n' + RULE + '\n' + NO_CHOICE + '\n'


class GuidanceBindingTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[1] / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='guidance-binding-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.assertTrue(self.base.is_relative_to(cache))
        self.env = patch.dict(os.environ, {'CODEX_HOME': str(self.base / 'codex-home')})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.request = self.file('request.txt', 'DIGR:: Execute the delegated synthetic task; no external paid authority.\n')
        self.instruction = self.file('instruction.txt', 'Synthetic local fixture; form the task and lock deterministic rules.\n')
        self.root = self.base / 'a'
        self.session = create_session(self.root, request=self.request, p_run=PIN, visits_path=self.base / 'visits')

    def file(self, name, text):
        path = self.base / name
        path.write_text(text, encoding='utf-8', newline='')
        return path

    def complete(self, root=None, name='source', **changes):
        root = root or self.root
        consult.prepare_request(root, input_path=self.instruction, exchange_id=name, max_tokens=128)
        directory = root / 'consult' / 'exchanges' / name
        (directory / 'public.md').write_text(PUBLIC, encoding='utf-8', newline='')
        attempt = consult._read(directory / 'attempt.json')
        attempt.update(transport_status='RESPONDED', public_status='COMPLETE', finish_reason='stop',
            response_model=consult.DEFAULT_MODEL, http_status=200, public_sha256=sha256(PUBLIC.encode()).hexdigest(),
            public_byte_length=len(PUBLIC.encode()), billing_status='KNOWN', known_cost_usd=0.0,
            synthetic_fixture=True)
        attempt.update(changes)
        consult._write(directory / 'attempt.json', attempt)
        return {'exchange_id': name, 'public_sha256': sha256(PUBLIC.encode()).hexdigest()}

    def proposal(self, receipt):
        return {'brief': {key: 'Synthetic fixed ' + key for key in foundation.BRIEF_FIELDS},
                'questions': [], 'guidance': receipt}

    def adopt(self, proposal=None):
        receipt = self.complete()
        proposal = proposal or self.proposal(receipt)
        first = foundation.propose_foundation(self.root, proposal, reason='Synthetic initial source-bound task')
        return foundation.adopt_commission(self.root, self.commission(first, receipt))

    def commission(self, brief, receipt, **changes):
        value = {'revision': brief['revision'], 'guidance': receipt,
            'explicit_execution_commission': True, 'no_new_user_choice': True,
            'commission_source': self.session['request_origin'],
            'commission_sha256': self.session['request_sha256'],
            'reason': 'Synthetic original delegation; this fixture is not actual user consent.'}
        value.update(changes)
        return value

    def message(self, text, action='continue'):
        path = self.file('current-' + str(load_lifecycle(self.root)['message_id'] + 1) + '.txt', text)
        message = ingest_message(self.root, source=path, source_ref='synthetic:' + path.name,
                                 route_pin=PIN if text.lstrip().startswith('DIGR') else None)
        if action is not None:
            handle_message(self.root, message_id=message['message_id'], action=action,
                           reason='Synthetic actual consequence, not intent authentication')
        return guidance.input_ref(load_lifecycle(self.root))

    def covered(self, previous, brief, kind='DIRECT_USER_DECISION', sources=None):
        return {'kind': kind, 'input_ref': guidance.input_ref(load_lifecycle(self.root)),
            'previous_brief_sha256': previous['brief_sha256'],
            'changed_fields': sorted(key for key in foundation.BRIEF_FIELDS if previous['brief'][key] != brief[key]),
            'no_new_substantive_prior': True, 'no_new_user_choice': True,
            'guidance_quote': RULE, 'reason': 'Synthetic application of the selected existing rule.',
            'sources': sources or [{'kind': 'CURRENT_USER_INPUT', 'quote': 'Budget ceiling is now 0.25'}]}

    def test_hashed_request_binds_distinct_session_uuid(self):
        a = self.complete()
        other = self.base / 'b'
        b = create_session(other, request=self.request, p_run=PIN, visits_path=self.base / 'visits')
        self.complete(other)
        _, attempt_a, request_a = consult._load(self.root, a['exchange_id'])
        _, attempt_b, request_b = consult._load(other, a['exchange_id'])
        self.assertEqual(self.session['request_sha256'], b['request_sha256'])
        self.assertNotEqual(self.session['task_uuid'], b['task_uuid'])
        self.assertNotEqual(request_a['user'], request_b['user'])
        self.assertNotEqual(attempt_a['request_sha256'], attempt_b['request_sha256'])
        self.assertEqual(guidance.public_receipt(self.root, a)['task_identity']['task_uuid'], self.session['task_uuid'])

    def test_copy_into_same_text_new_task_rejected_by_actual_loader(self):
        receipt = self.complete()
        other = self.base / 'b'
        create_session(other, request=self.request, p_run=PIN, visits_path=self.base / 'visits')
        copied = other / 'consult' / 'exchanges' / 'source'
        copied.parent.mkdir(parents=True)
        shutil.copytree(self.root / 'consult' / 'exchanges' / 'source', copied)
        with self.assertRaisesRegex(ValueError, 'task UUID'):
            guidance.public_receipt(other, receipt)

    def test_same_task_move_preserves_identity(self):
        receipt = self.complete()
        moved = self.base / 'moved'
        shutil.move(str(self.root), str(moved))
        observed = guidance.public_receipt(moved, receipt)
        self.assertEqual(observed['task_identity']['task_uuid'], self.session['task_uuid'])

    def test_copied_foundation_is_not_a_same_text_new_task_decision(self):
        self.adopt()
        other = self.base / 'b'
        create_session(other, request=self.request, p_run=PIN, visits_path=self.base / 'visits')
        shutil.copyfile(self.root / 'foundation.json', other / 'foundation.json')
        with self.assertRaisesRegex(ValueError, 'different task UUID'):
            foundation.load_foundation(other)

    def test_rehashed_request_still_cannot_drop_task_identity(self):
        self.complete()
        directory, attempt, request = consult._load(self.root, 'source')
        request.pop('user')
        consult._write(directory / 'request.json', request)
        attempt['request_sha256'] = consult._hash(consult._json_bytes(request))
        consult._write(directory / 'attempt.json', attempt)
        with self.assertRaisesRegex(ValueError, 'task UUID'):
            consult._load(self.root, 'source')

    def test_new_paper_request_combines_scope_and_task_identity(self):
        from runtime import codex_paper as paper
        batch = self.base / 'batch'
        paper.initialize(batch, p_run=PIN, authorization=self.request,
                         source_ref='SYNTHETIC_PAPER_SELECTION', task_root=self.root)
        parameters = {'N': 1, 'R': 1, 'D': 0, 'V': 0, 'L': 3, 'T': '1min', 'B': 0,
                      'S': {'n': 1, 't': '1min', 'r': 0, 'b': 0}}
        selected = paper.add_paper(batch, paper_id='one', title='Synthetic paper', line='M01',
                                   owner='synthetic-native', parameters=parameters)
        consult.prepare_request(self.root, input_path=self.instruction, paper_root=Path(selected['paper_root']),
                                exchange_id='paper', max_tokens=128)
        _, attempt, request = consult._load(self.root, 'paper')
        self.assertEqual(attempt['task_binding']['authoring_scope'], attempt['authoring_scope'])
        self.assertEqual(request['user'], consult._binding_user(attempt['task_binding']))
        self.assertNotEqual(request['user'], 'digr-paper-' + attempt['authoring_scope_sha256'])

    def test_new_member_request_combines_scope_and_task_identity(self):
        from runtime import codex_council as council
        council.create_council(self.root, council_id='synthetic', native_actors=['native'],
                               enable_claude=True, member_count=1)
        result = council.prepare_round(self.root, 'synthetic', max_tokens=128)
        job = result['rounds'][-1]['jobs']['member-1']
        self.assertEqual(job['status'], 'PREPARED')
        _, attempt, request = consult._load(self.root, job['exchange_id'])
        self.assertEqual(attempt['task_binding']['council_scope'], attempt['council_scope'])
        self.assertEqual(request['user'], consult._binding_user(attempt['task_binding']))
        self.assertNotEqual(request['user'], 'digr-council-' + attempt['council_scope_sha256'])

    def legacy(self):
        root = self.base / 'legacy'
        session = create_session(root, request=self.request, p_run=OLD_PIN, visits_path=self.base / 'visits')
        receipt = self.complete(root)
        directory, attempt, request = consult._load(root, 'source')
        self.assertNotIn('task_binding', attempt)
        self.assertNotIn('user', request)
        claim_id = wallet.claim_id(root, session, 'source')
        ledger = wallet.ledger_path()
        ledger.parent.mkdir(parents=True)
        with closing(sqlite3.connect(ledger)) as db:
            db.execute('CREATE TABLE claims (claim_id TEXT PRIMARY KEY,task_id TEXT,exchange_id TEXT,request_sha256 TEXT,wallet_id TEXT,state TEXT)')
            db.execute('INSERT INTO claims VALUES (?,?,?,?,?,?)', (claim_id, wallet.task_id(root, session),
                'source', attempt['request_sha256'], 'SYNTHETIC_NO_PAID_ACCOUNT', 'KNOWN'))
            db.commit()
        attempt['wallet_claim'] = {'format': wallet.FORMAT, 'claim_id': claim_id,
            'ledger_path': ledger.as_posix(), 'request_sha256': attempt['request_sha256'],
            'wallet_id': 'SYNTHETIC_NO_PAID_ACCOUNT'}
        consult._write(directory / 'attempt.json', attempt)
        receipt['legacy_task_adoption'] = {'basis': 'PRECALL_WALLET_CLAIM', 'claim_id': claim_id}
        return root, session, receipt

    def test_explicit_legacy_wallet_adoption_is_read_only_and_rejects_new_task(self):
        root, session, receipt = self.legacy()
        directory = root / 'consult' / 'exchanges' / 'source'
        before = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
        self.assertEqual(guidance.public_receipt(root, receipt)['task_identity']['task_uuid'], session['task_uuid'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()})
        stripped = {k: v for k, v in receipt.items() if k != 'legacy_task_adoption'}
        with self.assertRaisesRegex(ValueError, 'explicit adoption'):
            guidance.public_receipt(root, stripped)
        other = self.base / 'other-legacy'
        create_session(other, request=self.request, p_run=OLD_PIN, visits_path=self.base / 'visits')
        copied = other / 'consult' / 'exchanges' / 'source'
        copied.parent.mkdir(parents=True)
        shutil.copytree(directory, copied)
        consult._load(other, 'source')  # Old pin's original loader semantics are unchanged.
        with self.assertRaisesRegex(ValueError, 'different task UUID'):
            guidance.public_receipt(other, receipt)

    def test_legacy_claim_needs_independent_matching_ledger_row(self):
        root, _, receipt = self.legacy()
        with closing(sqlite3.connect(wallet.ledger_path())) as db:
            db.execute('UPDATE claims SET request_sha256=?', ('f' * 64,))
            db.commit()
        with self.assertRaisesRegex(ValueError, 'no committed same-task'):
            guidance.public_receipt(root, receipt)

    def test_missing_partial_wrong_model_wrong_role_and_public_hash_rejected(self):
        changes = ({'public_status': 'PARTIAL'}, {'response_model': 'other'},
                   {'participation_role': 'council_member'}, {'public_sha256': 'f' * 64})
        receipts = [self.complete(name='bad-' + str(index)) for index in range(len(changes))]
        for receipt, changes in zip(receipts, changes):
            path = self.root / 'consult' / 'exchanges' / receipt['exchange_id'] / 'attempt.json'
            original = consult._read(path)
            consult._write(path, dict(original, **changes))
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                guidance.public_receipt(self.root, receipt)
            consult._write(path, original)
        with self.assertRaises(ValueError):
            foundation.propose_foundation(self.root, self.proposal(None), reason='Missing formal source')

    def test_commission_keeps_original_authority_without_forging_plan_consent(self):
        value = self.adopt()
        self.assertFalse(value['confirmation']['user_saw_this_plan'])
        self.assertIsNone(value['confirmation']['user_confirmed_revision'])
        self.assertEqual(value['confirmation']['source'], self.session['request_origin'])
        self.assertEqual(foundation.require_foundation_ready(self.root)['revision'], 1)

    def test_direct_budget_material_change_reuses_guide_without_new_confirmation(self):
        previous = self.adopt()
        self.message('Budget ceiling is now 0.25; the delegated goal and locked rule are unchanged.')
        proposal = self.proposal(previous['guidance'])
        proposal['brief']['resources'] = 'Actual direct ceiling 0.25'
        proposal['covered_change'] = self.covered(previous, proposal['brief'])
        result = foundation.propose_foundation(self.root, proposal, reason='Apply the actual direct user constraint')
        self.assertEqual(result['status'], 'CONFIRMED')
        self.assertEqual(result['guidance']['exchange_id'], 'source')
        self.assertIsNone(result['confirmation']['user_confirmed_revision'])
        self.assertFalse(result['confirmation']['user_saw_this_plan'])
        self.assertEqual(result['confirmation']['current_input_id'], 0)
        self.assertEqual(result['covered_change']['input_ref']['message_id'], 1)
        self.assertEqual(len(list((self.root / 'consult' / 'exchanges').glob('*/attempt.json'))), 1)
        foundation.require_foundation_ready(self.root)
        self.assertIn('DIRECT_USER_DECISION', foundation.foundation_packet(self.root))

    def test_non_material_label_cannot_change_resources(self):
        previous = self.adopt()
        proposal = self.proposal(previous['guidance'])
        proposal['brief']['resources'] = 'New constraint'
        with self.assertRaisesRegex(ValueError, 'decision fields changed'):
            foundation.propose_foundation(self.root, proposal, reason='False editorial label', change_kind='non_material')

    def test_source_observation_remains_non_material(self):
        previous = self.adopt()
        self.message('A new source observation; no changed decision.')
        proposal = self.proposal(previous['guidance'])
        proposal['brief']['basis'] = 'Actual added source observation'
        value = foundation.propose_foundation(self.root, proposal, reason='Observation only', change_kind='non_material')
        self.assertEqual(value['status'], 'CONFIRMED')

    def test_locked_execution_and_established_fact_need_actual_artifact_bytes(self):
        previous = self.adopt()
        fact = self.file('synthetic-fact.txt', 'SYNTHETIC: locked arithmetic yielded result R.\n')
        source = {'kind': 'ACTUAL_ARTIFACT', 'path': str(fact), 'sha256': sha256(fact.read_bytes()).hexdigest(),
                  'quote': 'locked arithmetic yielded result R'}
        for kind in ('LOCKED_EXECUTION', 'ESTABLISHED_FACT'):
            proposal = self.proposal(previous['guidance'])
            proposal['brief'] = deepcopy(previous['brief'])
            proposal['brief']['results'] = 'Apply deterministic R under the existing rule: ' + kind
            proposal['covered_change'] = self.covered(previous, proposal['brief'], kind, [source])
            result = foundation.propose_foundation(self.root, proposal, reason='Apply settled execution')
            self.assertEqual(result['status'], 'CONFIRMED')
            previous = result
        fact.write_text('Different artifact', encoding='utf-8')
        proposal['brief']['results'] = 'Another fixed fact application'
        proposal['covered_change'] = self.covered(previous, proposal['brief'], 'ESTABLISHED_FACT', [source])
        with self.assertRaises(ValueError):
            guidance.covered_revision(self.root, self.session, proposal['covered_change'], previous=previous, brief=proposal['brief'])

    def test_covered_claim_must_bind_current_source_all_fields_and_actual_guidance(self):
        previous = self.adopt()
        self.message('Budget ceiling is now 0.25; preserve the locked goal.')
        proposal = self.proposal(previous['guidance'])
        proposal['brief']['resources'] = '0.25'
        base = self.covered(previous, proposal['brief'])
        for change in ({'kind': 'PURE_ENGINEERING'}, {'changed_fields': ['goal']}, {'input_ref': previous['guidance']['input_ref']},
                {'guidance_quote': 'Invented rule'}, {'no_new_substantive_prior': False},
                {'sources': [{'kind': 'CURRENT_USER_INPUT', 'quote': 'A new model-authored goal'}]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                guidance.covered_revision(self.root, self.session, dict(base, **change), previous=previous, brief=proposal['brief'])

    def test_new_substantive_prior_cannot_use_old_current_exchange(self):
        previous = self.adopt()
        proposal = self.proposal(previous['guidance'])
        proposal['brief']['approach'] = 'New subjective route not locked by the prior source'
        with self.assertRaisesRegex(ValueError, 'new substantive prior'):
            foundation.propose_foundation(self.root, proposal, reason='New prior, same old message')
        self.message('Actual current input introduces a new delegated route question.')
        with self.assertRaisesRegex(ValueError, 'current input'):
            foundation.propose_foundation(self.root, proposal, reason='New prior, newer message')
        proposal['guidance'] = self.complete(name='new-current-guidance')
        draft = foundation.propose_foundation(self.root, proposal, reason='New actual current guidance')
        with self.assertRaisesRegex(ValueError, 'actual unchanged commission scope'):
            foundation.adopt_commission(self.root, self.commission(draft, proposal['guidance'],
                continue_existing_commission=True, guidance_no_new_choice_quote=NO_CHOICE))
        adopted = foundation.adopt_commission(self.root, self.commission(draft, proposal['guidance'],
            continue_existing_commission=True, guidance_no_new_choice_quote=NO_CHOICE,
            commission_scope_unchanged=True, commission_scope_quote='Execute the delegated synthetic task',
            input_ref=guidance.input_ref(load_lifecycle(self.root))))
        self.assertEqual(adopted['status'], 'CONFIRMED')
        self.assertFalse(adopted['confirmation']['user_saw_this_plan'])
        self.assertIsNone(adopted['confirmation']['user_confirmed_revision'])

    def test_pause_pending_stop_and_revocation_cannot_reuse_or_rebind(self):
        previous = self.adopt()
        self.message('Pending actual correction', action=None)
        with self.assertRaisesRegex(ValueError, 'pending'):
            foundation.require_foundation_ready(self.root)
        with self.assertRaisesRegex(ValueError, 'pending'):
            foundation.bind_guidance(self.root, {'revision': 1, 'guidance': previous['guidance']})
        message = load_lifecycle(self.root)
        handle_message(self.root, message_id=message['message_id'], action='pause', reason='Actual pause fixture')
        with self.assertRaisesRegex(ValueError, 'PAUSED'):
            guidance.public_receipt(self.root, previous['guidance'], current=False)
        self.message('Stop the task', action='stop')
        with self.assertRaisesRegex(ValueError, 'STOPPED'):
            foundation.require_foundation_ready(self.root)

    def test_single_colon_override_does_not_request_new_claude(self):
        previous = self.adopt()
        self.message('DIGR: Execute only the fixed existing task.', action='continue')
        self.assertEqual(load_lifecycle(self.root)['claude_policy']['mode'], 'DENY')
        proposal = self.proposal(None)
        result = foundation.propose_foundation(self.root, proposal, reason='Current single-colon override', change_kind='non_material')
        self.assertNotIn('guidance', result)
        self.assertEqual(result['status'], 'CONFIRMED')
        foundation.require_foundation_ready(self.root)
        self.assertEqual(len(list((self.root / 'consult' / 'exchanges').glob('*/attempt.json'))), 1)


if __name__ == '__main__':
    unittest.main()
