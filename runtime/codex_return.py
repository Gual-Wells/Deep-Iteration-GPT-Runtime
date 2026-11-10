"""A current, source-bound return snapshot for a managed Codex task.

The model selects public facts and judges the result. This utility preserves
those declarations, renders their views, and detects changed dependencies.
It never collects chats, infers N/R/D/V, or certifies semantic completion.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
from typing import Any, Mapping
import uuid

from .codex_session import (
    _read_activity, _read_json, _session, _write_json, derive_activity, session_report,
)
from .codex_timeline import fragment, render_svg, validate as validate_timeline

FORMAT = 'digr-codex-return-1'
_TEXT_FIELDS = ('result', 'scope', 'evidence', 'limits', 'time_and_responsibilities')
_TASK_FIELDS = ('format', 'P_run', 'request_sha256', 'M_target',
                'request_origin', 'created_wall_ns', 'explicit_parameters', 'clock_anchor',
                'foundation_required', 'lifecycle_required', 'decisions')


def _path(base: Path, supplied: str | Path) -> Path:
    """Keep the selected entry path; resolve separately to detect alias changes."""
    candidate = Path(supplied)
    return Path(os.path.abspath(candidate if candidate.is_absolute() else base / candidate))


def _file_ref(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f'return dependency must be an existing file: {path}')
    digest = sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'resolved_path': str(path.resolve()), 'sha256': digest.hexdigest()}


def _fingerprints(paths: set[Path]) -> dict[str, dict[str, Any]]:
    return {str(path): _file_ref(path) for path in sorted(paths)}


def _tool_paths() -> set[Path]:
    runtime = Path(__file__).resolve().parent
    files = {runtime / (name + '.py') for name in
             ('codex_return', 'codex_timeline', 'codex_session', 'codex_foundation', 'codex_lifecycle')}
    files.update({runtime.parent / 'tools' / name for name in ('codex.py', 'codex_return.py')})
    files.update(path for path in (runtime / 'assets').glob('codex_timeline*') if path.is_file())
    return files


def _tool_state() -> dict[str, dict[str, Any]]:
    return _fingerprints(_tool_paths())


def _native_state(root: Path) -> dict[str, Any]:
    """Bind task, line and clock facts; lifecycle housekeeping is separate.

    Directory candidates bind only their entry identity, matching the native
    session contract. Return actual deliverable files explicitly to bind bytes.
    """
    root, metadata = _session(root)
    files = {root / 'REQUEST.txt'}
    if (root / 'foundation.json').exists():
        files.add(root / 'foundation.json')
    if metadata.get('decisions'):
        files.add(_path(root, metadata['decisions']))
    candidates, activity_paths = {}, []
    common = root / 'common' / 'activity.jsonl'
    if common.exists():
        files.add(common)
        activity_paths.append(common)
    for folder in sorted((root / 'lines').iterdir()):
        if not folder.is_dir():
            continue
        package_path = folder / 'line.json'
        package = _read_json(package_path)
        if package.get('line_id') != folder.name:
            raise ValueError(f'line package identity mismatch: {package_path}')
        files.add(package_path)
        clock = folder / 'activity.jsonl'
        if clock.exists():
            files.add(clock)
            activity_paths.append(clock)
        if package.get('candidate'):
            candidate = _path(folder, package['candidate'])
            if candidate.is_file():
                files.add(candidate)
            elif candidate.is_dir():
                candidates[folder.name] = {'path': str(candidate),
                    'resolved_path': str(candidate.resolve()), 'kind': 'directory-entry-only'}
            else:
                raise ValueError(f'line candidate is missing: {candidate}')
    active, unknown = [], []
    for path in activity_paths:
        try:
            if derive_activity(_read_activity(path))['active'] is not None:
                active.append(str(path))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            unknown.append({'path': str(path), 'reason': str(exc)})
    lifecycle = _lifecycle(root)
    return {'task': {key: metadata.get(key) for key in _TASK_FIELDS},
            'task_input_ref': lifecycle.get('task_input_ref'),
            'files': _fingerprints(files), 'directory_candidates': candidates,
            'open_activity': active, 'unreadable_activity': unknown}


def _lifecycle(root: Path) -> dict[str, Any]:
    from .codex_lifecycle import load_lifecycle
    return load_lifecycle(root)


def _strings(data: Mapping[str, Any], field: str) -> list[str]:
    value = data.get(field, [])
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f'{field} must be a list of non-empty strings; [] is allowed')
    return value


def _input(root: Path, path: Path) -> tuple[dict[str, Any], set[Path], bytes]:
    raw = path.read_bytes()
    data = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('unsupported return-input schema')
    for field in _TEXT_FIELDS:
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f'explicit text required for {field}')
    if data.get('mode', 'recorded') != 'recorded':
        raise ValueError('illustration cannot stand in for a recorded task return')
    for field in ('decisions', 'unhandled', 'sources'):
        data[field] = _strings(data, field)
    artifacts = data.get('artifacts', [])
    if not isinstance(artifacts, list):
        raise ValueError('artifacts must be a list; text-only returns use []')
    paths = {path} | {_path(path.parent, source) for source in data['sources']}
    normal = []
    for item in artifacts:
        if (not isinstance(item, dict) or not isinstance(item.get('path'), str)
                or not isinstance(item.get('label'), str) or not item['label'].strip()):
            raise ValueError('each artifact needs a path and a non-empty label')
        selected = _path(path.parent, item['path'])
        paths.add(selected)
        normal.append({'label': item['label'], 'path': str(selected)})
    data['artifacts'] = normal
    timeline = data.get('timeline')
    if isinstance(timeline, str):
        timeline_path = _path(path.parent, timeline)
        timeline = _read_json(timeline_path)
        paths.add(timeline_path)
    if timeline is not None:
        validate_timeline(timeline)
        if timeline['mode'] != 'recorded':
            raise ValueError('a constructed illustration cannot close an actual execution record')
        if timeline.get('protocol_pin') != _session(root)[1]['P_run']:
            raise ValueError('return timeline must identify this task P_run')
        if not isinstance(timeline.get('notice'), str) or not timeline['notice'].strip():
            raise ValueError('recorded timeline needs an explicit collection/coverage notice')
        data['timeline'] = timeline
    return data, paths, raw


def _relative(path: str | Path, folder: Path) -> str:
    try:
        return os.path.relpath(path, folder).replace(os.sep, '/')
    except ValueError:
        # A user-owned original may live on a different Windows drive.
        return Path(path).as_uri()


def _write_views(folder: Path, data: Mapping[str, Any], report: Mapping[str, Any]) -> None:
    _write_json(folder / 'native-report.json', report)
    artifacts = [(item['label'], _relative(item['path'], folder)) for item in data['artifacts']]
    bullets = lambda items: '\n'.join('- ' + item for item in items) or '- 无；这是操作者的明确声明。'
    body = ['# 返回结果', '', data['result'], '']
    body.extend('[' + label + '](' + path + ')' for label, path in artifacts)
    body += ['', '## 依据与范围', '', data['scope'], '', data['evidence'], '',
             '## 决定与实际后果', '', bullets(data['decisions']), '',
             '## 未落实事项', '', bullets(data['unhandled']), '',
             '## 时间与责任事实', '', data['time_and_responsibilities'], '',
             '## 使用限制', '', data['limits'], '']
    timeline = data.get('timeline')
    if timeline is not None:
        _write_json(folder / 'public-facts.json', timeline)
        (folder / 'pipeline.svg').write_text(render_svg(timeline), encoding='utf-8')
        body += ['[静态图](pipeline.svg) · [互动细读](details.html) · [同源公开事实](public-facts.json)', '']
    else:
        body += ['未提供时间图；文字返回独立可用，不从活动钟、计数或mtime补造过程。', '']
    body += ['这是冻结快照；当前性须由return status重新核验。字节未变不认证语义品质。']
    (folder / 'RETURN.md').write_text('\n'.join(body) + '\n', encoding='utf-8')

    sections = '<h1>返回结果</h1><p>' + escape(data['result']).replace('\n', '<br>') + '</p>'
    sections += '<p>' + ' · '.join('<a href="' + escape(path, quote=True) + '">' + escape(label) + '</a>' for label, path in artifacts) + '</p>'
    for title, field in (('决定与实际后果', 'decisions'), ('未落实事项', 'unhandled')):
        sections += '<h2>' + title + '</h2><ul>' + ''.join('<li>' + escape(item) + '</li>' for item in data[field]) + '</ul>'
    sections += '<p>' + escape(data['scope']) + '</p>'
    sections += fragment(timeline) if timeline is not None else '<p>未提供时间图；文字返回独立可用，不从活动钟、计数或mtime补造过程。</p>'
    for title, field in (('依据', 'evidence'), ('时间与责任事实', 'time_and_responsibilities'), ('使用限制', 'limits')):
        sections += '<h2>' + title + '</h2><p>' + escape(data[field]).replace('\n', '<br>') + '</p>'
    # The timeline fragment inherits these host variables. A standalone page
    # must supply them; otherwise its SVG can become black-on-black.
    theme = ':root{--font-size-base:16px;--background:#fff;--foreground:#172b43;--muted-foreground:#52647b;--border:#dce3eb;--red:#d83c52;--blue:#3265ce;--purple:#8851c3;--yellow:#b27b13;--orange:#d16522;--green:#21825c;color-scheme:light dark}@media(prefers-color-scheme:dark){:root{--background:#111923;--foreground:#e8eef8;--muted-foreground:#b4c1d4;--border:#374454;--red:#ff8c9c;--blue:#88b1ff;--purple:#cca7ff;--yellow:#e7c46d;--orange:#ffb57c;--green:#85d5b6}}'
    css = 'body{max-width:1100px;margin:auto;padding:18px;font:16px/1.6 system-ui;background:var(--background);color:var(--foreground);overflow-wrap:anywhere}a{color:var(--blue)}select{font:inherit;width:100%;padding:8px}button{font:inherit}h1,h2{line-height:1.3}'
    page = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>返回快照</title><style>' + theme + css + '</style><body>' + sections + '<p>本页为冻结快照；运行return status核验当前性。没有常驻监视或内容认证。</p></body></html>'
    (folder / 'details.html').write_text(page, encoding='utf-8')


def _pointer(root: Path) -> tuple[Path, dict[str, Any]]:
    pointer = _read_json(root / 'current-return.json')
    if pointer.get('format') != FORMAT:
        raise ValueError('unsupported current-return pointer')
    path = _path(root, pointer['receipt'])
    container = (root / 'returns').resolve()
    if not container.is_relative_to(root) or not path.resolve().is_relative_to(container):
        raise ValueError('return receipt escapes the task returns directory')
    return path, pointer


def _entry(root: Path, result: Mapping[str, Any]) -> None:
    lines = ['# 当前返回', '', '状态：' + result['current_receipt'],
             '核验时刻：' + datetime.now(timezone.utc).isoformat(), '',
             '此状态只表示本次核验；后续改动须再次运行return status。']
    if result.get('receipt'):
        folder = Path(result['receipt']).parent
        lines += ['', '[结果、依据与限制](' + _relative(folder / 'RETURN.md', root) + ') · '
                  '[可点按细读](' + _relative(folder / 'details.html', root) + ')']
        if (folder / 'pipeline.svg').exists():
            lines[-1] += ' · [静态图](' + _relative(folder / 'pipeline.svg', root) + ')'
    if result['issues']:
        lines += ['', '当前性或记录限制：'] + ['- ' + issue for issue in result['issues']]
    if result['cannot_close']:
        lines += ['', '正常终结限制：'] + ['- ' + reason for reason in result['cannot_close']]
    lines += ['', '生命周期：' + result['lifecycle_status'], '',
              '散列不认证内容品质、真实同意、责任数量或全部有效时间。']
    target = root / 'CURRENT_RETURN.md'
    temporary = target.with_name(target.name + '.new-' + uuid.uuid4().hex)
    with temporary.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write('\n'.join(lines) + '\n')
    temporary.replace(target)  # Replace the entry; never follow a repointed link.


def return_status(root: Path, *, refresh_entry: bool = False) -> dict[str, Any]:
    """Recheck current bytes and closure, without changing task lifecycle."""
    root, metadata = _session(root)
    lifecycle = _lifecycle(root)
    result = {'format': FORMAT, 'current_receipt': 'MISSING', 'receipt': None,
              'P_run': metadata['P_run'], 'lifecycle_status': lifecycle['status'],
              'issues': [], 'semantic_certification': False,
              'can_close': False, 'cannot_close': [],
              'scope': 'selected current bytes and declared return; not semantic completion'}
    if not (root / 'current-return.json').exists():
        result['issues'].append('no return snapshot has been sealed')
    else:
        try:
            receipt_path, pointer = _pointer(root)
            expected = {'resolved_path': pointer['receipt_resolved_path'],
                        'sha256': pointer['receipt_sha256']}
            if _file_ref(receipt_path) != expected:
                raise ValueError('return receipt changed or its entry was redirected')
            receipt = _read_json(receipt_path)
            if receipt.get('format') != FORMAT or receipt.get('task_root') != str(root):
                raise ValueError('return receipt does not belong to this task')
            result['receipt'] = str(receipt_path)
            result['coverage'] = receipt['coverage']
            for name, ref in receipt['inputs'].items():
                if _file_ref(Path(name)) != ref:
                    result['issues'].append('selected input changed or redirected: ' + name)
            for name, ref in receipt['outputs'].items():
                if _file_ref(receipt_path.parent / name) != ref:
                    result['issues'].append('generated return changed or redirected: ' + name)
            if _native_state(root) != receipt['native_state']:
                result['issues'].append('task, line, candidate or activity facts changed')
            if _tool_state() != receipt['tool_state']:
                result['issues'].append('return or renderer implementation changed or was redirected')
            result['current_receipt'] = 'STALE' if result['issues'] else 'READY_UNCLOSED'
            closure = lifecycle.get('closure') or {}
            closed_ref = closure.get('result_ref') or {}
            if (not result['issues'] and lifecycle['status'] == 'CLOSED'
                    and closed_ref.get('path') == str(receipt_path.resolve()).replace('\\', '/')
                    and closed_ref.get('sha256') == pointer['receipt_sha256']):
                result['current_receipt'] = 'CLOSED'
        except (OSError, ValueError, TypeError, KeyError) as exc:
            result['current_receipt'] = 'STALE'
            result['issues'].append(str(exc))
    if lifecycle.get('managed') is False:
        result['cannot_close'].append('legacy session has no managed lifecycle; use its pinned toolchain')
    elif lifecycle['status'] != 'ACTIVE':
        result['cannot_close'].append('managed task is ' + lifecycle['status'])
    if lifecycle.get('managed') and lifecycle.get('message_id') != lifecycle.get('handled_message_id'):
        result['cannot_close'].append('new user message is pending; process its actual consequence first')
    if result['current_receipt'] not in {'READY_UNCLOSED', 'CLOSED'}:
        result['cannot_close'].append('a current sealed return is required before normal task closure')
    result['can_close'] = result['current_receipt'] == 'READY_UNCLOSED' and not result['cannot_close']
    if refresh_entry:
        _entry(root, result)
    return result


def seal_return(root: Path, input_path: Path) -> dict[str, Any]:
    """Freeze one selected public return; a text-only result needs no software."""
    root, metadata = _session(root)
    from .codex_lifecycle import require_active
    require_active(root)
    path = _path(Path.cwd(), input_path)
    data, paths, raw = _input(root, path)
    controls = {root / name for name in ('lifecycle.json', 'current-return.json', 'CURRENT_RETURN.md')}
    if any(selected.resolve() in controls for selected in paths):
        raise ValueError('select source/result snapshots, not mutable lifecycle or return control files')
    inputs = _fingerprints(paths)
    tool_state = _tool_state()
    if inputs[str(path)]['sha256'] != sha256(raw).hexdigest():
        raise ValueError('return input changed while being read; retry from current input')
    native = _native_state(root)
    if native['open_activity']:
        raise ValueError('end or recover open managed activity before sealing a return')
    returns = root / 'returns'
    if not returns.resolve().is_relative_to(root):
        raise ValueError('task returns directory is redirected outside the task')
    returns.mkdir(exist_ok=True)
    folder = returns / ('return-' + uuid.uuid4().hex)
    folder.mkdir()
    (folder / 'input.json').write_bytes(raw)
    _write_views(folder, data, session_report(root))
    if inputs != _fingerprints(paths) or native != _native_state(root) or tool_state != _tool_state():
        raise ValueError('return dependencies changed during rendering; no current pointer was published')
    outputs = {file.name: _file_ref(file) for file in sorted(folder.iterdir()) if file.is_file()}
    receipt = {'format': FORMAT, 'task_root': str(root), 'P_run': metadata['P_run'],
               'coverage': data['scope'], 'inputs': inputs, 'native_state': native,
               'tool_state': tool_state,
               'outputs': outputs, 'semantic_certification': False,
               'collection_scope': 'explicit selected public facts; no automatic chat collection'}
    receipt_path = folder / 'receipt.json'
    _write_json(receipt_path, receipt, new=True)
    _write_json(root / 'current-return.json', {'format': FORMAT,
                'receipt': _relative(receipt_path, root),
                'receipt_sha256': _file_ref(receipt_path)['sha256'],
                'receipt_resolved_path': str(receipt_path.resolve())})
    return return_status(root, refresh_entry=True)


def close_return(root: Path, *, reason: str, outcome: str = 'CLOSED') -> dict[str, Any]:
    """Close through the actual lifecycle, referencing the current receipt.

    A real STOP/CANCEL takes precedence over packaging: those outcomes call
    lifecycle termination first and never require a return snapshot.
    """
    from .codex_lifecycle import close_session
    if outcome not in {'CLOSED', 'STOPPED', 'CANCELLED'}:
        raise ValueError('close outcome must be CLOSED, STOPPED or CANCELLED')
    if outcome in {'STOPPED', 'CANCELLED'}:
        close_session(root, reason=reason, status=outcome)
        return return_status(root, refresh_entry=True)
    current = return_status(root)
    if current['current_receipt'] not in {'READY_UNCLOSED', 'CLOSED'}:
        raise ValueError('a current sealed return is required before normal task closure')
    if current['current_receipt'] == 'CLOSED':
        return return_status(root, refresh_entry=True)
    if not current['can_close']:
        raise ValueError('; '.join(current['cannot_close']))
    close_session(root, reason=reason, result=Path(current['receipt']), status='CLOSED')
    return return_status(root, refresh_entry=True)
