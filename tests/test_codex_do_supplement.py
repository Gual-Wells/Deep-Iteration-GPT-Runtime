import json
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from runtime.codex_foundation import BRIEF_FIELDS, confirm_foundation, load_foundation, propose_foundation
from runtime.codex_lifecycle import handle_message, ingest_message, load_lifecycle, require_active, terminate_message
from runtime.codex_profile import ActiveContext, classify_invocation, decide_boundary
from runtime.codex_return import close_return, seal_return
from runtime.codex_session import create_session
from runtime.routing import candidate_route_key


PIN = '0.17.0@' + 'a' * 40
OLD_PIN = '0.16.0@' + 'b' * 40


class DoSupplementSurfaceTests(unittest.TestCase):
    def test_exact_leading_marker_preserves_the_payload_and_stays_native(self):
        payloads = ('  DIGR(X=Gmail)::正文\r\n', '(X=Gmail) 仅作为内容\n', '\n')
        for prefix in ('DO:', 'DO：'):
            for payload in payloads:
                for pin in (None, PIN):
                    with self.subTest(prefix=prefix, payload=payload, pin=pin):
                        raw = '\t\u3000' + prefix + payload
                        value = classify_invocation(raw, p_run=pin)
                        self.assertEqual(value['supplement'], {'kind': 'DO', 'prefix': prefix, 'text': payload})
                        self.assertEqual(value['classification'], 'NATIVE')
                        self.assertIsNone(candidate_route_key(raw))
                        self.assertIsNone(value['task'])
                        self.assertFalse(value['delivery_selection']['explicit'])
                        self.assertNotIn('claude_selection', value)
                        self.assertNotIn('supplement', classify_invocation(raw, p_run=OLD_PIN))
        for raw in ('do：正文', 'Do:正文', 'DO ：正文', '“DO：正文”', '引用 DO:正文'):
            self.assertNotIn('supplement', classify_invocation(raw, p_run=PIN), raw)
        outer = classify_invocation('DIGR:DO:正文', p_run=PIN)
        self.assertEqual(outer['task'], 'DO:正文')
        self.assertNotIn('supplement', outer)

    def test_boundary_applies_do_only_to_an_unfinished_deep_task(self):
        active = ActiveContext('current', 'DEEP', 'ACTIVE')
        paused = ActiveContext('current', 'DEEP', 'PAUSED')
        ordinary = ActiveContext('ordinary', 'LIGHT', 'ACTIVE')
        raw = 'DO：DIGR::补充'
        self.assertEqual(decide_boundary('NEW_TURN', raw, active=active, p_run=OLD_PIN).action, 'CONTINUE')
        for context, expected in ((active, 'HANDLE_SUPPLEMENT'), (paused, 'HANDLE_SUPPLEMENT_KEEP_PAUSED')):
            boundary = decide_boundary('NEW_TURN', raw, active=context, p_run=PIN)
            self.assertEqual((boundary.mode, boundary.action), ('DEEP', expected))
            self.assertTrue(boundary.preserve_task)
            self.assertFalse(boundary.route_required)
            self.assertEqual(boundary.continuation_of, 'current')
        changed = decide_boundary('STEER', raw, active=active, expected_turn_id='current', goal_changed=True)
        self.assertEqual(changed.action, 'REALIGN_GOAL')
        finished = [ActiveContext('finished', 'DEEP', status) for status in ('CLOSED', 'STOPPED', 'CANCELLED')]
        for context in (None, ordinary, *finished):
            boundary = decide_boundary('NEW_TURN', raw, active=context)
            self.assertEqual((boundary.mode, boundary.action), ('LIGHT', 'SUPPLEMENT_NEEDS_TASK'))
            self.assertFalse(boundary.preserve_task)
            self.assertFalse(boundary.route_required)


