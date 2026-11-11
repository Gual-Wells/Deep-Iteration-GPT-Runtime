"""Constructed fixtures test source/privacy/version behaviour, not learning gains."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from runtime import codex_preprint as core
from runtime import codex_preprint_export as publisher
from runtime import codex_preprint_learning as learning


ROOT = Path(__file__).resolve().parents[1]


def spec(book_id='learning-fixture', contract=True):
    result = {'id': book_id, 'title': 'Constructed source fixture',
              'public_scene': 'Two engineers inspect a measurement record.',
              'actors': [{'id': 'a', 'name': 'A', 'outward': {'voice': 'plain'},
                          'inner': {'canary': 'PRIVATE_INNER_A'},
                          'own_background': ['PRIVATE_BACKGROUND_A']},
                         {'id': 'b', 'name': 'B', 'outward': {'voice': 'plain'},
                          'inner': {'canary': 'PRIVATE_INNER_B'}}],
              'directors': [{'id': 'world', 'interest': 'ordinary conditions'}],
              'initial_state': {'canary': 'PRIVATE_WORLD'}}
    if contract:
        result['learning_contract'] = {'schema_version': 1,
            'target_domain': 'edge-ai-inference-interview',
            'why_relevant': 'A bounded inference measurement must be explained.',
            'difficulty_focus': 'A number does not answer the next decision.',
            'intended_uses': ['Explain the scope of evidence.']}
    return result


class LearningTests(unittest.TestCase):
    def setUp(self):
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='esp-learning-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'book'
        core.initialize(self.root, spec())
        self.op = 0
        self.first = self.event('speech', 'a', 'I have a timing figure, not a reliability result.')
        self.event('inner', 'a', 'PRIVATE_THOUGHT_CANARY')
        self.world = self.event('world', public='The log is on the table.')
        self.second = self.event('speech', 'b', 'Can we ship on that?')
        self.third = self.event('speech', 'a', 'We could try it, but I cannot promise a result.')

    def event(self, kind, actor=None, text=None, public=None, root=None):
        root = root or self.root
        self.op += 1
        event = {'kind': kind, 'source_ref': 'constructed-native-source'}
        if kind == 'world':
            event.update(proposal='A log arrives.', decision='apply', reason='Constructed event',
                         changes={'unseen': 'PRIVATE_WORLD_CHANGE'},
                         percepts=[{'to': ['public'], 'text': public},
                                   {'to': ['a'], 'text': 'PRIVATE_PERCEPT_CANARY'}])
        else:
            event.update(actor=actor, text=text, executor='constructed-independent-context',
                         packet_sha256=core.actor_packet(root, actor,
                             'inner' if kind == 'inner' else 'outward')['packet_sha256'])
        return core.append_event(root, event, expected_revision=core.load(root)['revision'],
                                 operation_id='event-' + str(self.op))['event_id']

    def case(self, case_id='evidence'):
        return {'id': case_id, 'cue': '有计时数字，但对方问能不能发货',
                'intent': '说明证据能支持的行动', 'why_hard': '对方换了要回答的问题',
                'what_changed': '对方仍请求一个更大决定，公开记录没有新增可靠性测试',
                'event_ids': [self.first, self.world, self.second, self.third],
                'usage': [{'event_id': self.first, 'surface': 'a timing figure',
                           'meaning': '计时得到的数字', 'function': '限定已有信息',
                           'conditions': '只说明已经记录的东西', 'register': '技术讨论',
                           'frequency_status': 'not checked',
                           'variants': [{'text': 'a latency measurement',
                                         'explanation': '作者候选变式，不是本场台词'}]}]}

    def add(self, case=None, root=None, operation_id='case-1', **extra):
        root = root or self.root
        return learning.add_cases(root, {'cases': [case or self.case()], **extra},
            expected_revision=core.load(root)['revision'], operation_id=operation_id)

    def review_payload(self, decision='useful'):
        state = core.load(self.root)
        return {'decision': decision, 'reviewer': 'attributed human semantic review',
                'reason': 'The actual exchange preserves the limited evidence and unresolved decision.',
                'content_sha256': learning.content_digest(state),
                'case_findings': [{'case_id': c['id'], 'judgment': decision,
                                   'reason': 'The complete source exchange supports this interpretation.'}
                                  for c in state.get('learning_cases', [])]}

    def judge(self, decision='useful', operation_id='review-1'):
        return learning.review(self.root, self.review_payload(decision),
            expected_revision=core.load(self.root)['revision'], operation_id=operation_id)

    def test_contract_is_optional_and_does_not_change_legacy_read(self):
        learning.validate_spec(spec(contract=False))
        root = Path(self.temp.name) / 'old'
        core.initialize(root, spec('old', contract=False))
        before = (root / 'preprint.json').read_bytes()
        self.assertEqual(learning.status(core.load(root))['status'], 'NOT_REQUIRED')
        self.assertEqual((root / 'preprint.json').read_bytes(), before)
        for bad in (None, {}, {'schema_version': True},
                    {**spec()['learning_contract'], 'intended_uses': []}):
            value = spec(); value['learning_contract'] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                learning.validate_spec(value)
        other = spec(); other['learning_contract']['target_domain'] = 'a relevant new field'
        learning.validate_spec(other)

    def test_fragments_keep_public_observations_but_never_backstage(self):
        self.add()
        state = core.load(self.root)
        case = state['learning_cases'][0]
        self.assertEqual([e['id'] for e in case['public_fragment']], self.case()['event_ids'])
        text = learning.review_markdown(state, publisher._public_events(state))
        self.assertIn('The log is on the table.', text)
        self.assertIn('Can we ship on that?', text)
        self.assertIn('有计时数字', text)
        self.assertIn('非角色原句', text)
        self.assertNotIn('PRIVATE_', text)
        self.assertNotIn('constructed-native-source', text)
        self.assertEqual(state['learner_evidence'], [])

    def test_case_rejects_nonpublic_skips_reordering_and_single_turn_cards(self):
        private = next(e['id'] for e in core.load(self.root)['events'] if e['kind'] == 'inner')
        for ids in ([self.first, private, self.second], [self.first, self.second],
                    [self.second, self.first], [self.first], [self.first, self.first], [{}]):
            case = self.case(); case['event_ids'] = ids
            before = (self.root / 'preprint.json').read_bytes()
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.add(case)
            self.assertEqual((self.root / 'preprint.json').read_bytes(), before)

    def test_usage_must_be_in_the_selected_public_speech(self):
        for change in ({'event_id': self.world}, {'surface': 'never spoken'}, {'start': True},
                       {'surface': 'PRIVATE_THOUGHT_CANARY'}, {'learner_mastery': True}):
            case = self.case(); case['usage'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.add(case)
        case = self.case(); case['creator_note'] = 'PRIVATE_EXTRA'
        with self.assertRaises(ValueError):
            self.add(case)

    def test_review_is_content_bound_and_does_not_stale_itself(self):
        self.add()
        before = learning.status(core.load(self.root))
        self.assertEqual(before['status'], 'UNREVIEWED')
        self.judge()
        state = core.load(self.root)
        after = learning.status(state)
        self.assertEqual(after['content_sha256'], before['content_sha256'])
        self.assertTrue(after['review_current'])
        self.assertEqual(after['decision'], 'useful')
        self.assertFalse(after['needs_review'])
        self.assertFalse(after['semantic_certification'])
        changed = deepcopy(state)
        changed['spec']['actors'][0]['conditions'] = {'stress': 'new actual condition'}
        self.assertEqual(learning.status(changed)['status'], 'STALE_REVIEW')
        changed = deepcopy(state); changed['perturbations'] = [{'status': 'active'}]
        self.assertTrue(learning.status(changed)['needs_review'])
        stale = self.review_payload()
        self.event('speech', 'b', 'The next result changes the question.')
        with self.assertRaisesRegex(ValueError, 'content changed'):
            learning.review(self.root, stale, expected_revision=core.load(self.root)['revision'],
                            operation_id='stale-review')

    def test_reviews_need_actual_reasons_and_every_case_and_respect_rejection(self):
        self.add()
        for changes in ({'reason': ''}, {'reviewer': ''}, {'case_findings': []},
                        {'case_findings': [{'case_id': 'evidence', 'judgment': 'useful', 'reason': ''}]},
                        {'case_findings': [{'case_id': 'evidence', 'judgment': 'reject', 'reason': 'Wrong sense.'}]}):
            payload = self.review_payload(); payload.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                learning.review(self.root, payload, expected_revision=core.load(self.root)['revision'],
                                operation_id='bad-review')
        self.judge('reject')
        result = learning.status(core.load(self.root))
        self.assertTrue(result['review_current'])
        self.assertEqual(result['decision'], 'reject')
        self.assertTrue(result['needs_revision'])

    def test_mutation_retries_conflicts_and_explicit_replacement(self):
        revision = core.load(self.root)['revision']
        payload = {'cases': [self.case()]}
        first = learning.add_cases(self.root, payload, expected_revision=revision, operation_id='retry')
        second = learning.add_cases(self.root, payload, expected_revision=revision, operation_id='retry')
        self.assertTrue(second['retried'])
        self.assertEqual(first['content_sha256'], second['content_sha256'])
        with self.assertRaisesRegex(ValueError, 'revision conflict'):
            learning.add_cases(self.root, {'cases': [self.case('other')]},
                expected_revision=revision, operation_id='conflict')
        with self.assertRaisesRegex(ValueError, 'id exists'):
            self.add(operation_id='duplicate')
        self.judge()
        case = self.case(); case['what_changed'] = 'Revised account of the still-open decision.'
        self.add(case, operation_id='replacement', replace=True)
        self.assertTrue(learning.status(core.load(self.root))['needs_review'])

    def test_projection_tampering_and_changed_source_cannot_render(self):
        self.add()
        state = core.load(self.root)
        public = publisher._public_events(state)
        public[0]['text'] += ' PRIVATE_INJECTION'
        with self.assertRaisesRegex(ValueError, 'exact current public'):
            learning.review_markdown(state, public)
        changed = deepcopy(state)
        changed['events'][0]['text'] = 'An edited utterance.'
        self.assertFalse(learning.status(changed)['bindings_current'])
        with self.assertRaises(ValueError):
            learning.review_markdown(changed, publisher._public_events(changed))

    def test_find_and_relations_preserve_semantic_kinds_and_target_identity(self):
        self.add()
        other_root = Path(self.temp.name) / 'other'
        core.initialize(other_root, spec('another-book'))
        first = self.event('speech', 'a', 'We have a timing figure for this device.', root=other_root)
        second = self.event('speech', 'b', 'That leaves the application delay open.', root=other_root)
        other = self.case('other-case')
        other['cue'] = '另一个设备的计时与整机延迟'
        other['event_ids'] = [first, second]
        other['usage'][0]['event_id'] = first
        self.add(other, root=other_root)
        relation = {'id': 'r1', 'kind': 'exact-use', 'source_case_id': 'evidence',
                    'target_root': str(other_root), 'target_case_id': 'other-case',
                    'source_surface': 'a timing figure', 'target_surface': 'a timing figure',
                    'explanation': 'Both actual spans name a timing measurement.',
                    'differences': 'The second case concerns a different device and question.'}
        learning.add_cases(self.root, {'series_relations': [relation]},
            expected_revision=core.load(self.root)['revision'], operation_id='relation')
        result = learning.find([self.root, other_root], '发货')
        self.assertEqual(len(result['results']), 1)
        found = result['results'][0]
        self.assertEqual(found['case']['public_fragment'][0]['id'], self.first)
        self.assertEqual(found['series_relations'][0]['target_binding'], 'CURRENT_CASE')

        self.assertNotIn('target_root', found['series_relations'][0])
        self.assertNotIn('PRIVATE_', json.dumps(found['case']))
        self.assertEqual(learning.find(self.root, 'timing')['results'][0]['series_relations'][0]
                         ['target_binding'], 'NOT_INCLUDED')
        self.assertEqual(learning.find(self.root, '不存在的处境')['results'], [])
        changed = deepcopy(other); changed['intent'] = 'An explicitly revised target intent.'
        self.add(changed, root=other_root, operation_id='other-revision', replace=True)
        self.assertEqual(learning.find([self.root, other_root], '发货')['results'][0]
                         ['series_relations'][0]['target_binding'], 'CHANGED_CASE')
        self.assertFalse(learning.status(core.load(self.root))['linked_sources_current'])
        with self.assertRaises(ValueError):
            learning.review_markdown(core.load(self.root), publisher._public_events(core.load(self.root)))
        learning.add_cases(self.root, {'series_relations': [relation], 'replace': True},
            expected_revision=core.load(self.root)['revision'], operation_id='refresh-target')
        relation.update(id='r2', kind='handling-function')
        relation.pop('source_surface'); relation.pop('target_surface')
        learning.add_cases(self.root, {'series_relations': [relation]},
            expected_revision=core.load(self.root)['revision'], operation_id='handling-relation')
        state = core.load(self.root)
        text = learning.review_markdown(state, publisher._public_events(state))
        self.assertIn('不计作词块复现', text)
        self.assertNotIn(str(other_root), text)

    def test_use_relations_require_real_spans_and_replaced_sources_need_reanchoring(self):
        self.add()
        relation = {'id': 'local-relation', 'kind': 'handling-function', 'source_case_id': 'evidence',
                    'target_root': str(self.root), 'target_case_id': 'evidence',
                    'source_surface': 'a timing figure', 'target_surface': 'a timing figure',
                    'explanation': 'A constructed identity relation, not a learning result.',
                    'differences': 'Same source fixture; no second encounter is claimed.'}
        for change in ({'target_surface': 'an invented phrase'}, {'target_case_id': 'absent'},
                       {'kind': 'exact-use'}):
            payload = {'series_relations': [{**relation, **change}]}
            with self.subTest(change=change), self.assertRaises(ValueError):
                learning.add_cases(self.root, payload, expected_revision=core.load(self.root)['revision'],
                                   operation_id='invalid-relation')
        learning.add_cases(self.root, {'series_relations': [relation]},
            expected_revision=core.load(self.root)['revision'], operation_id='local-relation')
        changed = self.case(); changed['intent'] = 'A revised handling interpretation.'
        self.add(changed, replace=True, operation_id='changed-case')
        self.assertFalse(learning.status(core.load(self.root))['bindings_current'])
        with self.assertRaisesRegex(ValueError, 'relation source changed'):
            self.judge()
        learning.add_cases(self.root, {'series_relations': [relation], 'replace': True},
            expected_revision=core.load(self.root)['revision'], operation_id='reanchor-relation')
        self.judge()
        self.assertTrue(learning.status(core.load(self.root))['review_current'])


    def test_relative_relation_survives_copy_and_uses_the_copied_series(self):
        self.add()
        other_root=Path(self.temp.name)/'other'
        core.initialize(other_root,spec('portable-other'))
        a=self.event('speech','a','We have a timing figure for this device.',root=other_root)
        b=self.event('speech','b','That is one measurement.',root=other_root)
        other=self.case('other-case');other['event_ids']=[a,b];other['usage'][0]['event_id']=a
        self.add(other,root=other_root)
        learning.add_cases(self.root,{'series_relations':[{'id':'portable','kind':'handling-function',
            'source_case_id':'evidence','target_root':'../other','target_case_id':'other-case',
            'explanation':'Both limit the measurement claim.','differences':'Different decisions remain.'}]},
            expected_revision=core.load(self.root)['revision'],operation_id='relative-link')
        self.judge()
        moved=Path(self.temp.name)/'portable-series';moved.mkdir()
        shutil.copytree(self.root,moved/'book');shutil.copytree(other_root,moved/'other')
        self.assertTrue(learning.status(core.load(moved/'book'),root=moved/'book')['review_current'])
        other['cue']='Changed original, not the copy.'
        self.add(other,root=other_root,replace=True,operation_id='change-original-target')
        self.assertFalse(learning.status(core.load(self.root),root=self.root)['bindings_current'])
        self.assertTrue(learning.status(core.load(moved/'book'),root=moved/'book')['bindings_current'])
        result=learning.find([moved/'book',moved/'other'],'发货')
        self.assertEqual(result['results'][0]['series_relations'][0]['target_binding'],'CURRENT_CASE')
        out=moved/'edition';self.assertEqual(publisher.export(moved/'book',out)['status'],'CURRENT')
        self.assertNotIn(str(other_root),(out/'phone/PUBLIC-REVIEW.md').read_text(encoding='utf-8'))


    def test_new_learning_write_promotes_legacy_without_rewriting_native_events(self):
        state=core.load(self.root);state['schema_version']=1
        core._write(self.root/'preprint.json',core._sealed(state))
        original_events=deepcopy(state['events'])
        result=self.add()
        self.assertEqual(result['schema_migration'],{'from':1,'to':2})
        self.assertEqual(core.load(self.root)['events'],original_events)
        self.assertEqual(core.load(self.root)['schema_version'],2)


if __name__ == '__main__':
    unittest.main()
