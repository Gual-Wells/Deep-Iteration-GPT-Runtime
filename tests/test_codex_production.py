"""Run the production record and prepare gates with local receipt fixtures."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from runtime import codex_collaboration as collaboration, codex_consult as consult, codex_production as production
from runtime.codex_lifecycle import handle_message, ingest_message
from runtime.codex_session import create_session

PIN = '1.1.0@' + 'f' * 40


class ProductionRecordTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[1] / '.cache'
        cache.mkdir(exist_ok=True)
        temp = TemporaryDirectory(prefix='codex-production-', dir=cache)
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.root = self.work / 'session'
        create_session(self.root, request=self.file('user.txt', 'DIGR:: Produce the assigned result.'), p_run=PIN)
        self.scope = self.file('assignment.md', 'Shared sources and acceptance criteria.\r\n')
        self.host = self.file('host.md', 'Use the same assignment to return the result.')
        guard = patch.object(consult, '_opener', side_effect=AssertionError('No provider send allowed'))
        guard.start()
        self.addCleanup(guard.stop)

    def file(self, name, body):
        path = self.work / name
        path.write_bytes(body.encode('utf-8'))
        return path

    def start(self, production_id='explanation'):
        return production.start(self.root, production_id, scope_path=self.scope,
                                actor='D01', dispatch_ref='host-dispatch-1')

    def prepare(self, exchange, **kwargs):
        return consult.prepare_request(self.root, input_path=self.host, exchange_id=exchange, max_tokens=100,
                                       production_id='explanation', **kwargs)

    def fixture_return(self, exchange, body, *, public_status='COMPLETE', model=None):
        directory, attempt, request = consult._load(self.root, exchange)
        raw = body.encode('utf-8')
        consult._write_bytes(directory / 'public.md', raw)
        attempt.update(transport_status='RESPONDED', public_status=public_status, billing_status='KNOWN',
                       known_cost_usd=0, http_status=200, response_model=model or request['model'],
                       finish_reason='stop', public_sha256=consult._hash(raw), public_byte_length=len(raw))
        consult._write(directory / 'attempt.json', attempt)

    def test_actual_pair_arbitration_and_applied_file(self):
        state = self.start()
        self.assertEqual(state['status'], 'DISPATCHED')
        self.assertFalse(production.completion_status(self.root)['complete'])
        self.prepare('claude-candidate')
        self.fixture_return('claude-candidate', 'Claude candidate.\n', public_status='PARTIAL')
        arbitration = {'production_stage': 'arbitration', 'candidate_exchange': 'claude-candidate'}
        with self.assertRaisesRegex(ValueError, 'native candidate'):
            self.prepare('arbitration', **arbitration)
        native = self.file('draft.md', 'Native candidate.\r\n')
        with self.assertRaisesRegex(ValueError, 'assigned native actor'):
            production.submit_native(self.root, 'explanation', actor='other', output_path=native, return_ref='return-1')
        production.submit_native(self.root, 'explanation', actor='D01', output_path=native, return_ref='return-1')
        with self.assertRaisesRegex(ValueError, 'complete actual Claude return'):
            self.prepare('arbitration', **arbitration)
        self.fixture_return('claude-candidate', 'Claude candidate.\n', model='anthropic/claude-opus-4')
        with self.assertRaisesRegex(ValueError, 'complete actual Claude return'):
            self.prepare('arbitration', **arbitration)
        self.fixture_return('claude-candidate', 'Claude candidate.\n')
        self.prepare('arbitration', **arbitration)
        _, attempt, request = consult._load(self.root, 'arbitration')
        self.assertEqual(request['messages'][-2], {'role': 'assistant', 'content': 'Claude candidate.\n'})
        self.assertIn('Native candidate.\r\n', request['messages'][-1]['content'])
        self.assertNotIn('Claude candidate.\n', request['messages'][-1]['content'])
        request['messages'][-2]['content'] = 'A different draft'
        with self.assertRaisesRegex(ValueError, 'replay the actual'):
            production.require_current(self.root, attempt['production'], request=request)
        final = self.file('final.md', 'Final artifact adopts the native structure.')
        applied = {'arbitration_exchange': 'arbitration', 'output_path': final, 'effect': 'Adopted the native structure'}
        with self.assertRaisesRegex(ValueError, 'complete actual Claude return'):
            production.record_applied(self.root, 'explanation', **applied)
        self.fixture_return('arbitration', 'Adopt the native structure.')
        self.assertFalse(production.completion_status(self.root)['complete'])
        recorded = production.record_applied(self.root, 'explanation', **applied)
        self.assertEqual(recorded['applied']['arbitration']['exchange_id'], 'arbitration')
        self.assertEqual(recorded['applied']['binding']['candidate_exchange'], 'claude-candidate')
        self.assertTrue(production.completion_status(self.root)['complete'])
        self.assertEqual(production.require_applied(self.root, 'explanation'), recorded['applied'])
        final.write_bytes(b'changed since application')
        with self.assertRaisesRegex(ValueError, 'final artifact differs'):
            production.require_applied(self.root, 'explanation')
        self.assertEqual(production.inspect(self.root, 'explanation')['status'], 'APPLIED')
        self.assertEqual(production.completion_status(self.root)['unresolved_productions'], ['explanation'])
        with self.assertRaisesRegex(ValueError, 'same current assignment and arbitration'):
            production.record_applied(self.root, 'explanation', **{**applied, 'arbitration_exchange': 'claude-candidate'})
        reapplied = production.record_applied(self.root, 'explanation', **applied)
        original = recorded['applied']['output']
        self.assertNotEqual(reapplied['applied']['output']['sha256'], original['sha256'])
        self.assertEqual(reapplied['applied']['previous_outputs'][0]['output'], original)
        self.assertEqual(Path(original['snapshot_path']).read_bytes(), b'Final artifact adopts the native structure.')
        self.assertTrue(production.completion_status(self.root)['complete'])

    def test_one_formal_scope_binds_two_coequal_external_arbitrations(self):
        self.root = self.work / 'paired'
        create_session(self.root, request=self.file('paired.txt', 'DIGR:: Produce the shared result.'),
                       p_run='1.7.0@' + 'b' * 40)
        self.start()
        for name, model in collaboration.EXTERNAL_MODELS.items():
            self.prepare(name + '-candidate', model=model)
            _, attempt, _ = consult._load(self.root, name + '-candidate')
            self.assertTrue(attempt['collaboration_contract']['subjective_guidance_priority'])
            self.fixture_return(name + '-candidate', name + ' public candidate.\n',
                                model=collaboration.OPENROUTER_SNAPSHOTS[model])
        production.submit_native(self.root, 'explanation', actor='D01',
                                 output_path=self.file('native.md', 'Native public candidate.'), return_ref='return-2')
        for name, model in collaboration.EXTERNAL_MODELS.items():
            self.prepare(name + '-ruling', model=model, production_stage='arbitration',
                         candidate_exchange=name + '-candidate')
            self.fixture_return(name + '-ruling', name + ' public ruling.', model=collaboration.OPENROUTER_SNAPSHOTS[model])
        final = self.file('joint.md', 'An artifact applying both complete rulings.')
        recorded = production.record_applied(self.root, 'explanation', arbitration_exchange='carbon-ruling',
            peer_exchange='sonnet-ruling', output_path=final, effect='Adopted compatible supported decisions.')
        self.assertEqual(recorded['applied']['peer']['arbitration']['exchange_id'], 'sonnet-ruling')
        self.assertTrue(production.require_applied(self.root, 'explanation', arbitration_exchange='sonnet-ruling'))
        self.assertTrue(production.completion_status(self.root)['complete'])

    def test_user_revision_invalidates_prepared_stage_and_explicitly_releases_old_assignment(self):
        self.start()
        binding, _ = production.bind_exchange(self.root, 'explanation', stage='candidate')
        quote = 'Use this new scope and retire the earlier production assignment.'
        selected = ingest_message(self.root, source=self.file('change.txt', quote), source_ref='user-revision')
        handle_message(self.root, message_id=selected['message_id'], action='revise', reason='Changed the scope')
        with self.assertRaisesRegex(ValueError, 'current content input'):
            production.require_current(self.root, binding)
        self.assertFalse(production.inspect(self.root, 'explanation')['current'])
        self.start('replacement')
        with self.assertRaisesRegex(ValueError, 'later handled user source'):
            production.release(self.root, 'explanation', disposition='superseded', source='made-up', quote=quote,
                               effect='Replace the old scope', replacement_production_id='replacement')
        retired = production.release(self.root, 'explanation', disposition='superseded', source='user-revision',
            quote=quote, effect='Replace the old scope', replacement_production_id='replacement')
        self.assertEqual(retired['status'], 'SUPERSEDED')
        self.assertFalse(retired['complete'])
        self.assertEqual(production.completion_status(self.root)['unresolved_productions'], ['replacement'])

    def test_old_pin_and_council_only_do_not_register_formal_production(self):
        for name, pin, request, error in (
                ('old', '1.0.0@' + 'e' * 40, 'DIGR:: An existing task.', 'Stable 1.1'),
                ('one-layer', PIN, 'DIGR: An existing council-only task.', 'two-layer')):
            with self.subTest(name=name):
                root = self.work / name
                create_session(root, request=self.file(name + '.txt', request), p_run=pin)
                with self.assertRaisesRegex(ValueError, error):
                    production.start(root, 'explanation', scope_path=self.scope, actor='D01', dispatch_ref='event')
                self.assertTrue(production.completion_status(root)['complete'])


if __name__ == '__main__':
    unittest.main()
