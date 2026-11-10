import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, '-B', str(ROOT / 'tools/codex.py'), 'voice']


class VoiceExportTests(unittest.TestCase):
    def test_project_file_carries_its_material_and_working_internal_links(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'companion.md'
            result = subprocess.run([*CLI, 'export', 'project', '--out', str(out)],
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads(result.stdout)
            self.assertFalse(receipt['global_install_performed'])
            self.assertFalse(receipt['voice_behavior_observed'])
            content = out.read_text(encoding='utf-8')
            manifest = json.loads((ROOT / 'voice/manifest.json').read_text(encoding='utf-8'))
            for key in ('examples', 'professional', 'hosts'):
                self.assertIn((ROOT / manifest[key]).read_text(encoding='utf-8').strip(), content)
            self.assertNotIn('(references/', content)
            for anchor in re.findall(r'\]\(#([^)]+)\)', content):
                self.assertIn(f'id="{anchor}"', content)

    def test_export_refuses_to_overwrite_an_existing_user_file(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'existing.txt'
            original = b'user original\x00\xff'
            out.write_bytes(original)
            result = subprocess.run([*CLI, 'export', 'resident', '--out', str(out)],
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 2)
            self.assertEqual(out.read_bytes(), original)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