class DoSupplementLifecycleTests(unittest.TestCase):
    def setUp(self):
        cache = (Path(__file__).resolve().parents[1] / '.cache').resolve()
        cache.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='codex-do-test-', dir=cache)
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.root = self.folder / 'task'
        self.request = self.write('request', 'DIGR：产出可检查的样例。\n')
        create_session(self.root, request=self.request, p_run=PIN, visits_path=self.folder / 'visits.jsonl')

    def write(self, name, text):
        path = self.folder / (name + '.txt')
        path.write_bytes(text.encode('utf-8'))
        return path

    def ingest(self, ref, raw):
        return ingest_message(self.root, source=self.write(ref, raw), source_ref=ref)

    def handle(self, message, action):
        return handle_message(self.root, message_id=message['message_id'], action=action,
                              reason='Apply the interpreted fixture decision')

    def accept_brief(self):
        brief = {key: 'Bounded sample for the lifecycle fixture' for key in BRIEF_FIELDS}
        proposal = propose_foundation(self.root, {'brief': brief, 'questions': []}, reason='Fixture brief')
        answer = '按当前约定执行。\n'
        self.ingest('accept-brief', answer)
        confirm_foundation(self.root, revision=proposal['revision'], user_text=answer, source='accept-brief')

    def test_active_supplement_is_pending_and_preserves_existing_decisions(self):
        self.accept_brief()
        accepted = load_foundation(self.root)['confirmation']
        original = (self.root / 'REQUEST.txt').read_bytes()
        frozen = load_lifecycle(self.root)
        raw = '  DO： DIGR(X=Gmail)::作为补充正文保留。\r\n'
        value = self.ingest('current-supplement', raw)
        self.assertEqual(value['P_run'], PIN)
        self.assertEqual(value['status'], 'ACTIVE')
        self.assertEqual(value['task_input_ref'], frozen['task_input_ref'])
        self.assertNotEqual(value['message_id'], value['handled_message_id'])
        with self.assertRaisesRegex(ValueError, 'pending'):
            require_active(self.root)
        current = load_lifecycle(self.root)['current_message']
        self.assertEqual(current['source']['text'], raw)
        self.assertEqual(current['source']['sha256'], sha256(raw.encode('utf-8')).hexdigest())
        self.assertEqual(current['supplement']['text'], ' DIGR(X=Gmail)::作为补充正文保留。\r\n')
        self.assertFalse(current['route_required'])
        self.assertEqual(current['surface'], 'NATIVE')
        updated = self.handle(value, 'ordinary')
        self.assertEqual(require_active(self.root)['task_input_ref']['message_id'], value['message_id'])
        self.assertEqual(updated['claude_policy'], frozen['claude_policy'])
        self.assertEqual(updated['delivery_policy'], frozen['delivery_policy'])
        self.assertEqual(updated['delivery_history'], [])
        self.assertEqual(load_foundation(self.root)['confirmation'], accepted)
        self.assertEqual((self.root / 'REQUEST.txt').read_bytes(), original)

    def test_equal_text_at_a_new_source_is_a_distinct_message_while_paused(self):
        self.handle(self.ingest('pause', '暂停当前任务。'), 'pause')
        raw = 'DO: 保留先前结论。'
        first = self.handle(self.ingest('first', raw), 'ordinary')
        with self.assertRaisesRegex(ValueError, 'already observed'):
            self.ingest('first', raw)
        pending = self.ingest('second', raw)
        with self.assertRaisesRegex(ValueError, 'paused task needs'):
            self.handle(pending, 'continue')
        second = self.handle(pending, 'ordinary')
        self.assertEqual(second['status'], 'PAUSED')
        self.assertNotEqual(first['message_id'], second['message_id'])
        self.assertEqual(first['task_input_ref']['source_sha256'], second['task_input_ref']['source_sha256'])
        self.assertEqual(second['task_input_ref']['source_ref'], 'second')
        self.assertEqual(second['recent_messages'][-1]['source']['source_ref'], 'first')
        self.assertEqual(second['recent_messages'][-1]['supplement'], {'kind': 'DO', 'prefix': 'DO:'})

    def test_material_revision_and_priority_stop_use_the_interpreted_actions(self):
        self.accept_brief()
        proposed_change = self.ingest('material-revision', 'DO：更换已确认的交付对象。')
        self.assertEqual(load_foundation(self.root)['status'], 'CONFIRMED')
        self.handle(proposed_change, 'revise')
        self.assertEqual(load_foundation(self.root)['status'], 'REVOKED')
        self.ingest('older-pending', 'DO: 上一项尚未处理。')
        stop = self.write('priority-stop', 'DO：立即停止当前任务。')
        ended = terminate_message(self.root, source=stop, source_ref='priority-stop',
                                  action='stop', reason='Actual interpreted priority stop in the fixture')
        self.assertEqual(ended['status'], 'STOPPED')
        self.assertEqual(ended['current_message']['supplement']['text'], '立即停止当前任务。')
        self.assertTrue(ended['recent_messages'][-1]['pending_at_termination'])

    def test_closed_task_and_new_task_creation_refuse_an_unbound_do(self):
        self.accept_brief()
        response = {'schema_version': 2, 'result': 'Constructed result.', 'key_changes': 'Completed fixture.',
                    'work_process': '| Time | Work |\n| --- | --- |\n| Unknown | Closed the fixture |',
                    'argument_scope': 'Lifecycle behavior.',
                    'parameters': 'Fixture only.', 'sources': [], 'artifacts': []}
        seal_return(self.root, self.write('return', json.dumps(response)))
        close_return(self.root, reason='Finished the constructed task')
        closed = load_lifecycle(self.root)
        self.assertEqual(closed['status'], 'CLOSED')
        raw = 'DO：DIGR::无接续对象的输入。'
        with self.assertRaisesRegex(ValueError, 'specify the target or start a new DIGR invocation'):
            self.ingest('after-close', raw)
        self.assertEqual(load_lifecycle(self.root), closed)
        new_root = self.folder / 'new-task'
        with self.assertRaisesRegex(ValueError, 'EXECUTING original request'):
            create_session(new_root, request=self.write('standalone-do', raw), p_run=PIN,
                           visits_path=self.folder / 'visits.jsonl')
        self.assertFalse(new_root.exists())

    def test_old_pin_keeps_ordinary_message_semantics(self):
        old_task = self.folder / 'old-task'
        create_session(old_task, request=self.request, p_run=OLD_PIN, visits_path=self.folder / 'visits.jsonl')
        raw = 'DO：补充旧版任务。'
        selected = ingest_message(old_task, source=self.write('older-version', raw), source_ref='older-version')
        self.assertEqual((selected['P_run'], selected['current_message']['surface']), (OLD_PIN, 'NATIVE'))
        self.assertNotIn('supplement', selected['current_message'])
        self.assertEqual(selected['current_message']['source']['text'], raw)
