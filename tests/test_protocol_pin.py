import unittest
from runtime.protocol_pin import validate_commit_sha, raw_file_url

class TestProtocolPin(unittest.TestCase):
    def test_sha(self):
        sha = "a" * 40
        self.assertEqual(validate_commit_sha(sha), sha)
    def test_bad_sha(self):
        with self.assertRaises(ValueError):
            validate_commit_sha("abc")
    def test_url(self):
        sha = "b" * 40
        self.assertEqual(
            raw_file_url("Gual-Wells", "Deep-Iteration-GPT-Runtime", sha, "manifest.json"),
            f"https://raw.githubusercontent.com/Gual-Wells/Deep-Iteration-GPT-Runtime/{sha}/manifest.json",
        )

if __name__ == "__main__":
    unittest.main()
