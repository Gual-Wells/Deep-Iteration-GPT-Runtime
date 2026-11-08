import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, '-B', str(ROOT / 'tools/codex.py')]
PARAMETERS = {'N': 12, 'T': '60min', 'R': 4, 'B': 0,
              'S': {'n': 3, 't': '30min', 'r': 1, 'b': 0}, 'D': 3, 'V': 3, 'L': 3}


class CodexCliTests(unittest.TestCase):
    def call(self, *args):
        result = subprocess.run([*CLI, *map(str, args)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_real_command_path_to_resumable_binary_candidate_and_clock_report(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            request = base / 'request.txt'
            request.write_bytes(b'\xef\xbb\xbfDIGR: keep original\r\n')
            params = base / 'parameters.json'
            params.write_text(json.dumps(PARAMETERS), encoding='utf-8')
            task = base / 'task'
            anchor = ['--anchor-pid', str(os.getpid())] if sys.platform == 'win32' else []
            self.call('task', 'create', '--out', task, '--request', request,
                      '--p-run', '0.6.0@' + 'a' * 40, *anchor)
            self.call('line', 'create', '--root', task, '--id', 'M01', '--parameters', params)
            self.call('clock', 'begin', '--root', task, '--owner', 'M01', '--state', 'MAIN')
            candidate = base / 'candidate.pdf'
            candidate.write_bytes(b'%PDF-binary-\x00')
            status = base / 'status.json'
            status.write_text(json.dumps({'candidate': 'candidate.pdf', 'content_status': 'DRAFT',
                'responsibility_status': 'IN_PROGRESS', 'next_action': 'Read the PDF',
                'unhandled': ['independent return still pending']}), encoding='utf-8')
            self.call('line', 'update', '--root', task, '--id', 'M01', '--input', status)
            packet = self.call('line', 'packet', '--root', task, '--id', 'M01')
            self.assertIn('candidate.pdf', packet)
            self.assertIn('independent return still pending', packet)
            self.call('clock', 'end', '--root', task, '--owner', 'M01', '--continued')
            report = json.loads(self.call('clock', 'report', '--root', task))
            self.assertEqual((task / 'REQUEST.txt').read_bytes(), request.read_bytes())
            self.assertEqual(report['registered_line_count'], 1)
            self.assertIsNone(report['effective_M_count'])
            self.assertGreater(report['timing']['global_known_union_ns']['T_ns'], 0)

    def test_authorization_advice_and_backward_compatible_passthrough(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'operation.json'
            path.write_text(json.dumps({'context': {'scope': 'the existing release', 'authorized': True},
                'operation': 'push', 'within_task': True, 'capability': 'AVAILABLE'}), encoding='utf-8')
            result = json.loads(self.call('permissions', '--input', path))
            self.assertEqual(result['next_action'], 'PROCEED_WITHIN_TASK')
            self.assertFalse(result['operation_executed'])
        self.assertIn('context', self.call('workbench', '--help'))
        self.assertIn('capture', self.call('experience', '--help'))

    def test_resumption_keeps_explicit_free_heading_correction_and_selected_history(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            request, work, params = base / 'request.txt', base / 'notes.md', base / 'parameters.json'
            request.write_text('Original task stays intact.', encoding='utf-8')
            work.write_text('## 已确认的新细节\nOnly export historical v1.\n\n'
                            '## 当前关键问题\nHow to continue?\n', encoding='utf-8')
            params.write_text(json.dumps(PARAMETERS), encoding='utf-8')
            case_note = base / 'case.md'
            case_note.write_text('History is a candidate, not current authority.', encoding='utf-8')
            case = base / 'case.json'
            self.call('experience', 'capture', '--note', case_note, '--source', 'notes.md:1-2', '--out', case)
            task = base / 'task'
            self.call('task', 'create', '--out', task, '--request', request, '--p-run', 'fixture@' + '0' * 40)
            self.call('line', 'create', '--root', task, '--id', 'M01', '--parameters', params,
                      '--work', work, '--corrections-topic', '已确认的新细节', '--experience', 'case.json')
            packet = self.call('line', 'packet', '--root', task, '--id', 'M01')
            self.assertIn('Original task stays intact.', packet)
            self.assertIn('Only export historical v1.', packet)
            self.assertIn('History is a candidate, not current authority.', packet)
            self.assertEqual(work.read_text(encoding='utf-8').count('Only export historical v1.'), 1)

    def test_invalid_input_has_no_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'not-object.json'
            path.write_text('[]', encoding='utf-8')
            result = subprocess.run([*CLI, 'permissions', '--input', str(path)],
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
