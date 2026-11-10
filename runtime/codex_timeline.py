"""A truthful time/identity projection of supplied public DIGR facts.

No scheduler, automatic log inference, responsibility counter or clock estimator.
The same data produces a portable SVG and a responsive conversation fragment.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime
from html import escape
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata

KINDS={'M':'完整主进度','N':'主线推进','R':'整体重开','S':'来源工作面','D':'竞争性介入','V':'持续领域'}
EVENTS={'bootstrap':('⊙','自举'),'council':('◎','议会'),'send':('→','发出'),
        'receive':('↩','收到'),'decision':('◇','决定'),'apply':('✓','落实'),
        'reenter':('↻','再入'),'close':('■','关闭'),'pause':('Ⅱ','暂停'),
        'candidate':('●','候选'),'note':('·','说明')}
LINKS={'message','handling','application','reference','correlation'}
KEY=re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$')


def need(ok,message):
    if not ok:raise ValueError(message)


def scalar(value):
    return value is None or (type(value) in (int,float) and math.isfinite(value) and value>=0)


def metadata(item):
    for field in ('artifact_versions','references','unhandled'):
        if field in item:need(isinstance(item[field],list) and all(isinstance(x,str) for x in item[field]),field+' must be a list of strings')
    if 'executor' in item:need(isinstance(item['executor'],str),'executor must be a string')
    if 'domain' in item:need(isinstance(item['domain'],str) and item['domain'],'domain must be named')


def validate(data):
    need(isinstance(data,dict) and data.get('schema_version')==1,'unsupported timeline schema')
    need(data.get('mode') in ('illustration','recorded'),'declare illustration or recorded mode')
    need(data.get('title') and data.get('axis_domain'),'title and axis_domain required')
    if data['mode']=='recorded':
        origin=datetime.fromisoformat(data['origin'].replace('Z','+00:00'))
        need(origin.tzinfo is not None,'recorded origin needs an explicit timezone')
    tracks=data['tracks'];need(isinstance(tracks,list) and tracks,'no identities')
    by_id={};events={}
    for track in tracks:
        metadata(track)
        tid=track['id'];kind=track['kind']
        need(KEY.fullmatch(tid) and tid not in by_id,'invalid/duplicate identity')
        need(kind in KINDS,'unknown responsibility class')
        pattern=r'M\d{2,}' if kind=='M' else r'M\d{2,}\.'+kind+r'\d{2,}'
        need(re.fullmatch(pattern,tid),'identity needs M scope, e.g. M01.V01')
        by_id[tid]=track
        for segment in track.get('segments',[]):
            metadata(segment)
            need(scalar(segment.get('start')) and scalar(segment.get('end')),'invalid segment time')
            a,b=segment.get('start'),segment.get('end')
            need(a is None or b is None or a<=b,'segment end precedes start')
            need(segment.get('label'),'segment label required')
            if data['mode']=='recorded':need(segment.get('source_ref'),'recorded interval needs source_ref')
    for track in tracks:
        if track['kind']!='M':need(track['id'].split('.')[0] in by_id,'main scope missing')
    for event in data.get('events',[]):
        metadata(event)
        eid=event['id'];need(KEY.fullmatch(eid) and eid not in events,'invalid/duplicate event id')
        need(event['track'] in by_id or event['track']=='COMMON','event identity missing')
        need(event['kind'] in EVENTS and scalar(event.get('at')),'invalid event kind/time')
        need(event.get('label'),'event label required')
        if data['mode']=='recorded':need(event.get('source_ref'),'recorded event needs source_ref')
        events[eid]=event
    adjacency=defaultdict(list)
    for link in data.get('links',[]):
        a,b=link['from'],link['to'];kind=link['kind']
        need(a in events and b in events and a!=b and kind in LINKS,'invalid event relationship')
        if kind not in ('reference','correlation'):
            adjacency[a].append(b)
    visiting=set();done=set();order=[]
    def visit(eid):
        need(eid not in visiting,'causal relationship cycle')
        if eid in done:return
        visiting.add(eid)
        for child in adjacency[eid]:visit(child)
        visiting.remove(eid);done.add(eid);order.append(eid)
    for eid in events:visit(eid)
    # Causal order is transitive even through events whose timestamps are missing.
    # A local clock may be comparable with itself without mapping to the main axis.
    prior=defaultdict(dict)
    for eid in reversed(order):
        event=events[eid];domain=event.get('domain',data['axis_domain']);at=event.get('at')
        known=prior[eid]
        if at is not None:
            need(domain not in known or known[domain]<=at,'comparable causal time runs backwards (including transitive path)')
            known[domain]=max(known.get(domain,at),at)
        for child in adjacency[eid]:
            for key,value in known.items():prior[child][key]=max(prior[child].get(key,value),value)
    for highlight in data.get('highlights',[]):
        need(highlight.get('label') and all(eid in events for eid in highlight.get('events',[])),
             'invalid highlighted fact')
    for phase in data.get('phases',[]):
        need(scalar(phase.get('start')) and scalar(phase.get('end')) and
             phase.get('start') is not None and phase.get('end') is not None and
             phase['start']<=phase['end'],'invalid phase annotation')
    return data


def position(data,item,key):
    """Unrelated clock coordinates remain unlocated, even when numeric."""
    return item.get(key) if item.get('domain',data['axis_domain'])==data['axis_domain'] else None


def read(path):
    return validate(json.loads(Path(path).read_text(encoding='utf-8-sig')))


def short_id(tid):
    sub=str.maketrans('0123456789','₀₁₂₃₄₅₆₇₈₉')
    tail=tid.split('.')[-1]
    match=re.fullmatch(r'([A-Z])(\d+)',tail)
    return match[1]+str(int(match[2])).translate(sub) if match else tid


def prefix(data):
    return 'digr-'+hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:10]


def extent(data):
    values=[0.0]
    for track in data['tracks']:
        for segment in track.get('segments',[]):
            values.extend(v for k in ('start','end') if (v:=position(data,segment,k)) is not None)
    values.extend(v for event in data.get('events',[]) if (v:=position(data,event,'at')) is not None)
    for phase in data.get('phases',[]):values.extend((phase['start'],phase['end']))
    return max(values) or 1.0


def has_locations(data):
    return bool(data.get('phases')) or any(position(data,e,'at') is not None for e in data.get('events',[])) or any(
        position(data,s,key) is not None for t in data['tracks'] for s in t.get('segments',[]) for key in ('start','end'))


def time_scale(maximum):
    """One axis unit for the whole projection, including its responsive redraw."""
    if maximum < 1:return 1000.0,'毫秒'
    if maximum < 120:return 1.0,'秒'
    return 1.0/60,'分'


def time_label(seconds,maximum):
    multiplier,unit=time_scale(maximum)
    return f'{seconds*multiplier:.4g}{unit}'


def unlocated_facts(data):
    notes=[];events={e['id']:e for e in data.get('events',[])}
    for event in events.values():
        if position(data,event,'at') is None:notes.append(event['track']+' · '+event['label']+'（时间未定位）')
    for track in data['tracks']:
        for segment in track.get('segments',[]):
            if any(position(data,segment,key) is None for key in ('start','end')):
                notes.append(track['id']+' · '+segment['label']+'（区间不完整）')
    for link in data.get('links',[]):
        a,b=events[link['from']],events[link['to']]
        if position(data,a,'at') is None or position(data,b,'at') is None:
            notes.append('已记录关系（无主轴耗时）：'+a['label']+' → '+b['label']+' ['+link['kind']+']')
    return notes


def highlighted_facts(data):
    """Keep default facts attached to their actual main scope in multi-M views."""
    multiple=sum(t['kind']=='M' for t in data['tracks'])>1
    events={e['id']:e for e in data.get('events',[])}
    facts=[]
    for item in data.get('highlights',[]):
        scopes=sorted({events[eid]['track'].split('.')[0] for eid in item.get('events',[])})
        scope=' / '.join('U0' if s=='COMMON' else s for s in scopes)
        facts.append((scope+'｜' if multiple and scope else '')+item['label'])
    return facts


def wrapped(text,width):
    limit=max(20,int((width-24)/7));lines=[];line='';units=0
    for char in text:
        size=2 if unicodedata.east_asian_width(char) in ('W','F') else 1
        if units+size>limit:lines.append(line);line='';units=0
        line+=char;units+=size
    if line:lines.append(line)
    return lines


def render_svg(data,width=1440,theme='light',focus=None):
    validate(data);need(type(width) is int and 320<=width<=4096,'width must be 320..4096')
    need(theme in ('light','dark','host'),'unknown theme')
    uid=prefix(data);narrow=width<560
    left=72 if narrow else 204;right=width-18;plot=right-left;maximum=extent(data)
    unlocated=[line for note in unlocated_facts(data) for line in wrapped('未定位事实｜'+note,width)]
    y0=182;row=46;height=y0+len(data['tracks'])*row+(156 if narrow else 104)+23*len(unlocated)
    x=lambda value:left+value/maximum*plot
    ys={track['id']:y0+i*row for i,track in enumerate(data['tracks'])};ys['COMMON']=99
    palette=({'bg':'#ffffff','fg':'#172b43','muted':'#52647b','grid':'#dce3eb',
              'M':'#d83c52','N':'#3265ce','R':'#8851c3','S':'#b27b13','D':'#d16522','V':'#21825c'} if theme=='light' else
             {'bg':'#111923','fg':'#e8eef8','muted':'#b4c1d4','grid':'#374454',
              'M':'#ff8c9c','N':'#88b1ff','R':'#cca7ff','S':'#e7c46d','D':'#ffb57c','V':'#85d5b6'})
    if theme=='host':
        palette={'bg':'var(--background)','fg':'var(--foreground)','muted':'var(--muted-foreground)',
                 'grid':'var(--border)',**{kind:f'var(--{name})' for kind,name in
                  {'N':'blue','R':'purple','S':'yellow','D':'orange','V':'green','M':'red'}.items()}}
    e=escape;out=[]
    def add(s):out.append(s)
    multiplier,unit=time_scale(maximum)
    add(f'<svg xmlns="http://www.w3.org/2000/svg" class="digr-timeline" role="img" aria-labelledby="{uid}-title {uid}-desc" width="{width}" height="{height}" viewBox="0 0 {width} {height}" data-maximum="{maximum}" data-time-multiplier="{multiplier}" data-time-unit="{unit}" data-time-known="{str(has_locations(data)).lower()}" data-y0="{y0}" data-row="{row}">')
    add(f'<title id="{uid}-title">{e(data["title"])}</title><desc id="{uid}-desc">横轴为同一可比域的时间，纵轴为有类型的工作标识，N/R不代表额外代理。细线只表示标识延续；工作区段不自动证明有效T。未知时间不定位；返回、决定、落实分别记录。</desc>')
    add('<style>.digr-timeline{font-family:"Segoe UI","Microsoft YaHei",sans-serif;font-size:14px;font-weight:400}')
    add(f'.digr-timeline text{{fill:{palette["fg"]}}}.digr-timeline .muted{{fill:{palette["muted"]}}}.digr-timeline .grid{{stroke:{palette["grid"]};stroke-width:1}}')
    add('.digr-timeline .flow{fill:none;stroke-width:1.5;opacity:1;pointer-events:none}.digr-timeline .selected{opacity:1}.digr-timeline .segment{fill-opacity:.22}.digr-timeline .life{stroke-width:1;stroke-dasharray:3 5;opacity:.45;pointer-events:none}')
    add('.digr-timeline .focus-mark{stroke-width:2}.digr-timeline .event-label{font-size:12px}.digr-timeline .secondary{font-size:12px}.digr-timeline .decor{pointer-events:none}</style>')
    add(f'<defs><marker id="{uid}-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7" fill="none" stroke="{palette["muted"]}"/></marker></defs>')
    add(f'<rect class="decor" width="100%" height="100%" fill="{palette["bg"]}"/>')
    add(f'<text x="12" y="27" class="chart-title" data-full-title="{e(data["title"],quote=True)}" font-size="20" font-weight="500">{e(data["title"] if not narrow else "DIGR · 时间 × 工作标识")}</text>')
    mode='结构示意 · 编排时间，不代表本次执行' if data['mode']=='illustration' else '已记录事实 · 只定位同一可比时钟域'
    add(f'<text x="12" y="52" class="secondary muted mode-label" data-full-mode="{mode}">{mode if not narrow else "结构示意 · 非本轮实录" if data["mode"]=="illustration" else "实录 · 同一可比时钟域"}</text>')
    for phase in data.get('phases',[]):
        a,b=phase['start'],phase['end'];w=x(b)-x(a)
        add(f'<rect class="decor phase" data-start="{a}" data-end="{b}" x="{x(a):.2f}" y="72" width="{w:.2f}" height="27" fill="{palette["grid"]}" opacity=".45"/>')
        add(f'<text class="phase-label secondary" data-mid="{(a+b)/2}" data-phase-start="{a}" data-phase-end="{b}" x="{x((a+b)/2):.2f}" y="90" text-anchor="middle"'+(' style="display:none"' if w<len(phase['label'])*12+8 else '')+f'>{e(phase["label"])}</text>')
    add(f'<g class="timeline-axis" data-left="{left}"><line x1="{left}" y1="124" x2="{right}" y2="124" class="grid"/>')
    ticks=2 if narrow else 6
    for i in range(ticks+1 if has_locations(data) else 0):
        value=maximum*i/ticks
        add(f'<line x1="{x(value):.2f}" y1="119" x2="{x(value):.2f}" y2="{height-76}" class="grid decor" opacity=".5"/><text x="{x(value):.2f}" y="145" text-anchor="middle" class="secondary muted">{time_label(value,maximum)}</text>')
    if not has_locations(data):add(f'<text x="{left}" y="145" class="secondary muted">时间未定位</text>')
    add('</g>')
    add('<text x="12" y="143" class="secondary muted">身份 Xᵢ</text>')
    for track in data['tracks']:
        tid=track['id'];y=ys[tid];color=palette[track['kind']]
        add(f'<g data-track="{e(tid)}"><line x1="{left}" x2="{right}" y1="{y}" y2="{y}" class="grid decor" opacity=".45"/>')
        label=short_id(tid)
        add(f'<text x="12" y="{y+5}" font-weight="500">{label}</text>')
        add(f'<text x="51" y="{y+5}" class="track-detail secondary muted"'+(' style="display:none"' if narrow else '')+f'>{e(track.get("label",KINDS[track["kind"]]))}</text>')
        if tid.startswith('M') and '.' in tid:
            add(f'<text x="12" y="{y+20}" class="scope-label secondary muted">{e(tid.split(".")[0])}</text>')
        segments=track.get('segments',[])
        located=[v for s in segments for key in ('start','end') if (v:=position(data,s,key)) is not None]
        if located:
            add(f'<line class="life" data-start="{min(located)}" data-end="{max(located)}" x1="{x(min(located)):.2f}" x2="{x(max(located)):.2f}" y1="{y}" y2="{y}" stroke="{color}"/>')
        for index,segment in enumerate(segments):
            a,b=position(data,segment,'start'),position(data,segment,'end')
            sid=f'{tid}-segment-{index}'
            if a is None or b is None:
                known=a if a is not None else b
                if known is not None:add(f'<text data-at="{known}" data-y="{y+5}" x="{x(known):.2f}" y="{y+5}" class="muted">?</text>')
                continue
            label=segment['label'];w=max(2,x(b)-x(a))
            hint=f'{tid} · {label} · {a:g}–{b:g}秒；执行者：'+segment.get('executor','未记录')+'；对象：'+'、'.join(segment.get('artifact_versions',[]))+'；'+segment.get('note','输入声明的工作窗，非有效计时认证')
            add(f'<rect class="segment" data-segment="{sid}" data-start="{a}" data-end="{b}" data-label="{e(label,quote=True)}" data-tooltip="{e(hint,quote=True)}" x="{x(a):.2f}" y="{y-11}" width="{w:.2f}" height="22" rx="4" fill="{color}"><title>{e(hint)}</title></rect>')
            visible=(not narrow and w>len(label)*13+14)
            add(f'<text class="bar-label secondary decor" data-start="{a}" data-end="{b}" x="{x(a)+7:.2f}" y="{y+5}"'+('' if visible else ' style="display:none"')+f'>{e(label)}</text>')
        add('</g>')
    by_event={event['id']:event for event in data.get('events',[])}
    selected={focus} if focus else set()
    for link in data.get('links',[]):
        if focus and focus in (link['from'],link['to']):selected.update((link['from'],link['to']))
        a,b=by_event[link['from']],by_event[link['to']]
        ta,tb=position(data,a,'at'),position(data,b,'at')
        if ta is None or tb is None:continue
        show=bool(focus and focus in (a['id'],b['id'])) or bool(link.get('overview'))
        ya,yb=ys[a['track']],ys[b['track']];xa,xb=x(ta),x(tb)
        mid=(xa+xb)/2
        dash=' stroke-dasharray="3 4"' if link['kind'] in ('reference','correlation') else ''
        arrow='' if link['kind'] in ('correlation','reference') else f' marker-end="url(#{uid}-arrow)"'
        add(f'<path class="flow" data-from="{a["id"]}" data-to="{b["id"]}" data-overview="{str(bool(link.get("overview"))).lower()}" d="M{xa:.2f},{ya} C{mid:.2f},{ya} {mid:.2f},{yb} {xb:.2f},{yb}" stroke="{palette["muted"]}"{dash}{arrow}'+('' if show else ' style="display:none"')+'/>')
    for event in data.get('events',[]):
        at=position(data,event,'at')
        if at is None:continue
        y=ys[event['track']];xx=x(at);kind=event['kind'];glyph,word=EVENTS[kind]
        hint=f'{glyph} {event["label"]} · {at:g}秒；'+event.get('note','')
        color=palette[by_event[event['id']]['track'].split('.')[-1][0]] if event['track']!='COMMON' else palette['muted']
        add(f'<g data-event="{event["id"]}" data-at="{at}" data-y="{y}" transform="translate({xx:.2f},{y})" data-tooltip="{e(hint,quote=True)}">')
        if kind=='decision':add(f'<path d="M0,-9 L9,0 L0,9 L-9,0 Z" fill="{palette["bg"]}" stroke="{color}" stroke-width="1.6"/>')
        elif kind in ('bootstrap','council'):
            add(f'<circle r="7" fill="{palette["bg"]}" stroke="{color}" stroke-width="1.6"/>')
            add(f'<circle r="{2 if kind=="bootstrap" else 4}" fill="{color if kind=="bootstrap" else palette["bg"]}" stroke="{color}"/>')
        elif kind=='close':add(f'<rect x="-5" y="-5" width="10" height="10" fill="{color}"/>')
        else:add(f'<text y="5" text-anchor="middle" font-size="17" font-weight="500">{glyph}</text>')
        add(f'<title>{e(hint)}</title></g>')
        label=event.get('display_label')
        if label:add(f'<text class="event-label" data-at="{at}" data-y="{y-17}" x="{xx:.2f}" y="{y-17}" text-anchor="middle">{e(label)}</text>')
    footer=(['⊙ 自举　◎ 议会　↩ 收到','◇ 决定　✓ 落实　↻ 再入　■ 关闭',
             '细线：标识延续，不表示持续执行。','区段：输入声明的工作窗。','时间跨度不直接等于有效 T。'] if narrow else
            ['⊙ 自举　◎ 议会　↩ 收到　◇ 决定　✓ 落实　↻ 再入　■ 关闭',
             '细线＝标识延续；区段＝所述工作。时间跨度不直接等于有效 T，来源 t 包含于 T。'])+unlocated
    for i,line in enumerate(footer):add(f'<text x="12" y="{height-25-(len(footer)-1-i)*23}" class="secondary muted footer">{e(line)}</text>')
    add('</svg>')
    return '\n'.join(out)


def fragment(data):
    """Host fragment, with responsive projection and keyboard-accessible detail."""
    validate(data);uid=prefix(data)
    fingerprint=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    svg=render_svg(data,1024,'host')
    unlocated=unlocated_facts(data)
    options=['<option value="">全局概览</option>']
    grouped=[{'id':'COMMON','label':'共同前置','segments':[]},*data['tracks']]
    for track in grouped:
        entries=[]
        for event in data.get('events',[]):
            if event['track']!=track['id']:continue
            suffix='（时间未定位）' if position(data,event,'at') is None else ''
            entries.append(f'<option value="{event["id"]}">{escape(event["label"]+suffix)}</option>')
        for index,segment in enumerate(track.get('segments',[])):
            suffix='（主轴未定位）' if any(position(data,segment,k) is None for k in ('start','end')) else ''
            entries.append(f'<option value="span:{track["id"]}-segment-{index}">{escape("区段："+segment["label"]+suffix)}</option>')
        if entries:options.append(f'<optgroup label="{escape(track["id"]+" · "+track.get("label",""),quote=True)}">'+''.join(entries)+'</optgroup>')
    mains=[t for t in data['tracks'] if t['kind']=='M']
    groups=''.join(f'<button class="btn" type="button" data-main="{t["id"]}" aria-expanded="false" aria-controls="{uid}-figure">{t["id"]} 展开</button>' for t in mains) if len(mains)>1 else ''
    facts=''.join('<li>'+escape(label)+'</li>' for label in highlighted_facts(data))
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    script=(Path(__file__).resolve().parent/'assets/codex_timeline_view.js').read_text(encoding='utf-8')
    return f'''<section id="{uid}" data-fingerprint="{fingerprint}" aria-label="DIGR全流程时间与身份图">
<style>
#{uid}{{display:grid;gap:calc(var(--font-size-base)*.75)}}
#{uid} .digr-timeline{{display:block;width:100%;height:auto;font-size:var(--font-size-base)}}
#{uid} .digr-timeline .secondary,#{uid} .digr-timeline .event-label{{font-size:calc(var(--font-size-base)*.86)}}
#{uid} .digr-timeline .bar-label{{pointer-events:none}}
#{uid} .diagram-legend{{display:flex;gap:calc(var(--font-size-base)*.75);flex-wrap:wrap}}
#{uid} [data-figure]{{position:relative}}
#{uid} [data-row-controls]{{position:absolute;inset:0;pointer-events:none}}
#{uid} .row-control{{position:absolute;left:0;height:44px;display:flex;align-items:center;gap:calc(var(--font-size-base)*.25);pointer-events:none}}
#{uid} .row-control[hidden]{{display:none}}
#{uid} .row-description{{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
#{uid} .hit-target{{display:inline-flex;align-items:center;min-width:44px;min-height:44px;max-width:100%;pointer-events:auto}}
#{uid} .hit-target:has(>button[hidden]){{display:none}}
#{uid} .selector-field{{min-width:0;width:100%}}
#{uid} [data-inspector],#{uid} [data-detail],#{uid} .detail-relations{{display:grid;gap:calc(var(--font-size-base)*.75);overflow-wrap:anywhere}}
#{uid} .inspector-heading{{display:flex;align-items:center;justify-content:space-between;gap:calc(var(--font-size-base)*.5);flex-wrap:wrap}}
#{uid} [data-candidates][hidden]{{display:none}}
#{uid} [data-detail] dl{{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:calc(var(--font-size-base)*.25) calc(var(--font-size-base)*.75);margin:0}}
#{uid} [data-detail] dt,#{uid} [data-detail] dd{{margin:0}}
#{uid} .detail-relation{{display:flex;align-items:center;gap:calc(var(--font-size-base)*.5);flex-wrap:wrap}}
#{uid} .detail-relation>span:not(.hit-target){{min-width:0;flex:1;overflow-wrap:anywhere}}
@media(max-width:559px){{#{uid} [data-detail] dl{{grid-template-columns:1fr}}#{uid} [data-detail] dd{{margin-bottom:calc(var(--font-size-base)*.25)}}}}
</style>
<div class="text-small">{'结构示意 · 时间与行为均为编排，非本轮实录' if data['mode']=='illustration' else '已记录事实 · 未定位时间单独保留'}</div>
{('<div class="text-small">观测起点：'+escape(data['origin'])+'</div>') if data['mode']=='recorded' else ''}
<div class="diagram-legend text-small">N 主线推进 · R 整体重开 · S 来源面 · D 竞争介入 · V 持续领域 · M 完整主进度</div>
<div class="text-small">⊙ 自举　◎ 议会　↩ 收到　◇ 决定　✓ 落实　↻ 再入　■ 关闭；虚线关联无执行方向。</div>
<ul class="text-small">{facts}</ul>
<div class="viz-controls" data-groups>{groups}</div>
<div class="text-small text-muted" data-range></div>
<div class="text-small text-muted">点工作行标题查看本行全部条目；图上点按会先区分附近的行为与区段。</div>
<div data-figure id="{uid}-figure">{svg}<div data-row-controls></div></div>
<section data-inspector id="{uid}-inspector" aria-labelledby="{uid}-inspector-title">
<div class="inspector-heading"><h3 data-inspector-title id="{uid}-inspector-title">行为与工作区段详情</h3><button type="button" class="btn" data-back-chart hidden>返回图中</button></div>
<div class="selector-field"><label class="form-label" for="{uid}-select">完整条目快捷选择</label><select class="form-select" id="{uid}-select" data-select>{''.join(options)}</select></div>
<div class="selector-field" data-candidates hidden><label class="form-label" data-candidate-label for="{uid}-candidate">选择附近条目</label><select class="form-select" id="{uid}-candidate" data-candidate-select></select></div>
<div aria-live="polite" data-detail>选择行为或区段，查看执行者、对象版本和已记录关系。</div>
</section>
<div class="text-small text-muted">{'未定位：'+escape('；'.join(unlocated)) if unlocated else '示意阶段可重叠、往返；议会可以分批交流，不是全员同步栅栏。'}</div>
<script type="application/json" data-model>{payload}</script>
<script>(()=>{{const root=document.getElementById('{uid}');{script}}})();</script>
</section>'''
