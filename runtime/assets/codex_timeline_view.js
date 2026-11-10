const model=JSON.parse(root.querySelector('[data-model]').textContent);
const figure=root.querySelector('svg.digr-timeline'),stage=root.querySelector('[data-figure]');
const select=root.querySelector('[data-select]'),panel=root.querySelector('[data-inspector]'),detail=root.querySelector('[data-detail]');
const candidateBox=root.querySelector('[data-candidates]'),candidateSelect=root.querySelector('[data-candidate-select]'),candidateLabel=root.querySelector('[data-candidate-label]'),backButton=root.querySelector('[data-back-chart]');
const fingerprint=root.dataset.fingerprint;
const eventMap=new Map(model.events.map(e=>[e.id,e]));
const items=new Map(eventMap);
model.tracks.forEach(t=>t.segments?.forEach((s,i)=>items.set(`span:${t.id}-segment-${i}`,{...s,id:`span:${t.id}-segment-${i}`,track:t.id,kind:'interval'})));
const mains=model.tracks.filter(t=>t.kind==='M'),mainIds=new Set(mains.map(t=>t.id));
const byTrack=new Map(model.tracks.map(t=>[t.id,t]));
if(model.events.some(e=>e.track==='COMMON'))byTrack.set('COMMON',{id:'COMMON',kind:'U0',label:'共同前置'});
const validCollapsed=value=>new Set(Array.isArray(value)?value.filter(id=>mainIds.has(id)):[]);
const saved=window.openai?.widgetState?.privateContent,sameData=saved?.fingerprint===fingerprint;
let selected=sameData&&items.has(saved?.event)?saved.event:'';
let collapsed=sameData&&Array.isArray(saved?.collapsed)?validCollapsed(saved.collapsed):new Set(mains.length>1?mains.map(t=>t.id):[]);
let contextTrack='',candidateIds=[],candidateMode='',width=1024,ys=new Map();
const max=Number(figure.dataset.maximum),y0=Number(figure.dataset.y0),row=Number(figure.dataset.row);
const multiplier=Number(figure.dataset.timeMultiplier)||1/60,unit=figure.dataset.timeUnit||'分',ns='http://www.w3.org/2000/svg';
const kindWords={bootstrap:'自举',council:'议会',send:'发出',receive:'收到',decision:'决定',apply:'落实',reenter:'再入',close:'关闭',pause:'暂停',candidate:'候选',note:'说明',interval:'工作区段'};
const linkWords={message:'消息',handling:'处理',application:'落实',reference:'材料引用',correlation:'相关（无因果方向）'};
const leftEdge=()=>width<560?72:204;
const pos=t=>leftEdge()+Number(t)/max*(width-leftEdge()-18);
const element=(tag,attrs={},text)=>{const n=document.createElement(tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text!=null)n.textContent=text;return n;};
const svgElement=(tag,attrs={},text)=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text!=null)n.textContent=text;return n;};
const located=(i,key)=>i[key]!=null&&(!i.domain||i.domain===model.axis_domain);
const fullyLocated=i=>i.kind==='interval'?located(i,'start')&&located(i,'end'):located(i,'at');
const shortId=tid=>{if(tid==='COMMON')return 'U0';const m=tid.split('.').at(-1).match(/^([A-Z])(\d+)$/);return m?m[1]+String(Number(m[2])).replace(/\d/g,c=>'₀₁₂₃₄₅₆₇₈₉'[Number(c)]):tid;};
function timeText(item){
 if(item.kind==='interval'){const raw=`${item.start??'?'}–${item.end??'?'}秒`;return fullyLocated(item)?raw:`主轴未定位；本地输入起止 ${raw}（时钟域：${item.domain||model.axis_domain}）`;}
 if(located(item,'at'))return `${item.at}秒`;
 return item.at==null?`主轴未定位（时刻缺失；时钟域：${item.domain||model.axis_domain}）`:`主轴未定位；本地输入 ${item.at}秒（时钟域：${item.domain}）`;
}
function activeSet(){
 const set=new Set(selected?[selected]:[]);if(!eventMap.has(selected))return set;
 let changed=true;while(changed){changed=false;for(const l of model.links){if(['reference','correlation'].includes(l.kind))continue;if(set.has(l.from)||set.has(l.to)){for(const id of [l.from,l.to])if(!set.has(id)){set.add(id);changed=true;}}}}
 for(const l of model.links)if(l.from===selected||l.to===selected){set.add(l.from);set.add(l.to);}return set;
}
function effectiveTargets(){for(const b of root.querySelectorAll('button')){if(b.parentElement.classList.contains('hit-target'))continue;const target=element('span',{class:'hit-target'});b.before(target);target.append(b);target.addEventListener('click',event=>{if(event.target===target&&!b.disabled)b.click();});}}
function save(){Promise.resolve(window.openai?.setWidgetState?.({modelContent:{timeline:fingerprint,event:selected||null,versions:items.get(selected)?.artifact_versions||[]},privateContent:{fingerprint,event:selected,collapsed:[...collapsed].sort()}})).catch(()=>{});}
function revealSelection(){const item=items.get(selected);if(item)collapsed.delete(item.track.split('.')[0]);for(const id of activeSet()){const event=eventMap.get(id);if(event)collapsed.delete(event.track.split('.')[0]);}}
function focusPanel(preferCandidates=false){const target=preferCandidates&&!candidateBox.hidden?candidateSelect:backButton;if(!target.hidden)target.focus({preventScroll:true});panel.scrollIntoView({block:'nearest'});}
function choose(id,{retainCandidates=false,moveFocus=true}={}){if(id!==''&&!items.has(id))return;selected=id;if(!retainCandidates){contextTrack=items.get(id)?.track||'';candidateIds=[];candidateMode='';}revealSelection();layout();save();if(moveFocus)focusPanel();}
function openCandidates(tid,ids,mode){contextTrack=tid;candidateIds=ids;candidateMode=mode;selected=ids.length===1?ids[0]:'';revealSelection();layout();save();focusPanel(ids.length>1);}
function renderDetail(){
 const item=items.get(selected),track=byTrack.get(item?.track||contextTrack);
 root.querySelector('[data-inspector-title]').textContent=track?`${track.id} · ${track.label||'工作标识'}`:'行为与工作区段详情';
 candidateBox.hidden=candidateIds.length<2;candidateSelect.replaceChildren(element('option',{value:''},'请选择一项'));
 for(const id of candidateIds){const i=items.get(id);candidateSelect.append(element('option',{value:id},`${kindWords[i.kind]} · ${i.label} · ${timeText(i)}`));}
 candidateSelect.value=candidateIds.includes(selected)?selected:'';
 candidateLabel.textContent=candidateMode==='row'?`本行共 ${candidateIds.length} 项（含未定位条目）`:`此处有 ${candidateIds.length} 项，分别选择查看`;
 detail.replaceChildren();backButton.hidden=!track;
 if(!item){detail.append(element('p',{},contextTrack?(candidateIds.length?'选择一项，查看它自己的版本、范围、说明和关系。':'本行没有登记行为或区段。'):'选择图中工作行、时间邻域，或使用完整条目快捷选择。'));return;}
 detail.append(element('h3',{},item.label));if(item.note)detail.append(element('p',{},item.note));
 const fields=[['工作标识',item.track],['类型',kindWords[item.kind]],['时间范围',timeText(item)],['执行者',item.executor||'输入未记录'],['本条对象版本',item.artifact_versions?.length?item.artifact_versions.join('、'):'输入未记录'],['本条依据',item.source_ref||'输入未记录']];if(item.references?.length)fields.push(['本条引用材料',item.references.join('、')]);
 const dl=element('dl');for(const [label,value] of fields)dl.append(element('dt',{class:'text-muted'},label),element('dd',{},value));detail.append(dl);
 const direct=model.links.filter(l=>l.from===item.id||l.to===item.id);
 if(direct.length){const relations=element('div',{class:'detail-relations'});relations.append(element('p',{},'与本条直接相连的已记录关系'));
  for(const link of direct){const outgoing=link.from===item.id,other=eventMap.get(outgoing?link.to:link.from),plain=['reference','correlation'].includes(link.kind),label=`${plain?'关联':outgoing?'后续':'前序'} · ${linkWords[link.kind]}`;
   const line=element('div',{class:'detail-relation'}),button=element('button',{type:'button',class:'btn','data-related':other.id,'aria-label':`${label}：${other.label}`},label);button.addEventListener('click',()=>choose(other.id));line.append(button,element('span',{},other.label));relations.append(line);
  }detail.append(relations);
 }else detail.append(element('p',{class:'text-muted'},item.kind==='interval'?'输入没有把此区段登记为行为关系端点。':'输入没有登记与本条直接相连的关系。'));
}
const rowControls=new Map();
for(const [tid,track] of byTrack){const control=element('div',{class:'row-control','data-row-control':tid}),button=element('button',{class:'btn',type:'button','data-row':tid,'data-tooltip':`${tid} · ${track.label||''}`,'aria-label':`${tid} ${track.label||''}，查看本行所有行为和区段`,'aria-controls':panel.id},tid),description=element('span',{class:'row-description text-small','data-tooltip':track.label||tid},track.label||'');button.addEventListener('click',()=>openCandidates(tid,[...items.values()].filter(i=>i.track===tid).map(i=>i.id),'row'));control.append(button,description);root.querySelector('[data-row-controls]').append(control);rowControls.set(tid,{control,button,description});}
function refresh(){
 select.value=selected;renderDetail();effectiveTargets();const set=activeSet();
 for(const path of figure.querySelectorAll('[data-from]')){const a=eventMap.get(path.dataset.from),b=eventMap.get(path.dataset.to),linked=set.has(a.id)&&set.has(b.id);path.style.display=ys.has(a.track)&&ys.has(b.track)&&(linked||(!selected&&path.dataset.overview==='true'))?'':'none';path.style.opacity='1';}
 for(const mark of figure.querySelectorAll('[data-event]'))mark.style.opacity=!selected||set.has(mark.dataset.event)?'1':'.32';
 figure.querySelector('[data-focus-ring]')?.remove();const chosen=items.get(selected);if(chosen&&chosen.kind!=='interval'&&fullyLocated(chosen)&&ys.has(chosen.track))figure.append(svgElement('circle',{'data-focus-ring':'',cx:pos(chosen.at),cy:ys.get(chosen.track),r:13,fill:'none',stroke:'var(--foreground)','stroke-width':2,'pointer-events':'none'}));
 for(const button of root.querySelectorAll('[data-main]')){const hidden=collapsed.has(button.dataset.main),count=model.tracks.filter(t=>t.id.startsWith(button.dataset.main+'.')).length;button.setAttribute('aria-expanded',String(!hidden));button.textContent=`${button.dataset.main} ${hidden?'展开':'折叠'}（${count}个子标识）`;}
 root.querySelector('[data-range]').textContent=`当前显示 ${ys.size-1} / ${model.tracks.length} 个工作标识${collapsed.size?'；折叠内容仍完整保留，不代表已完成':''}。细线表示标识延续，不表示持续执行或有效T。`;
 if(mains.length>1)root.querySelector('[data-range]').textContent+=' '+mains.map(m=>{const classes=['N','R','S','D','V'].map(k=>k+model.tracks.filter(t=>t.id.startsWith(m.id+'.')&&t.kind===k).length).join('/');return `${m.id} 输入标识覆盖 ${classes}；本线配置：${m.configuration?JSON.stringify(m.configuration):'未提供'}；未处理后果：${m.unhandled?.length?m.unhandled.join('；'):'输入未声明（不等于没有）'}`;}).join(' ｜');
}
function layout(){
 width=Math.max(160,Math.round(stage.getBoundingClientRect().width));const narrow=width<560,left=leftEdge(),right=width-18;
 ys=new Map([['COMMON',99]]);let count=0;for(const t of model.tracks)if(t.kind==='M'||!collapsed.has(t.id.split('.')[0]))ys.set(t.id,y0+count++*row);
 const h=y0+Math.max(0,count-1)*row+40;figure.setAttribute('viewBox',`0 0 ${width} ${h}`);figure.setAttribute('width',width);figure.setAttribute('height',h);
 figure.querySelector('.chart-title').textContent=narrow?'DIGR · 时间 × 工作标识':figure.querySelector('.chart-title').dataset.fullTitle;figure.querySelector('.mode-label').textContent=narrow?(model.mode==='illustration'?'结构示意 · 非本轮实录':'实录 · 同一可比时钟域'):figure.querySelector('.mode-label').dataset.fullMode;
 for(const group of figure.querySelectorAll('[data-track]')){const tid=group.dataset.track,visible=ys.has(tid),original=y0+model.tracks.findIndex(t=>t.id===tid)*row;group.style.display=visible?'':'none';if(visible)group.setAttribute('transform',`translate(0,${ys.get(tid)-original})`);group.querySelector('text')?.setAttribute('visibility','hidden');group.querySelectorAll('.track-detail,.scope-label').forEach(label=>label.setAttribute('visibility','hidden'));}
 for(const [tid,r] of rowControls){r.control.hidden=!ys.has(tid);if(!ys.has(tid))continue;r.control.style.top=`${ys.get(tid)-22}px`;r.control.style.width=`${left-2}px`;r.button.textContent=narrow?shortId(tid):tid;r.description.textContent=narrow?(tid.includes('.')?shortId(tid.split('.')[0]):''):byTrack.get(tid).label||'';}
 figure.querySelectorAll('[data-track]>.grid').forEach(line=>{line.setAttribute('x1',left);line.setAttribute('x2',right);});
 for(const node of figure.querySelectorAll('[data-start]')){const a=pos(node.dataset.start),b=pos(node.dataset.end);if(node.tagName==='line'){node.setAttribute('x1',a);node.setAttribute('x2',b);}else if(node.tagName==='rect'){node.setAttribute('x',a);node.setAttribute('width',Math.max(2,b-a));}else{node.setAttribute('x',a+7);node.style.display=!narrow&&(b-a)>node.textContent.length*13+14?'':'none';}}
 for(const node of figure.querySelectorAll('[data-mid]')){node.setAttribute('x',pos(node.dataset.mid));const room=pos(node.dataset.phaseEnd)-pos(node.dataset.phaseStart);node.style.display=room>node.textContent.length*12+8?'':'none';}
 for(const node of figure.querySelectorAll('[data-at]')){const e=eventMap.get(node.dataset.event),y=e?ys.get(e.track):Number(node.dataset.y),x=pos(node.dataset.at);if(node.tagName==='g'){node.style.display=y===undefined?'none':'';if(y!==undefined)node.setAttribute('transform',`translate(${x},${y})`);}else{node.setAttribute('x',x);if(node.classList.contains('event-label')){const original=Number(node.dataset.y)+17,tid=model.tracks.find((t,i)=>y0+i*row===original)?.id;node.style.display=narrow||tid&&!ys.has(tid)?'none':'';if(tid&&ys.has(tid))node.setAttribute('y',ys.get(tid)-17);}}}
 for(const path of figure.querySelectorAll('[data-from]')){const a=eventMap.get(path.dataset.from),b=eventMap.get(path.dataset.to);if(!ys.has(a.track)||!ys.has(b.track))continue;const xa=pos(a.at),xb=pos(b.at),ya=ys.get(a.track),yb=ys.get(b.track),m=(xa+xb)/2;path.setAttribute('d',`M${xa},${ya} C${m},${ya} ${m},${yb} ${xb},${yb}`);}
 const axis=figure.querySelector('.timeline-axis');axis.replaceChildren();if(figure.dataset.timeKnown==='true'){axis.append(svgElement('line',{x1:left,x2:right,y1:124,y2:124,class:'grid decor'}));const ticks=narrow?2:6;for(let i=0;i<=ticks;i++){const t=max*i/ticks,x=pos(t);axis.append(svgElement('line',{x1:x,x2:x,y1:119,y2:y0+count*row-24,class:'grid decor',opacity:'.5'}),svgElement('text',{x,y:145,'text-anchor':i===0?'start':i===ticks?'end':'middle',class:'secondary muted'},`${Number((t*multiplier).toPrecision(4))}${unit}`));}}else axis.append(svgElement('text',{x:left,y:145},'时间未定位'));
 figure.querySelectorAll('.footer').forEach(node=>node.style.display='none');refresh();
}
select.addEventListener('change',()=>choose(select.value,{moveFocus:false}));candidateSelect.addEventListener('change',()=>{if(candidateSelect.value)choose(candidateSelect.value,{retainCandidates:true,moveFocus:false});});
for(const button of root.querySelectorAll('[data-main]'))button.addEventListener('click',()=>{const id=button.dataset.main;if(collapsed.has(id))collapsed.delete(id);else collapsed.add(id);layout();save();});
backButton.addEventListener('click',()=>{const tid=items.get(selected)?.track||contextTrack;if(!tid)return;collapsed.delete(tid.split('.')[0]);layout();rowControls.get(tid)?.button.focus({preventScroll:true});rowControls.get(tid)?.control.scrollIntoView({block:'nearest'});save();});
figure.addEventListener('click',event=>{const box=figure.getBoundingClientRect(),px=(event.clientX-box.left)*width/box.width,py=(event.clientY-box.top)*Number(figure.getAttribute('height'))/box.height;if(px<leftEdge()||px>width-18)return;const closest=[...ys].filter(([tid])=>byTrack.has(tid)).sort((a,b)=>Math.abs(a[1]-py)-Math.abs(b[1]-py))[0];if(!closest||Math.abs(closest[1]-py)>22)return;const tid=closest[0],lane=[...items.values()].filter(i=>i.track===tid),nearby=lane.filter(i=>fullyLocated(i)&&(i.kind==='interval'?px>=pos(i.start)-4&&px<=pos(i.end)+4:Math.abs(pos(i.at)-px)<=22));nearby.sort((a,b)=>(a.kind==='interval'?10000:Math.abs(pos(a.at)-px))-(b.kind==='interval'?10000:Math.abs(pos(b.at)-px)));openCandidates(tid,(nearby.length?nearby:lane).map(i=>i.id),nearby.length?'nearby':'row');});
window.addEventListener('openai:set_globals',event=>{const state=event.detail?.globals?.widgetState?.privateContent,next=state?.event;if(state?.fingerprint!==fingerprint||typeof next!=='string'||next!==''&&!items.has(next))return;const nextCollapsed=Array.isArray(state.collapsed)?validCollapsed(state.collapsed):collapsed,equalCollapsed=[...nextCollapsed].sort().join('|')===[...collapsed].sort().join('|');/* Host echoes must preserve the nearby chooser. */if(next===selected&&equalCollapsed)return;if(next!==selected){contextTrack=items.get(next)?.track||'';candidateIds=[];candidateMode='';}selected=next;collapsed=nextCollapsed;layout();});
new ResizeObserver(layout).observe(stage);layout();
