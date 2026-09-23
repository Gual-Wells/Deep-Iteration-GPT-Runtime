import hashlib,json,tempfile,unittest
from pathlib import Path
from runtime.runtime_package import attest_runtime_package
from tools.build_runtime_artifact import ROOT,build

SHA='a'*40

def blob_sha(data:bytes)->str:
    return hashlib.sha1(f'blob {len(data)}\0'.encode('ascii')+data).hexdigest()

class TestRuntimePackage(unittest.TestCase):
    def test_built_archive_attests_as_one_boundary_and_emits_protocol_load(self):
        manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
        paths=set(manifest['deterministic_helpers'])
        paths.update(('manifest.json','VERSION',manifest['execution_bundle']['path'],manifest['entrypoint'],*manifest['core']))
        tree={'truncated':False,'tree':[
            {'path':p,'type':'blob','sha':blob_sha((ROOT/p).read_bytes())}
            for p in sorted(paths)
        ]}
        with tempfile.TemporaryDirectory() as td:
            archive=Path(td)/'runtime.zip';build(archive,SHA)
            receipt=attest_runtime_package(archive,expected_commit_sha=SHA,git_tree=tree)
        self.assertEqual(receipt.commit_sha,SHA)
        self.assertEqual(receipt.helper_count,len(manifest['deterministic_helpers']))
        self.assertEqual(receipt.protocol_member_count,1+len(manifest['core']))
        pl=receipt.protocol_load
        self.assertEqual(pl['commit_sha'],SHA)
        self.assertEqual(pl['version'],manifest['version'])
        self.assertEqual(pl['protocol'],manifest['protocol'])
        self.assertEqual(pl['source_mode'],'bundle')
        self.assertEqual([x['path'] for x in pl['members']],[manifest['entrypoint'],*manifest['core']])
    def test_truncated_tree_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            archive=Path(td)/'runtime.zip';build(archive,SHA)
            with self.assertRaisesRegex(ValueError,'truncated'):
                attest_runtime_package(archive,expected_commit_sha=SHA,git_tree={'truncated':True,'tree':[]})

if __name__=='__main__':unittest.main()
