import base64
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from runtime.codex_transport import (
    BRANCH_URL, MANIFEST, REF, REF_URL, REPOSITORY, VERSION, CodexRepositoryTransport, load_acquisition,
)
from runtime.protocol_pin import raw_file_url
from runtime.repository_transport import TransportResponse

SHA = 'a' * 40


class CodexTransportTests(unittest.TestCase):
    def fixture(self, *, connector=False, wrapped=False):
        self.calls = []
        core = ['codex/CHARACTER.md', 'codex/PARAMETERS.md', 'codex/COLLABORATION.md', 'codex/PERMISSIONS.md']
        paths = [VERSION, 'codex/STARTUP.md', 'codex/PROTOCOL.md', *core,
                 'codex/HELP.md', 'codex/AGENTS.light.md', 'codex/ROUTER.experimental.txt', 'codex/WORKBENCH.md']
        files = {path: ('full original ' + path + '\n').encode('utf-8') for path in paths}
        files[VERSION] = b'0.6.0\n'
        bundle = 'codex/EXECUTION_PROTOCOL.json'
        members = ['codex/PROTOCOL.md', *core]
        files[bundle] = json.dumps({'schema_version': 1, 'version': '0.6.0',
            'protocol': 'digr-codex-native-v6', 'members': [
                {'path': path, 'content': files[path].decode('utf-8'),
                 'sha256': sha256(files[path]).hexdigest(), 'byte_length': len(files[path])}
                for path in members]}).encode('utf-8')
        manifest = {'version': '0.6.0', 'protocol': 'digr-codex-native-v6', 'version_path': VERSION,
            'startup_slice': ['codex/STARTUP.md'], 'entrypoint': members[0], 'core': core,
            'help': 'codex/HELP.md', 'light_instructions': 'codex/AGENTS.light.md',
            'experimental_router': 'codex/ROUTER.experimental.txt', 'workbench_guide': 'codex/WORKBENCH.md',
            'execution_bundle': {'path': bundle, 'schema': 1, 'members': members},
            'file_sha256': {path: sha256(raw).hexdigest() for path, raw in files.items()}}
        files[MANIFEST] = json.dumps(manifest).encode('utf-8')
        responses = {REF_URL: json.dumps({'ref': 'refs/heads/' + REF,
                        'object': {'type': 'commit', 'sha': SHA}}).encode('utf-8'),
                     BRANCH_URL: json.dumps({'name': REF, 'commit': {'sha': SHA}}).encode('utf-8')}
        for path, raw in files.items():
            responses[raw_file_url(*REPOSITORY.split('/'), SHA, path)] = (
                json.dumps({'type': 'file', 'path': path, 'encoding': 'base64',
                            'content': base64.b64encode(raw).decode('ascii')}).encode('utf-8') if wrapped else raw)
        self.responses = responses

        def fetch(request):
            self.calls.append(request)
            return TransportResponse(request.url, 200 if request.url in responses else 404,
                responses.get(request.url, b'missing'), 'github_connector' if connector else 'direct_https',
                'live_direct' if request.mutable_ref else 'immutable_sha')
        return CodexRepositoryTransport(fetch)

    def test_minimal_startup_then_same_pin_execution(self):
        transport = self.fixture()
        startup = transport.acquire()
        self.assertEqual(list(startup.files), [MANIFEST, VERSION, 'codex/STARTUP.md'])
        self.assertEqual([x.url for x in self.calls[:2]], [REF_URL, BRANCH_URL])
        boundary = len(self.calls)
        executing = transport.acquire('execution', startup=startup)
        self.assertEqual(executing.sha, SHA)
        self.assertTrue(all('/' + SHA + '/' in x.url for x in self.calls[boundary:]))
        self.assertIn('codex/CHARACTER.md', executing.files)
        self.assertIn('codex/PERMISSIONS.md', executing.files)
        self.assertFalse(executing.summary()['run_started'])

    def test_head_disagreement_does_not_read_files(self):
        transport = self.fixture()
        self.responses[BRANCH_URL] = json.dumps({'name': REF, 'commit': {'sha': 'b' * 40}}).encode()
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            transport.acquire()
        self.assertEqual(len(self.calls), 2)

    def test_exported_startup_continues_without_new_mutable_resolution(self):
        transport = self.fixture()
        startup = transport.acquire()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'startup'
            startup.export(out)
            restored = load_acquisition(out)
            self.responses[BRANCH_URL] = json.dumps({'name': REF, 'commit': {'sha': 'b' * 40}}).encode()
            boundary = len(self.calls)
            executing = transport.acquire('execution', startup=restored)
            self.assertEqual(executing.sha, SHA)
            self.assertFalse(executing.summary()['new_live_ref_resolution'])
            self.assertTrue(all(not x.mutable_ref for x in self.calls[boundary:]))
            (out / VERSION).write_text('changed', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'bytes changed'):
                load_acquisition(out)

    def test_help_uses_no_execution_members_and_decodes_contents(self):
        acquired = self.fixture(wrapped=True).acquire('help')
        self.assertEqual(acquired.files['codex/HELP.md'], b'full original codex/HELP.md\n')
        self.assertNotIn('codex/PROTOCOL.md', acquired.files)

    def test_declared_bundle_failure_does_not_fall_back_to_other_paths(self):
        transport = self.fixture()
        key = raw_file_url(*REPOSITORY.split('/'), SHA, 'codex/EXECUTION_PROTOCOL.json')
        del self.responses[key]
        with self.assertRaises(ValueError):
            transport.acquire('execution')
        self.assertEqual(self.calls[-1].url, key)
        self.assertFalse(any(x.url.endswith('/codex/PROTOCOL.md') for x in self.calls))

    def test_execution_member_hash_must_match_manifest_too(self):
        transport = self.fixture()
        key = raw_file_url(*REPOSITORY.split('/'), SHA, MANIFEST)
        manifest = json.loads(self.responses[key])
        manifest['file_sha256']['codex/CHARACTER.md'] = '0' * 64
        self.responses[key] = json.dumps(manifest).encode()
        with self.assertRaisesRegex(ValueError, 'member/manifest hash mismatch'):
            transport.acquire('execution')

    def test_native_connector_head_is_one_real_branch_response(self):
        transport = self.fixture(connector=True)
        acquired = transport.acquire(connector=True)
        self.assertEqual(self.calls[0].url, BRANCH_URL)
        self.assertFalse(any(x.url == REF_URL for x in self.calls))
        self.assertEqual(acquired.sha, SHA)
        transport = self.fixture()
        with self.assertRaisesRegex(ValueError, 'actual GitHub connector'):
            transport.acquire(connector=True)

    def test_untrusted_response_and_existing_export_are_rejected(self):
        transport = self.fixture()
        original = transport.fetch

        def indexed(request):
            r = original(request)
            return TransportResponse(r.request_url, r.status, r.body, 'search', 'untrusted')
        transport.fetch = indexed
        with self.assertRaises(ValueError):
            transport.acquire()
        acquired = self.fixture().acquire()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'acquired'
            acquired.export(out)
            original = (out / VERSION).read_bytes()
            with self.assertRaises(FileExistsError):
                acquired.export(out)
            self.assertEqual((out / VERSION).read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
