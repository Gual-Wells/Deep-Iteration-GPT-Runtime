#!/usr/bin/env python3
"""Prepare and cold-validate deterministic DIGR 5.0.0-Berta2 artifacts.

Standard-library only.  The builder rejects symlinks/path traversal, tests the
source before cache cleanup, regenerates FILE_TREE/SHA256SUMS, writes a sorted
fixed-timestamp ZIP, cold-extracts it to a temporary directory, verifies every
hash, and reruns the full validation suite from the extracted copy. DEFLATE byte
reproducibility is scoped to the same Python/zlib build environment.
"""
from __future__ import annotations
import argparse
import hashlib
import json
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
EXCLUDED_DIRS = {
    '.git', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.hypothesis',
    '.tox', '.nox', '.cache', '__pycache__', 'htmlcov',
}
EXCLUDED_SUFFIXES = {'.pyc', '.pyo'}
EXCLUDED_FILES = {'.coverage', 'coverage.xml', '.testmondata'}
TREE_FILE = 'FILE_TREE.txt'
SUMS_FILE = 'SHA256SUMS.txt'
DESCRIPTOR_FILE = 'runtime-descriptor.json'
PERSONALIZATION_TEMPLATE = 'local-personalization/PERSONALIZATION_TEMPLATE.txt'
COMPACT_PERSONALIZATION = 'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt'
FREE_GO_PERSONALIZATION = 'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FREE_GO.txt'
FULL_PERSONALIZATION = 'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FULL.txt'
STANDALONE_PERSONALIZATION = 'CHATGPT_LOCAL_PERSONALIZATION.txt'
CONFIG_SENTINEL = '<!-- DIGR_LOCAL_PERSONALIZATION_END -->\n'
FIXED_ZIP_TIME = (2026, 8, 20, 0, 0, 0)
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
        if p.name in EXCLUDED_FILES:
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


def execution_set_sha256(members: list[dict]) -> str:
    """Hash ordered execution member receipts using the Berta2 canonical form."""
    canonical = json.dumps(
        [
            {'path': item['path'], 'sha256': item['sha256'], 'byte_length': item['byte_length']}
            for item in members
        ],
        ensure_ascii=False, sort_keys=True, separators=(',', ':'),
    ).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def _validate_manifest_paths(manifest: dict) -> None:
    """Reject unsafe paths in every manifest-controlled navigation surface."""
    scalar_keys = ('runtime_descriptor', 'bootstrap_entry', 'model_protocol_source', 'entrypoint', 'help', 'workspace_spec')
    list_keys = ('startup_slice', 'core', 'deterministic_helpers')
    paths: list[str] = []
    for key in scalar_keys:
        value = manifest.get(key)
        if not isinstance(value, str):
            raise RuntimeError(f'manifest {key} must be a path string')
        paths.append(value)
    for key in list_keys:
        values = manifest.get(key)
        if not isinstance(values, list) or not values or not all(isinstance(x, str) for x in values):
            raise RuntimeError(f'manifest {key} must be a non-empty path list')
        paths.extend(values)
    schemas = manifest.get('schemas')
    if not isinstance(schemas, dict) or not schemas or not all(isinstance(x, str) for x in schemas.values()):
        raise RuntimeError('manifest schemas must map names to paths')
    paths.extend(schemas.values())
    bundle = manifest.get('execution_bundle')
    if not isinstance(bundle, dict) or not isinstance(bundle.get('path'), str):
        raise RuntimeError('manifest execution_bundle path missing')
    bundle_members = bundle.get('members')
    expected_members = [manifest.get('entrypoint'), *manifest.get('core', [])]
    if (not isinstance(bundle_members, list)
            or not all(isinstance(x, str) for x in bundle_members)
            or bundle_members != expected_members):
        raise RuntimeError('manifest execution_bundle members must exactly match entrypoint/core order')
    paths.append(bundle['path'])
    paths.extend(bundle_members)
    for value in paths:
        _safe_rel(value)
    _assert_portable_unique(paths)


