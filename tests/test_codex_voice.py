from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RETIRED_DISTRIBUTION_MESSAGE = 'Use the original DIGR Codex 1.x distribution for the task.'


class RetiredAddonCommandTests(unittest.TestCase):
    def test_direct_commands_point_to_the_original_distribution(self):
        for name in ('paper', 'knowledge', 'voice', 'preprint', 'personal'):
            with self.subTest(name=name):
                script = ROOT / 'tools' / f'codex_{name}.py'
                result = subprocess.run([sys.executable, '-B', str(script), '--help'],
                                        capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(RETIRED_DISTRIBUTION_MESSAGE, result.stderr)
                self.assertEqual(result.stdout, '')

    def test_retired_voice_export_leaves_existing_user_file_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'existing.txt'
            original = b'user original\x00\xff'
            out.write_bytes(original)
            script = ROOT / 'tools/codex_voice.py'
            result = subprocess.run(
                [sys.executable, '-B', str(script), 'export', 'resident', '--out', str(out)],
                capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 2)
            self.assertIn(RETIRED_DISTRIBUTION_MESSAGE, result.stderr)
            self.assertEqual(out.read_bytes(), original)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
