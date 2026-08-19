"""Deterministic parameter-format resolution for DIGR 5.0 Alpha 2.

This module is deliberately *not* a workload planner.  It resolves only the
structural part of an already-routed EXECUTING invocation:

* full-width/ASCII punctuation in the invocation header is canonicalized;
* canonical relative parameter order is enforced;
* explicit labels and S/D/L markers are anchors;
* a bare numeric token can never become T/t;
* positional values are accepted only when a single legal mapping exists.

Richer natural-language understanding may classify/normalize a token before it
is passed here, but the final mapping is deterministic and unique-or-fail.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
import re
from typing import Any, Mapping
from .duration import parse_canonical_duration_seconds, has_duration_semantics
from .validation import require_binary, require_isolation_level, require_nonnegative_int

_PUNCT = str.maketrans({'（':'(', '）':')', '，':',', '：':':'})
_INT = re.compile(r'^\s*\d+\s*$')
_LABEL = re.compile(r'^\s*([A-Za-z]+)\s*=\s*(.*?)\s*$')
_MARKER = re.compile(r'^\s*([SDL])(?:\((.*)\))?\s*$', re.S)


class ResolutionStatus(str, Enum):
    RESOLVED = 'RESOLVED'
    AMBIGUOUS = 'AMBIGUOUS'
    INVALID = 'INVALID'


@dataclass(frozen=True)
class SourceParameterResolution:
    n: int | None = None
    t_seconds: float | None = None
    r: int | None = None
    b: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParameterResolution:
    status: ResolutionStatus
    N: int | None = None
    T_seconds: float | None = None
    R: int | None = None
    B: int = 0
    S: SourceParameterResolution = SourceParameterResolution()
    D_s: int | None = None
    L_e: int = 1
    normalized_surface: str | None = None
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.status, ResolutionStatus):
            object.__setattr__(self, 'status', ResolutionStatus(self.status))
        for name in ('N','R','D_s'):
            value = getattr(self, name)
            if value is not None:
                require_nonnegative_int(name, value)
        require_binary('B', self.B)
        require_isolation_level('L_e', self.L_e)
        if not isinstance(self.S, SourceParameterResolution):
            raise TypeError('S must be SourceParameterResolution')
        object.__setattr__(self, 'diagnostics', tuple(self.diagnostics))

    @property
    def resolved(self) -> bool:
        return self.status is ResolutionStatus.RESOLVED

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d['status'] = self.status.value
        return d

    @property
    def reason(self) -> str | None:
        return '; '.join(self.diagnostics) if self.diagnostics else None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> 'ParameterResolution':
        sd=d.get('S') or {}
        return cls(ResolutionStatus(d['status']),d.get('N'),d.get('T_seconds'),d.get('R'),d.get('B',0),SourceParameterResolution(sd.get('n'),sd.get('t_seconds'),sd.get('r'),sd.get('b',0)),d.get('D_s'),d.get('L_e',1),d.get('normalized_surface'),tuple(d.get('diagnostics',[])))


def normalize_header_surface(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError('parameter surface must be str')
    return text.translate(_PUNCT)


def _strip_outer_group(surface: str | None) -> str:
    if surface is None:
        return ''
    s = normalize_header_surface(surface).strip()
    if not s:
        return ''
    if s[0] == '(':
        if len(s) < 2 or s[-1] != ')':
            raise ValueError('parameter surface is not a complete parenthesized group')
        return s[1:-1].strip()
    return s


def _split_top(text: str) -> list[str]:
    if not text.strip():
        return []
    out: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in text:
        if ch == '(':
            depth += 1
            buf.append(ch)
        elif ch == ')':
            depth -= 1
            if depth < 0:
                raise ValueError('unexpected closing parenthesis')
            buf.append(ch)
        elif ch == ',' and depth == 0:
            token = ''.join(buf).strip()
            if not token:
                raise ValueError('empty parameter token')
            out.append(token); buf=[]
        else:
            buf.append(ch)
    if depth != 0:
        raise ValueError('unbalanced parameter group')
    token = ''.join(buf).strip()
    if not token:
        raise ValueError('empty parameter token')
    out.append(token)
    return out


def _canonical_scalar(token: str, semantic_normalizations: Mapping[str,str] | None=None) -> str:
    raw=token.strip()
    if semantic_normalizations is None or raw not in semantic_normalizations:return raw
    value=semantic_normalizations[raw]
    if not isinstance(value,str) or not value.strip():raise ValueError('semantic normalization values must be non-empty text')
    canon=value.strip()
    if _INT.fullmatch(canon) or has_duration_semantics(canon):return canon
    raise ValueError(f'semantic normalization for {raw!r} must yield canonical count or duration text')

def _count(token: str, semantic_normalizations: Mapping[str,str] | None=None) -> int | None:
    token=_canonical_scalar(token,semantic_normalizations)
    if not _INT.fullmatch(token):return None
    return int(token.strip())

def _duration(token: str, semantic_normalizations: Mapping[str,str] | None=None) -> float | None:
    token=_canonical_scalar(token,semantic_normalizations)
    if not has_duration_semantics(token):return None
    return parse_canonical_duration_seconds(token)

def _token_fits(param: str, token: str, semantic_normalizations: Mapping[str,str] | None=None) -> tuple[bool, Any]:
    if param in ('N','R','n','r','D_s'):
        v = _count(token,semantic_normalizations); return (v is not None, v)
    if param in ('T','t'):
        v = _duration(token,semantic_normalizations); return (v is not None, v)
    if param in ('B','b'):
        v = _count(token,semantic_normalizations)
        return (v in (0,1), v)
    if param == 'L_e':
        v = _count(token,semantic_normalizations)
        return (v in (1,2,3), v)
    raise AssertionError(param)


def _resolve_positional(tokens: list[str], *, source: bool=False, semantic_normalizations: Mapping[str,str] | None=None) -> tuple[str, dict[str, Any] | None]:
    """Resolve one N/T/R(/B) or n/t/r(/b) positional segment."""
    base = ['n','t','r'] if source else ['N','T','R']
    binary = 'b' if source else 'B'
    if len(tokens) > 4:
        return 'INVALID', None
    if not tokens:
        return 'RESOLVED', {binary: 0}
    candidates: list[dict[str, Any]] = []
    if len(tokens) == 4:
        param_sets = [base + [binary]]
    else:
        # B/b is fixed-default when it is not explicitly present as the fourth
        # positional item.  Remaining values occupy an ordered subset of N/T/R.
        from itertools import combinations
        param_sets = [list(c) for c in combinations(base, len(tokens))]
    for params in param_sets:
        values: dict[str, Any] = {binary: 0}
        ok = True
        for p, tok in zip(params, tokens):
            good, v = _token_fits(p, tok, semantic_normalizations)
            if not good:
                ok=False; break
            values[p]=v
        if ok:
            candidates.append(values)
    # Deduplicate structurally identical candidates.
    unique: list[dict[str, Any]] = []
    seen=set()
    for c in candidates:
        key=tuple(sorted(c.items()))
        if key not in seen:
            seen.add(key); unique.append(c)
    if len(unique) == 1:
        return 'RESOLVED', unique[0]
    if len(unique) == 0:
        return 'INVALID', None
    return 'AMBIGUOUS', None


def _parse_labeled(token: str, *, source: bool=False, semantic_normalizations: Mapping[str,str] | None=None) -> tuple[str, Any] | None:
    m = _LABEL.fullmatch(token)
    if not m:
        return None
    label, raw = m.group(1), m.group(2)
    canon = label
    if source:
        allowed={'n':'n','t':'t','r':'r','b':'b'}
        canon=allowed.get(label.lower())
    else:
        allowed={'n':'N','t':'T','r':'R','b':'B','s':'D_s','d':'D_s','l':'L_e','e':'L_e'}
        canon=allowed.get(label.lower())
        if label in ('N','T','R','B'):
            canon=label
    if canon is None:
        raise ValueError(f'unknown parameter label: {label}')
    good, value = _token_fits(canon, raw, semantic_normalizations)
    if not good:
        if canon in ('T','t') and _count(raw,semantic_normalizations) is not None:
            raise ValueError(f'{canon} requires explicit duration semantics; bare numeric is forbidden')
        raise ValueError(f'invalid value for {canon}: {raw}')
    return canon, value


def _resolve_segment_with_labels(tokens: list[str], *, source: bool=False, semantic_normalizations: Mapping[str,str] | None=None) -> tuple[ResolutionStatus, dict[str, Any] | None, str | None]:
    """Resolve a mixed labeled/positional segment while preserving token order."""
    base = ['n','t','r','b'] if source else ['N','T','R','B']
    binary = 'b' if source else 'B'
    parsed=[]
    seen_labels=set()
    for tok in tokens:
        try: lab=_parse_labeled(tok,source=source,semantic_normalizations=semantic_normalizations)
        except ValueError as exc: return ResolutionStatus.INVALID,None,str(exc)
        if lab is not None:
            if lab[0] in seen_labels:return ResolutionStatus.INVALID,None,f'duplicate explicit parameter {lab[0]}'
            seen_labels.add(lab[0])
        parsed.append((tok,lab))
    if not any(lab is not None for _,lab in parsed):
        status,vals=_resolve_positional(tokens,source=source,semantic_normalizations=semantic_normalizations)
        return ResolutionStatus(status),vals,None

    candidates=[]
    def walk(i,last_idx,used,vals):
        if i==len(parsed):
            out=dict(vals);out.setdefault(binary,0);candidates.append(out);return
        tok,lab=parsed[i]
        if lab is not None:
            p,v=lab;idx=base.index(p)
            if idx<=last_idx or p in used:return
            walk(i+1,idx,used|{p},{**vals,p:v});return
        # In a partially labeled segment B/b is never inferred positionally;
        # it is a fixed default unless explicitly labeled.
        for idx,p in enumerate(base):
            if idx<=last_idx or p in used or p==binary:continue
            good,v=_token_fits(p,tok,semantic_normalizations)
            if good:walk(i+1,idx,used|{p},{**vals,p:v})
    walk(0,-1,set(),{})
    uniq=[];seen=set()
    for c in candidates:
        key=tuple(sorted(c.items()))
        if key not in seen:seen.add(key);uniq.append(c)
    if len(uniq)==1:return ResolutionStatus.RESOLVED,uniq[0],None
    if not uniq:return ResolutionStatus.INVALID,None,'no legal ordered mapping remains after explicit labels'
    return ResolutionStatus.AMBIGUOUS,None,'multiple legal ordered mappings remain'

def _parse_marker(token: str) -> tuple[str, str | None] | None:
    m=_MARKER.fullmatch(token)
    if not m:return None
    return m.group(1), m.group(2)


def _tail_anchor(token: str) -> bool:
    """Return whether a top-level token establishes the S/D/L tail boundary."""
    if _parse_marker(token) is not None:
        return True
    m = _LABEL.fullmatch(token)
    return bool(m and m.group(1).lower() in {'s', 'd', 'l', 'e'})


def _resolve_dl_tail(tokens: list[str], *, semantic_normalizations: Mapping[str,str] | None=None) -> tuple[ResolutionStatus, int | None, int, str | None]:
    """Resolve the ordered D/L tail without letting later tokens move backwards.

    D()/L() are complete positional anchors: an empty D marker occupies D with
    semantic ``s`` missing, and an empty L marker occupies L at its fixed
    default L1. Bare values may fill omitted D/L positions only when their
    placement is uniquely implied by the surrounding anchors.
    """
    if not tokens:
        return ResolutionStatus.RESOLVED, None, 1, None

    parsed: list[tuple[str, int | None, Any]] = []
    # kind, explicit position (0=D,1=L) or None for bare, explicit value
    for tok in tokens:
        mark = _parse_marker(tok)
        if mark is not None:
            k, arg = mark
            if k == 'S':
                return ResolutionStatus.INVALID, None, 1, 'S marker is out of canonical order'
            pos = 0 if k == 'D' else 1
            value: Any = None if pos == 0 else 1
            if arg is not None and arg.strip():
                try:
                    lab = _parse_labeled(arg, source=False, semantic_normalizations=semantic_normalizations)
                except ValueError as exc:
                    return ResolutionStatus.INVALID, None, 1, str(exc)
                expected = 'D_s' if pos == 0 else 'L_e'
                if lab is not None:
                    if lab[0] != expected:
                        return ResolutionStatus.INVALID, None, 1, f'{k}() contains a value for the wrong parameter'
                    value = lab[1]
                else:
                    good, value = _token_fits(expected, arg, semantic_normalizations)
                    if not good:
                        return ResolutionStatus.INVALID, None, 1, f'invalid {k}() value'
            parsed.append(('explicit', pos, value))
            continue

        try:
            lab = _parse_labeled(tok, source=False, semantic_normalizations=semantic_normalizations)
        except ValueError as exc:
            return ResolutionStatus.INVALID, None, 1, str(exc)
        if lab is not None:
            if lab[0] not in ('D_s', 'L_e'):
                return ResolutionStatus.INVALID, None, 1, f'{lab[0]} is out of the D/L tail scope'
            parsed.append(('explicit', 0 if lab[0] == 'D_s' else 1, lab[1]))
        else:
            parsed.append(('bare', None, tok))

    candidates: list[tuple[int | None, int]] = []

    def walk(i: int, last_pos: int, D_s: int | None, L_e: int) -> None:
        if i == len(parsed):
            candidates.append((D_s, L_e)); return
        kind, pos, value = parsed[i]
        if kind == 'explicit':
            assert pos is not None
            if pos <= last_pos:
                return
            if pos == 0:
                walk(i + 1, pos, value, L_e)
            else:
                walk(i + 1, pos, D_s, value)
            return
        raw = value
        for candidate_pos, param in ((0, 'D_s'), (1, 'L_e')):
            if candidate_pos <= last_pos:
                continue
            good, val = _token_fits(param, raw, semantic_normalizations)
            if not good:
                continue
            if candidate_pos == 0:
                walk(i + 1, candidate_pos, val, L_e)
            else:
                walk(i + 1, candidate_pos, D_s, val)

    walk(0, -1, None, 1)
    unique = list(dict.fromkeys(candidates))
    if len(unique) == 1:
        return ResolutionStatus.RESOLVED, unique[0][0], unique[0][1], None
    if not unique:
        return ResolutionStatus.INVALID, None, 1, 'no legal ordered D/L tail mapping'
    return ResolutionStatus.AMBIGUOUS, None, 1, 'multiple legal ordered D/L tail mappings remain'


def resolve_parameter_surface(surface: str | None, semantic_normalizations: Mapping[str,str] | None=None) -> ParameterResolution:
    try:
        inner=_strip_outer_group(surface)
        normalized='(' + inner + ')' if surface is not None else None
        tokens=_split_top(inner)
    except ValueError as exc:
        return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalize_header_surface(surface or ''), diagnostics=(str(exc),))
    if not tokens:
        return ParameterResolution(ResolutionStatus.RESOLVED, normalized_surface=normalized)

    # Find a structural boundary into S/D/L. Explicit D/L labels are anchors too.
    boundary = next((i for i,tok in enumerate(tokens) if _tail_anchor(tok)), None)
    if boundary is None:
        if len(tokens) <= 4:
            main_tokens=tokens; tail_tokens=[]
        else:
            main_tokens=tokens[:4]; tail_tokens=tokens[4:]
            if len(tail_tokens)>2:
                return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=('too many positional parameters',))
    else:
        main_tokens=tokens[:boundary]; tail_tokens=tokens[boundary:]

    m_status,mvals,mwhy=_resolve_segment_with_labels(main_tokens,source=False,semantic_normalizations=semantic_normalizations)
    if m_status is not ResolutionStatus.RESOLVED:
        return ParameterResolution(m_status, normalized_surface=normalized, diagnostics=((mwhy or 'main parameter mapping failed'),))
    assert mvals is not None

    # Optional S marker is the first tail item only. Its nested values are the
    # only place where n/t/r/b positional values live.
    svals={'b':0}
    if tail_tokens:
        mark=_parse_marker(tail_tokens[0])
        if mark is not None and mark[0]=='S':
            arg=mark[1]
            if arg is not None and arg.strip():
                try: stoks=_split_top(arg)
                except ValueError as exc:
                    return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=(f'S: {exc}',))
                s_status,parsed,swhy=_resolve_segment_with_labels(stoks,source=True,semantic_normalizations=semantic_normalizations)
                if s_status is not ResolutionStatus.RESOLVED:
                    return ParameterResolution(s_status, normalized_surface=normalized, diagnostics=(f'S: {swhy or "mapping failed"}',))
                svals.update(parsed or {})
            tail_tokens=tail_tokens[1:]
        elif any((_parse_marker(x) or ('',None))[0]=='S' for x in tail_tokens[1:]):
            return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=('S marker is out of canonical order',))

    dl_status,D_s,L_e,dlwhy=_resolve_dl_tail(tail_tokens,semantic_normalizations=semantic_normalizations)
    if dl_status is not ResolutionStatus.RESOLVED:
        return ParameterResolution(dl_status, normalized_surface=normalized, diagnostics=((dlwhy or 'D/L tail mapping failed'),))

    S=SourceParameterResolution(n=svals.get('n'),t_seconds=svals.get('t'),r=svals.get('r'),b=svals.get('b',0))
    used=[]
    if semantic_normalizations:
        for raw,canon in semantic_normalizations.items():
            if raw in inner:used.append(f'semantic-normalization:{raw}=>{canon}')
    return ParameterResolution(
        ResolutionStatus.RESOLVED,
        N=mvals.get('N'),T_seconds=mvals.get('T'),R=mvals.get('R'),B=mvals.get('B',0),
        S=S,D_s=D_s,L_e=L_e,normalized_surface=normalized,diagnostics=tuple(used),
    )
