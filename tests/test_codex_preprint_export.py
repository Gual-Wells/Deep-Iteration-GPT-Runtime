from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from runtime import codex_preprint as p
from runtime import codex_preprint_export as publication


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


if __name__ == '__main__':
    unittest.main()
