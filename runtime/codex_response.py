"""Render the five-part report intended for the conversation response body.

This checks a selected Markdown document, not a host UI event, factual accuracy,
or whether the model actually pasted that document into its final response.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from html.parser import HTMLParser
import re


SECTIONS = (
    ('result', '结果'),
    ('key_changes', '关键变化'),
    ('work_process', '工作过程'),
    ('verification_limits', '核验与限制'),
    ('parameters', '参数'),
)


def _prose_lines(text: str):
    """Yield Markdown lines outside fenced code; keep their original indices."""
    fence_char, fence_size = '', 0
    for index, line in enumerate(text.splitlines()):
        stripped = line.lstrip(' ')
        indent = len(line) - len(stripped)
        if indent <= 3 and stripped[:1] in ('`', '~'):
            char = stripped[0]
            size = len(stripped) - len(stripped.lstrip(char))
            if size >= 3:
                if not fence_char:
                    fence_char, fence_size = char, size
                    continue
                if char == fence_char and size >= fence_size and not stripped[size:].strip():
                    fence_char, fence_size = '', 0
                    continue
        if not fence_char:
            yield index, line
    if fence_char:
        raise ValueError('unclosed Markdown code fence')


def _without_inline_code(line: str) -> str:
    """Ignore matched CommonMark backtick spans, including literal HTML samples."""
    pieces = []
    cursor = 0
    while cursor < len(line):
        start = line.find('`', cursor)
        if start < 0:
            pieces.append(line[cursor:])
            break
        pieces.append(line[cursor:start])
        end_run = start
        while end_run < len(line) and line[end_run] == '`':
            end_run += 1
        marker = line[start:end_run]
        close = end_run
        while True:
            close = line.find(marker, close)
            if close < 0:
                pieces.append(line[start:])
                return ''.join(pieces)
            after = close + len(marker)
            if (close == 0 or line[close - 1] != '`') and (after == len(line) or line[after] != '`'):
                cursor = after
                break
            close = after
    return ''.join(pieces)


class _RawHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.found = False

    def handle_starttag(self, tag, attrs):
        # Markdown URL autolinks are prose, not HTML containers.
        # HTMLParser also treats <user@example.org> as a tag, whereas Markdown
        # renders that syntax as an email autolink; @ cannot name an HTML tag.
        if '@' not in tag and not tag.startswith(('https:', 'http:', 'mailto:')):
            self.found = True

    def handle_endtag(self, tag):
        self.found = True

    def handle_comment(self, data):
        self.found = True


def _has_work_table(text: str) -> bool:
    """Recognize a Markdown table with a fact row, without interpreting facts."""
    lines = [line.strip() for _, line in _prose_lines(text)]
    cells = lambda line: [cell.strip() for cell in re.split(r'(?<!\\)\|', line.strip('|'))]
    for index in range(1, len(lines) - 1):
        header, divider, row = lines[index - 1:index + 2]
        if '|' not in header or '|' not in divider or '|' not in row:
            continue
        columns = cells(divider)
        if (len(columns) >= 2 and len(cells(header)) == len(columns)
                and all(re.fullmatch(r':?-+:?', cell) for cell in columns)
                and any(cells(row))):
            return True
    return False


def validate_response(text: str) -> None:
    """Check five ordered, nonempty level-two sections and no raw prose HTML.

    Subheadings and literal code are allowed. Artifact links are allowed. This
    function deliberately does not guess whether a linked artifact replaces an
    explanation, certify parameter responsibility, or claim UI enforcement.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError('response must be nonempty Markdown text')
    lines = text.splitlines()
    headings = []
    parser = _RawHTML()
    prose = []
    for index, line in _prose_lines(text):
        stripped = line.lstrip(' ')
        if len(line) - len(stripped) <= 3:
            if stripped.startswith('## ') and not stripped.startswith('### '):
                headings.append((index, stripped[3:].strip()))
            elif stripped.startswith('# '):
                raise ValueError('use the five level-two report sections; subheadings start at level three')
            prose.append(line)
    parser.feed(_without_inline_code('\n'.join(prose)))
    parser.close()
    if parser.found:
        raise ValueError('raw HTML cannot carry the response report; quote code samples as Markdown code')
    if [title for _, title in headings] != [title for _, title in SECTIONS]:
        raise ValueError('response needs five ordered sections: ' + ' -> '.join(title for _, title in SECTIONS))
    if any(line.strip() for line in lines[:headings[0][0]]):
        raise ValueError('the response starts with the result section, without an outer code fence or preface')
    for position, (start, title) in enumerate(headings):
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        if not any(line.strip() for line in lines[start + 1:end]):
            raise ValueError('empty response section: ' + title)
    work = '\n'.join(lines[headings[2][0] + 1:headings[3][0]])
    if not _has_work_table(work):
        raise ValueError('work process needs a readable Markdown time/work table; unknown times may be explicit')


def render_response(data: Mapping[str, object]) -> str:
    """Preserve authored Markdown inside a fixed, small report envelope."""
    parts = []
    for field, title in SECTIONS:
        body = data.get(field)
        if not isinstance(body, str) or not body.strip():
            raise ValueError('explicit Markdown body required for ' + field)
        parts.append('## ' + title + '\n\n' + body.strip())
    text = '\n\n'.join(parts) + '\n'
    validate_response(text)
    return text


def render_work_table(rows: Sequence[tuple[str, str]]) -> str:
    """Render selected time/work facts; never derive durations or fill gaps."""
    if not rows:
        raise ValueError('select work rows, using an explicit unknown time when necessary')
    lines = ['| 时间／记录范围 | 工作与后果 |', '| --- | --- |']
    for row in rows:
        if len(row) != 2 or any(not isinstance(cell, str) or not cell.strip() for cell in row):
            raise ValueError('each work row needs a nonempty time/range and work description')
        # A table cell stays on one physical line; numeric pipe entities remain
        # literal characters to the reader rather than becoming column breaks.
        cells = [' '.join(cell.splitlines()).strip().replace('|', '&#124;') for cell in row]
        lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)
