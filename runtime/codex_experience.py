"""Source-bound, explicitly selected experience candidates.

Ordinary notes and workbench materials remain valid. This optional container
keeps a model-authored note beside the exact source excerpts it used, and can
show that an original location has changed or disappeared. It does not infer
preferences, select applicable cases, promote authority, or write global memory.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Iterable

from runtime.codex_workbench import read_material

FORMAT = 'digr-experience-candidate/1'


def _digest(text: str) -> str:
    # read_material normalizes source line endings and retains line numbers.
    return sha256(text.encode('utf-8')).hexdigest()


def _quoted(text: str) -> str:
    length = max((len(m[0]) for m in re.finditer(r'`+', text)), default=0)
    fence = '`' * max(3, length + 1)
    return f'{fence}text\n{text.rstrip()}\n{fence}'


def capture_candidate(note: str, *, sources: Iterable[str], base: Path) -> dict:
    """Capture selected text evidence for a freely written candidate note.

    The model supplies the interpretation, conditions, exceptions and possible
    next action in ordinary prose when useful. Requiring named fields would not
    prove their truth or relevance. No candidate need be created after feedback.
    """
    if not isinstance(note, str) or not note.strip():
        raise ValueError('经验候选需要非空说明')
    evidence = []
    for spec in sources:
        location, excerpt = read_material(spec, base=Path(base))
        evidence.append({'source': location, 'excerpt': excerpt, 'sha256': _digest(excerpt)})
    if not evidence:
        raise ValueError('带源候选需要至少一个明确选入的材料片段；普通笔记可直接用 --material')
    return {'format': FORMAT, 'note': note, 'evidence': evidence}


def write_candidate(path: Path, candidate: dict) -> None:
    """Create one explicitly named local file, preserving any existing file."""
    _validate(candidate)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(candidate, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def _validate(candidate: object) -> dict:
    if not isinstance(candidate, dict) or candidate.get('format') != FORMAT:
        raise ValueError('不是可识别的带源经验候选')
    if not isinstance(candidate.get('note'), str) or not candidate['note'].strip():
        raise ValueError('经验候选没有非空说明')
    if not isinstance(candidate.get('evidence'), list) or not candidate['evidence']:
        raise ValueError('经验候选没有来源片段')
    for entry in candidate['evidence']:
        if not isinstance(entry, dict) or any(
            not isinstance(entry.get(field), str) or not entry[field]
            for field in ('source', 'excerpt', 'sha256')
        ):
            raise ValueError('经验候选的来源片段不完整')
        if _digest(entry['excerpt']) != entry['sha256']:
            raise ValueError('经验候选内部的来源片段与摘要不一致')
    return candidate


def _source_status(entry: dict) -> str:
    try:
        _, current = read_material(entry['source'], base=Path.cwd())
    except (OSError, ValueError):
        return '当前未读到原位置；下面仅为当时保存的片段。'
    if _digest(current) != entry['sha256']:
        return '当前原位置已变化；下面仅为当时保存的片段，需重新判断。'
    return ('本轮重读的该片段相同；只核对选中片段。周边上下文、当前目标和授权仍须按本题核对，'
            '不证明转述真实或经验适用。')


def render_candidates(paths: Iterable[Path], *, max_chars: int | None = None) -> str:
    """Render only selected files, with saved evidence and current source status.

    Source drift is visible rather than silently repaired. A snapshot remains a
    historical observation; it is not an instruction or a current user request.
    The caller decides applicability and retains current task/steering context.
    """
    if max_chars is not None and max_chars <= 0:
        raise ValueError('max_chars 必须为正数')
    selected = tuple(Path(path).resolve() for path in paths)
    if not selected:
        return ''
    parts = [
        '## 明确选入的历史候选',
        '以下是可修订的历史材料与模型解释。当前用户目标与最新纠正优先；'
        '相同词语不证明条件相同，保存或选入不提升为稳定偏好，不自动授权新工作或 Memory 写入。'
        '是否适用、是否改变本题下一项工作，仍按实际材料判断。',
    ]
    for path in selected:
        candidate = _validate(json.loads(path.read_text(encoding='utf-8-sig')))
        parts += ['### '+path.name, '候选位置：'+path.as_posix(),
                  '**候选说明**', _quoted(candidate['note'])]
        for entry in candidate['evidence']:
            parts += ['**来源片段**', entry['source'], _source_status(entry), _quoted(entry['excerpt'])]
    packet = '\n\n'.join(parts)+'\n'
    if max_chars is not None and len(packet) > max_chars:
        raise ValueError(
            f'历史候选共{len(packet)}字符，超过所选{max_chars}字符；'
            '请主动减少候选或来源范围，不静默删除条件或证据。'
        )
    return packet
