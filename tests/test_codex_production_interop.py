"""Exercise actual Consult send, budget and return transitions through localhost."""
import json
from pathlib import Path
import unittest

import test_codex_council as fixture
from runtime import codex_consult as consult, codex_consult_budget as budget, codex_production as production
from runtime.codex_lifecycle import handle_message, ingest_message
from runtime.codex_return import return_status
from runtime.codex_session import create_session


class ProductionInteropTests(unittest.TestCase):
    setUp = fixture.CouncilRuntimeTests.setUp
    stop_server = fixture.CouncilRuntimeTests.stop_server
    file = fixture.CouncilRuntimeTests.file
    facts = fixture.CouncilRuntimeTests.facts

    def task(self, name, *, allow):
        request = self.file(name + '-user.txt', 'DIGR:: Prepare the same synthetic product.')
        root = self.folder / name
        create_session(root, request=request, p_run='1.1.0@' + 'f' * 40)
        return root

    def send(self, exchange):
        decision = self.file(exchange + '-split-decision.json', json.dumps({
            'decision': 'Use actual sources and leave engineering with the native fixture.',
            'local_work': [{'task': 'Compose the request', 'result': 'Complete local fixture content.'}],
            'claude_value': 'Read and answer the bound content request.',
            'context_decision': 'Keep the shared assignment and the required candidate texts.',
        }))
        bound = self.folder / (exchange + '-split-plan.json')
        consult.bind_split_decision(self.root, exchange, input_path=decision, output=bound)
        return consult.call_once(self.root, exchange, facts=self.facts(), ceiling_usd=.2,
                                 split_path=bound, config_path=self.config)

    def test_paid_flow_needs_two_actual_candidates_and_applied_output(self):
        with self.assertRaisesRegex(ValueError, 'register real native'):
            consult.prepare_request(self.root, input_path=self.redeliberation)
        consult.prepare_request(self.root, input_path=self.redeliberation, guidance=True, exchange_id='guidance')
        scope = self.file('shared.md', 'Produce one usable result for the shared requirements.')
        production.start(self.root, 'work', scope_path=scope, actor='native-actual',
                         dispatch_ref='synthetic-host-dispatch')
        consult.prepare_request(self.root, input_path=self.redeliberation, production_id='work',
                                max_tokens=100, exchange_id='candidate')
        self.assertFalse(return_status(self.root)['production_completion']['complete'])

        costs = [
            {'exchange_id': 'candidate', 'facts': self.facts(), 'ceiling_usd': .2},
            {'planned_production': {'production_id': 'work', 'stage': 'arbitration',
                                    'model': consult.DEFAULT_MODEL, 'max_tokens': 100,
                                    'purpose': 'Compare the two exact candidates.'},
             'facts': self.facts(), 'ceiling_usd': .2},
        ]
        offer = budget.preview(self.root, jobs=costs, task_ceiling_usd=.5,
                               scope='One paired production and arbitration', wallet_id='synthetic-one-account')
        quote = 'I approve both quoted stages up to $0.50.'
        reply = self.file('approval.txt', quote)
        current = ingest_message(self.root, source=reply, source_ref='actual-fixture-approval')
        handle_message(self.root, message_id=current['message_id'], action='budget', reason='Approve these two stages')
        budget.approve(self.root, preview_path=self.file('offer.json', json.dumps(offer)),
                       user_text=quote, source='actual-fixture-approval', quote=quote)

        candidate = self.send('candidate')
        self.assertEqual(candidate['exchange']['public_status'], 'COMPLETE')
        self.assertNotIn(self.native.read_text().strip(), json.dumps(self.server.requests[0], ensure_ascii=False))
        with self.assertRaisesRegex(ValueError, 'actual assigned native candidate'):
            consult.prepare_request(self.root, input_path=self.redeliberation, production_id='work',
                                    production_stage='arbitration', candidate_exchange='candidate')
        self.assertEqual(len(self.server.requests), 1)

        production.submit_native(self.root, 'work', actor='native-actual', output_path=self.native,
                                 return_ref='synthetic-host-native-return')
        consult.prepare_request(self.root, input_path=self.redeliberation, production_id='work',
                                production_stage='arbitration', candidate_exchange='candidate',
                                max_tokens=100, exchange_id='verdict')
        verdict = self.send('verdict')
        sent = self.server.requests[1]['messages']
        self.assertEqual(sent[-2]['content'], Path(candidate['public_path']).read_bytes().decode('utf-8'))
        self.assertIn(self.native.read_bytes().decode('utf-8'), sent[-1]['content'])
        self.assertEqual(verdict['exchange']['budget_facts']['authorization_evidence']['production']['stage'],
                         'arbitration')
        self.assertFalse(return_status(self.root)['production_completion']['complete'])

        final = self.file('selected.md', 'The chosen result incorporates the actual arbitration.')
        production.record_applied(self.root, 'work', arbitration_exchange='verdict', output_path=final,
                                  effect='Apply the selected synthetic content.')
        self.assertTrue(return_status(self.root)['production_completion']['complete'])
        with self.assertRaisesRegex(ValueError, 'already started'):
            consult.call_once(self.root, 'verdict', facts=self.facts(), ceiling_usd=.2)
        self.assertEqual(len(self.server.requests), 2)
