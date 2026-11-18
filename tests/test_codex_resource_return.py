"""Real helper integration, no external model or credentials."""
import json
from pathlib import Path
import tempfile
import unittest

from runtime.codex_allot import plan, observe
from runtime.codex_council import create_council, close_council
from runtime.codex_foundation import BRIEF_FIELDS, propose_foundation, confirm_foundation
from runtime.codex_lifecycle import load_lifecycle, ingest_message, handle_message
from runtime.codex_return import seal_return, response_body, return_status
from runtime.codex_session import create_session


class ResourceReturnTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def task(self, version='0.16.0'):
        request = self.base / (version + '-request.txt')
        request.write_text('DIGR: implement the selected synthetic design', encoding='utf-8')
        root = self.base / version
        create_session(root, request=request, p_run=version + '@' + 'e' * 40)
        propose_foundation(root, {'brief': {key: 'Explicit bounded fixture: ' + title for key, title in BRIEF_FIELDS.items()}, 'questions': []}, reason='Fixture scope')
        source = load_lifecycle(root)['current_message']['source']
        confirm_foundation(root, revision=1, user_text=source['text'], source=source['source_ref'])
        return root

    def final_input(self, root):
        data = {'schema_version': 2, 'result': 'Synthetic implementation completed.',
                'key_changes': 'Separate actual observations from selected resources.',
                'work_process': '| Time | Work |\n| --- | --- |\n| Recorded | Read the actual fixture |',
                'argument_scope': 'Helper integration only, no external inference.',
                'parameters': 'The selected synthetic task has ended.',
                'decisions': [], 'unhandled': [], 'sources': [], 'artifacts': []}
        path = root.parent / (root.name + '-return.json')
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def test_new_pin_adds_real_empty_usage_and_detects_new_observation(self):
        root = self.task()
        self.assertTrue(seal_return(root, self.final_input(root))['can_close'])
        body = response_body(root)
        self.assertIn('本任务用量', body)
        self.assertIn('未取得本任务结构化用量', body)
        (root / 'usage').mkdir()
        (root / 'usage/config.json').write_text('{"account_activity":"unknown"}', encoding='utf-8')
        self.assertEqual(return_status(root)['current_receipt'], 'STALE')

    def test_old_pin_keeps_its_response_contract(self):
        root = self.task('0.15.0')
        seal_return(root, self.final_input(root))
        self.assertNotIn('本任务用量', response_body(root))

    def test_native_council_is_a_real_closure_obligation(self):
        root = self.task()
        create_council(root, council_id='native-only', native_actors=['actual-native-id'])
        result = seal_return(root, self.final_input(root))
        self.assertFalse(result['can_close'])
        self.assertIn('native-only', result['council_completion']['unresolved_councils'])
        close_council(root, 'native-only', reason='Explicit synthetic partial scope; no deliberation claimed')
        result = seal_return(root, self.final_input(root))
        self.assertTrue(result['can_close'])
        self.assertTrue(result['council_completion']['councils'][0]['closed_with_declared_scope'])

    def test_allot_selection_is_not_execution_and_new_user_invalidates_it(self):
        root = self.task()
        block = {'block_id': 'native-block', 'model': 'actual-fixture-model',
                 'kind': 'response', 'evidence': ['Need a complete synthesis of existing results']}
        caps = {'data': [{'model': 'actual-fixture-model', 'supportedReasoningEfforts': [{'reasoningEffort': 'high'}]}]}
        selected = plan(root, block, caps, catalogue_ref='actual synthetic model/list result')
        self.assertFalse(selected['applied'])
        observation = observe(root, 'native-block', {'model': 'actual-fixture-model', 'effort': 'high', 'source_ref': 'actual synthetic host result'})
        self.assertTrue(observation['matches_selection'])
        change = self.base / 'change.txt'
        change.write_text('Continue with revised current requirements', encoding='utf-8')
        message = ingest_message(root, source=change, source_ref='synthetic current change')
        handle_message(root, message_id=message['message_id'], action='continue', reason='Synthetic continuation')
        with self.assertRaisesRegex(ValueError, 'superseded'):
            observe(root, 'native-block', {'model': 'actual-fixture-model', 'effort': 'high', 'source_ref': 'actual synthetic old result'})


if __name__ == '__main__':
    unittest.main()
