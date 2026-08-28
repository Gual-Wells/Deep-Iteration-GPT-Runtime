"""Deterministic parameter-format resolution for DIGR 5.0 stable.1.

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
from .validation import (
    require_binary, require_finite_nonnegative_number, require_isolation_level,
    require_nonnegative_int,
)

_PUNCT = str.maketrans({'（':'(', '）':')', '，':',', '：':':'})
_INT = re.compile(r'^\s*\d+\s*$')
_LABEL = re.compile(r'^\s*([A-Za-z]+)\s*=\s*(.*?)\s*$')
_MARKER = re.compile(r'^\s*([SDVL])(?:\((.*)\))?\s*$', re.S)
_PROFILE = re.compile(r'^\s*profile\s*=\s*(standard|标准)\s*$', re.I)
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
    source_policy: str = 'auto'
    V_o: int = 0

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

    def require_stable_ready(self) -> None:
        """Reject unresolved numeric freedom at the Berta1 execution gate."""
        if self.status is not ResolutionStatus.RESOLVED:
            raise ValueError('stable READY parameters must be RESOLVED')
        values = {
            'N': self.N, 'T_seconds': self.T_seconds, 'R': self.R,
            'S.n': self.S.n, 'S.t_seconds': self.S.t_seconds, 'S.r': self.S.r,
            'D_s': self.D_s,
            'V_o': self.V_o,
        }
        missing = [name for name, value in values.items() if value is None]
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
        return cls(ResolutionStatus(d['status']),d.get('N'),d.get('T_seconds'),d.get('R'),d.get('B',0),SourceParameterResolution(sd.get('n'),sd.get('t_seconds'),sd.get('r'),sd.get('b',0)),d.get('D_s'),d.get('L_e',1),d.get('normalized_surface'),tuple(d.get('diagnostics',[])),d.get('source_policy','auto'),d.get('V_o',0))


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
    """Apply the stable.1 standard profile without inventing source work.

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
        V_o=base.V_o,
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


def parameter_profile(surface: str | None) -> str:
    """Return the deterministic stable.1 profile selected by a surface."""
    try:
        inner = _strip_outer_group(surface)
        tokens = _split_top(inner)
    except ValueError:
        return 'invalid'
    if not tokens:
        return 'standard'
    if _uses_berta_surface(tokens):
        return 'berta1'
    if len(tokens) == 1 and (
        tokens[0].strip().lower() in {'standard', '标准'}
        or _PROFILE.fullmatch(tokens[0])
        or _TIME_POLICY.fullmatch(tokens[0])
        or _SOURCE_POLICY.fullmatch(tokens[0])
        or _duration(tokens[0]) is not None
    ):
        return 'standard'
    if any(_PROFILE.fullmatch(token) or _TIME_POLICY.fullmatch(token) or _SOURCE_POLICY.fullmatch(token) for token in tokens):
        return 'standard'
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
    src=SourceParameterResolution(source.get('n',0),source.get('t',0.0),source.get('r',0),source.get('b',0))
    result=ParameterResolution(
        ResolutionStatus.RESOLVED,
        N=values.get('N',2),T_seconds=values.get('T',0.0),R=values.get('R',1),B=values.get('B',0),
        S=src,D_s=values.get('D_s',0),L_e=values.get('L_e',1),
        normalized_surface=normalized,diagnostics=('profile:berta1','typed-anywhere:unique'),
        source_policy='auto',V_o=values.get('V_o',0),
    )
    try:result.require_stable_ready()
    except ValueError as exc:
        return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=result.diagnostics+(str(exc),))
    return result


