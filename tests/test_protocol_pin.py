import unittest
from runtime.protocol_pin import validate_commit_sha, raw_file_url

class TestProtocolPin(unittest.TestCase):
    def test_valid_sha(self):
        sha='EC732868B07BC5C8B35EF13EF0FBC7FE5FA3855A'
        self.assertEqual(validate_commit_sha(sha),sha.lower())
    def test_invalid_sha(self):
        with self.assertRaises(ValueError): validate_commit_sha('stable')
    def test_raw_url_is_immutable(self):
        sha='ec732868b07bc5c8b35ef13ef0fbc7fe5fa3855a'
        u=raw_file_url('Gual-Wells','Deep-Iteration-GPT-Runtime',sha,'manifest.json')
        self.assertIn('/'+sha+'/manifest.json',u)
        self.assertNotIn('/stable/',u)

if __name__=='__main__': unittest.main()
