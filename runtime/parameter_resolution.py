"""Deterministic parameter-format resolution for DIGR 5.0 Alpha 7.

Public order is N < T < R < B < S < D.  L is no longer a public parameter:
D isolation uses an internal fixed L1 baseline.  A bare numeric token can never
become T/t, and positional/labeled mappings must be unique.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
import re
from typing import Any, Mapping
from .duration import parse_canonical_duration_seconds, has_duration_semantics
from .validation import require_binary, require_nonnegative_int

_PUNCT = str.maketrans({'（':'(', '）':')', '，':',', '：':':'})
_INT = re.compile(r'^\s*\d+\s*$')
_LABEL = re.compile(r'^\s*([A-Za-z]+)\s*=\s*(.*?)\s*$')
_MARKER = re.compile(r'^\s*([SD])(?:\((.*)\))?\s*$', re.S)


class ResolutionStatus(str, Enum):
    RESOLVED='RESOLVED'; AMBIGUOUS='AMBIGUOUS'; INVALID='INVALID'


@dataclass(frozen=True)
class SourceParameterResolution:
    n:int|None=None
    t_seconds:float|None=None
    r:int|None=None
    b:int=1
    def __post_init__(self):
        for name in ('n','r'):
            value=getattr(self,name)
            if value is not None: require_nonnegative_int(name,value)
        require_binary('b',self.b)
    def to_dict(self)->dict[str,Any]: return asdict(self)


@dataclass(frozen=True)
class ParameterResolution:
    status:ResolutionStatus
    N:int|None=None
    T_seconds:float|None=None
    R:int|None=None
    B:int=1
    S:SourceParameterResolution=SourceParameterResolution()
    D_s:int|None=None
    normalized_surface:str|None=None
    diagnostics:tuple[str,...]=()

    def __post_init__(self):
        if not isinstance(self.status,ResolutionStatus): object.__setattr__(self,'status',ResolutionStatus(self.status))
        for name in ('N','R','D_s'):
            value=getattr(self,name)
            if value is not None: require_nonnegative_int(name,value)
        require_binary('B',self.B)
        if not isinstance(self.S,SourceParameterResolution): raise TypeError('S must be SourceParameterResolution')
        object.__setattr__(self,'diagnostics',tuple(self.diagnostics))

    @property
    def resolved(self)->bool: return self.status is ResolutionStatus.RESOLVED
    @property
    def reason(self)->str|None: return '; '.join(self.diagnostics) if self.diagnostics else None
    def to_dict(self)->dict[str,Any]:
        d=asdict(self);d['status']=self.status.value;return d

    @classmethod
    def from_dict(cls,d:dict[str,Any])->'ParameterResolution':
        sd=d.get('S') or {}
        return cls(
            ResolutionStatus(d['status']),d.get('N'),d.get('T_seconds'),d.get('R'),d.get('B',1),
            SourceParameterResolution(sd.get('n'),sd.get('t_seconds'),sd.get('r'),sd.get('b',1)),
            d.get('D_s'),d.get('normalized_surface'),tuple(d.get('diagnostics',[])),
        )


def normalize_header_surface(text:str)->str:
    if not isinstance(text,str): raise TypeError('parameter surface must be str')
    return text.translate(_PUNCT)


def _strip_outer_group(surface:str|None)->str:
    if surface is None:return ''
    s=normalize_header_surface(surface).strip()
    if not s:return ''
    if s[0]=='(':
        if len(s)<2 or s[-1]!=')':raise ValueError('parameter surface is not a complete parenthesized group')
        return s[1:-1].strip()
    return s


def _split_top(text:str)->list[str]:
    if not text.strip():return []
    out=[];buf=[];depth=0
    for ch in text:
        if ch=='(':
            depth+=1;buf.append(ch)
        elif ch==')':
            depth-=1
            if depth<0:raise ValueError('unexpected closing parenthesis')
            buf.append(ch)
        elif ch==',' and depth==0:
            token=''.join(buf).strip()
            if not token:raise ValueError('empty parameter token')
            out.append(token);buf=[]
        else:buf.append(ch)
    if depth!=0:raise ValueError('unbalanced parameter group')
    token=''.join(buf).strip()
    if not token:raise ValueError('empty parameter token')
    out.append(token);return out


def _canonical_scalar(token:str,semantic_normalizations:Mapping[str,str]|None=None)->str:
    raw=token.strip()
    if semantic_normalizations is None or raw not in semantic_normalizations:return raw
    value=semantic_normalizations[raw]
    if not isinstance(value,str) or not value.strip():raise ValueError('semantic normalization values must be non-empty text')
    canon=value.strip()
    if _INT.fullmatch(canon) or has_duration_semantics(canon):return canon
    raise ValueError(f'semantic normalization for {raw!r} must yield canonical count or duration text')


def _count(token:str,semantic_normalizations=None)->int|None:
    token=_canonical_scalar(token,semantic_normalizations)
    return int(token.strip()) if _INT.fullmatch(token) else None


def _duration(token:str,semantic_normalizations=None)->float|None:
    token=_canonical_scalar(token,semantic_normalizations)
    return parse_canonical_duration_seconds(token) if has_duration_semantics(token) else None


def _token_fits(param:str,token:str,semantic_normalizations=None)->tuple[bool,Any]:
    if param in ('N','R','n','r','D_s'):
        v=_count(token,semantic_normalizations);return v is not None,v
    if param in ('T','t'):
        v=_duration(token,semantic_normalizations);return v is not None,v
    if param in ('B','b'):
        v=_count(token,semantic_normalizations);return v in (0,1),v
    raise AssertionError(param)


def _resolve_positional(tokens:list[str],*,source:bool=False,semantic_normalizations=None)->tuple[ResolutionStatus,dict[str,Any]|None]:
    base=['n','t','r'] if source else ['N','T','R'];binary='b' if source else 'B'
    if len(tokens)>4:return ResolutionStatus.INVALID,None
    if not tokens:return ResolutionStatus.RESOLVED,{binary:1}
    if len(tokens)==4:
        param_sets=[base+[binary]]
    else:
        from itertools import combinations
        param_sets=[list(c) for c in combinations(base,len(tokens))]
    candidates=[]
    for params in param_sets:
        vals={binary:1};ok=True
        for p,tok in zip(params,tokens):
            good,v=_token_fits(p,tok,semantic_normalizations)
            if not good:ok=False;break
            vals[p]=v
        if ok:candidates.append(vals)
    uniq=[];seen=set()
    for c in candidates:
        key=tuple(sorted(c.items()))
        if key not in seen:seen.add(key);uniq.append(c)
    if len(uniq)==1:return ResolutionStatus.RESOLVED,uniq[0]
    if not uniq:return ResolutionStatus.INVALID,None
    return ResolutionStatus.AMBIGUOUS,None


def _parse_labeled(token:str,*,source:bool=False,semantic_normalizations=None)->tuple[str,Any]|None:
    m=_LABEL.fullmatch(token)
    if not m:return None
    label,raw=m.group(1),m.group(2)
    if source:
        canon={'n':'n','t':'t','r':'r','b':'b'}.get(label.lower())
    else:
        canon={'n':'N','t':'T','r':'R','b':'B','s':'D_s','d':'D_s'}.get(label.lower())
        if label in ('N','T','R','B'):canon=label
    if canon is None:raise ValueError(f'unknown parameter label: {label}')
    good,value=_token_fits(canon,raw,semantic_normalizations)
    if not good:
        if canon in ('T','t') and _count(raw,semantic_normalizations) is not None:
            raise ValueError(f'{canon} requires explicit duration semantics; bare numeric is forbidden')
        raise ValueError(f'invalid value for {canon}: {raw}')
    return canon,value


def _resolve_segment_with_labels(tokens:list[str],*,source:bool=False,semantic_normalizations=None):
    base=['n','t','r','b'] if source else ['N','T','R','B'];binary='b' if source else 'B'
    parsed=[];seen_labels=set()
    for tok in tokens:
        try:lab=_parse_labeled(tok,source=source,semantic_normalizations=semantic_normalizations)
        except ValueError as exc:return ResolutionStatus.INVALID,None,str(exc)
        if lab is not None:
            if lab[0] in seen_labels:return ResolutionStatus.INVALID,None,f'duplicate explicit parameter {lab[0]}'
            seen_labels.add(lab[0])
        parsed.append((tok,lab))
    if not any(lab is not None for _,lab in parsed):
        status,vals=_resolve_positional(tokens,source=source,semantic_normalizations=semantic_normalizations)
        return status,vals,None
    candidates=[]
    def walk(i,last_idx,used,vals):
        if i==len(parsed):
            out=dict(vals);out.setdefault(binary,1);candidates.append(out);return
        tok,lab=parsed[i]
        if lab is not None:
            p,v=lab
            if p not in base:return
            idx=base.index(p)
            if idx<=last_idx or p in used:return
            walk(i+1,idx,used|{p},{**vals,p:v});return
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


def _parse_marker(token:str)->tuple[str,str|None]|None:
    m=_MARKER.fullmatch(token);return (m.group(1),m.group(2)) if m else None


def _tail_anchor(token:str)->bool:
    if _parse_marker(token) is not None:return True
    m=_LABEL.fullmatch(token)
    return bool(m and m.group(1).lower() in {'s','d'})


def _resolve_d_tail(tokens:list[str],*,semantic_normalizations=None)->tuple[ResolutionStatus,int|None,str|None]:
    if not tokens:return ResolutionStatus.RESOLVED,None,None
    if len(tokens)>1:return ResolutionStatus.INVALID,None,'too many D-tail parameters'
    tok=tokens[0]
    mark=_parse_marker(tok)
    if mark is not None:
        kind,arg=mark
        if kind=='S':return ResolutionStatus.INVALID,None,'S marker is out of canonical order'
        if arg is None or not arg.strip():return ResolutionStatus.RESOLVED,None,None
        try:lab=_parse_labeled(arg,source=False,semantic_normalizations=semantic_normalizations)
        except ValueError as exc:return ResolutionStatus.INVALID,None,str(exc)
        if lab is not None:
            if lab[0]!='D_s':return ResolutionStatus.INVALID,None,'D() contains a value for the wrong parameter'
            return ResolutionStatus.RESOLVED,lab[1],None
        good,value=_token_fits('D_s',arg,semantic_normalizations)
        return (ResolutionStatus.RESOLVED,value,None) if good else (ResolutionStatus.INVALID,None,'invalid D() value')
    try:lab=_parse_labeled(tok,source=False,semantic_normalizations=semantic_normalizations)
    except ValueError as exc:return ResolutionStatus.INVALID,None,str(exc)
    if lab is not None:
        if lab[0]!='D_s':return ResolutionStatus.INVALID,None,f'{lab[0]} is out of the D tail scope'
        return ResolutionStatus.RESOLVED,lab[1],None
    good,value=_token_fits('D_s',tok,semantic_normalizations)
    return (ResolutionStatus.RESOLVED,value,None) if good else (ResolutionStatus.INVALID,None,'invalid D tail value')


def resolve_parameter_surface(surface:str|None,semantic_normalizations:Mapping[str,str]|None=None)->ParameterResolution:
    try:
        inner=_strip_outer_group(surface)
        normalized='('+inner+')' if surface is not None else None
        tokens=_split_top(inner)
    except ValueError as exc:
        return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalize_header_surface(surface or ''),diagnostics=(str(exc),))
    if not tokens:return ParameterResolution(ResolutionStatus.RESOLVED,normalized_surface=normalized)

    boundary=next((i for i,tok in enumerate(tokens) if _tail_anchor(tok)),None)
    if boundary is None:
        if len(tokens)<=4:main_tokens=tokens;tail_tokens=[]
        else:
            main_tokens=tokens[:4];tail_tokens=tokens[4:]
            if len(tail_tokens)>1:
                return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=('too many positional parameters',))
    else:
        main_tokens=tokens[:boundary];tail_tokens=tokens[boundary:]

    m_status,mvals,mwhy=_resolve_segment_with_labels(main_tokens,source=False,semantic_normalizations=semantic_normalizations)
    if m_status is not ResolutionStatus.RESOLVED:
        return ParameterResolution(m_status,normalized_surface=normalized,diagnostics=((mwhy or 'main parameter mapping failed'),))
    assert mvals is not None

    svals={'b':1}
    if tail_tokens:
        mark=_parse_marker(tail_tokens[0])
        if mark is not None and mark[0]=='S':
            arg=mark[1]
            if arg is not None and arg.strip():
                try:stoks=_split_top(arg)
                except ValueError as exc:return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=(f'S: {exc}',))
                s_status,parsed,swhy=_resolve_segment_with_labels(stoks,source=True,semantic_normalizations=semantic_normalizations)
                if s_status is not ResolutionStatus.RESOLVED:
                    return ParameterResolution(s_status,normalized_surface=normalized,diagnostics=(f'S: {swhy or "mapping failed"}',))
                svals.update(parsed or {})
            tail_tokens=tail_tokens[1:]
        elif any((_parse_marker(x) or ('',None))[0]=='S' for x in tail_tokens[1:]):
            return ParameterResolution(ResolutionStatus.INVALID,normalized_surface=normalized,diagnostics=('S marker is out of canonical order',))

    d_status,D_s,dwhy=_resolve_d_tail(tail_tokens,semantic_normalizations=semantic_normalizations)
    if d_status is not ResolutionStatus.RESOLVED:
        return ParameterResolution(d_status,normalized_surface=normalized,diagnostics=((dwhy or 'D tail mapping failed'),))

    S=SourceParameterResolution(n=svals.get('n'),t_seconds=svals.get('t'),r=svals.get('r'),b=svals.get('b',1))
    used=[]
    if semantic_normalizations:
        for raw,canon in semantic_normalizations.items():
            if raw in inner:used.append(f'semantic-normalization:{raw}=>{canon}')
    return ParameterResolution(
        ResolutionStatus.RESOLVED,N=mvals.get('N'),T_seconds=mvals.get('T'),R=mvals.get('R'),B=mvals.get('B',1),
        S=S,D_s=D_s,normalized_surface=normalized,diagnostics=tuple(used),
    )