def resolve_stable_parameter_surface(surface: str | None, semantic_normalizations: Mapping[str,str] | None=None) -> ParameterResolution:
    """Resolve stable.1 profiles, with Alpha 4 as the sole legacy fallback.

    Stable forms are deliberately small:

    * no parameters or ``standard`` -> N=2, R=1, T=0 soft, D=0, L=1;
    * one bare duration or ``min=<duration>`` -> hard time minimum;
    * ``target=<duration>`` -> soft time target.

    All other surfaces are passed through the Alpha 4 unique-or-fail parser.
    Legacy ``T``/``B`` remains accepted but is explicitly diagnosed. A hard
    policy with zero time is rejected during this local preflight parser.
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

    if _uses_berta_surface(tokens):
        return _resolve_berta_parameter_surface(surface,semantic_normalizations)

    if not tokens:
        return _standard_result(normalized_surface=normalized, diagnostics=('profile:standard',))

    if len(tokens) == 1 and tokens[0].strip().lower() in {'standard', '标准'}:
        return _standard_result(normalized_surface=normalized, diagnostics=('profile:standard',))

    stable_policy: tuple[str, float] | None = None
    remaining: list[str] = []
    saw_profile = False
    source_policy = 'auto'
    saw_source_policy = False
    for token in tokens:
        if _PROFILE.fullmatch(token):
            if saw_profile:
                return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=('duplicate profile selector',))
            saw_profile = True
            continue
        policy = _TIME_POLICY.fullmatch(token)
        if policy:
            if stable_policy is not None:
                return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=('multiple min/target time policies',))
            seconds = _duration(policy.group(2), semantic_normalizations)
            if seconds is None:
                return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=(f'{policy.group(1).lower()} requires explicit duration semantics',))
            stable_policy = (policy.group(1).lower(), seconds)
            continue
        source = _SOURCE_POLICY.fullmatch(token)
        if source:
            if saw_source_policy:
                return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=('duplicate source policy',))
            saw_source_policy=True
            source_policy=source.group(1).lower()
            continue
        remaining.append(token)

    # A lone duration is the compact hard-minimum spelling in stable.1.
    if not saw_profile and stable_policy is None and not saw_source_policy and len(tokens) == 1:
        seconds = _duration(tokens[0], semantic_normalizations)
        if seconds is not None:
            if seconds == 0:
                return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=('hard time minimum must be greater than zero',))
            return _standard_result(T_seconds=seconds, B=1, normalized_surface=normalized, diagnostics=('profile:standard', 'time-policy:min'))

    if saw_profile or stable_policy is not None or saw_source_policy:
        legacy_surface = '(' + ','.join(remaining) + ')'
        overlay = resolve_alpha4_parameter_surface(legacy_surface, semantic_normalizations)
        if overlay.status is not ResolutionStatus.RESOLVED:
            return ParameterResolution(overlay.status, normalized_surface=normalized, diagnostics=overlay.diagnostics)
        if overlay.T_seconds is not None or overlay.B != 0:
            return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=('min/target cannot be combined with legacy T/B',))
        if source_policy=='off' and any(x not in (None,0,0.0) for x in (overlay.S.n,overlay.S.t_seconds,overlay.S.r,overlay.S.b)):
            return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=('source=off requires zero S parameters',))
        policy_name, seconds = stable_policy or ('target', 0.0)
        hard = 1 if policy_name == 'min' else 0
        if hard and seconds == 0:
            return ParameterResolution(ResolutionStatus.INVALID, normalized_surface=normalized, diagnostics=('hard time minimum must be greater than zero',))
        return _standard_result(
            T_seconds=seconds, B=hard, overlay=overlay,
            normalized_surface=normalized,
            diagnostics=('profile:standard', f'time-policy:{policy_name}',f'source-policy:{source_policy}'),
            source_policy=source_policy,
        )

    legacy = resolve_alpha4_parameter_surface(surface, semantic_normalizations)
    if legacy.status is not ResolutionStatus.RESOLVED:
        return legacy
    warnings = ['profile:legacy-alpha4']
    # T/B compatibility is deliberately visible instead of silently becoming
    # the preferred stable.1 spelling.
    if legacy.T_seconds is not None or legacy.B != 0:
        warnings.append('legacy T/B accepted; prefer min=<duration> or target=<duration>')
    return _standard_result(
        T_seconds=0.0 if legacy.T_seconds is None else legacy.T_seconds,
        B=legacy.B,
        overlay=legacy,
        normalized_surface=legacy.normalized_surface,
        diagnostics=tuple(warnings),
        source_policy='auto',
    )


def resolve_parameter_surface(surface: str | None, semantic_normalizations: Mapping[str,str] | None=None) -> ParameterResolution:
    """Backward-compatible Alpha 4 entry point used by legacy run sessions."""
    return resolve_alpha4_parameter_surface(surface,semantic_normalizations)
