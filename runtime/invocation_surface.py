"""Deterministic DIGR 5.0 stable repository-surface classification.

The local router intentionally over-captures exact-uppercase ``DIGR`` and
``深度迭代`` prefixes.  After the pinned repository startup slice is available,
this module returns one of four states:

* EXECUTING - structurally clear invocation shell with non-empty task;
* HELP      - exact help command;
* NATIVE    - broad-router capture that is ordinary discussion, not a call;
* INVALID   - clear attempt to invoke DIGR whose invocation shell is broken.

No parameter meaning or task semantics are interpreted here.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from hashlib import sha256
from typing import Any
from .validation import require_nonempty_text

_PUNCT = str.maketrans({'（':'(', '）':')', '，':',', '：':':'})


class InvocationKind(str, Enum):
    EXECUTING = 'EXECUTING'
    HELP = 'HELP'
    NATIVE = 'NATIVE'
    INVALID = 'INVALID'


@dataclass(frozen=True)
class InvocationSurface:
    kind: InvocationKind
    alias: str
    raw_message_sha256: str
    parameter_surface: str | None = None
    task_raw: str | None = None
    reason: str | None = None

    def __post_init__(self):
        if not isinstance(self.kind, InvocationKind):
            object.__setattr__(self, 'kind', InvocationKind(self.kind))
        alias = require_nonempty_text('alias', self.alias)
        if alias not in ('DIGR', '深度迭代'):
            raise ValueError('unsupported DIGR alias')
        object.__setattr__(self, 'alias', alias)
        digest = require_nonempty_text('raw_message_sha256', self.raw_message_sha256).lower()
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('raw_message_sha256 must be 64 lowercase hex characters')
        object.__setattr__(self, 'raw_message_sha256', digest)
        if self.kind is InvocationKind.EXECUTING:
            if self.task_raw is None or not self.task_raw.strip():
                raise ValueError('executing invocation requires a non-empty task')
        elif self.task_raw is not None:
            raise ValueError('non-executing invocation cannot carry task_raw')
        if self.reason is not None and not self.reason.strip():
            raise ValueError('reason must be non-empty when present')

    @property
    def executing(self) -> bool:
        return self.kind is InvocationKind.EXECUTING

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self); d['kind'] = self.kind.value; return d


def _message_digest(message: str) -> str:
    return sha256(message.encode('utf-8')).hexdigest()


def _alias_at_head(message: str) -> tuple[str, str] | None:
    s = message.lstrip()
    if s.startswith('DIGR'):
        return 'DIGR', s[4:]
    if s.startswith('深度迭代'):
        return '深度迭代', s[len('深度迭代'):]
    return None


def _normalize_header_char(ch: str) -> str:
    return ch.translate(_PUNCT)


def _consume_group_mixed(text: str) -> tuple[str, str] | None:
    """Consume a group after punctuation normalization.

    Full-width/ASCII opening and closing parentheses may be mixed because only
    the invocation header is canonicalized. The task body is never rewritten.
    """
    if not text or _normalize_header_char(text[0]) != '(':
        return None
    depth = 0
    for i, raw in enumerate(text):
        ch = _normalize_header_char(raw)
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth < 0:
                return None
            if depth == 0:
                return text[:i+1], text[i+1:]
    return None


def classify_surface(message: str) -> InvocationSurface | None:
    if not isinstance(message, str):
        raise TypeError('message must be str')
    hit = _alias_at_head(message)
    if hit is None:
        return None
    alias, remainder = hit
    digest = _message_digest(message)
    if remainder.strip() == '/help':
        return InvocationSurface(InvocationKind.HELP, alias, digest)

    rest = remainder.lstrip()
    parameter_surface: str | None = None
    if rest.startswith(('(', '（')):
        consumed = _consume_group_mixed(rest)
        if consumed is None:
            return InvocationSurface(
                InvocationKind.INVALID, alias, digest,
                reason='unbalanced parameter surface',
            )
        parameter_surface, rest = consumed
        rest = rest.lstrip()

    if rest.startswith((':', '：')):
        task = rest[1:]
        if not task.strip():
            return InvocationSurface(
                InvocationKind.INVALID, alias, digest,
                parameter_surface=parameter_surface,
                reason='task is empty',
            )
        return InvocationSurface(
            InvocationKind.EXECUTING, alias, digest,
            parameter_surface=parameter_surface, task_raw=task,
        )

    if parameter_surface is not None:
        return InvocationSurface(
            InvocationKind.INVALID, alias, digest,
            parameter_surface=parameter_surface,
            reason='parameter surface requires a task separator',
        )

    # Ordinary broad-prefix phrases such as "DIGR是什么？" remain native.
    return InvocationSurface(
        InvocationKind.NATIVE, alias, digest,
        parameter_surface=parameter_surface,
        reason='broad route capture is not an invocation',
    )
