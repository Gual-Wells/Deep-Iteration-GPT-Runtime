import unittest
from runtime.protocol_pin import ProtocolRef, validate_commit_sha, validate_repo_path, raw_file_url

class TestPin(unittest.TestCase):
    def test_sha(self):
        self.assertEqual(validate_commit_sha('A'*40),'a'*40)

    def test_ref_and_url(self):
        r=ProtocolRef('Gual-Wells','Deep-Iteration-GPT-Runtime','1'*40,'core/中文 spec.md')
        self.assertIn('1'*40,r.raw_url)
        self.assertIn('%E4%B8%AD%E6%96%87%20spec.md',r.raw_url)

    def test_unsafe_repo_paths(self):
        for p in ('../x','core/../x','/abs','core\\x','.'):
            with self.subTest(p=p):
                with self.assertRaises(ValueError): validate_repo_path(p)
        with self.assertRaises(ValueError): raw_file_url('o/x','r','1'*40,'core/x.md')
        with self.assertRaises(ValueError): raw_file_url('o','../r','1'*40,'core/x.md')

    def test_bad_sha_and_types(self):
        with self.assertRaises(ValueError): validate_commit_sha('abc')
        with self.assertRaises(ValueError): ProtocolRef('', 'r','1'*40,'x')

if __name__ == '__main__': unittest.main()
