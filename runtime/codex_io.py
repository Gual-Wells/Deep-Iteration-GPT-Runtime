"""Short local file operations; retries never repeat a model request.

Each file has a short process-local read/replace mutex. Windows readers also
allow delete sharing, while replacement retries the same already durable source
for a bounded interval when another process still denies sharing.
"""
from __future__ import annotations

import os
from pathlib import Path
import time
import threading
from functools import lru_cache

_LOCKS_GUARD = threading.Lock()
_LOCKS: dict[str, threading.RLock] = {}


def _file_lock(path: Path):
    # Managed callers already supply their resolved path. Avoid opening the
    # file merely to resolve its name before entering the short mutex.
    identity = os.path.normcase(os.path.abspath(path))
    with _LOCKS_GUARD:
        if identity not in _LOCKS:
            _LOCKS[identity] = threading.RLock()
        return _LOCKS[identity]


@lru_cache(maxsize=1)
def _windows_read_api():
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes, close.restype = (wintypes.HANDLE,), wintypes.BOOL
    return create, close


def read_bytes(path: Path) -> bytes:
    path = Path(path)
    with _file_lock(path):
        return _read_bytes(path)


def _read_bytes(path: Path) -> bytes:
    if os.name != 'nt':
        return path.read_bytes()
    import ctypes
    import msvcrt
    create, close = _windows_read_api()
    handle = create(str(path), 0x80000000, 0x1 | 0x2 | 0x4, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        close(handle)
        raise
    with os.fdopen(descriptor, 'rb') as stream:
        return stream.read()


def replace(source: Path, target: Path, *, timeout: float = 1.0) -> None:
    """Retry a transient Windows sharing denial, preserving the same source."""
    source, target = Path(source), Path(target)
    end, delay = time.monotonic() + max(timeout, 0.0), .005
    while True:
        try:
            with _file_lock(target):
                source.replace(target)
            return
        except PermissionError as error:
            if (os.name != 'nt' or getattr(error, 'winerror', None) not in {5, 32, 33}
                    or time.monotonic() >= end):
                raise
            time.sleep(min(delay, max(end - time.monotonic(), 0.0)))
            delay = min(delay * 2, .05)
