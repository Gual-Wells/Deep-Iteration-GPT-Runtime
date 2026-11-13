from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from runtime.codex_foundation import (
    BRIEF_FIELDS, confirm_foundation, load_foundation, propose_foundation,
)
from runtime.codex_lifecycle import (
    close_session, consume_decision_message, handle_message, ingest_message,
    load_lifecycle, recover_session, require_active, require_open_decision, terminate_message,
)
from runtime.codex_session import activity, create_line, create_session, session_report
from runtime.codex_return import close_return, return_status, seal_return

ROOT = Path(__file__).resolve().parents[1]
PIN = '0.8.0@' + '1' * 40
NEW_ROUTE_PIN = '0.8.1@' + '2' * 40
EXAMPLE_REQUEST = 'DIGR：请比较现有执行表现。只研究，先不要推送。\n'
EXAMPLE_CORRECTION = '上轮应区分普通工作与DIGR工作；这是纠错。\n'
EXAMPLE_CLARIFICATION = '我刚才没有重新调用，只是在指出前一轮的问题。\n'


def parameters():
    return {'N': 12, 'T': 0, 'R': 4, 'B': 0,
            'S': {'n': 0, 't': 0, 'r': 0, 'b': 0}, 'D': 3, 'V': 3, 'L': 3}


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        cache = (ROOT / '.cache').resolve()
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='codex-lifecycle-test-', dir=cache)
        self.folder = Path(self.temp.name).resolve()
        if not self.folder.is_relative_to(cache) or not self.folder.name.startswith('codex-lifecycle-test-'):
            raise RuntimeError('refusing cleanup outside the intended task cache')
        self.addCleanup(self.temp.cleanup)
        self.root = self.folder / 'session'
        self.request = self.file('request.txt', EXAMPLE_REQUEST)
        create_session(self.root, request=self.request, p_run=PIN)
        create_line(self.root, 'M01', parameters=parameters())

    def file(self, name, text):
        path = self.folder / name
        path.write_text(text, encoding='utf-8', newline='')
        return path

    def message(self, text, *, ref=None, route_pin=None):
        counter = load_lifecycle(self.root)['message_id'] + 1
        ref = ref or 'actual-conversation-message-' + str(counter)
        source = self.file('input-' + str(counter) + '.txt', text)
        result = ingest_message(self.root, source=source, source_ref=ref, route_pin=route_pin)
        return result['message_id'], source, ref

    def propose(self):
        return propose_foundation(self.root,
            {'brief': {key: 'A bounded constructed comparison; no project change or publication.' for key in BRIEF_FIELDS},
             'questions': []}, reason='A concrete task brief for the behavioural path')

    def confirm(self, revision):
        message_id, reply, ref = self.message('按这份完整说明继续执行。\n')
        text = reply.read_text(encoding='utf-8')
        # This order also works once the public foundation API consumes the
        # selected source itself: consumption is idempotent for this exact reply.
        require_open_decision(self.root, user_text=text, source=ref)
        value = confirm_foundation(self.root, revision=revision, user_text=text, source=ref)
        consume_decision_message(self.root, message_id=message_id, user_text=text,
                                 source=ref, kind='confirm', reason='Recorded actual decision on current task')
        return value

    def ready(self):
        return self.confirm(self.propose()['revision'])

    def sealed_result(self):
        source = self.file('constructed-result.txt', 'The selected bounded result.\n')
        data = {'schema_version': 2, 'result': 'The selected bounded result.',
                'key_changes': 'The constructed result was revised.',
                'work_process': '| Time | Work |\n| --- | --- |\n| Unknown | Constructed fixture |',
                'verification_limits': 'No semantic certification.',
                'parameters': 'No real task contribution or timing is claimed.',
                'artifacts': [], 'sources': [source.name]}
        selected = self.file('constructed-return.json', json.dumps(data))
        return seal_return(self.root, selected)

    def test_original_readonly_DIGR_stays_explicit_and_ordinary_cannot_create_new_session(self):
        value = load_lifecycle(self.root)
        self.assertEqual(value['current_message']['surface'], 'EXECUTING')
        self.assertEqual(value['P_run'], PIN)
        self.assertEqual(value['status'], 'ACTIVE')
        # A read-only question can do foundation research without claiming
        # formal execution or gaining write/publication authority.
        activity(self.root, 'COMMON', 'begin', scope='FOUNDATION', state='SOURCE')
        activity(self.root, 'COMMON', 'end', continued=True)
        self.propose()
        with self.assertRaisesRegex(ValueError, 'confirmation'):
            activity(self.root, 'M01', 'begin', state='MAIN')
        for index, text in enumerate((EXAMPLE_CORRECTION, EXAMPLE_CLARIFICATION,
                                      'DIGR/help', 'DIGR：  ', 'digr：普通大小写')):
            with self.subTest(text=text):
                source = self.file('cannot-invoke-' + str(index) + '.txt', text)
                target = self.folder / ('rejected-' + str(index))
                with self.assertRaisesRegex(ValueError, 'EXECUTING original request'):
                    create_session(target, request=source, p_run=PIN)
                self.assertFalse(target.exists())

    def test_completed_return_consumes_continuation_for_representative_ordinary_corrections(self):
        self.ready()
        metadata = (self.root / 'session.json').read_bytes()
        selected = self.sealed_result()
        result = Path(selected['receipt'])
        closed = close_session(self.root, result=result, reason='Selected protocol return was completed')
        self.assertEqual(closed['status'], 'CLOSED')
        self.assertEqual(closed['closure']['result_ref']['path'], result.as_posix())
        self.assertEqual((self.root / 'session.json').read_bytes(), metadata)
        anchor = closed['task_input_ref']
        for text in (EXAMPLE_CORRECTION, EXAMPLE_CLARIFICATION):
            message_id, _, _ = self.message(text)
            with self.assertRaisesRegex(ValueError, 'cannot reopen'):
                handle_message(self.root, message_id=message_id, action='continue', reason='Deliberately wrong continuation')
            handle_message(self.root, message_id=message_id, action='ordinary', reason='Retrospective correction only')
            self.assertEqual(load_lifecycle(self.root)['status'], 'CLOSED')
            self.assertEqual(load_lifecycle(self.root)['task_input_ref'], anchor)
            with self.assertRaisesRegex(ValueError, 'CLOSED'):
                require_open_decision(self.root)
            for state, scope in [('MAIN', 'EXECUTION'), ('SOURCE', 'FOUNDATION'), ('META', 'EXECUTION')]:
                with self.subTest(state=state, scope=scope), self.assertRaisesRegex(ValueError, 'CLOSED'):
                    activity(self.root, 'M01', 'begin', state=state, scope=scope)
        # A real new invocation is another session, never an implicit reopen.
        next_root = self.folder / 'fresh-explicit-session'
        create_session(next_root, request=self.request, p_run=NEW_ROUTE_PIN)
        self.assertEqual(load_lifecycle(next_root)['status'], 'ACTIVE')
        self.assertEqual(load_lifecycle(self.root)['status'], 'CLOSED')

    def test_same_task_steer_fences_old_checkpoint_then_carries_existing_decision(self):
        accepted = self.ready()
        foundation_bytes = (self.root / 'foundation.json').read_bytes()
        activity(self.root, 'M01', 'begin', state='MAIN')
        message_id, _, _ = self.message('补充：文件名用 specimen.txt，其余目标、路线和投入不变。\n')
        log = self.root / 'lines/M01/activity.jsonl'
        before = log.read_bytes()
        with self.assertRaisesRegex(ValueError, 'pending'):
            activity(self.root, 'M01', 'checkpoint', continued=True)
        self.assertEqual(log.read_bytes(), before)
        handle_message(self.root, message_id=message_id, action='continue',
                       reason='A filename clarification inside the accepted task')
        activity(self.root, 'M01', 'checkpoint', continued=True)
        activity(self.root, 'M01', 'end', continued=True)
        self.assertEqual(load_foundation(self.root)['confirmation'], accepted['confirmation'])
        self.assertEqual((self.root / 'foundation.json').read_bytes(), foundation_bytes)
        self.assertEqual(load_lifecycle(self.root)['P_run'], PIN)

    def test_ordinary_supplement_keeps_open_work_decision_and_frozen_pin(self):
        self.ready()
        foundation = (self.root / 'foundation.json').read_bytes()
        metadata = (self.root / 'session.json').read_bytes()
        activity(self.root, 'M01', 'begin', state='MAIN')
        message_id, _, _ = self.message('补充一点说明；没有要求中止。\n')
        value = handle_message(self.root, message_id=message_id, action='ordinary',
                               reason='An ordinary message is a supplement to the unfinished task')
        self.assertEqual(require_active(self.root)['status'], 'ACTIVE')
        self.assertEqual(value['task_input_ref']['message_id'], message_id)
        self.assertEqual(value['P_run'], PIN)
        self.assertIsNotNone(session_report(self.root)['timing']['lines']['M01']['active'])
        self.assertEqual((self.root / 'foundation.json').read_bytes(), foundation)
        self.assertEqual((self.root / 'session.json').read_bytes(), metadata)
        activity(self.root, 'M01', 'checkpoint', continued=True)
        activity(self.root, 'M01', 'end', continued=True)

    def test_help_discussion_and_invalid_surface_do_not_consume_unfinished_task(self):
        accepted = self.ready()['confirmation']
        for text in ('DIGR/help', 'DIGR是什么？', 'DIGR： ', 'DIGR：再补充一项'):
            with self.subTest(text=text):
                message_id, _, _ = self.message(text, route_pin=NEW_ROUTE_PIN)
                value = handle_message(self.root, message_id=message_id, action='continue',
                                       reason='Acquired message surface is not a lifecycle end')
                self.assertEqual(value['status'], 'ACTIVE')
                self.assertEqual(value['P_run'], PIN)
                self.assertEqual(load_foundation(self.root)['confirmation'], accepted)

    def test_ordinary_supplement_stales_old_return_without_ending_the_task(self):
        self.ready()
        self.sealed_result()
        self.assertEqual(return_status(self.root)['current_receipt'], 'READY_UNCLOSED')
        message_id, _, _ = self.message('返回前请把已约定的说明补充进去。\n')
        handle_message(self.root, message_id=message_id, action='ordinary', reason='Same-task supplement')
        self.assertEqual(load_lifecycle(self.root)['status'], 'ACTIVE')
        self.assertEqual(return_status(self.root)['current_receipt'], 'STALE')
        with self.assertRaisesRegex(ValueError, 'current sealed return'):
            close_return(self.root, reason='A stale return must not close past the new input')

    def test_direct_close_cannot_bypass_the_protocol_return(self):
        self.ready()
        arbitrary = self.file('draft.txt', 'This is only a draft.\n')
        for result in (None, arbitrary):
            with self.subTest(result=result), self.assertRaisesRegex(ValueError, 'current sealed return'):
                close_session(self.root, result=result, reason='Attempted premature normal closure')
            self.assertEqual(require_active(self.root)['status'], 'ACTIVE')
        selected = self.sealed_result()
        with self.assertRaisesRegex(ValueError, 'current sealed return'):
            close_session(self.root, result=arbitrary, reason='Wrong receipt cannot consume the task')
        close_session(self.root, result=Path(selected['receipt']), reason='Current protocol return selected')
        self.assertEqual(load_lifecycle(self.root)['status'], 'CLOSED')

    def test_material_correction_revokes_before_next_work_and_keeps_foundation_research_possible(self):
        self.ready()
        activity(self.root, 'M01', 'begin', state='MAIN')
        message_id, _, _ = self.message('将结果改为一个全新产品，先不要开工。\n')
        handle_message(self.root, message_id=message_id, action='revise', reason='Changed the contracted result')
        self.assertEqual(load_foundation(self.root)['status'], 'REVOKED')
        self.assertIsNone(load_foundation(self.root)['confirmation'])
        self.assertIsNone(session_report(self.root)['timing']['lines']['M01']['active'])
        with self.assertRaisesRegex(ValueError, 'revoked'):
            activity(self.root, 'M01', 'begin', state='MAIN')
        activity(self.root, 'COMMON', 'begin', scope='FOUNDATION', state='SOURCE')
        activity(self.root, 'COMMON', 'end', continued=True)
        renewed = self.propose()
        self.confirm(renewed['revision'])
        activity(self.root, 'M01', 'begin', state='MAIN')
        activity(self.root, 'M01', 'end', continued=True)

    def test_prefix_supplement_keeps_route_reference_separate_and_does_not_claim_network(self):
        self.ready()
        message_id, source, ref = self.message('DIGR：再补一项说明，仍是同一任务。\n')
        value = load_lifecycle(self.root)
        self.assertEqual(value['current_message']['surface'], 'ROUTE_PENDING')
        with self.assertRaisesRegex(ValueError, 'upstream route pin'):
            handle_message(self.root, message_id=message_id, action='continue', reason='Same unfinished task')
        # The upstream router performs its real fetch, then supplies its pin
        # reference. This test supplies only the reference and says exactly so.
        attached = ingest_message(self.root, source=source, source_ref=ref, route_pin=NEW_ROUTE_PIN)
        self.assertEqual(attached['message_id'], message_id)
        handle_message(self.root, message_id=message_id, action='continue', reason='Same unfinished task after upstream routing')
        value = require_active(self.root)
        self.assertEqual(value['P_run'], PIN)
        self.assertEqual(value['current_message']['upstream_route_pin_ref'], NEW_ROUTE_PIN)
        self.assertIn('not performed', value['current_message']['route_basis'])

    def test_pause_unknown_host_recovery_and_stop_are_applied_to_real_clock_entrances(self):
        accepted = self.ready()['confirmation']
        activity(self.root, 'M01', 'begin', state='MAIN')
        message_id, _, _ = self.message('暂停这项任务。\n')
        handle_message(self.root, message_id=message_id, action='pause', reason='Actual task pause')
        recover_session(self.root, reason='After actual context recovery, inspect persisted files')
        self.assertEqual(load_lifecycle(self.root)['status'], 'PAUSED')
        with self.assertRaisesRegex(ValueError, 'PAUSED'):
            activity(self.root, 'COMMON', 'begin', state='SOURCE', scope='FOUNDATION')
        message_id, _, _ = self.message(EXAMPLE_CORRECTION)
        handle_message(self.root, message_id=message_id, action='ordinary', reason='Correction does not revoke pause')
        self.assertEqual(load_lifecycle(self.root)['status'], 'PAUSED')
        message_id, _, _ = self.message('继续刚才暂停的同一项任务。\n')
        handle_message(self.root, message_id=message_id, action='resume', reason='Explicit resume of the unfinished task')
        self.assertEqual(load_foundation(self.root)['confirmation'], accepted)
        activity(self.root, 'M01', 'begin', state='SOURCE')
        message_id, _, _ = self.message('停止任务，不要再继续。\n')
        stopped = handle_message(self.root, message_id=message_id, action='stop', reason='Stop the current task now')
        self.assertEqual(stopped['status'], 'STOPPED')
        self.assertIsNone(session_report(self.root)['timing']['lines']['M01']['active'])
        self.assertEqual(load_foundation(self.root)['status'], 'REVOKED')
        with self.assertRaisesRegex(ValueError, 'STOPPED'):
            activity(self.root, 'M01', 'begin', state='MAIN')
        activity(self.root, 'M01', 'recover', reason='Cleanup remains possible after stop')
        message_id, _, _ = self.message(EXAMPLE_CLARIFICATION)
        with self.assertRaisesRegex(ValueError, 'cannot reopen'):
            handle_message(self.root, message_id=message_id, action='resume', reason='Deliberately wrong restart')
        handle_message(self.root, message_id=message_id, action='ordinary', reason='Only a retrospective correction')
        self.assertEqual(load_lifecycle(self.root)['status'], 'STOPPED')

    def test_unknown_lifecycle_blocks_new_work_but_history_and_end_recover_survive(self):
        self.ready()
        activity(self.root, 'M01', 'begin', state='MAIN')
        lifecycle = self.root / 'lifecycle.json'
        original = lifecycle.read_bytes()
        lifecycle.write_text('{broken lifecycle', encoding='utf-8')
        with self.assertRaises(ValueError):
            activity(self.root, 'M01', 'checkpoint', continued=True)
        activity(self.root, 'M01', 'end', continued=True)
        activity(self.root, 'M01', 'recover', reason='Cleanup ignores unreadable continuation state')
        report = session_report(self.root)
        self.assertEqual(report['lifecycle']['status'], 'UNREADABLE')
        self.assertEqual(report['report_status'], 'PARTIAL_READ')
        self.assertEqual(report['timing']['lines']['M01']['closed_interval_count'], 1)
        self.assertEqual(lifecycle.read_text(encoding='utf-8'), '{broken lifecycle')
        lifecycle.write_bytes(original)

    def test_pending_foundation_reply_is_bound_then_consumed_after_the_real_decision(self):
        proposal = self.propose()
        message_id, reply, ref = self.message('按当前整体说明开始。\n')
        text = reply.read_text(encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'does not match'):
            require_open_decision(self.root, user_text=EXAMPLE_CORRECTION, source=ref)
        with self.assertRaisesRegex(ValueError, 'does not match'):
            require_open_decision(self.root, user_text=text, source='invented earlier source')
        guarded = require_open_decision(self.root, user_text=text, source=ref)
        self.assertNotEqual(guarded['message_id'], guarded['handled_message_id'])
        with self.assertRaisesRegex(ValueError, 'pending'):
            activity(self.root, 'M01', 'begin', state='MAIN')
        confirm_foundation(self.root, revision=proposal['revision'], user_text=text, source=ref)
        consume_decision_message(self.root, message_id=message_id, user_text=text,
                                 source=ref, kind='confirm', reason='Current whole-task execution decision')
        activity(self.root, 'M01', 'begin', state='MAIN')
        activity(self.root, 'M01', 'end', continued=True)
        # Source snapshots prove bytes, not intent: no test here treats any
        # nonempty reply or any supplied action name as certified agreement.

    def test_real_stop_source_has_priority_over_an_earlier_pending_supplement(self):
        self.ready()
        activity(self.root, 'M01', 'begin', state='MAIN')
        self.message('补充内容尚未处理。\n')
        stop = self.file('priority-stop.txt', '现在立即停止。\n')
        value = terminate_message(self.root, source=stop, source_ref='new-real-stop',
            action='stop', reason='The current stop takes priority over the older pending input')
        self.assertEqual(value['status'], 'STOPPED')
        self.assertEqual(value['current_message']['source']['text'], '现在立即停止。\n')
        self.assertTrue(value['recent_messages'][-1]['pending_at_termination'])
        self.assertIsNone(session_report(self.root)['timing']['lines']['M01']['active'])
        repeated = terminate_message(self.root, source=stop, source_ref='new-real-stop',
            action='stop', reason='Retry the same actual stop')
        self.assertEqual(repeated['message_id'], value['message_id'])
        with self.assertRaisesRegex(ValueError, 'STOPPED'):
            activity(self.root, 'M01', 'begin', state='MAIN')

    def test_old_source_cannot_be_reingested_as_a_new_resume(self):
        self.ready()
        mid, original, ref = self.message('继续当前同一任务。\n', ref=' original-resume ')
        handle_message(self.root, message_id=mid, action='continue', reason='A real continuation')
        pause, _, _ = self.message('现在暂停。\n')
        handle_message(self.root, message_id=pause, action='pause', reason='A later real pause')
        with self.assertRaisesRegex(ValueError, 'already observed'):
            ingest_message(self.root, source=original, source_ref=ref.strip())
        self.assertEqual(load_lifecycle(self.root)['status'], 'PAUSED')
        # Equal words with a genuinely different supplied source remain possible;
        # a source reference is a local identity, not user authentication.
        newer = ingest_message(self.root, source=original, source_ref='genuinely-new-resume')
        handle_message(self.root, message_id=newer['message_id'], action='resume', reason='New actual resume decision')
        self.assertEqual(require_active(self.root)['status'], 'ACTIVE')

    def test_public_cli_keeps_bom_and_crlf_reply_source_identity(self):
        proposal = self.propose()
        reply = self.folder / 'windows-reply.txt'
        reply.write_bytes(b'\xef\xbb\xbf' + '按当前说明执行。\r\n'.encode('utf-8'))
        ingest_message(self.root, source=reply, source_ref='windows-current-reply')
        command = [sys.executable, '-B', str(ROOT / 'tools/codex.py'), 'foundation', 'confirm',
            '--root', str(self.root), '--revision', str(proposal['revision']),
            '--reply-file', str(reply), '--source', 'windows-current-reply']
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(load_foundation(self.root)['confirmation']['user_text'], '按当前说明执行。\r\n')
        self.assertEqual(load_lifecycle(self.root)['message_id'], load_lifecycle(self.root)['handled_message_id'])

    def test_managed_format_rejects_a_legacy_writer_downgrade(self):
        metadata = self.root / 'session.json'
        current = json.loads(metadata.read_text(encoding='utf-8'))
        self.assertEqual(current['format'], 'digr-codex-session-2')
        current['format'] = 'digr-codex-session-1'
        metadata.write_text(json.dumps(current), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'format-2'):
            load_lifecycle(self.root)

    def test_bounded_sources_and_replayed_message_cannot_rewrite_current_consequence(self):
        self.ready()
        first_id = None
        for number in range(12):
            message_id, _, _ = self.message('普通说明 ' + str(number) + '\n')
            first_id = first_id or message_id
            handle_message(self.root, message_id=message_id, action='ordinary', reason='An ordinary discussion, no work continuation')
        value = load_lifecycle(self.root)
        self.assertEqual(len(value['recent_messages']), 8)
        self.assertEqual(value['status'], 'ACTIVE')
        self.assertTrue(all('text' not in item['source'] for item in value['recent_messages']))
        before = (self.root / 'lifecycle.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'stale/replayed'):
            handle_message(self.root, message_id=first_id, action='resume', reason='Attempt to replay an old continuation')
        self.assertEqual((self.root / 'lifecycle.json').read_bytes(), before)

    def test_failed_invalidation_keeps_pending_fence_and_failed_stop_history_still_stops(self):
        self.ready()
        activity(self.root, 'M01', 'begin', state='MAIN')
        message_id, _, _ = self.message('结果需要重要调整，先不要继续。\n')
        with patch('runtime.codex_foundation.revoke_foundation', side_effect=OSError('constructed storage failure')):
            with self.assertRaises(OSError):
                handle_message(self.root, message_id=message_id, action='revise', reason='Changed the accepted result')
        self.assertNotEqual(load_lifecycle(self.root)['message_id'], load_lifecycle(self.root)['handled_message_id'])
        with self.assertRaisesRegex(ValueError, 'pending'):
            activity(self.root, 'M01', 'checkpoint', continued=True)
        handle_message(self.root, message_id=message_id, action='revise', reason='Retry the actual pending correction')
        activity(self.root, 'COMMON', 'begin', state='SOURCE', scope='FOUNDATION')
        message_id, _, _ = self.message('立即停止。\n')
        with patch('runtime.codex_foundation.revoke_foundation', side_effect=OSError('constructed storage failure')):
            with self.assertRaises(OSError):
                handle_message(self.root, message_id=message_id, action='stop', reason='Stop is applied before history cleanup')
        self.assertEqual(load_lifecycle(self.root)['status'], 'STOPPED')
        with self.assertRaisesRegex(ValueError, 'STOPPED'):
            activity(self.root, 'M01', 'begin', state='MAIN')
        activity(self.root, 'COMMON', 'end', continued=True)
        activity(self.root, 'COMMON', 'recover', reason='Cleanup after a failed history update remains possible')

    def test_legacy_pin_does_not_gain_current_lifecycle_or_reject_historical_request(self):
        source = self.file('legacy-request.txt', 'A preserved pre-0.8 ordinary original request.\n')
        root = self.folder / 'legacy'
        create_session(root, request=source, p_run='0.6.0@' + '3' * 40)
        before = (root / 'session.json').read_bytes()
        create_line(root, 'M01', parameters=parameters())
        self.assertFalse(require_active(root)['managed'])
        self.assertFalse(require_open_decision(root)['managed'])
        self.assertEqual(session_report(root)['lifecycle']['status'], 'LEGACY_UNMANAGED')
        activity(root, 'M01', 'begin', state='MAIN')
        activity(root, 'M01', 'end', continued=True)
        activity(root, 'M01', 'recover', reason='Historical cleanup remains available')
        with self.assertRaisesRegex(ValueError, 'legacy session'):
            close_session(root, reason='Do not silently promote a frozen run')
        self.assertFalse((root / 'lifecycle.json').exists())
        self.assertEqual((root / 'session.json').read_bytes(), before)

    def test_public_cli_connects_selected_reply_pending_steer_and_real_stop(self):
        cli = [sys.executable, '-B', str(ROOT / 'tools/codex.py')]

        def call(*args, expected=0):
            result = subprocess.run([*cli, *map(str, args)], cwd=ROOT,
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            return json.loads(result.stdout) if expected == 0 else result.stderr

        root = self.folder / 'cli-session'
        proposal = self.file('cli-proposal.json', json.dumps({
            'brief': {key: 'Constructed bounded research comparison.' for key in BRIEF_FIELDS}, 'questions': []}))
        params = self.file('cli-parameters.json', json.dumps(parameters()))
        reply = self.file('cli-reply.txt', '按已经展示的完整说明继续。\n')
        steer = self.file('cli-steer.txt', '补充：用较短的结果文件名，其余不变。\n')
        call('task', 'create', '--out', root, '--request', self.request, '--p-run', PIN)
        call('line', 'create', '--root', root, '--id', 'M01', '--parameters', params)
        call('foundation', 'propose', '--root', root, '--input', proposal, '--reason', 'Actual presented constructed brief')
        call('task', 'message', '--root', root, '--source-file', reply, '--source-ref', 'constructed-go-ahead')
        call('foundation', 'confirm', '--root', root, '--revision', 1,
             '--reply-file', reply, '--source', 'constructed-go-ahead')
        call('clock', 'begin', '--root', root, '--owner', 'M01', '--state', 'MAIN')
        message = call('task', 'message', '--root', root, '--source-file', steer, '--source-ref', 'constructed-steer')
        self.assertIn('pending', call('clock', 'checkpoint', '--root', root, '--owner', 'M01', '--continued', expected=2))
        call('task', 'handle', '--root', root, '--message-id', message['message_id'],
             '--action', 'continue', '--reason', 'Clarification within the same accepted task')
        call('clock', 'checkpoint', '--root', root, '--owner', 'M01', '--continued')
        call('clock', 'end', '--root', root, '--owner', 'M01', '--continued')
        self.assertEqual(call('task', 'terminate', '--root', root, '--status', 'STOPPED', '--reason', 'Actual stop')['status'], 'STOPPED')
        self.assertIn('STOPPED', call('foundation', 'confirm', '--root', root, '--revision', 1,
                                     '--reply-file', reply, '--source', 'constructed-go-ahead', expected=2))
        call('task', 'recover', '--root', root, '--reason', 'Inspect stopped task without restarting')
        self.assertEqual(call('task', 'lifecycle', '--root', root)['status'], 'STOPPED')


if __name__ == '__main__':
    unittest.main()
