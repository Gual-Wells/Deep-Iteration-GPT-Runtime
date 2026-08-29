"""Structural parsing and native completion for DIGR 5.0.0-Berta2.

This module is deliberately *not* a workload planner.  It resolves only the
structural part of an already-routed EXECUTING invocation:

* full-width/ASCII punctuation in the invocation header is canonicalized;
* canonical relative parameter order is enforced;
* explicit labels and S/D/V/L markers are anchors;
* a bare numeric token can never become T/t;
* positional values are accepted only when a single legal mapping exists.

The parser never invents workload values. Missing task-scale values remain
``None`` until a model-owned native completion is supplied. Deterministic code
then validates that completion without choosing it.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
import re
from typing import Any, Mapping
from .duration import parse_canonical_duration_seconds, has_duration_semantics
from .validation import (
    require_binary, require_finite_nonnegative_number, require_isolation_level,
    require_nonnegative_int,
)

_PUNCT = str.maketrans({'（':'(', '）':')', '，':',', '：':':'})
_INT = re.compile(r'^\s*\d+\s*$')
_LABEL = re.compile(r'^\s*([A-Za-z]+)\s*=\s*(.*?)\s*$')
_MARKER = re.compile(r'^\s*([SDVL])(?:\((.*)\))?\s*$', re.S)
_PROFILE = re.compile(r'^\s*profile\s*=\s*(adaptive|standard|自适应|标准)\s*$', re.I)
_TIME_POLICY = re.compile(r'^\s*(min|target)\s*=\s*(.*?)\s*$', re.I)
_SOURCE_POLICY = re.compile(r'^\s*source\s*=\s*(auto|required|off)\s*$', re.I)


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

    def __post_init__(self):
        for name in ('n', 'r'):
            value = getattr(self, name)
            if value is not None:
                require_nonnegative_int(f'S.{name}', value)
        if self.t_seconds is not None:
            require_finite_nonnegative_number('S.t_seconds', self.t_seconds)
        require_binary('S.b', self.b)

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
    source_policy: str = 'required'
    V_o: int | None = None

    def __post_init__(self):
        if not isinstance(self.status, ResolutionStatus):
            object.__setattr__(self, 'status', ResolutionStatus(self.status))
        for name in ('N','R','D_s','V_o'):
            value = getattr(self, name)
            if value is not None:
                require_nonnegative_int(name, value)
        if self.T_seconds is not None:
            require_finite_nonnegative_number('T_seconds', self.T_seconds)
        require_binary('B', self.B)
        require_isolation_level('L_e', self.L_e)
        if not isinstance(self.S, SourceParameterResolution):
            raise TypeError('S must be SourceParameterResolution')
        object.__setattr__(self, 'diagnostics', tuple(self.diagnostics))
        policy = self.source_policy.lower() if isinstance(self.source_policy,str) else self.source_policy
        if policy not in ('auto','required','off'):
            raise ValueError('source_policy must be auto/required/off')
        object.__setattr__(self,'source_policy',policy)

    @property
    def missing_parameters(self) -> tuple[str, ...]:
        values = {
            'N': self.N, 'T_seconds': self.T_seconds, 'R': self.R,
            'S.n': self.S.n, 'S.t_seconds': self.S.t_seconds, 'S.r': self.S.r,
            'D_s': self.D_s, 'V_o': self.V_o,
        }
        return tuple(name for name, value in values.items() if value is None)

    def require_stable_ready(self) -> None:
        """Reject unresolved native-completion freedom at the execution gate."""
        if self.status is not ResolutionStatus.RESOLVED:
            raise ValueError('stable READY parameters must be RESOLVED')
        missing = list(self.missing_parameters)
        if missing:
            raise ValueError('stable READY parameters are not concrete: ' + ', '.join(missing))
        if self.B == 1 and self.T_seconds <= 0:
            raise ValueError('B=1 requires explicit T>0')
        if self.S.b == 1 and self.S.t_seconds <= 0:
            raise ValueError('S.b=1 requires explicit S.t>0')

    @property
    def resolved(self) -> bool:
        return self.status is ResolutionStatus.RESOLVED

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d['status'] = self.status.value
        d['diagnostics'] = list(self.diagnostics)
        return d

    @property
    def reason(self) -> str | None:
        return '; '.join(self.diagnostics) if self.diagnostics else None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> 'ParameterResolution':
        sd=d.get('S') or {}
        return cls(ResolutionStatus(d['status']),d.get('N'),d.get('T_seconds'),d.get('R'),d.get('B',0),SourceParameterResolution(sd.get('n'),sd.get('t_seconds'),sd.get('r'),sd.get('b',0)),d.get('D_s'),d.get('L_e',1),d.get('normalized_surface'),tuple(d.get('diagnostics',[])),d.get('source_policy','required'),d.get('V_o'))


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
    if param in ('N','R','n','r','D_s','V_o'):
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
        allowed={'n':'N','t':'T','r':'R','b':'B','s':'D_s','d':'D_s','v':'V_o','o':'V_o','l':'L_e','e':'L_e'}
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


def resolve_alpha4_parameter_surface(surface: str | None, semantic_normalizations: Mapping[str,str] | None=None) -> ParameterResolution:
    """Resolve the Alpha 4 structural format without stable.1 profile defaults.

    This is intentionally public for the one supported compatibility path.
    New hosts should call :func:`resolve_parameter_surface`.
    """
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


def _standard_result(
    *, T_seconds: float = 0.0, B: int = 0,
    overlay: ParameterResolution | None = None,
    normalized_surface: str | None = None,
    diagnostics: tuple[str, ...] = (),
    source_policy: str = 'auto',
) -> ParameterResolution:
    """Apply the explicit fixed standard profile.

    Source selection remains ``auto`` at the semantic layer. Numeric S minima
    default to concrete zeroes; REQUIRED versus WAIVED is a separate semantic
    disposition. D=0 is a real zero lower bound, not an off switch.
    """
    base = overlay or ParameterResolution(ResolutionStatus.RESOLVED)
    source=SourceParameterResolution(
        0 if base.S.n is None else base.S.n,
        0.0 if base.S.t_seconds is None else base.S.t_seconds,
        0 if base.S.r is None else base.S.r,
        base.S.b,
    )
    if source_policy=='off':
        source=SourceParameterResolution(0,0.0,0,0)
    result = ParameterResolution(
        ResolutionStatus.RESOLVED,
        N=2 if base.N is None else base.N,
        T_seconds=T_seconds if base.T_seconds is None else base.T_seconds,
        R=1 if base.R is None else base.R,
        B=B,
        S=source,
        D_s=0 if base.D_s is None else base.D_s,
        L_e=base.L_e,
        normalized_surface=normalized_surface if normalized_surface is not None else base.normalized_surface,
        diagnostics=tuple(base.diagnostics) + tuple(diagnostics),
        source_policy=source_policy,
        V_o=0 if base.V_o is None else base.V_o,
    )
    try:
        result.require_stable_ready()
    except ValueError as exc:
        return ParameterResolution(
            ResolutionStatus.INVALID,
            normalized_surface=result.normalized_surface,
            diagnostics=result.diagnostics + (str(exc),),
            source_policy=source_policy,
        )
    return result


def _adaptive_result(
    *, overlay: ParameterResolution | None = None,
    T_seconds: float | None = None,
    B: int | None = None,
    normalized_surface: str | None = None,
    diagnostics: tuple[str, ...] = (),
    source_policy: str = 'required',
) -> ParameterResolution:
    """Preserve structural values while leaving task-scale choices to the model."""
    base = overlay or ParameterResolution(ResolutionStatus.RESOLVED)
    source = base.S
    if source_policy == 'off':
        source = SourceParameterResolution(
            0 if source.n is None else source.n,
            0.0 if source.t_seconds is None else source.t_seconds,
            0 if source.r is None else source.r,
            source.b,
        )
    return ParameterResolution(
        ResolutionStatus.RESOLVED,
        N=base.N,
        T_seconds=base.T_seconds if T_seconds is None else T_seconds,
        R=base.R,
        B=base.B if B is None else B,
        S=source,
        D_s=base.D_s,
        L_e=base.L_e,
        normalized_surface=normalized_surface if normalized_surface is not None else base.normalized_surface,
        diagnostics=tuple(base.diagnostics) + tuple(diagnostics),
        source_policy=source_policy,
        V_o=base.V_o,
    )


def complete_native_parameters(
    structural: ParameterResolution,
    completion: Mapping[str, Any],
) -> ParameterResolution:
    """Validate model-selected task-scale values without selecting them.

    ``completion`` may use top-level ``N``, ``T_seconds``/``T``, ``R``,
    ``D_s``/``D`` and ``V_o``/``V`` plus either a nested ``S`` mapping or flat
    ``n``, ``t_seconds``/``t`` and ``r``. Explicit structural values may be
    repeated only when byte-for-byte equal after numeric normalization.
    """
    if not isinstance(structural, ParameterResolution) or structural.status is not ResolutionStatus.RESOLVED:
        raise ValueError('native completion requires a structurally resolved parameter surface')
    if not isinstance(completion, Mapping):
        raise TypeError('native completion must be a mapping')
    allowed={'N','T_seconds','T','R','D_s','D','V_o','V','S','n','t_seconds','t','r'}
    unknown=sorted(str(k) for k in completion if k not in allowed)
    if unknown:
        raise ValueError('unknown native completion field(s): ' + ', '.join(unknown))
    nested=completion.get('S',{})
    if not isinstance(nested,Mapping):
        raise TypeError('native completion S must be a mapping')
    nested_unknown=sorted(str(k) for k in nested if k not in {'n','t_seconds','t','r'})
    if nested_unknown:
        raise ValueError('unknown native completion S field(s): ' + ', '.join(nested_unknown))

    def one(*names):
        values=[]
        for name in names:
            if name in completion:values.append((name,completion[name]))
            if name in nested:values.append((f'S.{name}',nested[name]))
        if len(values)>1:
            first=values[0][1]
            if any(value!=first for _,value in values[1:]):
                raise ValueError('conflicting native completion aliases: ' + ', '.join(name for name,_ in values))
        return values[0][1] if values else None

    proposed={
        'N':one('N'),'T_seconds':one('T_seconds','T'),'R':one('R'),
        'D_s':one('D_s','D'),'V_o':one('V_o','V'),
        'S.n':one('n'),'S.t_seconds':one('t_seconds','t'),'S.r':one('r'),
    }
    for name,value in tuple(proposed.items()):
        if value is None:continue
        if name in {'T_seconds','S.t_seconds'}:
            if isinstance(value,str):
                parsed=_duration(value)
                if parsed is None:raise ValueError(f'native completion {name} requires duration semantics')
                proposed[name]=parsed
            else:
                proposed[name]=require_finite_nonnegative_number(f'native completion {name}',value)
        else:
            proposed[name]=require_nonnegative_int(f'native completion {name}',value)
    existing={
        'N':structural.N,'T_seconds':structural.T_seconds,'R':structural.R,
        'D_s':structural.D_s,'V_o':structural.V_o,
        'S.n':structural.S.n,'S.t_seconds':structural.S.t_seconds,'S.r':structural.S.r,
    }
    for name,value in existing.items():
        supplied=proposed[name]
        if value is not None and supplied is not None and value!=supplied:
            raise ValueError(f'native completion cannot override explicit {name}')
    merged={name:(existing[name] if existing[name] is not None else proposed[name]) for name in existing}
    missing=[name for name,value in merged.items() if value is None]
    if missing:
        raise ValueError('native completion is missing: ' + ', '.join(missing))
    source=SourceParameterResolution(merged['S.n'],merged['S.t_seconds'],merged['S.r'],structural.S.b)
    result=ParameterResolution(
        ResolutionStatus.RESOLVED,
        N=merged['N'],T_seconds=merged['T_seconds'],R=merged['R'],B=structural.B,
        S=source,D_s=merged['D_s'],L_e=structural.L_e,
        normalized_surface=structural.normalized_surface,
        diagnostics=tuple(structural.diagnostics)+('completion:native',),
        source_policy=structural.source_policy,V_o=merged['V_o'],
    )
    result.require_stable_ready()
    if result.source_policy=='off' and any((result.S.n,result.S.t_seconds,result.S.r,result.S.b)):
        raise ValueError('source=off requires zero completed S values')
    return result


def parameter_profile(surface: str | None) -> str:
    """Describe which structural grammar/profile selected the invocation."""
    try:
        inner = _strip_outer_group(surface)
        tokens = _split_top(inner)
    except ValueError:
        return 'invalid'
    if not tokens:return 'adaptive'
    for token in tokens:
        m=_PROFILE.fullmatch(token)
        if m:
            return 'standard' if m.group(1).lower() in {'standard','标准'} else 'adaptive'
    if len(tokens)==1 and tokens[0].strip().lower() in {'standard','标准'}:return 'standard'
    remaining=[t for t in tokens if not (_TIME_POLICY.fullmatch(t) or _SOURCE_POLICY.fullmatch(t))]
    if _uses_berta_surface(remaining):return 'berta2'
    if not remaining:return 'adaptive'
    return 'legacy-alpha4'


def _uses_berta_surface(tokens: list[str]) -> bool:
    """Detect syntax that cannot be represented by the stable.1 grammar."""
    for token in tokens:
        marker=_parse_marker(token)
        if marker is not None and marker[0]=='V':
            return True
        label=_LABEL.fullmatch(token)
        if label and (label.group(1) in {'n','t','r','b','s','o','e','V','v'}):
            return True
    return False


def _resolve_berta_parameter_surface(
    surface: str | None,
    semantic_normalizations: Mapping[str,str] | None=None,
) -> ParameterResolution:
    """Resolve Berta typed-anywhere syntax with unique-or-fail bare values.

    Explicitly typed parameters are removed from positional consideration.
    Remaining bare values retain their relative order and are accepted only
    when exactly one mapping to the remaining canonical slots exists.
    """
    try:
        inner=_strip_outer_group(surface)
        normalized='(' + inner + ')' if surface is not None else None
        tokens=_split_top(inner)
    except ValueError as exc:
        return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalize_header_surface(surface or ''),diagnostics=(str(exc),))

    explicit: dict[str,Any]={}
    source: dict[str,Any]={}
    bare: list[str]=[]

    def put(target:dict[str,Any],name:str,value:Any)->str|None:
        if name in target:
            return f'duplicate explicit parameter {name}'
        target[name]=value
        return None

    def parse_value(name:str,raw:str)->tuple[bool,Any]:
        good,value=_token_fits(name,raw,semantic_normalizations)
        return good,value

    for token in tokens:
        marker=_parse_marker(token)
        if marker is not None:
            kind,arg=marker
            if kind=='S':
                if 'S' in explicit:
                    return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=('duplicate explicit parameter S',))
                explicit['S']=True
                if arg is not None and arg.strip():
                    try: stokens=_split_top(arg)
                    except ValueError as exc:
                        return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=(f'S: {exc}',))
                    status,values,why=_resolve_segment_with_labels(stokens,source=True,semantic_normalizations=semantic_normalizations)
                    if status is not ResolutionStatus.RESOLVED:
                        return ParameterResolution(status,normalized_surface=normalized,diagnostics=(f'S: {why or "mapping failed"}',))
                    for name,value in (values or {}).items():
                        if name in source and source[name]!=value:
                            return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=(f'duplicate explicit parameter {name}',))
                        source[name]=value
                continue
            name={'D':'D_s','V':'V_o','L':'L_e'}[kind]
            default={'D_s':None,'V_o':0,'L_e':1}[name]
            value=default
            if arg is not None and arg.strip():
                inner_label=_LABEL.fullmatch(arg)
                raw=arg
                if inner_label:
                    aliases={'D_s':{'D','d','s'},'V_o':{'V','v','o'},'L_e':{'L','l','e'}}[name]
                    if inner_label.group(1) not in aliases:
                        return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=(f'{kind}() contains a value for the wrong parameter',))
                    raw=inner_label.group(2)
                good,value=parse_value(name,raw)
                if not good:
                    return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=(f'invalid {kind}() value',))
            why=put(explicit,name,value)
            if why:return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=(why,))
            continue

        label=_LABEL.fullmatch(token)
        if label is None:
            bare.append(token);continue
        raw_label,raw=label.group(1),label.group(2)
        if raw_label in {'N','T','R','B'}:
            name=raw_label;target=explicit
        elif raw_label in {'n','t','r','b'}:
            name=raw_label;target=source
        elif raw_label in {'D','d','s'}:
            name='D_s';target=explicit
        elif raw_label in {'V','v','o'}:
            name='V_o';target=explicit
        elif raw_label in {'L','l','e'}:
            name='L_e';target=explicit
        else:
            return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=(f'unknown parameter label: {raw_label}',))
        good,value=parse_value(name,raw)
        if not good:
            if name in {'T','t'} and _count(raw,semantic_normalizations) is not None:
                why=f'{name} requires explicit duration semantics; bare numeric is forbidden'
            else: why=f'invalid value for {name}: {raw}'
            return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=(why,))
        why=put(target,name,value)
        if why:return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=(why,))

    # S(...) and flat source labels describe the same namespace; repeated
    # values are still duplicates rather than harmless aliases.
    if explicit.get('S') and any(
        _LABEL.fullmatch(t) and _LABEL.fullmatch(t).group(1) in {'n','t','r','b'}
        for t in tokens
    ):
        return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=('S() cannot be combined with flat source labels',))

    slots=('N','T','R','B','D_s','V_o','L_e')
    available=[name for name in slots if name not in explicit]
    from itertools import combinations
    candidates=[]
    for chosen in combinations(available,len(bare)) if len(bare)<=len(available) else ():
        values=dict(explicit);ok=True
        for name,raw in zip(chosen,bare):
            good,value=parse_value(name,raw)
            if not good:ok=False;break
            values[name]=value
        if ok:candidates.append(values)
    unique=[];seen=set()
    for candidate in candidates:
        key=tuple(sorted((k,str(v)) for k,v in candidate.items() if k!='S'))
        if key not in seen:seen.add(key);unique.append(candidate)
    if len(unique)!=1:
        if not unique:
            why='no legal mapping remains for unlabeled parameters'
            status=ResolutionStatus.INVALID
        else:
            mappings=[]
            for candidate in unique[:12]:
                mapped=[name for name in slots if name in candidate and name not in explicit]
                mappings.append('['+','.join(mapped)+']')
            why='ambiguous unlabeled parameters; candidates: ' + ', '.join(mappings)
            status=ResolutionStatus.AMBIGUOUS
        return ParameterResolution(status,normalized_surface=normalized,diagnostics=(why,))
    values=unique[0]
    src=SourceParameterResolution(source.get('n'),source.get('t'),source.get('r'),source.get('b',0))
    result=ParameterResolution(
        ResolutionStatus.RESOLVED,
        N=values.get('N'),T_seconds=values.get('T'),R=values.get('R'),B=values.get('B',0),
        S=src,D_s=values.get('D_s'),L_e=values.get('L_e',1),
        normalized_surface=normalized,diagnostics=('profile:berta2','typed-anywhere:unique'),
        source_policy='required',V_o=values.get('V_o'),
    )
    return result


def resolve_stable_parameter_surface(surface: str | None, semantic_normalizations: Mapping[str,str] | None=None) -> ParameterResolution:
    """Resolve Berta2 structure while preserving Alpha4 invocation meaning.

    Omitted task-scale values stay unresolved for native semantic completion.
    The fixed N2/R1/no-time profile is selected only by explicit ``standard``
    or ``profile=standard``. A lone duration remains Alpha4 soft T; only
    ``min=`` creates a hard minimum. Policy tokens are removed before Berta2
    typed-anywhere dispatch so they compose with V and flat nested labels.
    """
    try:
        inner = _strip_outer_group(surface)
        normalized = '(' + inner + ')' if surface is not None else None
        tokens = _split_top(inner)
    except ValueError as exc:
        return ParameterResolution(
            ResolutionStatus.INVALID,
            normalized_surface=normalize_header_surface(surface or ''),
            diagnostics=(str(exc),),
        )

    # Legacy shorthand remains accepted, but selecting the fixed profile is
    # explicit. ``adaptive`` may be written explicitly for clarity.
    bare_profile=None
    if len(tokens)==1 and tokens[0].strip().lower() in {'standard','标准','adaptive','自适应'}:
        bare_profile=tokens[0].strip().lower();tokens=[]

    time_policy: tuple[str, float] | None = None
    remaining: list[str] = []
    profile_name: str | None = None
    source_policy: str | None = None
    saw_source_policy = False
    for token in tokens:
        profile=_PROFILE.fullmatch(token)
        if profile:
            if profile_name is not None:
                return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=('duplicate profile selector',))
            value=profile.group(1).lower()
            profile_name='standard' if value in {'standard','标准'} else 'adaptive'
            continue
        policy = _TIME_POLICY.fullmatch(token)
        if policy:
            if time_policy is not None:
                return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=('multiple min/target time policies',))
            seconds = _duration(policy.group(2), semantic_normalizations)
            if seconds is None:
                return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=(f'{policy.group(1).lower()} requires explicit duration semantics',))
            time_policy = (policy.group(1).lower(), seconds)
            continue
        source = _SOURCE_POLICY.fullmatch(token)
        if source:
            if saw_source_policy:
                return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=('duplicate source policy',))
            saw_source_policy=True
            source_policy=source.group(1).lower()
            continue
        remaining.append(token)

    if bare_profile is not None:
        profile_name='standard' if bare_profile in {'standard','标准'} else 'adaptive'

    structural_surface='(' + ','.join(remaining) + ')'
    if _uses_berta_surface(remaining):
        overlay=_resolve_berta_parameter_surface(structural_surface,semantic_normalizations)
    else:
        overlay=resolve_alpha4_parameter_surface(structural_surface,semantic_normalizations)
    if overlay.status is not ResolutionStatus.RESOLVED:
        return ParameterResolution(overlay.status,normalized_surface=normalized,diagnostics=overlay.diagnostics)

    if time_policy is not None and (overlay.T_seconds is not None or overlay.B!=0):
        return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=('min/target cannot be combined with explicit T/B',))
    policy_name,seconds=(time_policy if time_policy is not None else (None,None))
    hard=1 if policy_name=='min' else (0 if policy_name=='target' else overlay.B)
    if hard==1 and seconds==0:
        return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=('hard time minimum must be greater than zero',))
    chosen_source=source_policy or ('auto' if profile_name=='standard' else 'required')
    if chosen_source=='off' and any(x not in (None,0,0.0) for x in (overlay.S.n,overlay.S.t_seconds,overlay.S.r,overlay.S.b)):
        return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=('source=off requires zero S parameters',))

    diagnostics=[]
    if profile_name=='standard':diagnostics.append('profile:standard')
    elif _uses_berta_surface(remaining):diagnostics.append('profile:berta2')
    elif remaining:diagnostics.append('profile:legacy-alpha4')
    else:diagnostics.append('profile:adaptive')
    if remaining and not _uses_berta_surface(remaining) and (overlay.T_seconds is not None or overlay.B!=0):
        diagnostics.append('legacy T/B accepted; bare duration remains soft; prefer min= for hard or target= for explicit soft')
    if policy_name is not None:diagnostics.append(f'time-policy:{policy_name}')
    diagnostics.append(f'source-policy:{chosen_source}')

    if profile_name=='standard':
        return _standard_result(
            T_seconds=0.0 if seconds is None else seconds,B=hard,
            overlay=overlay,normalized_surface=normalized,
            diagnostics=tuple(diagnostics),source_policy=chosen_source,
        )
    return _adaptive_result(
        overlay=overlay,T_seconds=seconds,B=hard,
        normalized_surface=normalized,diagnostics=tuple(diagnostics),
        source_policy=chosen_source,
    )


def resolve_parameter_surface(surface: str | None, semantic_normalizations: Mapping[str,str] | None=None) -> ParameterResolution:
    """Backward-compatible Alpha 4 entry point used by legacy run sessions."""
    return resolve_alpha4_parameter_surface(surface,semantic_normalizations)
