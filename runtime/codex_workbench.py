"""Question-focused context for actual task research and production.

One editable Markdown workbench holds the user's goal and substantive notes.
The model chooses questions, competing approaches and useful material; these
utilities assemble readable context and controlled D/V inputs, never score
thinking, dispatch agents or certify work counts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Iterable

GOAL = '用户目标'
DELIVERY = '交付形态与价值'
STEERING = '用户纠正与已确认要求'
QUESTION = '当前关键问题'
RESEARCH = '研究、竞争解释与方案'
RESULT = '当前产物与可继续的位置'
NEXT = '值得继续的工作'


@dataclass(frozen=True)
class Section:
    level: int
    title: str
    start: int
    end: int
    text: str


def sections(text: str) -> tuple[Section, ...]:
    """Find ATX sections outside fences; user goals may contain Markdown."""
    lines = text.splitlines(keepends=True)
    starts: list[tuple[int, int, str]] = []
    fence_char = ''
    fence_length = 0
    for index, line in enumerate(lines):
        fence = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line.rstrip('\r\n'))
        if fence:
            marks, rest = fence.groups()
            if not fence_char:
                fence_char, fence_length = marks[0], len(marks)
            elif marks[0] == fence_char and len(marks) >= fence_length and not rest.strip():
                fence_char, fence_length = '', 0
            continue
        if fence_char:
            continue
        heading = re.match(r'^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$', line.rstrip('\r\n'))
        if heading:
            starts.append((index, len(heading[1]), heading[2]))
    result = []
    for position, (start, level, title) in enumerate(starts):
        end = next((s for s, depth, _ in starts[position+1:] if depth <= level), len(lines))
        result.append(Section(level, title, start+1, end, ''.join(lines[start+1:end]).strip()))
    return tuple(result)


def _quoted_request(request: str) -> str:
    runs = [len(m[0]) for m in re.finditer(r'`+', request)]
    fence = '`' * max(3, max(runs, default=0)+1)
    separator = '' if request.endswith('\n') else '\n'
    return f'{fence}text\n{request}{separator}{fence}'


def create_workbench(request: str) -> str:
    if not request.strip():
        raise ValueError('用户目标不能为空')
    return (
        '# 问题与交付工作台\n\n'
        f'## {GOAL}\n{_quoted_request(request)}\n\n'
        f'## {DELIVERY}\n\n'
        f'## {STEERING}\n\n'
        f'## {QUESTION}\n\n'
        f'## {RESEARCH}\n\n'
        f'## {RESULT}\n\n'
        f'## {NEXT}\n\n'
    )


def _required_and_selected(
    text: str, topic: str | None, *, challenge: bool, request: str | None = None,
) -> list[tuple[str, str]]:
    found = sections(text)
    top = {s.title: s.text for s in found if s.level == 2}
    goal = request if request is not None else top.get(GOAL)
    if not goal or not goal.strip():
        raise ValueError(f'请通过 --request 提供原始委托，或在工作笔记保留“{GOAL}”节')
    selected = [(GOAL, _quoted_request(goal) if request is not None else goal)]
    selected += [(label, top[label]) for label in (DELIVERY, STEERING) if top.get(label)]
    if not challenge:
        for label in (QUESTION, RESULT, NEXT):
            if top.get(label):
                selected.append((label, top[label]))
        if topic:
            matches = [s for s in found if s.title == topic]
            if len(matches) != 1:
                raise ValueError(f'研究小节必须唯一匹配：{topic}')
            selected.append((f'当前研究：{topic}', matches[0].text))
        elif top.get(RESEARCH):
            selected.append((RESEARCH, top[RESEARCH]))
        elif request is not None and not any(top.get(k) for k in (QUESTION, RESULT, NEXT)):
            selected.append(('已有工作笔记', text))
    return selected


def read_material(spec: str, *, base: Path) -> tuple[str, str]:
    """Read a selected text file/range, including Windows drive-letter paths."""
    match = re.fullmatch(r'(.+):(\d+)(?:-(\d+))?', spec)
    raw_path = match[1] if match else spec
    path = Path(raw_path)
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    if path.suffix.lower() in ('.pdf', '.epub'):
        raise ValueError('PDF/EPUB 请使用现有阅读/页段工具；此处按文本行读取，不要求转换完整原书')
    start = int(match[2]) if match else 1
    end = int(match[3] or match[2]) if match else None
    if start < 1 or (end is not None and end < start):
        raise ValueError(f'材料行范围超出文件：{spec}')
    selected = []
    count = 0
    with path.open(encoding='utf-8-sig') as stream:
        for count, line in enumerate(stream, 1):
            if count >= start:
                selected.append(f'{count}: {line.rstrip(chr(13)+chr(10))}')
            if end is not None and count == end:
                break
    if count < start or (end is not None and count < end):
        raise ValueError(f'材料行范围超出文件：{spec}；文件共{count}行')
    end = count if end is None else end
    content = '\n'.join(selected)
    return f'{path.as_posix()}:{start}-{end}', content


def context_packet(
    work: Path,
    *,
    question: str | None = None,
    topic: str | None = None,
    materials: Iterable[str] = (),
    candidates: Iterable[str] = (),
    kind: str = 'focus',
    max_chars: int = 24000,
    request: Path | None = None,
) -> str:
    if kind not in ('focus', 'D', 'V'):
        raise ValueError('kind 必须为 focus、D 或 V')
    if max_chars <= 0:
        raise ValueError('max_chars 必须为正数')
    if kind != 'focus' and (not question or not question.strip()):
        raise ValueError('D/V 输入需要说明具体研究问题或介入设想')
    work = Path(work).resolve()
    original = work.read_text(encoding='utf-8-sig')
    request_text = Path(request).read_text(encoding='utf-8-sig') if request is not None else None
    pairs = _required_and_selected(original, topic, challenge=kind != 'focus', request=request_text)
    heading = '# 当前问题工作上下文' if kind == 'focus' else f'# {kind} 研究输入'
    parts = [heading, f'工作台：{work.as_posix()}']
    if question:
        parts += ['## 本次研究焦点', question.strip()]
    for title, body in pairs:
        parts += ['## '+title, body]
    if kind != 'focus':
        instruction = (
            '围绕介入设想深入研究或试作，返回有内容的方案、材料和对主线的后果。'
            if kind == 'D' else
            '持续发展这一不同视角，保留自己的问题和发现，随重要进展继续研究；返回非重复的实质发现。'
        )
        parts += ['## 工作要求', instruction]
    for title, specs in (('明确选入的候选', candidates), ('明确选入的材料', materials)):
        for spec in specs:
            location, content = read_material(spec, base=work.parent)
            parts += ['## '+title, location, '```text\n'+content+'\n```']
    packet = '\n\n'.join(parts).rstrip()+'\n'
    if len(packet) > max_chars:
        raise ValueError(
            f'上下文共{len(packet)}字符，超过所选{max_chars}字符。'
            '请用 --topic 选研究小节、缩小材料行范围，或提高 --max-chars；目标与用户纠正不会被静默截断。'
        )
    return packet


def topic_index(work: Path) -> str:
    work = Path(work).resolve()
    found = sections(work.read_text(encoding='utf-8-sig'))
    return '\n'.join(f'{work.as_posix()}:{s.start}-{s.end}  {s.title}' for s in found)+'\n'


def record_work(
    work: Path, text: str, *, topic: str = RESEARCH, kind: str = '发现与后果',
    refs: Iterable[str] = (),
) -> str:
    """Append a public work summary to an existing section, not a second ledger.

    The timestamp records this edit only. Entries do not infer adoption, task
    completion, effective work time or DIGR counts. Ordinary editing is valid.
    One writer owns the editable workbench; this is not a concurrent journal.
    """
    if not text.strip() or not kind.strip() or '\n' in kind or '\r' in kind:
        raise ValueError('记录需要非空正文和单行标题')
    refs = tuple(refs)
    if any(not ref.strip() or '\n' in ref or '\r' in ref for ref in refs):
        raise ValueError('引用需要非空单行位置')
    work = Path(work).resolve()
    raw = work.read_bytes()
    encoding = 'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'utf-8'
    original = raw.decode(encoding)
    found = sections(original)
    matches = [s for s in found if s.title == topic]
    if len(matches) != 1:
        raise ValueError(f'记录小节必须唯一匹配：{topic}')
    lines = original.splitlines(keepends=True)
    selected = matches[0]
    # A parent's trailing text belongs to its last child in Markdown. Keep a
    # general parent note in the parent's own body, before the first child.
    boundary = next((s.start-1 for s in found if selected.start < s.start <= selected.end), selected.end)
    prefix, suffix = ''.join(lines[:boundary]), ''.join(lines[boundary:])
    newline = '\r\n' if '\r\n' in original else '\n'
    timestamp = datetime.now().astimezone().isoformat(timespec='seconds')
    # Quoting permits arbitrary Markdown in a note without creating new topics.
    body = '\n'.join('> '+line for line in text.strip().splitlines())
    entry = f'**{kind.strip()} · 记录于 {timestamp}**\n\n{body}\n'
    if refs:
        entry += '\n引用：'+'；'.join(refs)+'\n'
    entry = entry.replace('\n', newline)
    gap = newline if prefix.endswith(newline) else newline+newline
    updated = prefix+gap+entry+newline+suffix
    work.write_bytes(updated.encode(encoding))
    return f'{work.as_posix()}:{len((prefix+gap).splitlines())+1}'
