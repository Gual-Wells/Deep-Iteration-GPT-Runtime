from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from runtime import codex_io


class LocalAtomicIOTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[1] / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='codex-atomic-io-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source, self.target = self.folder / 'durable.new', self.folder / 'state.json'
        self.source.write_bytes(b'new durable state')
        self.target.write_bytes(b'old visible state')

    @staticmethod
    def hold_without_delete_share(path):
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
        create.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes, kernel.CloseHandle.restype = (wintypes.HANDLE,), wintypes.BOOL
        flags = 0x02000000 if path.is_dir() else 0x80
        handle = create(str(path), 0x80000000, 0x1 | 0x2, None, 3, flags, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        return kernel, handle

    @unittest.skipUnless(os.name == 'nt', 'real Windows delete-sharing behavior')
    def test_our_short_file_transaction_closes_the_reader_before_replacement(self):
        opened, release = threading.Event(), threading.Event()
        fdopen = os.fdopen

        @contextmanager
        def hold_read(descriptor, mode):
            with fdopen(descriptor, mode) as stream:
                class Reader:
                    def read(self):
                        body = stream.read()
                        opened.set()
                        if not release.wait(2):
                            raise AssertionError('test did not release its open reader')
                        return body
                yield Reader()

        with ThreadPoolExecutor(2) as pool, patch.object(os, 'fdopen', side_effect=hold_read):
            job = pool.submit(codex_io.read_bytes, self.target)
            written = None
            try:
                self.assertTrue(opened.wait(1))
                written = pool.submit(codex_io.replace, self.source, self.target)
                time.sleep(.02)
                self.assertFalse(job.done())
                self.assertFalse(written.done())
                self.assertEqual(self.target.read_bytes(), b'old visible state')
            finally:
                release.set()
            self.assertEqual(job.result(1), b'old visible state')
            written.result(1)
        self.assertEqual(self.target.read_bytes(), b'new durable state')

    @unittest.skipUnless(os.name == 'nt', 'real Windows sharing denial and recovery')
    def test_real_sharing_denial_retries_the_same_source_after_the_reader_releases(self):
        kernel, handle = self.hold_without_delete_share(self.target)
        denied = threading.Event()
        replace = Path.replace

        def observed(source, target):
            try:
                return replace(source, target)
            except PermissionError as error:
                self.assertIn(error.winerror, {5, 32, 33})
                denied.set()
                raise

        with ThreadPoolExecutor(1) as pool, patch.object(Path, 'replace', observed):
            job = pool.submit(codex_io.replace, self.source, self.target)
            try:
                self.assertTrue(denied.wait(1), 'the test must observe a real OS sharing denial')
            finally:
                kernel.CloseHandle(handle)
            job.result(2)
        self.assertEqual(self.target.read_bytes(), b'new durable state')
        self.assertFalse(self.source.exists())

    @unittest.skipUnless(os.name == 'nt', 'real Windows sharing denial timeout')
    def test_persistent_real_sharing_denial_is_bounded_and_preserves_the_source(self):
        kernel, handle = self.hold_without_delete_share(self.target)
        try:
            started = time.monotonic()
            with self.assertRaises(PermissionError):
                codex_io.replace(self.source, self.target, timeout=.03)
            self.assertLess(time.monotonic() - started, .5)
        finally:
            kernel.CloseHandle(handle)
        self.assertEqual(self.target.read_bytes(), b'old visible state')
        self.assertEqual(self.source.read_bytes(), b'new durable state')

    @unittest.skipUnless(os.name == 'nt', 'real Windows directory sharing denial')
    def test_directory_publication_recovers_from_sharing_denial_and_respects_a_new_target(self):
        rename = Path.rename
        for conflict in (False, True):
            with self.subTest(conflict=conflict):
                staging = self.folder / ('staging-' + str(conflict))
                destination = self.folder / ('exchange-' + str(conflict))
                staging.mkdir()
                (staging / 'attempt.json').write_bytes(b'prepared bytes')
                denied = threading.Event()
                kernel, handle = self.hold_without_delete_share(staging)

                def observed(source, target):
                    try:
                        return rename(source, target)
                    except PermissionError as error:
                        self.assertIn(error.winerror, {5, 32, 33})
                        denied.set()
                        raise

                with ThreadPoolExecutor(1) as pool, patch.object(Path, 'rename', observed):
                    publish = pool.submit(codex_io.publish_directory, staging, destination)
                    try:
                        self.assertTrue(denied.wait(1), 'fixture must reach Windows sharing denial')
                        if conflict:
                            destination.mkdir()
                    finally:
                        kernel.CloseHandle(handle)
                    if conflict:
                        with self.assertRaises(FileExistsError):
                            publish.result(2)
                        self.assertEqual(list(destination.iterdir()), [])
                        self.assertEqual((staging / 'attempt.json').read_bytes(), b'prepared bytes')
                    else:
                        publish.result(2)
                        self.assertFalse(staging.exists())
                        self.assertEqual((destination / 'attempt.json').read_bytes(), b'prepared bytes')

    def test_unrelated_permission_error_is_not_retried_or_suppressed(self):
        failure = PermissionError('synthetic unrelated access failure')
        with patch.object(Path, 'replace', side_effect=failure) as replace:
            with self.assertRaises(PermissionError) as caught:
                codex_io.replace(self.source, self.target)
        self.assertIs(caught.exception, failure)
        self.assertEqual(replace.call_count, 1)
        self.assertTrue(self.source.exists())


if __name__ == '__main__':
    unittest.main()
