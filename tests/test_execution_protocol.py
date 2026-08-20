import hashlib,json,unittest
from runtime.execution_protocol import (
    ExecutingProtocolLoadReceipt,verify_execution_bundle,receipt_from_individual_files,
)
SHA='a'*40
PATHS=('entry/E.md','core/A.md')
FILES=(('entry/E.md',b'# entry\n'),('core/A.md',b'# core\n'))
MANIFEST={
    'version':'5.0.0-alpha.4','protocol':'digr-v5.0','entrypoint':'entry/E.md','core':['core/A.md'],
    'execution_bundle':{'path':'bundle/EXECUTION_PROTOCOL.json','schema':1,'members':list(PATHS)},
}
MB=(json.dumps(MANIFEST,separators=(',',':'))+'\n').encode()
def bundle_bytes(files=FILES):
    obj={'schema_version':1,'version':'5.0.0-alpha.4','protocol':'digr-v5.0','members':[]}
    for p,b in files:
        obj['members'].append({'path':p,'sha256':hashlib.sha256(b).hexdigest(),'byte_length':len(b),'content':b.decode()})
    return (json.dumps(obj,sort_keys=True,separators=(',',':'))+'\n').encode()

class TestExecutionProtocol(unittest.TestCase):
    def test_bundle_verifies_exact_logical_members(self):
        out=verify_execution_bundle(bundle_bytes(),commit_sha=SHA,manifest_bytes=MB,expected_paths=PATHS)
        self.assertEqual(out.receipt.source_mode,'bundle')
        self.assertEqual(out.receipt.member_paths,PATHS)
        self.assertEqual(out.receipt.manifest_sha256,hashlib.sha256(MB).hexdigest())
        self.assertEqual(ExecutingProtocolLoadReceipt.from_dict(out.receipt.to_dict()),out.receipt)
    def test_bundle_rejects_missing_reordered_or_tampered_member(self):
        with self.assertRaises(ValueError):verify_execution_bundle(bundle_bytes(FILES[:1]),commit_sha=SHA,manifest_bytes=MB,expected_paths=PATHS)
        with self.assertRaises(ValueError):verify_execution_bundle(bundle_bytes(tuple(reversed(FILES))),commit_sha=SHA,manifest_bytes=MB,expected_paths=PATHS)
        obj=json.loads(bundle_bytes());obj['members'][0]['content']='tampered\n'
        with self.assertRaises(ValueError):verify_execution_bundle(json.dumps(obj).encode(),commit_sha=SHA,manifest_bytes=MB,expected_paths=PATHS)
    def test_individual_compatibility_normalizes_same_receipt_shape(self):
        out=receipt_from_individual_files(commit_sha=SHA,manifest_bytes=MB,expected_paths=PATHS,files=FILES)
        self.assertEqual(out.receipt.source_mode,'individual');self.assertEqual(out.receipt.member_paths,PATHS)
if __name__=='__main__':unittest.main()
