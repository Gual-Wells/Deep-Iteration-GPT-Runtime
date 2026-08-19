#!/usr/bin/env python3
"""Build and cold-validate a deterministic DIGR 5.0.0-alpha.3 source ZIP.

Standard-library only.  The builder rejects symlinks/path traversal, tests the
source before cache cleanup, regenerates FILE_TREE/SHA256SUMS, writes a sorted
fixed-timestamp ZIP, cold-extracts it to a temporary directory, verifies every
hash, and reruns the full validation suite from the extracted copy.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {'.git', '.pytest_cache', '.mypy_cache', '.ruff_cache', '__pycache__'}
EXCLUDED_SUFFIXES = {'.pyc', '.pyo'}
TREE_FILE = 'FILE_TREE.txt'
SUMS_FILE = 'SHA256SUMS.txt'
FIXED_ZIP_TIME = (2026, 8, 19, 0, 0, 0)
_HEX64 = re.compile(r'^[0-9a-f]{64}$')
_WINDOWS_RESERVED = {
    'CON', 'PRN', 'AUX', 'NUL', 'CLOCK$',
    *(f'COM{i}' for i in range(1, 10)),
    *(f'LPT{i}' for i in range(1, 10)),
}
_WINDOWS_INVALID_CHARS = set('<>:\"|?*')


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd.resolve(), check=True)


def _safe_rel(text: str) -> PurePosixPath:
    if not text or '\\' in text or text.startswith('/') or '\x00' in text:
        raise ValueError(f'unsafe release path: {text!r}')
    p = PurePosixPath(text)
    if any(part in ('', '.', '..') for part in p.parts):
        raise ValueError(f'unsafe release path: {text!r}')
    _windows_portable_key(p)
    return p


def _windows_portable_key(path: PurePosixPath) -> str:
    """Return a Windows-style collision key or reject a non-portable path.

    Windows' common unpacking behavior is case-insensitive and also aliases
    trailing spaces/dots and reserved device basenames.  Release archives must
    therefore be portable before they are written, not merely valid POSIX ZIPs.
    """
    folded: list[str] = []
    for part in path.parts:
        if part.endswith((' ', '.')):
            raise ValueError(f'Windows-nonportable trailing space/dot: {path.as_posix()!r}')
        if any(ord(ch) < 32 or ch in _WINDOWS_INVALID_CHARS for ch in part):
            raise ValueError(f'Windows-nonportable character in path: {path.as_posix()!r}')
        stem = part.split('.', 1)[0].upper()
        if stem in _WINDOWS_RESERVED:
            raise ValueError(f'Windows-reserved path component: {path.as_posix()!r}')
        folded.append(part.casefold())
    return '/'.join(folded)


def _assert_portable_unique(paths: list[str]) -> None:
    seen: dict[str, str] = {}
    for text in paths:
        p = _safe_rel(text)
        key = _windows_portable_key(p)
        prior = seen.get(key)
        if prior is not None and prior != text:
            raise RuntimeError(
                f'cross-platform release path collision: {prior!r} vs {text!r}'
            )
        seen[key] = text


def clean_caches(root: Path) -> None:
    root = root.resolve()
    for p in sorted(root.rglob('*'), key=lambda x: len(x.parts), reverse=True):
        if p.is_symlink():
            continue
        if p.is_dir() and p.name in EXCLUDED_DIRS:
            shutil.rmtree(p)
        elif p.is_file() and p.suffix in EXCLUDED_SUFFIXES:
            p.unlink()


def release_files(root: Path) -> list[Path]:
    root = root.resolve()
    out: list[Path] = []
    for p in root.rglob('*'):
        if p.is_symlink():
            raise RuntimeError(f'symlink is not allowed in release tree: {p.relative_to(root)}')
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        _safe_rel(rel.as_posix())
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if p.suffix in EXCLUDED_SUFFIXES:
            continue
        out.append(rel)
    out = sorted(out, key=lambda x: x.as_posix())
    _assert_portable_unique([p.as_posix() for p in out])
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_manifests(root: Path) -> list[Path]:
    root = root.resolve()
    (root / TREE_FILE).touch()
    (root / SUMS_FILE).touch()
    files = release_files(root)
    (root / TREE_FILE).write_text(
        ''.join(f'{p.as_posix()}\n' for p in files), encoding='utf-8', newline='\n'
    )
    files = release_files(root)
    lines = []
    for rel in files:
        if rel.as_posix() == SUMS_FILE:
            continue
        lines.append(f'{sha256(root / rel)}  {rel.as_posix()}\n')
    (root / SUMS_FILE).write_text(''.join(lines), encoding='utf-8', newline='\n')
    return release_files(root)


def build_zip(root: Path, output: Path, files: list[Path]) -> None:
    root = root.resolve()
    output = output.resolve()
    if root == output or root in output.parents:
        raise ValueError('output ZIP must be outside the release root')
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in files:
            _safe_rel(rel.as_posix())
            src = root / rel
            if src.is_symlink():
                raise RuntimeError(f'symlink is not allowed: {rel}')
            data = src.read_bytes()
            info = zipfile.ZipInfo(rel.as_posix(), FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def _declared_tree(root: Path) -> list[str]:
    lines = (root / TREE_FILE).read_text(encoding='utf-8').splitlines()
    if len(lines) != len(set(lines)):
        raise RuntimeError('FILE_TREE contains duplicate paths')
    for line in lines:
        _safe_rel(line)
    _assert_portable_unique(lines)
    return lines


def verify_tree_and_hashes(root: Path) -> None:
    root = root.resolve()
    declared = _declared_tree(root)
    actual = [p.as_posix() for p in release_files(root)]
    if declared != actual:
        raise RuntimeError('FILE_TREE.txt does not match release files')

    sums: dict[str, str] = {}
    for line in (root / SUMS_FILE).read_text(encoding='utf-8').splitlines():
        if '  ' not in line:
            raise RuntimeError('malformed SHA256SUMS line')
        digest, rel = line.split('  ', 1)
        _safe_rel(rel)
        if not _HEX64.fullmatch(digest):
            raise RuntimeError(f'malformed SHA256 digest for {rel}')
        if rel in sums:
            raise RuntimeError(f'duplicate SHA256 entry: {rel}')
        sums[rel] = digest
    expected = set(actual) - {SUMS_FILE}
    if set(sums) != expected:
        raise RuntimeError('SHA256SUMS file set does not match release tree')
    for rel, digest in sums.items():
        if sha256(root / rel) != digest:
            raise RuntimeError(f'SHA256 mismatch: {rel}')


def _zip_member_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def cold_validate(output: Path) -> None:
    output = output.resolve()
    with zipfile.ZipFile(output, 'r') as zf:
        bad = zf.testzip()
        if bad is not None:
            raise RuntimeError(f'ZIP CRC/header validation failed at {bad}')
        members = zf.namelist()
        if members != sorted(members):
            raise RuntimeError('ZIP members are not sorted deterministically')
        if len(members) != len(set(members)):
            raise RuntimeError('ZIP contains duplicate member names')
        _assert_portable_unique(members)
        for info in zf.infolist():
            _safe_rel(info.filename)
            if _zip_member_is_symlink(info):
                raise RuntimeError(f'ZIP symlink member rejected: {info.filename}')
            if '__pycache__' in info.filename or info.filename.endswith(('.pyc', '.pyo')):
                raise RuntimeError('ZIP contains bytecode/cache artifacts')
        with tempfile.TemporaryDirectory(prefix='digr-release-') as td:
            dest = Path(td).resolve()
            zf.extractall(dest)
            verify_tree_and_hashes(dest)
            run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], dest)
            run([sys.executable, 'tests/validate_repo.py'], dest)


def build_release(root: Path, output: Path) -> str:
    root = root.resolve()
    output = output.resolve()
    run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], root)
    run([sys.executable, 'tests/validate_repo.py'], root)
    clean_caches(root)
    files = write_manifests(root)
    verify_tree_and_hashes(root)
    build_zip(root, output, files)
    cold_validate(output)
    return sha256(output)


def export_personalization(root: Path, output: Path, *, full: bool=False) -> str:
    root = root.resolve()
    output = output.resolve()
    if root == output or root in output.parents:
        raise ValueError('personalization output must be outside the release root')
    name = 'CHATGPT_LOCAL_PERSONALIZATION_FULL.txt' if full else 'CHATGPT_LOCAL_PERSONALIZATION.txt'
    src = root / 'local-personalization' / name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(src.read_bytes())
    return sha256(output)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--personalization-output', type=Path)
    ap.add_argument('--full-personalization-output', type=Path)
    args = ap.parse_args()
    digest = build_release(ROOT, args.output)
    extras=[]
    if args.personalization_output is not None:
        pdigest = export_personalization(ROOT, args.personalization_output)
        extras.append(f'personalization={args.personalization_output.resolve()} sha256={pdigest}')
    if args.full_personalization_output is not None:
        fdigest = export_personalization(ROOT, args.full_personalization_output, full=True)
        extras.append(f'full_personalization={args.full_personalization_output.resolve()} sha256={fdigest}')
    extra=('; '+'; '.join(extras)) if extras else ''
    print(f'built {args.output.resolve()} ({len(release_files(ROOT))} files, sha256={digest}){extra}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