def _load_release_metadata(root: Path) -> tuple[dict, dict]:
    root = root.resolve()
    descriptor = json.loads((root / DESCRIPTOR_FILE).read_text(encoding='utf-8'))
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    _validate_manifest_paths(manifest)
    version = (root / 'VERSION').read_text(encoding='utf-8').strip()
    for key in ('schema', 'protocol', 'version', 'package_version', 'surface', 'engine_api', 'minimum_adapter', 'artifacts'):
        if key not in descriptor:
            raise RuntimeError(f'runtime descriptor missing {key}')
    if descriptor['version'] != version or manifest.get('version') != version:
        raise RuntimeError('navigation manifest/VERSION/runtime descriptor version drift')
    if descriptor['protocol'] != manifest.get('protocol'):
        raise RuntimeError('navigation manifest/runtime descriptor protocol drift')
    project = (root / 'pyproject.toml').read_text(encoding='utf-8')
    package_match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', project)
    if package_match is None or package_match.group(1) != descriptor['package_version']:
        raise RuntimeError('runtime descriptor/pyproject package_version drift')
    if manifest.get('runtime_descriptor') != DESCRIPTOR_FILE:
        raise RuntimeError('manifest runtime_descriptor navigation drift')
    if manifest.get('navigation_authority') is not True:
        raise RuntimeError('manifest must declare navigation_authority')
    adapter = descriptor['minimum_adapter']
    required_adapter_values = {
        'repository': 'Gual-Wells/Deep-Iteration-GPT-Runtime',
        'ref': 'stable',
        'descriptor_path': DESCRIPTOR_FILE,
        'navigation_source': 'manifest.json',
        'activation': 'after_pinned_startup_classifies_EXECUTING',
        'artifact_integrity': 'sha256_and_byte_length',
        'execution_set_integrity': 'ordered_member_count_and_execution_set_sha256',
    }
    if (not isinstance(adapter, dict)
            or any(adapter.get(key) != value for key, value in required_adapter_values.items())):
        raise RuntimeError('runtime descriptor minimum_adapter locator/integrity drift')
    engine_api = descriptor['engine_api']
    required_api_values = {
        'preflight': 'digr.preflight',
        'commit_delivery': 'digr.commit_delivery',
        'preflight_binding': 'runtime.host_adapter.HostAdapter.preflight',
        'start_binding': 'runtime.host_adapter.HostAdapter.start',
        'commit_delivery_binding': 'runtime.run_session.LiveDIGRRun.commit_delivery',
        'enforced_host_integration': 'required_for_canonical_attestation',
        'execution_without_host': 'MODEL_NATIVE',
        'canonical_attestation': 'requires_verified_host_enforcement',
    }
    if (not isinstance(engine_api, dict)
            or any(engine_api.get(key) != value for key, value in required_api_values.items())):
        raise RuntimeError('runtime descriptor logical/Python API binding drift')
    artifacts = descriptor['artifacts']
    for name in ('model_protocol', 'help', 'execution_bundle', 'navigation_manifest', 'navigation_version'):
        item = artifacts.get(name)
        base_keys = {'path', 'sha256', 'byte_length', 'media_type'}
        expected_keys = base_keys | ({'member_count', 'execution_set_sha256'} if name == 'execution_bundle' else set())
        if not isinstance(item, dict) or set(item) != expected_keys:
            raise RuntimeError(f'invalid descriptor artifact record: {name}')
        _safe_rel(item['path'])
        if not _HEX64.fullmatch(item['sha256']) or not isinstance(item['byte_length'], int) or item['byte_length'] < 0:
            raise RuntimeError(f'invalid descriptor artifact integrity: {name}')
        if name == 'execution_bundle':
            if not isinstance(item['member_count'], int) or item['member_count'] < 1:
                if item['member_count'] != 0 or item['byte_length'] != 0:
                    raise RuntimeError('invalid descriptor execution bundle member_count')
            if not _HEX64.fullmatch(item['execution_set_sha256']):
                raise RuntimeError('invalid descriptor execution_set_sha256')
    if manifest.get('execution_bundle', {}).get('path') != artifacts['execution_bundle']['path']:
        raise RuntimeError('descriptor/navigation manifest execution bundle path drift')
    return descriptor, manifest


