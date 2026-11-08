import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_release',ROOT/'tools/build_release.py')
br=importlib.util.module_from_spec(spec); spec.loader.exec_module(br)

class TestReleaseBuilder(unittest.TestCase):
    def seed(self, root: Path):
        (root/'a.txt').write_text('a\n',encoding='utf-8')
        (root/'sub').mkdir(); (root/'sub/b.txt').write_text('b\n',encoding='utf-8')
        br.write_manifests(root)

    def test_relative_root_verify(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.seed(root); br.verify_tree_and_hashes(root)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'a').write_text('x')
            try: (root/'link').symlink_to(root/'a')
            except OSError: self.skipTest('symlink unavailable')
            with self.assertRaises(RuntimeError): br.release_files(root)

    def test_private_cache_is_excluded_and_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cache = root / '.cache'
            cache.mkdir()
            note = cache / 'private.txt'
            note.write_text('local user material', encoding='utf-8')
            (cache / '__pycache__').mkdir()
            (cache / '__pycache__/private.pyc').write_bytes(b'private')
            (root / 'public.md').write_text('release', encoding='utf-8')
            (root / '.git').write_text('gitdir: private-worktree-location', encoding='utf-8')
            self.assertEqual(br.release_files(root), [Path('public.md')])
            br.clean_caches(root)
            self.assertEqual(note.read_text(encoding='utf-8'), 'local user material')
            self.assertTrue((cache / '__pycache__/private.pyc').exists())

    def test_checksum_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.seed(root)
            (root/br.SUMS_FILE).write_text('0'*64+'  ../escape\n',encoding='utf-8')
            with self.assertRaises((ValueError,RuntimeError)): br.verify_tree_and_hashes(root)

    def test_release_cleanup_keeps_git_database(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            git = root / '.git'
            (git / 'objects').mkdir(parents=True)
            original = git / 'objects' / 'keep'
            original.write_bytes(b'original repository data')
            (root / '__pycache__').mkdir()
            (root / '__pycache__/temporary.pyc').write_bytes(b'cache')
            br.clean_caches(root)
            self.assertEqual(original.read_bytes(), b'original repository data')
            self.assertFalse((root / '__pycache__').exists())
            self.assertEqual(br.release_files(root), [])

    def test_output_inside_source_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.seed(root)
            with self.assertRaises(ValueError): br.build_zip(root,root/'x.zip',br.release_files(root))

    def test_deterministic_zip_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); root=base/'src'; root.mkdir(); self.seed(root)
            files=br.release_files(root); a=base/'a.zip'; b=base/'b.zip'
            br.build_zip(root,a,files); br.build_zip(root,b,files)
            self.assertEqual(br.sha256(a),br.sha256(b))


    def test_casefold_collision_rejected(self):
        # A Windows filesystem aliases these names before release_files can
        # observe both. Exercise the same portability boundary without relying
        # on the host filesystem being case-sensitive.
        with self.assertRaises(RuntimeError):
            br._assert_portable_unique(['A.txt', 'a.txt'])

    def test_windows_reserved_name_rejected(self):
        with self.assertRaises(ValueError):
            br._safe_rel('CON.txt')

    def test_windows_trailing_dot_rejected(self):
        with self.assertRaises(ValueError):
            br._safe_rel('name.')

    def test_personalization_export_inside_source_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'local-personalization').mkdir()
            (root/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').write_text('x\n',encoding='utf-8')
            with self.assertRaises(ValueError): br.export_personalization(root,root/'copy.txt')

    def test_personalization_export_is_exact_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); root=base/'src'; (root/'local-personalization').mkdir(parents=True)
            src=root/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt'; src.write_bytes(b'router\n')
            out=base/'router.txt'
            digest=br.export_personalization(root,out)
            self.assertEqual(out.read_bytes(),src.read_bytes())
            self.assertEqual(digest,br.sha256(src))


    def test_full_personalization_export_is_exact_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);root=base/'src';(root/'local-personalization').mkdir(parents=True)
            src=root/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FULL.txt';src.write_bytes(b'expanded router reference\n')
            out=base/'router-full.txt';digest=br.export_personalization(root,out,full=True)
            self.assertEqual(out.read_bytes(),src.read_bytes());self.assertEqual(digest,br.sha256(src))

if __name__ == '__main__': unittest.main()
