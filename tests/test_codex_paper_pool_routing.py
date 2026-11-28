from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from runtime import codex_paper_pool_route as pp
from runtime.codex_foundation import BRIEF_FIELDS, adopt_commission, propose_foundation
from runtime.codex_lifecycle import handle_message, ingest_message
from runtime.codex_profile import classify_invocation
from runtime.codex_return import close_return, response_body, seal_return
from runtime.codex_session import create_session


PIN = '2.0.0@' + 'a' * 40
OLD = '1.9.0@' + 'b' * 40
BASELINE = {'environment': ['selected workspace and tools'], 'routes': ['existing route'],
            'access': ['author manuscript'], 'search': ['current literature'], 'research': ['check premises']}
BRIEF = {key: 'Synthetic work fixture.' for key in BRIEF_FIELDS}


class PaperPoolRoutingTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.base = Path(folder.name).resolve()
        self.request = self.write('request.txt', 'DIGR(F=0)：Compare the supplied work and find recent related work.')
        self.product = self.write('primary.md', 'Actual fixture primary work and analysis.')
        self.pool_work = self.write('pool.md', 'Actual fixture pool synthesis and scoped limits.')
        self.original = self.write('research.md', '\n'.join(
            f'attempt:{kind}: observed {target}' for kind in pp.SOURCE_FIELDS for target in BASELINE[kind]))
        self.evidence = self.write('evidence.md', 'Fixture source evidence for the separate review.')
        self.root = self.base / 'task'

    def write(self, name, text):
        path = self.base / name
        path.write_text(text, encoding='utf-8')
        return path

    def create(self, *, pin=PIN, root=None):
        root = root or self.root
        return create_session(root, request=self.request, p_run=pin,
                              visits_path=self.base / 'visits.jsonl', run_id=root.name)

    def proposal(self, *, academic=True, task_only=False):
        plan = {'academic': academic, 'reason': 'Classification from the actual task object.',
                'baseline': deepcopy(BASELINE)}
        if academic:
            plan['assignment'] = {
                'question': 'Which comparison assumptions survive?',
                'work': 'Review the paper and the material comparison conditions.',
                'deliverable': 'A comparison matrix and boundary analysis.',
                'acceptance': 'A reviewer can identify the source and rejected transfers.',
                'source_scope': 'task-only' if task_only else 'pool-and-task',
            }
            if task_only:
                plan['assignment']['scope_basis'] = 'Synthetic user-selected original only.'
        return {'brief': {**BRIEF, pp.PLAN_FIELD: plan}, 'questions': []}

    def start(self, *, academic=True, task_only=False, root=None):
        root = root or self.root
        meta = self.create(root=root)
        proposed = propose_foundation(root, self.proposal(academic=academic, task_only=task_only),
                                      reason='Original purpose from the fixture.')
        adopt_commission(root, {
            'revision': proposed['revision'], 'commission_source': meta['request_origin'],
            'commission_sha256': meta['request_sha256'], 'commission_scope_quote': 'Compare the supplied work',
            'explicit_execution_commission': True, 'no_new_user_choice': True,
            'reason': 'Apply the existing synthetic commission.',
        })

    def return_input(self, *, replacement=None, extra_delivery=None):
        data = {
            'schema_version': 3, 'result': 'Primary fixture result.',
            'key_changes': 'Fixture route was exercised.',
            'work_process': '| Work | Observation |\n|---|---|\n| Fixture | Completed |',
            'argument_scope': 'Fixture evidence only.', 'parameters': 'Synthetic F0.',
            'sources': [str(self.product)],
            'artifacts': [{'label': 'Unreviewed substitute' if replacement else 'Current final product',
                           'path': str(replacement or self.product)}],
        }
        if extra_delivery is not None:
            data['delivery_files'] = [str(replacement or self.product), str(extra_delivery)]
        return self.write('replacement.json' if replacement or extra_delivery else 'return.json', json.dumps(data))

    def baseline_results(self):
        for kind in pp.SOURCE_FIELDS:
            for target in BASELINE[kind]:
                pp.baseline_result(self.root, kind=kind, target=target, disposition='used',
                                   reason='The original route recorded this actual fixture result.',
                                   attempt=f'attempt:{kind}', evidence_anchor=f'observed {target}',
                                   artifact=self.original)

    def work_result(self, *, task_only=False):
        pp.dispatch(self.root, actor='fixture-worker', source='actual fixture handoff')
        sources = [self.evidence]
        if not task_only:
            query = {'corpus_fingerprint': 'fixture-corpus', 'query': ['scope'],
                     'results': [{'paper_id': 'P0001'}]}
            receipt = pp.record_query(self.root, context=pp.query_context(self.root),
                                      query=query, response=query)
            sources.append(self.write('query.json', json.dumps({**query, 'task_query_receipt': receipt})))
        pp.result(self.root, artifact=self.pool_work, contribution='Independent comparison with its conditions.',
                  sources=sources, citations=[] if task_only else ['P0001'])
        pp.consider(self.root, disposition='applied', effect='Changed one comparison in the main result.',
                    artifact=self.product, return_input=self.return_input())

    def test_plan_is_required_and_preserves_baseline_for_both_routes(self):
        self.create()
        with self.assertRaisesRegex(ValueError, 'semantic academic decision'):
            propose_foundation(self.root, {'brief': BRIEF}, reason='This omits identification.')
        incomplete = self.proposal()
        del incomplete['brief'][pp.PLAN_FIELD]['assignment']
        with self.assertRaisesRegex(ValueError, 'substantive Paper Pool assignment'):
            propose_foundation(self.root, incomplete, reason='This omits the academic work package.')
        # Use fresh task identities for confirmed examples.
        academic_root, ordinary_root = self.base / 'academic', self.base / 'ordinary'
        self.start(root=academic_root)
        self.start(academic=False, root=ordinary_root)
        self.assertEqual(pp.route(academic_root)['baseline'], pp.route(ordinary_root)['baseline'])
        self.assertEqual(pp.route(academic_root)['baseline'], BASELINE)
        self.assertEqual(pp.route(academic_root)['target']['name'], 'Paper Pool')
        self.assertIsNone(pp.route(ordinary_root)['target'])
        self.assertTrue(pp.completion(ordinary_root)['can_close'])

    def test_baseline_can_return_while_pending_and_required_results_cannot_be_skipped(self):
        self.start()
        input_path = self.return_input()
        staged = seal_return(self.root, input_path)
        self.assertEqual(staged['current_receipt'], 'READY_UNCLOSED')
        self.assertIn('Primary fixture result.', response_body(self.root))
        self.assertFalse(staged['can_close'])
        self.work_result()
        self.assertFalse(pp.completion(self.root)['can_close'])
        self.assertEqual(len(pp.completion(self.root)['missing_baseline_results']), 3)
        self.baseline_results()
        self.assertTrue(pp.completion(self.root)['can_close'])
        other = self.write('unreviewed.md', 'An unreviewed replacement with a different conclusion.')
        changed = seal_return(self.root, self.return_input(replacement=other))
        self.assertFalse(changed['can_close'])
        self.assertIn('Paper Pool consideration must cover the selected reply and final artifacts',
                      changed['cannot_close'])
        self.assertFalse(seal_return(self.root, self.return_input(extra_delivery=other))['can_close'])
        self.assertTrue(seal_return(self.root, input_path)['can_close'])
        self.pool_work.write_text('Changed after the evidence was adopted.', encoding='utf-8')
        self.assertFalse(pp.completion(self.root)['can_close'])
        self.assertFalse(seal_return(self.root, input_path)['can_close'])

    def test_original_only_work_does_not_read_the_private_catalog(self):
        self.start(task_only=True)
        pp.dispatch(self.root, actor='fixture-worker', source='actual fixture handoff')
        with self.assertRaisesRegex(ValueError, 'does not select catalog'):
            pp.query_context(self.root)
        self.work_result(task_only=True)
        self.baseline_results()
        self.assertTrue(seal_return(self.root, self.return_input())['can_close'])
        self.assertEqual(close_return(self.root, reason='Synthetic scoped work complete.')['current_receipt'], 'CLOSED')

    def test_real_retarget_gets_a_new_binding_but_nonmaterial_note_keeps_it(self):
        self.start()
        self.work_result()
        self.baseline_results()
        old = pp.route(self.root)['revision']
        observation = self.proposal()
        observation['brief']['basis'] = 'Corrected location of an unchanged original.'
        propose_foundation(self.root, observation, reason='Existing scope unchanged.', change_kind='non_material')
        self.assertEqual(pp.route(self.root)['revision'], old)
        self.assertTrue(pp.completion(self.root)['can_close'])
        observation['brief'][pp.PLAN_FIELD]['baseline']['search'].append('new source')
        with self.assertRaisesRegex(ValueError, 'material revision'):
            propose_foundation(self.root, observation, reason='Would change the baseline.', change_kind='non_material')
        supplement = self.write('new.txt', 'DO: Use the material to prepare a travel expense form instead.')
        ingested = ingest_message(self.root, source=supplement, source_ref='fixture:retarget')
        handle_message(self.root, message_id=ingested['message_id'], action='revise',
                       reason='Academic to ordinary is a real change of product.')
        new = propose_foundation(self.root, self.proposal(academic=False), reason='Actual ordinary replacement.')
        self.assertNotEqual(new['brief']['paper_pool_revision'], old)
        self.assertFalse(pp.completion(self.root)['can_close'])
        adopt_commission(self.root, {
            'revision': new['revision'], 'commission_message_id': ingested['message_id'],
            'commission_source': 'fixture:retarget',
            'commission_sha256': ingested['current_message']['source']['sha256'],
            'commission_scope_quote': 'prepare a travel expense form',
            'explicit_execution_commission': True, 'no_new_user_choice': True,
            'reason': 'Follow the actual revised fixture commission.',
        })
        self.assertIsNone(pp.route(self.root)['target'])
        self.assertTrue(pp.completion(self.root)['can_close'])
        self.assertTrue((self.root / 'paper-pool' / f'u0-{old}' / 'work.json').is_file())

    def test_pool_receipt_binds_response_bytes_and_no_search_is_not_a_failure(self):
        self.start()
        pp.dispatch(self.root, actor='fixture-worker', source='actual fixture handoff')
        with self.assertRaisesRegex(ValueError, 'actual in-task catalog query'):
            pp.result(self.root, artifact=self.pool_work, contribution='Standalone review.',
                      sources=[self.evidence], citations=[], pool_issue='Unobserved claim of failure.')
        query = {'corpus_fingerprint': 'fixture-corpus', 'query': ['scope'],
                 'results': [{'paper_id': 'P0001', 'evidence': {'position': 120}}]}
        receipt = pp.record_query(self.root, context=pp.query_context(self.root),
                                  query=query, response=query)
        query['results'][0]['evidence']['position'] = 999999
        tampered = self.write('tampered.json', json.dumps({**query, 'task_query_receipt': receipt}))
        with self.assertRaisesRegex(ValueError, 'changed or comes from another assignment'):
            pp.result(self.root, artifact=self.pool_work, contribution='Review citing a false position.',
                      sources=[tampered], citations=['P0001'])
        with self.assertRaisesRegex(ValueError, 'actual catalog JSON response'):
            pp.result(self.root, artifact=self.pool_work, contribution='Unverified reference.',
                      sources=[self.evidence], citations=['P0001'])

    def test_original_targets_need_their_actual_attempt_and_evidence(self):
        self.start()
        with self.assertRaisesRegex(ValueError, 'attempt or its exact evidence anchor'):
            pp.baseline_result(self.root, kind='access', target=BASELINE['access'][0], disposition='unavailable',
                               reason='Unverified fixture assertion.', attempt='missed task',
                               evidence_anchor='fixture source', artifact=self.evidence)
        with self.assertRaisesRegex(ValueError, 'original planned target'):
            pp.baseline_result(self.root, kind='access', target='unplanned', disposition='used',
                               reason='Misbound fixture observation.', attempt='attempt:access',
                               evidence_anchor='observed author manuscript', artifact=self.original)

    def test_syntax_and_frozen_old_tasks_are_independent(self):
        self.assertEqual(classify_invocation('DIGR/help', p_run=PIN)['classification'], 'HELP')
        self.assertEqual(classify_invocation('普通问题：科研论文', p_run=PIN)['classification'], 'NATIVE')
        self.assertEqual(classify_invocation('DIGRP：论文', p_run=PIN)['classification'], 'INVALID')
        self.assertEqual(classify_invocation('DIGRP：论文', p_run=OLD)['addon_hint'], 'paper')
        old_root = self.base / 'old'
        self.create(pin=OLD, root=old_root)
        propose_foundation(old_root, {'brief': BRIEF}, reason='Frozen old fixture.')
        self.assertNotIn('paper_pool_completion', seal_return(old_root, self.return_input()))
