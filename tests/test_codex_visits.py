from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from runtime.codex_visits import append_visit, read_visits, run_projection, summarize_visits

ROOT = Path(__file__).resolve().parents[1]
SECOND = 1_000_000_000


def visit(eid, kind, second, *, actor='main', line='M01', run='target', category='WORK', **extra):
    # Constructed arithmetic fixtures, never purported tool observations.
    return {'schema_version': 1, 'event_id': eid, 'run_id': run,
            'actor_id': actor, 'line_id': line, 'event': kind, 'at_ns': second * SECOND,
            'phase': 'EXECUTION', 'category': category, 'work': eid, **extra}


class VisitTests(unittest.TestCase):
    def setUp(self):
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='codex-visits-test-', dir=cache)
        self.base = Path(self.temp.name).resolve()
        if not self.base.is_relative_to(cache.resolve()) or not self.base.name.startswith('codex-visits-test-'):
            raise RuntimeError('refusing cleanup outside intended test cache')
        self.addCleanup(self.temp.cleanup)
        self.path = self.base / 'visits.jsonl'

    def write(self, events):
        self.path.write_text(''.join(json.dumps(e) + '\n' for e in events), encoding='utf-8')

    def summary(self, events):
        self.write(events)
        return summarize_visits(read_visits(self.path), run_id='target')

    def test_union_includes_independent_participants_without_parallel_addition(self):
        events = [visit('a', 'BEGIN', 0), visit('b', 'BEGIN', 5, actor='D', category='SOURCE'),
                  visit('c', 'BEGIN', 8, actor='V', line='M02'),
                  visit('d', 'END', 15, actor='D'), visit('e', 'END', 20),
                  visit('f', 'END', 30, actor='V', line='M02'),
                  visit('g', 'BEGIN', 0, actor='other', run='other'),
                  visit('h', 'END', 1000, actor='other', run='other')]
        result = self.summary(events)
        self.assertEqual((result['T_seconds'], result['t_seconds']), (30, 10))
        self.assertEqual(result['by_line']['M01']['T_seconds'], 20)
        self.assertEqual(result['by_line']['M02']['T_seconds'], 22)
        self.assertEqual(result['approximate_interval_count'], 0)

    def test_missing_end_does_not_close_at_later_begin_or_now_and_targeted_repair_works(self):
        events = [visit('lost', 'BEGIN', 0, category='SOURCE'),
                  visit('new', 'BEGIN', 30), visit('new-end', 'END', 50)]
        result = self.summary(events)
        self.assertEqual(result['T_seconds'], 20)
        self.assertEqual(result['gaps'][0]['begin_event_id'], 'lost')
        events += [visit('repair', 'END', 10, begin_event_id='lost', approximate=True,
                         basis='Visible tool output ends this source visit at second 10.')]
        result = self.summary(events)
        self.assertEqual((result['T_seconds'], result['t_seconds']), (30, 10))
        self.assertEqual(result['T_closed_seconds'], 20)
        self.assertEqual(result['approximate_interval_count'], 1)
        self.assertEqual(result['gaps'], [])

    def test_repairs_change_union_by_coverage_and_can_leave_new_visit_open(self):
        events = [visit('a', 'BEGIN', 0, actor='A'), visit('b', 'END', 50, actor='A'),
                  visit('s', 'BEGIN', 5, actor='S', category='SOURCE'),
                  visit('se', 'END', 15, actor='S'),
                  visit('lost', 'BEGIN', 10, actor='D', category='SOURCE'),
                  visit('new', 'BEGIN', 30, actor='D')]
        before = self.summary(events)
        events += [visit('repair', 'END', 20, actor='D', begin_event_id='lost',
                         approximate=True, basis='Recorded interruption at second 20.')]
        after = self.summary(events)
        self.assertEqual((before['T_seconds'], before['t_seconds']), (50, 10))
        self.assertEqual((after['T_seconds'], after['t_seconds']), (50, 15))
        self.assertEqual(after['t_closed_seconds'], 10)
        self.assertEqual([g['begin_event_id'] for g in after['gaps']], ['new'])

    def test_duplicates_and_conflicting_ids_are_distinct(self):
        begin, end = visit('a', 'BEGIN', 0), visit('b', 'END', 10)
        result = self.summary([begin, begin, end, end])
        self.assertEqual(result['T_seconds'], 10)
        self.assertEqual(result['duplicate_event_count'], 2)
        self.write([begin, end])
        projection = run_projection(self.path, 'target')
        self.write([begin, begin, end, end])
        self.assertEqual(run_projection(self.path, 'target'), projection)
        conflict = dict(begin, at_ns=3 * SECOND)
        result = self.summary([begin, conflict, end])
        self.assertEqual(result['T_seconds'], 0)
        self.assertTrue(any(i['reason'] == 'conflicting-event-id' for i in result['issues']))

    def test_bad_rows_are_visible_but_preserve_other_readable_pairs(self):
        self.write([visit('a', 'BEGIN', 0), visit('b', 'END', 10)])
        with self.path.open('ab') as stream:
            stream.write(b'not-json\n\xff\n')
            stream.write(json.dumps(dict(visit('bad', 'BEGIN', 20), category='nonsense')).encode() + b'\n')
        result = summarize_visits(read_visits(self.path, run_id='target'), run_id='target')
        self.assertEqual(result['T_seconds'], 10)
        self.assertEqual(len(result['file_issues']), 2)
        self.assertEqual(len(result['issues']), 1)
        self.assertEqual(result['file_status'], 'PARTIAL_READ')

    def test_attributable_bad_event_breaks_affected_open_visit_only(self):
        events = [visit('a', 'BEGIN', 0), visit('d', 'BEGIN', 0, actor='D'),
                  dict(visit('bad', 'BEGIN', 5), category='invalid'),
                  visit('b', 'END', 10), visit('de', 'END', 12, actor='D')]
        result = self.summary(events)
        self.assertEqual(result['T_seconds'], 12)
        self.assertEqual(len(result['spans']), 1)
        self.assertEqual(result['spans'][0]['actor_id'], 'D')
        # The damaged observation breaks automatic continuity, not the Begin
        # evidence itself. A later, targeted, evidenced repair remains usable.
        events += [visit('repair', 'END', 5, begin_event_id='a', approximate=True,
                         basis='Constructed boundary fixture supported at second 5.')]
        result = self.summary(events)
        self.assertEqual(len(result['spans']), 2)
        self.assertEqual(result['approximate_interval_count'], 1)
        self.assertFalse(any(g['reason'] == 'missing-end-not-counted' for g in result['gaps']))
        self.assertEqual(result['unresolved_begin_count'], 0)
        self.assertEqual(result['by_line']['M01']['unresolved_begin_count'], 0)

    def test_rejected_end_cannot_be_absorbed_by_a_later_plain_end(self):
        events = [visit('a', 'BEGIN', 10), visit('backwards', 'END', 5),
                  visit('later', 'END', 100)]
        result = self.summary(events)
        self.assertEqual(result['T_seconds'], 0)
        self.assertTrue(any(g['reason'] == 'end-without-begin' for g in result['gaps']))
        events += [visit('repair', 'END', 20, begin_event_id='a', approximate=True,
                         basis='Constructed evidenced boundary at second 20.')]
        result = self.summary(events)
        self.assertEqual(result['T_seconds'], 10)
        self.assertEqual(result['T_closed_seconds'], 0)
        self.assertEqual(result['unresolved_begin_count'], 0)

        phases = [dict(visit('f', 'BEGIN', 0), phase='FOUNDATION'),
                  visit('wrong-phase', 'END', 5),
                  dict(visit('later-foundation', 'END', 30), phase='FOUNDATION')]
        self.write(phases)
        result = summarize_visits(read_visits(self.path), run_id='target', phase='FOUNDATION')
        self.assertEqual(result['T_seconds'], 0)
        phases += [dict(visit('repair-foundation', 'END', 4, begin_event_id='f', approximate=True,
                              basis='Constructed evidenced foundation boundary.'), phase='FOUNDATION')]
        self.write(phases)
        result = summarize_visits(read_visits(self.path), run_id='target', phase='FOUNDATION')
        self.assertEqual(result['T_seconds'], 4)

    def test_late_unbound_end_for_an_older_visit_preserves_the_newer_visit(self):
        events = [visit('old', 'BEGIN', 0), visit('new', 'BEGIN', 20),
                  visit('late-old-end', 'END', 5), visit('new-end', 'END', 30)]
        result = self.summary(events)
        self.assertEqual(result['T_seconds'], 10)
        self.assertEqual([(s['start_ns'], s['end_ns']) for s in result['spans']],
                         [(20 * SECOND, 30 * SECOND)])
        self.assertEqual([g['begin_event_id'] for g in result['gaps']
                          if g['reason'] == 'missing-end-not-counted'], ['old'])
        late = next(g for g in result['gaps'] if g['reason'] == 'late-unbound-end')
        self.assertEqual(late['candidate_begin_event_ids'], ['old'])
        self.assertIsNone(late['begin_event_id'])
        self.assertEqual(result['unresolved_begin_count'], 1)
        self.assertEqual(result['by_line']['M01']['unresolved_begin_count'], 1)

    def test_missing_file_and_other_run_append_do_not_change_selected_projection(self):
        self.assertEqual(read_visits(self.path)['file_status'], 'MISSING')
        before = run_projection(self.path, 'target')
        append_visit(self.path, run_id='other', actor_id='a', event='BEGIN')
        self.assertEqual(run_projection(self.path, 'target'), before)
        self.write([visit('a', 'BEGIN', 0), visit('b', 'END', 10)])
        before = run_projection(self.path, 'target')
        append_visit(self.path, run_id='other', actor_id='a', event='END')
        with self.path.open('ab') as stream:
            stream.write(b'{"schema_version":900,"run_id":"other"}\n')
        self.assertEqual(run_projection(self.path, 'target'), before)

    def test_observation_time_and_repair_rules_and_partial_tail_preservation(self):
        with self.assertRaisesRegex(ValueError, 'explicit at_ns'):
            append_visit(self.path, run_id='target', actor_id='a', event='END', at_ns=0)
        self.path.write_bytes(b'{"interrupted":')
        begin = append_visit(self.path, run_id='target', actor_id='a', event='BEGIN')
        end = append_visit(self.path, run_id='target', actor_id='a', event='END', at_ns=begin['at_ns'],
                           approximate=True, basis='Observed zero-duration boundary fixture.',
                           begin_event_id=begin['event_id'])
        self.assertEqual(begin['at_ns'], begin['recorded_at_ns'])
        self.assertGreaterEqual(end['recorded_at_ns'], end['at_ns'])
        self.assertTrue(self.path.read_bytes().startswith(b'{"interrupted":\n'))
        result = summarize_visits(read_visits(self.path), run_id='target')
        self.assertEqual(result['closed_interval_count'], 1)
        self.assertEqual(len(result['file_issues']), 1)

    def test_phase_idle_and_reversed_boundaries_never_count_as_execution_work(self):
        events = [dict(visit('a', 'BEGIN', 0), phase='FOUNDATION'),
                  dict(visit('b', 'END', 10), phase='FOUNDATION'),
                  visit('c', 'BEGIN', 10, category='IDLE'), visit('d', 'END', 20),
                  visit('e', 'BEGIN', 30), visit('f', 'END', 29)]
        result = self.summary(events)
        self.assertEqual(result['T_seconds'], 0)
        self.assertTrue(any(g['reason'] == 'end-before-begin' for g in result['gaps']))
        foundation = summarize_visits(read_visits(self.path), run_id='target', phase='FOUNDATION')
        self.assertEqual(foundation['T_seconds'], 10)

    def test_real_concurrent_processes_and_killed_lock_owner(self):
        # Real native file/process behavior, not mocked append or lock calls.
        writer = ('import sys; from pathlib import Path; from runtime.codex_visits import append_visit; '
                  'p=Path(sys.argv[1]); actor=sys.argv[2]; '
                  '[(append_visit(p,run_id="target",actor_id=actor,event="BEGIN"),'
                  'append_visit(p,run_id="target",actor_id=actor,event="END")) for _ in range(12)]')
        writers = [subprocess.Popen([sys.executable, '-B', '-c', writer, str(self.path), str(i)],
                                   cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for i in range(4)]
        for process in writers:
            output, error = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 0, (output, error))
        result = summarize_visits(read_visits(self.path), run_id='target')
        self.assertEqual(result['closed_interval_count'], 48)
        self.assertEqual(result['gaps'], [])
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['file_issues'], [])
        locker = ('import sys,time; from pathlib import Path; from runtime.codex_visits import _locked; '
                  '\nwith _locked(Path(sys.argv[1]),create=True):\n print("locked",flush=True); time.sleep(60)')
        process = subprocess.Popen([sys.executable, '-B', '-c', locker, str(self.path)], cwd=ROOT,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(lambda: process.poll() is None and process.kill())
        self.assertEqual(process.stdout.readline().strip(), b'locked')
        reader_code = ('import json,sys; from pathlib import Path; '
                       'from runtime.codex_visits import read_visits; p=Path(sys.argv[1]); '
                       '\ntry:\n p.read_bytes(); print("raw-readable",flush=True)'
                       '\nexcept OSError:\n print("raw-denied",flush=True)'
                       '\nprint(json.dumps(read_visits(p)["file_status"]),flush=True)')
        reader = subprocess.Popen([sys.executable, '-B', '-c', reader_code, str(self.path)], cwd=ROOT,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(lambda: reader.poll() is None and reader.kill())
        raw_result = reader.stdout.readline().strip()
        if sys.platform == 'win32':
            self.assertEqual(raw_result, b'raw-denied')
        else:
            self.assertEqual(raw_result, b'raw-readable')
        self.assertIsNone(reader.poll())
        process.kill()
        process.communicate(timeout=10)
        output, error = reader.communicate(timeout=10)
        self.assertEqual(reader.returncode, 0, error)
        self.assertEqual(json.loads(output), 'READABLE')
        append_visit(self.path, run_id='target', actor_id='after-kill', event='BEGIN')
        result = summarize_visits(read_visits(self.path), run_id='target')
        self.assertEqual(result['closed_interval_count'], 48)
        self.assertEqual(result['gaps'][-1]['actor_id'], 'after-kill')


if __name__ == '__main__':
    unittest.main()
