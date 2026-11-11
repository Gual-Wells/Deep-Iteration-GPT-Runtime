"""Source/order/privacy tests for authored lessons, not learning-outcome tests."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from runtime import codex_preprint as core
from runtime import codex_preprint_export as publication
from runtime import codex_preprint_learning as learning
from runtime import codex_preprint_study as study


ROOT = Path(__file__).resolve().parents[1]


class StudyTests(unittest.TestCase):
    def setUp(self):
        cache = ROOT / '.cache'; cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='esp-study-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'book'
        core.initialize(self.root, {'id': 'authored-study-fixture', 'title': 'Source fixture',
            'public_scene': 'Two people discuss an unconfirmed plan.',
            'actors': [{'id': 'a', 'name': 'A', 'outward': {'voice': 'plain'},
                        'inner': {'secret': 'PRIVATE_PROFILE'}},
                       {'id': 'b', 'name': 'B', 'outward': {'voice': 'plain'},
                        'inner': {'secret': 'PRIVATE_OTHER_PROFILE'}}],
            'initial_state': {'hidden': 'PRIVATE_WORLD'}})
        self.serial = 0
        self.first = self.event('speech', 'a', 'We could—no, let me check that first.')
        self.private = self.event('inner', 'a', 'PRIVATE_INNER_THOUGHT')
        self.second = self.event('speech', 'b', 'Does that mean you have already tested it?')
        self.third = self.event('speech', 'a', 'No. I have a timing figure, not that answer.')

    def event(self, kind, actor, text):
        self.serial += 1
        channel = 'inner' if kind == 'inner' else 'outward'
        return core.append_event(self.root, {'kind': kind, 'actor': actor, 'text': text,
            'source_ref': 'PRIVATE_ATTRIBUTION_PATH', 'executor': 'constructed-context',
            'packet_sha256': core.actor_packet(self.root, actor, channel)['packet_sha256']},
            expected_revision=core.load(self.root)['revision'], operation_id='event-' + str(self.serial))['event_id']

    def lesson(self):
        return {'id': 'evidence-lesson', 'title': '一个数字还没回答什么',
                'author': 'Constructed editorial author', 'purpose': '听出可能与已完成的区别',
                'sections': [
                    {'id': 'entry', 'kind': 'explanation', 'purpose': '给出理解入口',
                     'text': '先听原话。这份讲解不要求你回答或扮演人物。',
                     'source_section_ids': ['first-hearing']},
                    {'id': 'first-hearing', 'kind': 'source', 'purpose': '完整原句往返',
                     'event_ids': [self.first, self.second, self.third]},
                    {'id': 'contrast', 'kind': 'contrast', 'purpose': '作者对照示范',
                     'text': '下面是讲解者写的例子：We could try it. We tried it. 两句保留不同的行动状态。'},
                    {'id': 'repeat', 'kind': 'source', 'purpose': '同样原句重新听',
                     'event_ids': [self.first, self.second, self.third]},
                    {'id': 'follow-up', 'kind': 'source', 'purpose': '另取后面一句',
                     'event_ids': [self.third]}]}

    def add(self, lesson=None, **extra):
        payload = {'public_source_sha256': study.source_digest(core.load(self.root)),
                   'lessons': [lesson or self.lesson()], **extra}
        return study.add_lessons(self.root, payload, expected_revision=core.load(self.root)['revision'],
                                 operation_id='lesson-' + str(core.load(self.root)['revision']))

    def test_source_replays_are_exact_and_editorial_text_is_distinct(self):
        before = core.load(self.root)
        original_phone = publication._phone(before, {}, publication._cast(before), publication._public_events(before))
        self.add()
        state = core.load(self.root)
        self.assertEqual(study.status(state)['status'], 'CURRENT_SOURCE')
        self.assertEqual(study.source_digest(before), study.source_digest(state))
        self.assertNotEqual(learning.content_digest(before), learning.content_digest(state))
        text = study.phone_study(state, {'baseline_id': state['spec']['id']}, publication._public_events(state))
        self.assertEqual(text.count('We could—no, let me check that first.'), 2)
        self.assertEqual(text.count('No. I have a timing figure, not that answer.'), 3)
        self.assertLess(text.index('先听原话'), text.index('We could—no'))
        self.assertIn('authored contrast/example', text)
        self.assertIn('END STUDY\n\nSOURCE IDENTITY', text)
        self.assertNotIn('PRIVATE_', text)
        spoken=text.split('BEGIN STUDY',1)[1].split('END STUDY',1)[0]
        self.assertNotIn('Constructed editorial author',spoken)
        self.assertIn('Constructed editorial author',text.split('END STUDY',1)[1])
        # With the same binding, editorial additions never enter the full-scene script.
        self.assertEqual(original_phone,
            publication._phone(state, {}, publication._cast(state), publication._public_events(state)))

    def test_source_segments_cannot_be_rewritten_skipped_or_private(self):
        bad_lessons = []
        for ids in ([self.first, self.third], [self.private], [self.second, self.first], [{}]):
            lesson = self.lesson(); lesson['sections'][1]['event_ids'] = ids
            bad_lessons.append(lesson)
        lesson = self.lesson(); lesson['sections'][1]['text'] = 'An edited native line.'
        bad_lessons.append(lesson)
        lesson = self.lesson(); lesson['sections'][2]['kind'] = 'native'
        bad_lessons.append(lesson)
        lesson = self.lesson(); lesson['sections'][0]['source_section_ids'] = ['not-a-source']
        bad_lessons.append(lesson)
        for lesson in bad_lessons:
            before = (self.root / 'preprint.json').read_bytes()
            with self.subTest(lesson=lesson), self.assertRaises(ValueError):
                self.add(lesson)
            self.assertEqual((self.root / 'preprint.json').read_bytes(), before)

    def test_source_edits_invalidate_lesson_and_projection_injection_is_rejected(self):
        self.add()
        state = core.load(self.root)
        public = publication._public_events(state)
        public[0]['text'] = 'Private injection'
        with self.assertRaisesRegex(ValueError, 'exact current public'):
            study.phone_study(state, {}, public)
        self.event('speech', 'b', 'A later public observation changes the context.')
        state = core.load(self.root)
        self.assertFalse(study.status(state)['source_current'])
        with self.assertRaisesRegex(ValueError, 'missing or stale'):
            study.phone_study(state, {}, publication._public_events(state))

    def test_digest_tracks_public_context_but_not_private_world_or_review_records(self):
        original = core.load(self.root)
        changed = deepcopy(original); changed['world']['hidden'] = 'A new private condition.'
        self.assertEqual(study.source_digest(original), study.source_digest(changed))
        changed['learning_reviews'] = [{'reason': 'A private review record.'}]
        self.assertEqual(study.source_digest(original), study.source_digest(changed))
        changed['spec']['public_scene'] = 'A different public situation.'
        self.assertNotEqual(study.source_digest(original), study.source_digest(changed))
        with self.assertRaisesRegex(ValueError, 'public source changed'):
            study.add_lessons(self.root, {'public_source_sha256': '0' * 64,
                                         'lessons': [self.lesson()]},
                expected_revision=original['revision'], operation_id='wrong-source')

    def test_lessons_need_editorial_content_and_cannot_create_mastery(self):
        for modify in ('empty', 'source-only', 'editor-only', 'mastery'):
            lesson = self.lesson()
            if modify == 'empty':lesson['sections'] = []
            if modify == 'source-only':lesson['sections'] = [lesson['sections'][1]]
            if modify == 'editor-only':lesson['sections'] = [lesson['sections'][2]]
            if modify == 'mastery':lesson['learner_mastery'] = True
            with self.subTest(modify=modify), self.assertRaises(ValueError):
                self.add(lesson)
        self.assertEqual(core.load(self.root)['learner_evidence'], [])


if __name__ == '__main__':
    unittest.main()
