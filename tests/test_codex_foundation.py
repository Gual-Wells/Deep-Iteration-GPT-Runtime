"""Behavioral fixtures; simulated user replies are not real user consent."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from runtime.codex_foundation import (
    BRIEF_FIELDS, answer_foundation, confirm_foundation, foundation_packet,
    propose_foundation, require_foundation_ready, revoke_foundation,
)
from runtime.codex_session import (
    activity, create_line, create_session, line_packet, session_report, summarize_activity,
)

PARAMETERS = {'N': 5, 'T': '20min', 'R': 3, 'B': 0,
              'S': {'n': 3, 't': '10min', 'r': 2, 'b': 0}, 'D': 3, 'V': 3, 'L': 3}


def proposal():
    brief = {key: 'Explicit fixture explanation: ' + title for key, title in BRIEF_FIELDS.items()}
    brief['results'] = 'One usable handoff document, with existing original references.'
    brief['granularity'] = 'Whole handoff journey; do not atomize all source terminology.'
    return {'brief': brief, 'questions': [{'id': 'Q1', 'question': 'Reference or rewrite existing sources?',
            'why': 'Changes the production work and content identity.', 'options': ['Reference', 'Rewrite']}]}


class FoundationBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.request = self.base / 'original.txt'
        self.original = b'\xef\xbb\xbfDIGR: make a usable handoff\r\n'
        self.request.write_bytes(self.original)
        self.root = self.base / 'session'
        create_session(self.root, request=self.request, p_run='0.7.0@' + 'a' * 40)
        create_line(self.root, 'M01', parameters=PARAMETERS)

    def test_partial_answer_correction_confirmation_and_changed_scope(self):
        first = proposal()
        first['brief']['results'] = 'Incorrect intermediate deliverable: all terminology atoms.'
        propose_foundation(self.root, first, reason='Initial researched interpretation, deliberately wrong fixture.')
        activity(self.root, 'COMMON', 'begin', state='SOURCE', scope='FOUNDATION')
        activity(self.root, 'COMMON', 'end', continued=True)
        answer_foundation(self.root, 'Q1', revision=1, user_text='SIMULATED: reference originals; I need a usable handoff.',
                          source='fixture-reply-1', effect='Cancel terminology atomization; rewrite current outcome.')
        with self.assertRaises(ValueError):
            activity(self.root, 'M01', 'begin', state='MAIN')
        second = propose_foundation(self.root, proposal(), reason='User correction changes the complete outcome.')
        self.assertIn('usable handoff', foundation_packet(self.root))
        self.assertNotIn('Incorrect intermediate deliverable', foundation_packet(self.root))
        with self.assertRaises(ValueError):
            confirm_foundation(self.root, revision=1, user_text='SIMULATED: start', source='fixture-stale')
        confirm_foundation(self.root, revision=second['revision'], user_text='SIMULATED: this complete scope; proceed.',
                           source='fixture-reply-2')
        activity(self.root, 'M01', 'begin', state='MAIN')
        self.assertIn('CONFIRMED', line_packet(self.root, 'M01'))
        amended = deepcopy(proposal())
        amended['brief']['basis'] += ' A source path spelling was corrected, without changing use.'
        propose_foundation(self.root, amended, reason='Path fact only; outcome, method and costs unchanged.', change_kind='non_material')
        self.assertEqual(require_foundation_ready(self.root)['confirmation']['user_confirmed_revision'], 2)
        activity(self.root, 'M01', 'checkpoint', continued=True)
        amended['brief']['results'] = 'New unapproved database before any handoff.'
        propose_foundation(self.root, amended, reason='New intermediate production changes scope.')
        with self.assertRaises(ValueError):
            activity(self.root, 'M01', 'checkpoint', continued=True)
        activity(self.root, 'M01', 'end', continued=True)
        for state in ('MAIN', 'SOURCE', 'D_EXCLUSIVE', 'V_EXCLUSIVE'):
            with self.subTest(state=state), self.assertRaises(ValueError):
                activity(self.root, 'M01', 'begin', state=state)
        self.assertEqual((self.root / 'REQUEST.txt').read_bytes(), self.original)

    def test_new_question_cannot_inherit_confirmation_or_old_answer(self):
        current = proposal()
        propose_foundation(self.root, current, reason='Initial fixture')
        with self.assertRaises(ValueError):
            confirm_foundation(self.root, revision=1, user_text='SIMULATED: start', source='fixture')
        answer_foundation(self.root, 'Q1', revision=1, user_text='SIMULATED: Reference', source='fixture', effect='Use original references.', change_kind='non_material')
        confirm_foundation(self.root, revision=1, user_text='SIMULATED: start this scope', source='fixture')
        current['questions'][0]['options'] = ['Paid rebuild', 'Free export']
        with self.assertRaises(ValueError):
            propose_foundation(self.root, current, reason='Changed decision is not editorial.', change_kind='non_material')
        result = propose_foundation(self.root, current, reason='New resource decision.')
        self.assertNotIn('answer', result['questions'][0])
        with self.assertRaises(ValueError):
            require_foundation_ready(self.root)

    def test_read_only_to_public_deployment_cannot_be_editorial(self):
        current = proposal(); current['questions'] = []
        current['brief']['results'] = 'Local read-only explanation.'
        propose_foundation(self.root, current, reason='Read-only fixture')
        confirm_foundation(self.root, revision=1, user_text='SIMULATED: explain only.', source='fixture')
        current['brief']['results'] = 'Create a production service and publish it.'
        with self.assertRaisesRegex(ValueError, 'decision fields changed'):
            propose_foundation(self.root, current, reason='Claimed editorial change', change_kind='non_material')
        self.assertIn('Local read-only', foundation_packet(self.root))

    def test_revocation_stops_next_operation_but_allows_clock_cleanup(self):
        current = proposal(); current['questions'] = []
        propose_foundation(self.root, current, reason='Initial fixture')
        confirm_foundation(self.root, revision=1, user_text='SIMULATED: start.', source='fixture')
        activity(self.root, 'M01', 'begin', state='MAIN')
        result = revoke_foundation(self.root, user_text='SIMULATED: I only pointed out an earlier error.',
            source='fixture-current-user-message', reason='The activation was mistaken.')
        self.assertEqual(result['status'], 'REVOKED')
        self.assertIsNone(result['confirmation'])
        self.assertIsNotNone(result['accepted'])
        with self.assertRaisesRegex(ValueError, 'revoked'):
            activity(self.root, 'M01', 'checkpoint', continued=True)
        activity(self.root, 'M01', 'end', continued=True)
        with self.assertRaises(ValueError):
            confirm_foundation(self.root, revision=1, user_text='SIMULATED: reuse old start.', source='fixture-old')
        current['unaffected_lines'] = {'M01': 'Pretend the scope is unchanged.'}
        with self.assertRaisesRegex(ValueError, 'revoked'):
            propose_foundation(self.root, current, reason='Attempt to revive stale authority')

    def test_late_reply_and_scope_correction_cannot_reuse_old_consent(self):
        current = proposal()
        propose_foundation(self.root, current, reason='Initial fixture')
        answer_foundation(self.root, 'Q1', revision=1, user_text='SIMULATED: Reference', source='fixture', effect='Use references.', change_kind='non_material')
        confirm_foundation(self.root, revision=1, user_text='SIMULATED: proceed', source='fixture')
        activity(self.root, 'M01', 'begin', state='MAIN')
        answer_foundation(self.root, 'Q1', revision=1, user_text='SIMULATED: research only; stop coding.',
                          source='fixture-correction', effect='Cancel code production; discuss revised deliverable.')
        answer_foundation(self.root, 'Q1', revision=1, user_text='SIMULATED: same reply, transcription fix.',
                          source='fixture-editorial', effect='Only correct the transcription; prior correction remains.', change_kind='non_material')
        with self.assertRaises(ValueError):
            confirm_foundation(self.root, revision=1, user_text='SIMULATED: old start', source='fixture')
        with self.assertRaises(ValueError):
            activity(self.root, 'M01', 'checkpoint', continued=True)
        activity(self.root, 'M01', 'end', continued=True)
        current['brief']['results'] = 'Only the requested research explanation.'
        current['questions'][0]['question'] = 'Public release or local delivery?'
        current['unaffected_lines'] = {'M01': 'Only read previously approved sources; no code or pending release.'}
        propose_foundation(self.root, current, reason='New output and release choice.')
        with self.assertRaises(ValueError):
            answer_foundation(self.root, 'Q1', revision=1, user_text='SIMULATED: Reference', source='old', effect='Wrong question.')
        self.assertIn('One usable handoff', foundation_packet(self.root))
        self.assertEqual(require_foundation_ready(self.root, owner='M01')['status'], 'CONFIRMED_UNCHANGED_SCOPE')
        with self.assertRaises(ValueError):
            require_foundation_ready(self.root, owner='COMMON')

    def test_scope_accounting_and_unreadable_owner_stay_separate(self):
        def at(minute):
            return {'provider': 'fixture', 'domain': 'same', 'monotonic_ns': minute * 60_000_000_000,
                    'wall_ns': minute * 60_000_000_000}
        events = [{'action': 'begin', 'at': at(0), 'state': 'SOURCE', 'scope': 'FOUNDATION'},
                  {'action': 'checkpoint', 'at': at(2), 'declared_continuity': True},
                  {'action': 'end', 'at': at(4), 'declared_continuity': True},
                  {'action': 'begin', 'at': at(4), 'state': 'MAIN'},
                  {'action': 'end', 'at': at(7), 'declared_continuity': True}]
        normal = summarize_activity({'COMMON': events})['global_known_union_ns']
        early = summarize_activity({'COMMON': events}, scope='FOUNDATION')['global_known_union_ns']
        self.assertEqual(normal, {'T_ns': 180_000_000_000, 't_ns': 0})
        self.assertEqual(early, {'T_ns': 240_000_000_000, 't_ns': 240_000_000_000})
        (self.root / 'common' / 'activity.jsonl').write_text('broken log\n', encoding='utf-8')
        result = session_report(self.root)
        self.assertEqual(result['report_status'], 'PARTIAL_READ')
        self.assertIsNone(result['timing']['global_known_union_ns'])
        self.assertIsNone(result['foundation_timing']['global_known_union_ns'])


if __name__ == '__main__':
    unittest.main()
