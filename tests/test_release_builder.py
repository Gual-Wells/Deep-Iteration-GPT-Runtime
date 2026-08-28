import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
            root=Path(td); (root/'a').write_text('x',encoding='utf-8')
            try: (root/'link').symlink_to(root/'a')
            except OSError: self.skipTest('symlink unavailable')
            with self.assertRaises(RuntimeError): br.release_files(root)

    def test_checksum_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.seed(root)
            (root/br.SUMS_FILE).write_text('0'*64+'  ../escape\n',encoding='utf-8')
            with self.assertRaises((ValueError,RuntimeError)): br.verify_tree_and_hashes(root)

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
        with self.assertRaises(RuntimeError): br._assert_portable_unique(['A.txt','a.txt'])

    def test_windows_reserved_name_rejected(self):
        with self.assertRaises(ValueError): br._safe_rel('CON.txt')

    def test_windows_trailing_dot_rejected(self):
        with self.assertRaises(ValueError): br._safe_rel('name.')

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

    def test_execution_set_sha256_fixed_vector(self):
        members=[
            {'path':'entry/E.md','sha256':'0'*64,'byte_length':7},
            {'path':'core/A.md','sha256':'f'*64,'byte_length':11},
        ]
        self.assertEqual(br.execution_set_sha256(members),'a7802e168f122ed764b010d0abff955c7f9b736037d9e310702fd427fa439bba')

    def test_prepare_generated_artifacts_and_descriptor_integrity(self):
        br.prepare_generated_artifacts(ROOT)
        import json
        descriptor=json.loads((ROOT/br.DESCRIPTOR_FILE).read_text(encoding='utf-8'))
        for item in descriptor['artifacts'].values():
            path=ROOT/item['path'];self.assertEqual(path.stat().st_size,item['byte_length']);self.assertEqual(br.sha256(path),item['sha256'])
        self.assertEqual((ROOT/br.COMPACT_PERSONALIZATION).read_bytes(),(ROOT/br.FREE_GO_PERSONALIZATION).read_bytes())
        self.assertEqual((ROOT/br.COMPACT_PERSONALIZATION).read_bytes(),(ROOT/br.STANDALONE_PERSONALIZATION).read_bytes())

    def test_test_tool_caches_are_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'keep.txt').write_text('x',encoding='utf-8');(root/'tests/.cache').mkdir(parents=True);(root/'tests/.cache/x').write_text('x',encoding='utf-8');(root/'tests/__pycache__').mkdir();(root/'tests/__pycache__/x.pyc').write_bytes(b'x')
            self.assertEqual([p.as_posix() for p in br.release_files(root)],['keep.txt'])

    def test_every_manifest_controlled_path_rejects_traversal(self):
        manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
        mutations=(
            ('bootstrap_entry','../escape.md'),
            ('startup_slice',['../escape.md']),
            ('deterministic_helpers',['../escape.py']),
            ('core',['../escape.md']),
            ('schemas',{'bad':'../escape.schema.json'}),
            ('execution_bundle',{'path':'../escape.json','schema':1,'members':[manifest['entrypoint'],*manifest['core']]}),
        )
        for key,value in mutations:
            with self.subTest(key=key):
                changed=dict(manifest);changed[key]=value
                with self.assertRaises((ValueError,RuntimeError)):br._validate_manifest_paths(changed)

    def test_failed_cold_validation_preserves_existing_zip(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);root=base/'src';root.mkdir();self.seed(root)
            output=base/'release.zip';output.write_bytes(b'known-good')
            with patch.object(br,'cold_validate',side_effect=RuntimeError('validation failed')):
                with self.assertRaisesRegex(RuntimeError,'validation failed'):
                    br.publish_zip(root,output,br.release_files(root))
            self.assertEqual(output.read_bytes(),b'known-good')
            self.assertEqual(list(base.glob('.release.zip.*.tmp.zip')),[])

    def test_cold_validation_rechecks_hash_tree_after_tests(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);root=base/'src';root.mkdir();self.seed(root)
            archive=base/'release.zip';br.build_zip(root,archive,br.release_files(root))
            calls=[]
            def mutate_after_first_validation(cmd,cwd):
                calls.append(cmd)
                if len(calls)==1:
                    (cwd/'a.txt').write_text('mutated by cold test\n',encoding='utf-8')
            with patch.object(br,'run',side_effect=mutate_after_first_validation):
                with self.assertRaisesRegex(RuntimeError,'SHA256 mismatch: a.txt'):
                    br.cold_validate(archive)
            self.assertEqual(len(calls),2)

if __name__ == '__main__': unittest.main()
