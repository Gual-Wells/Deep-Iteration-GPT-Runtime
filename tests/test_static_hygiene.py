import ast
import re
import unittest
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.build_release import release_files


def source_files():
    return (ROOT / rel for rel in release_files(ROOT))

class TestStaticHygiene(unittest.TestCase):
    def test_python_310_syntax_gate(self):
        for p in source_files():
            if p.suffix != '.py': continue
            src=p.read_text(encoding='utf-8')
            with self.subTest(path=str(p.relative_to(ROOT))):
                ast.parse(src,filename=str(p),feature_version=(3,10))

    def test_text_utf8_lf_and_no_hidden_c0(self):
        text_suffix={'.md','.txt','.py','.json','.toml'}
        for p in source_files():
            if p.suffix not in text_suffix: continue
            data=p.read_bytes()
            with self.subTest(path=str(p.relative_to(ROOT))):
                self.assertFalse(data.startswith(b'\xef\xbb\xbf'))
                self.assertNotIn(b'\r',data)
                t=data.decode('utf-8')
                self.assertTrue(t.endswith('\n') or p.name in {'.gitignore'})
                bad=[c for c in t if ord(c)<32 and c not in '\n\t']
                self.assertEqual(bad,[])


    def test_release_tree_has_no_casefold_path_collisions(self):
        seen={}
        for p in source_files():
            rel=p.relative_to(ROOT).as_posix()
            key=rel.casefold()
            self.assertNotIn(key,seen,f'case-insensitive path collision: {seen.get(key)} vs {rel}')
            seen[key]=rel

    def test_local_markdown_relative_links_exist(self):
        pat=re.compile(r'\[[^\]]*\]\(([^)]+)\)')
        for p in source_files():
            if p.suffix != '.md': continue
            text=p.read_text(encoding='utf-8')
            for target in pat.findall(text):
                if '://' in target or target.startswith('#') or target.startswith('mailto:'):
                    continue
                target=target.split('#',1)[0]
                if not target: continue
                q=(p.parent/target).resolve()
                with self.subTest(source=str(p.relative_to(ROOT)),target=target):
                    self.assertTrue(q.exists(),f'{p}: broken link {target}')

if __name__=='__main__': unittest.main()