def write_model_protocol(root: Path) -> Path:
    """Generate the compact stable model protocol from its single author source."""
    root = root.resolve()
    descriptor, manifest = _load_release_metadata(root)
    source = _safe_rel(manifest['model_protocol_source']).as_posix()
    body = (root / source).read_text(encoding='utf-8').strip()
    rel = _safe_rel(descriptor['artifacts']['model_protocol']['path']).as_posix()
    out = root / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f'# DIGR Model Protocol — {descriptor["version"]}\n\n'
        '<!-- Generated by tools/build_release.py from entry/MODEL_PROTOCOL_SOURCE.md. -->\n\n'
        f'{body}\n',
        encoding='utf-8', newline='\n',
    )
    return out


def write_help_distribution(root: Path) -> Path:
    """Copy canonical zh-CN Help to its descriptor-declared distribution path."""
    root = root.resolve()
    descriptor, manifest = _load_release_metadata(root)
    rel = _safe_rel(descriptor['artifacts']['help']['path']).as_posix()
    out = root / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes((root / manifest['help']).read_bytes())
    return out


def _personalization_sections(template: str) -> tuple[str, str]:
    compact_marker = '[[COMPACT]]\n'
    full_marker = '[[FULL]]\n'
    if not template.startswith(compact_marker) or template.count(compact_marker) != 1 or template.count(full_marker) != 1:
        raise RuntimeError('personalization template markers are invalid')
    compact, full = template[len(compact_marker):].split(full_marker, 1)
    compact = compact.rstrip('\n') + '\n'
    full = full.rstrip('\n') + '\n'
    for name, text in (('compact', compact), ('full', full)):
        if not text.endswith(CONFIG_SENTINEL):
            raise RuntimeError(f'{name} personalization lacks terminal sentinel')
        if text.count(CONFIG_SENTINEL.strip()) != 1:
            raise RuntimeError(f'{name} personalization sentinel is not unique')
    return compact, full


def write_personalizations(root: Path) -> dict[str, Path]:
    """Render compact, full, FREE_GO and root standalone from one template."""
    root = root.resolve()
    compact, full = _personalization_sections((root / PERSONALIZATION_TEMPLATE).read_text(encoding='utf-8'))
    payloads = {
        COMPACT_PERSONALIZATION: compact,
        FREE_GO_PERSONALIZATION: compact,
        FULL_PERSONALIZATION: full,
        STANDALONE_PERSONALIZATION: compact,
    }
    out: dict[str, Path] = {}
    for rel, content in payloads.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8', newline='\n')
        out[rel] = path
    return out


def write_execution_bundle(root: Path) -> Path:
    """Regenerate the descriptor-declared immutable execution transport bundle."""
    root=root.resolve()
    descriptor,manifest=_load_release_metadata(root)
    meta=manifest.get('execution_bundle')
    if not isinstance(meta,dict):
        raise RuntimeError('manifest execution_bundle metadata missing')
    rel=_safe_rel(descriptor['artifacts']['execution_bundle']['path']).as_posix()
    if meta.get('path') != rel:
        raise RuntimeError('manifest execution_bundle navigation drift')
    if meta.get('schema')!=1:
        raise RuntimeError('unsupported execution bundle schema')
    expected=[manifest['entrypoint'],*manifest['core']]
    if meta.get('members') != expected:
        raise RuntimeError('manifest execution_bundle members drift from entrypoint/core order')
    members=[]
    for member in expected:
        safe=_safe_rel(member).as_posix();data=(root/safe).read_bytes()
        try: content=data.decode('utf-8')
        except UnicodeDecodeError as exc: raise RuntimeError(f'execution protocol member is not UTF-8: {safe}') from exc
        members.append({
            'path':safe,
            'sha256':hashlib.sha256(data).hexdigest(),
            'byte_length':len(data),
            'content':content,
        })
    payload={'schema_version':1,'version':manifest['version'],'protocol':manifest['protocol'],'members':members}
    out=root/rel;out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
    return out


def prepare_generated_artifacts(root: Path) -> list[Path]:
    """Generate every descriptor/local distribution artifact without building a ZIP."""
    root = root.resolve()
    write_personalizations(root)
    generated = [write_model_protocol(root), write_help_distribution(root), write_execution_bundle(root)]
    _write_descriptor_integrity(root)
    return generated


