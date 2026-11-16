"""Formula layout must preserve the chosen relations on standard pages."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'), 'Node is required for the local carrier')
class FormulaLayoutTests(unittest.TestCase):
    def layout(self, tex, options=None):
        script = "const {displayLayout}=require(process.argv[1]);console.log(JSON.stringify(displayLayout(JSON.parse(process.argv[2]),JSON.parse(process.argv[3]))));"
        result = subprocess.run([shutil.which('node'), '-e', script,
            str(Path(__file__).resolve().parents[1] / 'tools/render_paper.cjs'),
            json.dumps(tex), json.dumps(options or {})], check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    def test_standard_page_preserves_condition_and_legacy_renderer_can_still_split(self):
        tex = r'\xi_{ij}(t)\le\mathbf 1\{d_{ij}(t)\le d_{\max}\},\qquad j>1.'
        preserved = self.layout(tex, {'splitAtQquad': False})
        self.assertEqual(preserved['tex'], tex)
        self.assertFalse(preserved['splitAtQquad'])
        self.assertTrue(self.layout(tex)['splitAtQquad'])

    def test_authored_aligned_relation_and_nested_text_are_not_restructured(self):
        tex = r'\begin{aligned}a&=b\qquad c\\d&=e\end{aligned}\tag{4}'
        result = self.layout(tex, {'splitAtQquad': False})
        self.assertEqual(result['tex'], tex.removesuffix(r'\tag{4}'))
        self.assertEqual(result['labels'], ['4'])
        self.assertFalse(result['splitAtQquad'])
