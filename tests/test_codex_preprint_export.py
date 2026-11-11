from hashlib import sha256
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest

from runtime import codex_preprint as p
from runtime import codex_preprint_export as publication
from runtime import codex_preprint_learning as learning
from runtime import codex_preprint_study as study
from runtime import codex_preprint_context as context
from tools import codex_preprint as cli


ROOT = Path(__file__).resolve().parents[1]


class PreprintExportTests(unittest.TestCase):
    def setUp(self):
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='esp-export-test-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.root = self.work / 'source'
        self.out = self.work / 'publication'
        self.serial = 0
        self.secrets = []

        def secret(label):
            value = 'ESP_PRIVATE_CANARY_' + label.upper()
            self.secrets.append(value)
            return value

        self.spec = {
            'id': 'constructed-export-fixture',
            'title': 'Constructed export fixture, not a native scene',
            'public_scene': 'A bookshop closes at seven. Jo and Len are at the counter.',
            'actors': [
                {'id': 'jo', 'name': 'Jo', 'public_role': 'Bookshop worker',
                 'outward': {'voice': 'dry', 'private_plan': secret('jo_outward')},
                 'inner': {'pressure': secret('jo_inner_profile')},
                 'own_background': [secret('jo_background')],
                 'unrecognized_field': secret('actor_extra')},
                {'id': 'len', 'name': 'Len', 'public_role': 'A visitor with a recorder',
                 'outward': {'private_plan': secret('len_outward')},
                 'inner': {'pressure': secret('len_inner_profile')},
                 'own_background': [secret('len_background')]}
            ],
            'directors': [{'id': 'weather', 'interest': secret('director')}],
            'initial_state': {'unseen_fact': secret('world')},
            'sources': [{'title': secret('source_title'), 'url': 'https://invalid.example/' + secret('source_url')}],
            'anchors': [{'id': 'private-anchor', 'label': secret('anchor_label'),
                         'requires': {'private': secret('anchor_requires')},
                         'guide': secret('anchor_guide')},
                        {'id': 'public-projection-is-now-out-of-scope',
                         'public': {'label': secret('unused_anchor_public')}}],
            'unrecognized_spec': secret('rawspec_extra')
        }
        p.initialize(self.root, self.spec)
        self.public = self.event({'kind': 'speech', 'actor': 'len',
                                  'text': 'Could I have six quiet minutes?', 'audience': ['public'],
                                  'unrecognized_field': secret('event_extra')})
        self.event({'kind': 'inner', 'actor': 'jo', 'text': secret('inner_event')})
        self.event({'kind': 'inner_reply', 'actor': 'jo', 'text': secret('inner_reply')})
        self.private_text = secret('private_speech')
        self.private = self.event({'kind': 'speech', 'actor': 'jo', 'text': self.private_text,
                                  'audience': ['jo']})
        self.event({'kind': 'world', 'proposal': secret('proposal'), 'reason': secret('reason'),
                    'decision': 'apply', 'changes': {'hidden': secret('world_change')},
                    'percepts': [{'to': ['public'], 'text': 'The shutters rattle in the wind.'},
                                 {'to': ['jo'], 'text': secret('private_percept')}]})
        self.action = self.event({'kind': 'action', 'actor': 'jo',
                                  'text': 'Jo turns the sign toward the window.', 'audience': ['public']})
        self.event({'kind': 'speech', 'actor': 'jo', 'text': 'I still need to sort these books.',
                    'audience': ['public']})
        self.event({'kind': 'note', 'text': secret('creator_note')})
        self.serial += 1
        p.annotate(self.root, {'resources': [
            {'event_id': self.public['event_id'], 'surface': 'six quiet minutes',
             'meaning': 'a requested length of time with little noise',
             'function': 'request a bounded favour', 'register': 'polite conversation',
             'frequency_status': 'not independently checked', 'private_metadata': secret('language_extra')},
            {'event_id': self.private['event_id'], 'surface': self.private_text,
             'meaning': secret('private_language'), 'function': 'private', 'register': 'private',
             'frequency_status': 'not checked'},
            {'event_id': self.public['event_id'], 'surface': 'six quiet minutes',
             'meaning': secret('restricted_public_annotation'), 'function': 'private research',
             'register': 'private', 'frequency_status': 'not checked', 'audience': ['creator']}
        ]}, expected_revision=p.load(self.root)['revision'], operation_id='annotation-' + str(self.serial))

    def event(self, payload):
        self.serial += 1
        event = {'source_ref': 'ESP_PRIVATE_CANARY_EXECUTION_SOURCE', **payload}
        if 'ESP_PRIVATE_CANARY_EXECUTION_SOURCE' not in self.secrets:
            self.secrets.append('ESP_PRIVATE_CANARY_EXECUTION_SOURCE')
        if payload['kind'] in {'speech', 'action', 'inner', 'inner_reply'}:
            channel = 'inner' if payload['kind'] == 'inner' else 'outward'
            event.update(packet_sha256=p.actor_packet(self.root, payload['actor'], channel)['packet_sha256'],
                         executor='ESP_PRIVATE_CANARY_EXECUTOR')
            if 'ESP_PRIVATE_CANARY_EXECUTOR' not in self.secrets:
                self.secrets.append('ESP_PRIVATE_CANARY_EXECUTOR')
        return p.append_event(self.root, event, expected_revision=p.load(self.root)['revision'],
                              operation_id='event-' + str(self.serial))

    def test_publication_projects_only_public_text_and_keeps_creator_outside_phone(self):
        before = (self.root / 'preprint.json').read_bytes()
        result = publication.export(self.root, self.out)
        self.assertEqual(result['status'], 'CURRENT')
        phone = self.out / 'phone'
        self.assertEqual({f.name for f in phone.iterdir()}, {'LISTEN.md', 'PHONE.txt', 'PUBLIC-REVIEW.md'})
        public_files = ''.join(f.read_text(encoding='utf-8') for f in phone.iterdir())
        creator = (self.out / 'CREATOR.md').read_text(encoding='utf-8')
        for secret in self.secrets:
            with self.subTest(secret=secret):
                self.assertNotIn(secret, public_files)
                self.assertIn(secret, creator)
        self.assertIn('Could I have six quiet minutes?', public_files)
        self.assertIn('The shutters rattle in the wind.', public_files)
        self.assertIn('Jo turns the sign toward the window.', public_files)
        self.assertIn('I still need to sort these books.', public_files)
        self.assertEqual((self.root / 'preprint.json').read_bytes(), before)
        self.assertFalse((phone / 'CREATOR.md').exists())
        instructions = (phone / 'PHONE.txt').read_text(encoding='utf-8')
        self.assertIn('one phone model', instructions)
        self.assertIn('distinct, natural voices', instructions)
        self.assertNotIn('RETURN', instructions)
        self.assertNotIn('take over', instructions)
        self.assertNotIn('replace', instructions)
        self.assertNotIn('CONDITIONAL EVENT ANCHORS', instructions)

    def test_language_review_requires_a_public_submitted_utterance(self):
        publication.export(self.root, self.out)
        review = (self.out / 'phone' / 'PUBLIC-REVIEW.md').read_text(encoding='utf-8')
        self.assertIn('six quiet minutes', review)
        self.assertIn(self.public['event_id'], review)
        self.assertIn('Frequency status: not independently checked', review)
        self.assertNotIn(self.private['event_id'], review)
        self.assertNotIn('ESP_PRIVATE_CANARY', review)
        self.assertNotIn('learner_mastery', review)

    def test_creator_log_is_readable_in_event_order_and_keeps_the_complete_source(self):
        publication.export(self.root, self.out)
        state = p.load(self.root)
        creator = (self.out / 'CREATOR.md').read_text(encoding='utf-8')
        log, appendix = creator.split('## Complete source snapshot\n\n```json\n', 1)
        positions = [log.index('### ' + str(index) + ' · [' + event['id'] + ']')
                     for index, event in enumerate(state['events'], 1)]
        self.assertEqual(positions, sorted(positions))
        for label in ('M outward speech', 'M outward action', 'D fictional private speech',
                      'M → D private reply', 'World council · proposal and decision',
                      '**Proposal**', '**Recorded decision**: apply', '**Reason**', '**Perceived effects**'):
            self.assertIn(label, log)
        for event in state['events']:
            self.assertIn(event['source_ref'], log)
            if event.get('text'):
                self.assertIn(event['text'], log)
        self.assertIn('ESP_PRIVATE_CANARY_PRIVATE_PERCEPT', log)
        self.assertIn('The shutters rattle in the wind.', log)
        self.assertEqual(json.loads(appendix.rsplit('\n```', 1)[0]), state)

    def test_manifest_binds_exact_file_and_source_bytes(self):
        publication.export(self.root, self.out)
        manifest = json.loads((self.out / publication.MANIFEST).read_text(encoding='utf-8'))
        self.assertEqual(set(manifest['files']),
                         {'phone/LISTEN.md', 'phone/PHONE.txt', 'phone/PUBLIC-REVIEW.md', 'CREATOR.md'})
        self.assertEqual(manifest['phone_files'],
                         ['phone/LISTEN.md', 'phone/PHONE.txt', 'phone/PUBLIC-REVIEW.md'])
        self.assertEqual(manifest['source']['baseline_id'], self.spec['id'])
        self.assertEqual(manifest['source']['snapshot_sha256'], p.load(self.root)['integrity_sha256'])
        self.assertEqual(manifest['source']['source_file_sha256'],
                         sha256((self.root / 'preprint.json').read_bytes()).hexdigest())
        for name, digest in manifest['files'].items():
            self.assertEqual(digest, sha256((self.out / name).read_bytes()).hexdigest())
        self.assertEqual(publication.verify_export(self.root, self.out)['status'], 'CURRENT')

    def test_nonempty_output_is_preserved_and_integrity_failure_creates_no_export(self):
        self.out.mkdir()
        sentinel = self.out / 'original.txt'
        sentinel.write_bytes(b'preserve exactly')
        with self.assertRaisesRegex(ValueError, 'refusing overwrite'):
            publication.export(self.root, self.out)
        self.assertEqual(sentinel.read_bytes(), b'preserve exactly')
        self.assertEqual(list(self.out.iterdir()), [sentinel])
        source = self.root / 'preprint.json'
        altered = json.loads(source.read_text(encoding='utf-8'))
        altered['spec']['title'] = 'changed outside recorded operation'
        source.write_text(json.dumps(altered), encoding='utf-8')
        other = self.work / 'never-created'
        with self.assertRaisesRegex(ValueError, 'changed outside a recorded operation'):
            publication.export(self.root, other)
        self.assertFalse(other.exists())

    def test_new_source_revision_and_reformatted_bytes_are_detected_as_stale(self):
        publication.export(self.root, self.out)
        source = self.root / 'preprint.json'
        same_snapshot = json.loads(source.read_text(encoding='utf-8'))
        source.write_text(json.dumps(same_snapshot, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        status = publication.verify_export(self.root, self.out)
        self.assertEqual(status['status'], 'STALE_SOURCE')
        self.assertTrue(status['source_valid'])
        self.assertTrue(status['files_current'])
        self.event({'kind': 'speech', 'actor': 'len', 'text': 'Then I will be brief.', 'audience': ['public']})
        status = publication.verify_export(self.root, self.out)
        self.assertEqual(status['status'], 'STALE_SOURCE')
        self.assertFalse(status['source_current'])

    def test_file_modification_and_creator_copied_into_phone_are_detected(self):
        publication.export(self.root, self.out)
        phone = self.out / 'phone' / 'PHONE.txt'
        phone.write_text(phone.read_text(encoding='utf-8') + '\nchanged\n', encoding='utf-8')
        copied = self.out / 'phone' / 'CREATOR.md'
        copied.write_bytes((self.out / 'CREATOR.md').read_bytes())
        status = publication.verify_export(self.root, self.out)
        self.assertEqual(status['status'], 'MODIFIED_EXPORT')
        self.assertIn('phone/PHONE.txt', status['changed_files'])
        self.assertIn('phone/CREATOR.md', status['unexpected_files'])
        self.assertTrue(status['source_current'])

    def test_invalid_source_and_unsafe_manifest_path_are_not_reported_current(self):
        publication.export(self.root, self.out)
        source = self.root / 'preprint.json'
        altered = json.loads(source.read_text(encoding='utf-8'))
        altered['world']['hidden'] = 'unrecorded change'
        source.write_text(json.dumps(altered), encoding='utf-8')
        status = publication.verify_export(self.root, self.out)
        self.assertEqual(status['status'], 'INVALID_SOURCE')
        self.assertFalse(status['source_valid'])
        manifest_path = self.out / publication.MANIFEST
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['files']['../outside.txt'] = '0' * 64
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'invalid export manifest file path'):
            publication.verify_export(self.root, self.out)

    def test_empty_scene_and_empty_output_need_no_review_or_participation_files(self):
        other_root = self.work / 'empty-source'
        p.initialize(other_root, self.spec)
        self.out.mkdir()
        publication.export(other_root, self.out)
        self.assertEqual({f.name for f in (self.out / 'phone').iterdir()}, {'LISTEN.md', 'PHONE.txt'})
        phone = (self.out / 'phone' / 'PHONE.txt').read_text(encoding='utf-8')
        self.assertIn('No public event has yet been recorded.', phone)
        self.assertEqual(publication.verify_export(other_root, self.out)['status'], 'CURRENT')

    def test_linked_public_turns_preserve_context_without_private_links(self):
        second=self.event({'kind':'speech','actor':'jo','text':'Six, mind.','audience':['public']})
        payload={'resources':[{'event_id':second['event_id'],'surface':'mind','meaning':'A reminder',
            'function':'Keep the earlier limit','register':'spoken','frequency_status':'not checked',
            'related_event_ids':[self.public['event_id'],self.private['event_id']],
            'public_sources':[{'label':'Selected use reference','url':'https://example.invalid/reference'}],
            'source_notes':{'private':'ESP_PRIVATE_CANARY_EXTRA_RESEARCH'}}],
            'listening_threads':[{'id':'limits','label':'Hear the limit being kept','text':'A request meets a reminder.',
                'event_ids':[self.public['event_id'],second['event_id']]}]}
        before=(self.root/'preprint.json').read_bytes()
        bad=json.loads(json.dumps(payload));bad['listening_threads'][0]['event_ids'].append(self.private['event_id'])
        with self.assertRaisesRegex(ValueError,'non-public'):
            p.annotate(self.root,bad,expected_revision=p.load(self.root)['revision'],operation_id='private-thread')
        self.assertEqual((self.root/'preprint.json').read_bytes(),before)
        p.annotate(self.root,payload,expected_revision=p.load(self.root)['revision'],operation_id='public-thread')
        publication.export(self.root,self.out)
        review=(self.out/'phone/PUBLIC-REVIEW.md').read_text(encoding='utf-8')
        self.assertIn('Hear the limit being kept',review)
        self.assertIn('Could I have six quiet minutes?',review)
        self.assertIn('[Selected use reference](https://example.invalid/reference)',review)
        self.assertNotIn(self.private['event_id'],review)
        self.assertNotIn('ESP_PRIVATE_CANARY',review)
        self.assertEqual(p.load(self.root)['learner_evidence'],[])

    def _learning_contract(self):
        def change(state):
            state['spec']['learning_contract'] = {'schema_version': 1,
                'target_domain': 'international-daily', 'why_relevant': 'A favour has a real limit.',
                'difficulty_focus': 'A request must coexist with unfinished work.',
                'intended_uses': ['Understand a limited agreement.']}
            state['spec_sha256'] = p.digest(state['spec'])
            return {'constructed_contract': True}
        p._mutate(self.root, {'constructed_contract': True}, p.load(self.root)['revision'],
                  'contract-fixture', change)

    def _case_payload(self):
        events = publication._public_events(p.load(self.root))
        return {'cases': [{'id': 'limited-favour', 'cue': '请求安静时间但对方还有工作',
            'intent': '理解请求与回应之间的边界', 'why_hard': '各有眼前要做的事情',
            'what_changed': '对方说仍需整理书，没有许诺所有事情已完成',
            'event_ids': [event['id'] for event in events],
            'usage': [{'event_id': self.public['event_id'], 'surface': 'six quiet minutes',
                'meaning': '一段有限的安静时间', 'function': '请求有界帮助',
                'conditions': '对方是否可以答应仍要看回应', 'register': '礼貌口语',
                'frequency_status': 'not checked'}]}]}

    def _add_case(self):
        learning.add_cases(self.root, self._case_payload(), expected_revision=p.load(self.root)['revision'],
                           operation_id='case-fixture')

    def _lesson_payload(self):
        return {'public_source_sha256': study.source_digest(p.load(self.root)),
            'lessons': [{'id': 'favour-study', 'title': '听见请求的范围', 'author': 'Constructed editor',
                'purpose': '让原来往返中的词义可以听懂', 'sections': [
                    {'id': 'source', 'kind': 'source', 'purpose': '保留原话与回应',
                     'event_ids': [event['id'] for event in publication._public_events(p.load(self.root))]},
                    {'id': 'explanation', 'kind': 'explanation', 'purpose': '作者讲解',
                     'text': '这段讲解由编辑编写。six quiet minutes 是有边界的请求。',
                     'source_section_ids': ['source']}]}]}

    def _review_payload(self, decision='useful'):
        state = p.load(self.root)
        return {'content_sha256': learning.content_digest(state), 'decision': decision,
            'reviewer': 'Constructed substantive reviewer',
            'reason': 'The complete exchange and authored explanation retain the visible limit.',
            'case_findings': [{'case_id': case['id'], 'judgment': decision,
                'reason': 'The source fragment contains the actual request and response.'}
                for case in state['learning_cases']]}

    def _approve(self, decision='useful'):
        learning.review(self.root, self._review_payload(decision),
            expected_revision=p.load(self.root)['revision'],
            operation_id='review-fixture-' + str(p.load(self.root)['revision']))

    def test_learning_contract_publication_requires_current_useful_judgement(self):
        self._learning_contract(); self._add_case()
        for decision in (None, 'reject', 'revise'):
            if decision:self._approve(decision)
            with self.subTest(decision=decision), self.assertRaisesRegex(ValueError, 'current recorded useful'):
                publication.export(self.root, self.out)
            self.assertFalse(self.out.exists())
        self._approve()
        study.add_lessons(self.root, self._lesson_payload(), expected_revision=p.load(self.root)['revision'],
                          operation_id='lesson-fixture')
        with self.assertRaisesRegex(ValueError, 'current recorded useful'):
            publication.export(self.root, self.out)
        self._approve()
        self.assertEqual(publication.export(self.root, self.out)['status'], 'CURRENT')
        self.assertFalse(json.loads((self.out / publication.MANIFEST).read_text(encoding='utf-8'))
                         ['learning_review']['semantic_certification'])
        manifest = p.read(self.out / publication.MANIFEST)
        manifest['learning_review']['semantic_certification'] = True
        (self.out / publication.MANIFEST).write_text(json.dumps(manifest), encoding='utf-8')
        self.assertEqual(publication.verify_export(self.root, self.out)['status'], 'REVIEW_REQUIRED')

    def test_study_inventory_and_complete_scene_stay_separate(self):
        self._learning_contract(); self._add_case()
        state = p.load(self.root)
        original = publication._phone(state, {}, publication._cast(state), publication._public_events(state))
        study.add_lessons(self.root, self._lesson_payload(), expected_revision=state['revision'],
                          operation_id='lesson-fixture')
        self._approve()
        state = p.load(self.root)
        self.assertEqual(original, publication._phone(state, {}, publication._cast(state), publication._public_events(state)))
        result = publication.export(self.root, self.out)
        self.assertEqual(result['status'], 'CURRENT')
        scene = (self.out / 'phone/PHONE.txt').read_text(encoding='utf-8')
        lesson = (self.out / 'study/PHONE-STUDY.txt').read_text(encoding='utf-8')
        review = (self.out / 'phone/PUBLIC-REVIEW.md').read_text(encoding='utf-8')
        self.assertNotIn('这段讲解由编辑编写', scene)
        self.assertIn('这段讲解由编辑编写', lesson)
        self.assertIn('请求安静时间', review)
        self.assertIn('Preserve hesitation', scene)
        for secret in self.secrets:self.assertNotIn(secret, lesson + review)
        manifest = p.read(self.out / publication.MANIFEST)
        self.assertEqual(manifest['study_files'], ['study/PHONE-STUDY.txt'])
        (self.out / 'study/CREATOR.md').write_text('Unexpected creator material', encoding='utf-8')
        report = publication.verify_export(self.root, self.out)
        self.assertEqual(report['status'], 'MODIFIED_EXPORT')
        self.assertIn('study/CREATOR.md', report['unexpected_files'])
        (self.out / 'study/CREATOR.md').unlink()
        (self.out / 'study/PHONE-STUDY.txt').unlink()
        (self.out / 'study').rmdir()
        manifest['files'].pop('study/PHONE-STUDY.txt')
        manifest['study_files'] = []
        (self.out / publication.MANIFEST).write_text(json.dumps(manifest), encoding='utf-8')
        report = publication.verify_export(self.root, self.out)
        self.assertEqual(report['status'], 'MODIFIED_EXPORT')
        self.assertIn('study/PHONE-STUDY.txt', report['changed_files'])

    def test_capsule_always_requires_private_distribution_even_for_public_sharing(self):
        root = self.work / 'capsule-source'
        p.initialize(root, self.spec)
        view = {'audience': 'actor', 'book_id': self.spec['id'], 'role_id': 'len',
                'entries': [{'id': 'constructed-public-entry', 'sharing': 'public',
                             'text': 'ESP_PRIVATE_CAPSULE_CANARY'}],
                'unavailable': [], 'requires_private_publication': False}
        packet = {'view': view, 'view_sha256': p.digest(view)}
        context.bind_personal(root, 'len', packet, expected_revision=0, operation_id='bind-fixture')
        with self.assertRaisesRegex(ValueError, 'requires private distribution'):
            publication.export(root, self.out, distribution='public')
        self.assertFalse(self.out.exists())
        report = publication.export(root, self.out)
        self.assertEqual(report['distribution'], 'private')
        self.assertNotIn('ESP_PRIVATE_CAPSULE_CANARY', (self.out / 'phone/PHONE.txt').read_text(encoding='utf-8'))
        manifest = p.read(self.out / publication.MANIFEST)
        manifest['distribution'] = 'public'
        (self.out / publication.MANIFEST).write_text(json.dumps(manifest), encoding='utf-8')
        self.assertEqual(publication.verify_export(root, self.out)['status'], 'DISTRIBUTION_MISMATCH')

    def test_old_schema_one_manifests_remain_verifiable(self):
        publication.export(self.root, self.out)
        manifest = p.read(self.out / publication.MANIFEST)
        for key in ('study_files', 'distribution', 'private_distribution_required', 'learning_review'):
            manifest.pop(key)
        (self.out / publication.MANIFEST).write_text(json.dumps(manifest), encoding='utf-8')
        self.assertEqual(publication.verify_export(self.root, self.out)['status'], 'CURRENT')

    def test_public_perturbation_projection_keeps_only_explicit_public_percepts(self):
        state = p.load(self.root)
        state['events'].append({'id': 'constructed-perturbation-public-projection',
            'kind': 'perturbation', 'audience': ['creator'],
            'definition': {'hidden': 'PRIVATE_PERTURBATION_DEF'},
            'percepts': [{'to': ['public'], 'text': 'The shared screen goes dark.'},
                         {'to': ['jo'], 'text': 'PRIVATE_PERTURBATION_PERCEPT'}]})
        event = publication._public_events(state)[-1]
        self.assertEqual(event['kind'], 'observation')
        self.assertEqual(event['text'], 'The shared screen goes dark.')
        self.assertNotIn('PRIVATE_', json.dumps(event))

    def test_actual_cli_cases_lesson_review_find_publish_and_bind_context(self):
        def invoke(args):
            output, errors = io.StringIO(), io.StringIO()
            with redirect_stdout(output), redirect_stderr(errors):code = cli.main(args)
            self.assertEqual(code, 0, errors.getvalue())
            return json.loads(output.getvalue())

        def input_file(name, value):
            path = self.work / (name + '.json')
            path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
            return str(path)

        def mutate(command, name, payload):
            return invoke([command, '--root', str(self.root), '--input', input_file(name, payload),
                '--expected-revision', str(p.load(self.root)['revision']), '--operation-id', name])

        self._learning_contract()
        mutate('cases', 'cli-cases', self._case_payload())
        self.assertEqual(invoke(['learning-status', '--root', str(self.root)])['status'], 'UNREVIEWED')
        self.assertEqual(invoke(['find', '--root', str(self.root), '--query', '安静'])['results'][0]
                         ['case']['id'], 'limited-favour')
        source_status = invoke(['study-status', '--root', str(self.root)])
        self.assertEqual(source_status['public_source_sha256'], study.source_digest(p.load(self.root)))
        mutate('lesson', 'cli-lesson', self._lesson_payload())
        mutate('review', 'cli-review', self._review_payload())
        self.assertEqual(invoke(['publish', '--root', str(self.root), '--out', str(self.out),
                                 '--distribution', 'public'])['status'], 'CURRENT')
        root = self.work / 'cli-personal-book'; p.initialize(root, self.spec)
        view = {'audience': 'actor', 'book_id': self.spec['id'], 'role_id': 'len',
                'entries': [], 'unavailable': []}
        packet = {'view': view, 'view_sha256': p.digest(view)}
        receipt = invoke(['bind-context', '--root', str(root), '--actor', 'len',
            '--input', input_file('capsule', packet), '--expected-revision', '0', '--operation-id', 'cli-bind'])
        self.assertEqual(receipt['actor'], 'len')
        self.assertEqual(p.load(root)['spec']['actors'][1]['personal_context'], packet)


if __name__ == '__main__':
    unittest.main()