def _write_descriptor_integrity(root: Path) -> Path:
    """Atomically bind descriptor artifacts to their generated pinned bytes."""
    root = root.resolve()
    path = root / DESCRIPTOR_FILE
    descriptor = json.loads(path.read_text(encoding='utf-8'))
    for item in descriptor['artifacts'].values():
        artifact = root / _safe_rel(item['path']).as_posix()
        data = artifact.read_bytes()
        item['sha256'] = hashlib.sha256(data).hexdigest()
        item['byte_length'] = len(data)
    bundle_item = descriptor['artifacts']['execution_bundle']
    bundle = json.loads((root / bundle_item['path']).read_text(encoding='utf-8'))
    execution_set = [
        {'path': member['path'], 'sha256': member['sha256'], 'byte_length': member['byte_length']}
        for member in bundle['members']
    ]
    bundle_item['member_count'] = len(execution_set)
    bundle_item['execution_set_sha256'] = execution_set_sha256(execution_set)
    data = (json.dumps(descriptor, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    tmp = root / '.runtime-descriptor.json.tmp'
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return path


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
            verify_tree_and_hashes(dest)


def build_release(root: Path, output: Path) -> str:
    root = root.resolve()
    output = output.resolve()
    prepare_generated_artifacts(root)
    run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], root)
    run([sys.executable, 'tests/validate_repo.py'], root)
    clean_caches(root)
    files = write_manifests(root)
    verify_tree_and_hashes(root)
    publish_zip(root, output, files)
    return sha256(output)


def publish_zip(root: Path, output: Path, files: list[Path]) -> None:
    """Validate a same-directory temporary ZIP before replacing a published ZIP."""
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f'.{output.name}.', suffix='.tmp.zip', dir=output.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        build_zip(root, temporary, files)
        cold_validate(temporary)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()


def export_personalization(root: Path, output: Path, *, full: bool=False, free_go: bool=False) -> str:
    root = root.resolve()
    output = output.resolve()
    if root == output or root in output.parents:
        raise ValueError('personalization output must be outside the release root')
    if full and free_go:
        raise ValueError('full and free_go exports are mutually exclusive')
    if full:
        name = 'CHATGPT_LOCAL_PERSONALIZATION_FULL.txt'
    elif free_go:
        name = 'CHATGPT_LOCAL_PERSONALIZATION_FREE_GO.txt'
    else:
        name = 'CHATGPT_LOCAL_PERSONALIZATION.txt'
    src = root / 'local-personalization' / name
    output.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    fd, name = tempfile.mkstemp(prefix=f'.{output.name}.', suffix='.tmp', dir=output.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        temporary.write_bytes(data)
        if temporary.read_bytes() != data:
            raise RuntimeError('staged personalization bytes changed')
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return sha256(output)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path)
    ap.add_argument('--prepare-only', action='store_true')
    ap.add_argument('--personalization-output', type=Path)
    ap.add_argument('--full-personalization-output', type=Path)
    ap.add_argument('--free-go-personalization-output', type=Path)
    args = ap.parse_args()
    if args.prepare_only:
        if any(value is not None for value in (
                args.output,
                args.personalization_output,
                args.full_personalization_output,
                args.free_go_personalization_output,
        )):
            ap.error('--prepare-only cannot be combined with output/export options')
        prepare_generated_artifacts(ROOT)
        print(f'prepared descriptor artifacts for {ROOT}')
        return 0
    if args.output is None:
        ap.error('--output is required unless --prepare-only is used')
    digest = build_release(ROOT, args.output)
    extras=[]
    if args.personalization_output is not None:
        pdigest = export_personalization(ROOT, args.personalization_output)
        extras.append(f'personalization={args.personalization_output.resolve()} sha256={pdigest}')
    if args.full_personalization_output is not None:
        fdigest = export_personalization(ROOT, args.full_personalization_output, full=True)
        extras.append(f'full_personalization={args.full_personalization_output.resolve()} sha256={fdigest}')
    if args.free_go_personalization_output is not None:
        gdigest = export_personalization(ROOT, args.free_go_personalization_output, free_go=True)
        extras.append(f'free_go_personalization={args.free_go_personalization_output.resolve()} sha256={gdigest}')
    extra=('; '+'; '.join(extras)) if extras else ''
    print(f'built {args.output.resolve()} ({len(release_files(ROOT))} files, sha256={digest}){extra}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
