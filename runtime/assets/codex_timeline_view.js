const model=JSON.parse(root.querySelector('[data-model]').textContent);
const figure=root.querySelector('svg.digr-timeline');
const select=root.querySelector('[data-select]'),detail=root.querySelector('[data-detail]');
const eventMap=new Map(model.events.map(e=>[e.id,e]));
const items=new Map(eventMap);
model.tracks.forEach(t=>t.segments?.forEach((s,i)=>items.set(`span:${t.id}-segment-${i}`,{...s,id:`span:${t.id}-segment-${i}`,track:t.id,kind:'interval'})));
const mains=model.tracks.filter(t=>t.kind==='M');
const saved=window.openai?.widgetState?.privateContent;
let selected=items.has(saved?.event)?saved.event:'';
let collapsed=new Set(Array.isArray(saved?.collapsed)?saved.collapsed:mains.length>1?mains.map(t=>t.id):[]);
let width=1024,ys=new Map();
const max=Number(figure.dataset.maximum),y0=Number(figure.dataset.y0),row=Number(figure.dataset.row);
const pos=t=>(width<560?72:204)+Number(t)/max*(width-(width<560?72:204)-18);
function activeSet(){
 const set=new Set(selected?[selected]:[]);
 if(!eventMap.has(selected))return set;
 // Show the recorded causal component, not only one neighbouring arrow.
 let changed=true;
 while(changed){changed=false;for(const l of model.links){
  if(['reference','correlation'].includes(l.kind))continue;
  if(set.has(l.from)||set.has(l.to)){for(const id of [l.from,l.to])if(!set.has(id)){set.add(id);changed=true;}}
 }}
 for(const l of model.links)if(l.from===selected||l.to===selected){set.add(l.from);set.add(l.to);}
 return set;
}
function details(item){
 if(!item)return '默认已列关键处置事实；选择行为或区段查看执行者、对象版本和关系。';
 const executor=item.executor?` ｜执行者：${item.executor}`:'';
 const versions=item.artifact_versions?.length?` ｜对象：${item.artifact_versions.join('、')}`:'';
 const temporal=item.kind==='interval'
   ?` ｜区间：${item.start??'?'}–${item.end??'?'}秒`
   :` ｜时间：${item.at==null||item.domain&&item.domain!==model.axis_domain?'未定位（时刻缺失或不可比域）':item.at+'秒'}`;
 const set=activeSet();
 const relations=model.links.filter(l=>set.has(l.from)&&set.has(l.to)).map(l=>{
  const words={message:'消息',handling:'处理',application:'落实',reference:'材料引用',correlation:'相关（无因果方向）'};
  return `${words[l.kind]}：${eventMap.get(l.from).label} → ${eventMap.get(l.to).label}`;
 });
 return `${item.track} · ${item.label}${executor}${versions}${temporal} — ${item.note||''}${relations.length?' ｜已记录关系：'+relations.join('；'):''}${item.source_ref?' ｜依据：'+item.source_ref:''}`;
}
function refresh(){
 select.value=selected;detail.textContent=details(items.get(selected));
 const set=activeSet();
 for(const path of figure.querySelectorAll('[data-from]')){
  const a=eventMap.get(path.dataset.from),b=eventMap.get(path.dataset.to);
  const linked=set.has(a.id)&&set.has(b.id);
  path.style.display=ys.has(a.track)&&ys.has(b.track)&&(linked||(!selected&&path.dataset.overview==='true'))?'':'none';
  path.style.opacity='1';
 }
 for(const mark of figure.querySelectorAll('[data-event]'))mark.style.opacity=!selected||set.has(mark.dataset.event)?'1':'.32';
 for(const button of root.querySelectorAll('[data-main]')){
  const hidden=collapsed.has(button.dataset.main),count=model.tracks.filter(t=>t.id.startsWith(button.dataset.main+'.')).length;
  button.setAttribute('aria-expanded',String(!hidden));
  button.textContent=`${button.dataset.main} ${hidden?'展开':'折叠'}（${count}个子标识）`;
 }
 root.querySelector('[data-range]').textContent=`当前显示 ${ys.size-1} / ${model.tracks.length} 个工作标识${collapsed.size?'；折叠内容仍完整保留，不代表已完成':''}。细线表示标识延续，不表示持续执行或有效T。`;
 if(mains.length>1)root.querySelector('[data-range]').textContent+=' '+mains.map(m=>{
  const classes=['N','R','S','D','V'].map(k=>k+model.tracks.filter(t=>t.id.startsWith(m.id+'.')&&t.kind===k).length).join('/');
  return `${m.id} 输入标识覆盖 ${classes}；本线配置：${m.configuration?JSON.stringify(m.configuration):'未提供'}；未处理后果：${m.unhandled?.length?m.unhandled.join('；'):'输入未声明（不等于没有）'}`;
 }).join(' ｜');
}
function layout(){
 width=Math.max(160,Math.round(root.querySelector('[data-figure]').getBoundingClientRect().width));
 const narrow=width<560,left=narrow?72:204,right=width-18;
 ys=new Map([['COMMON',99]]);let count=0;
 for(const t of model.tracks)if(t.kind==='M'||!collapsed.has(t.id.split('.')[0]))ys.set(t.id,y0+count++*row);
 const h=y0+count*row+(narrow?24:104);
 figure.setAttribute('viewBox',`0 0 ${width} ${h}`);figure.setAttribute('width',width);figure.setAttribute('height',h);
 figure.querySelector('.chart-title').textContent=narrow?'DIGR · 时间 × 工作标识':figure.querySelector('.chart-title').dataset.fullTitle;
 figure.querySelector('.mode-label').textContent=narrow?(model.mode==='illustration'?'结构示意 · 非本轮实录':'实录 · 同一可比时钟域'):figure.querySelector('.mode-label').dataset.fullMode;
 for(const group of figure.querySelectorAll('[data-track]')){
  const tid=group.dataset.track,visible=ys.has(tid),original=y0+model.tracks.findIndex(t=>t.id===tid)*row;
  group.style.display=visible?'':'none';
  if(visible)group.setAttribute('transform',`translate(0,${ys.get(tid)-original})`);
 }
 figure.querySelectorAll('[data-track]>.grid').forEach(el=>{el.setAttribute('x1',left);el.setAttribute('x2',right);});
 figure.querySelectorAll('.track-detail').forEach(el=>el.style.display=narrow?'none':'');
 for(const el of figure.querySelectorAll('[data-start]')){
  const a=pos(el.dataset.start),b=pos(el.dataset.end);
  if(el.tagName==='line'){el.setAttribute('x1',a);el.setAttribute('x2',b);}
  else if(el.tagName==='rect'){el.setAttribute('x',a);el.setAttribute('width',Math.max(2,b-a));}
  else{el.setAttribute('x',a+7);el.style.display=!narrow&&(b-a)>el.textContent.length*13+14?'':'none';}
 }
 for(const el of figure.querySelectorAll('[data-mid]')){
  el.setAttribute('x',pos(el.dataset.mid));
  const room=pos(el.dataset.phaseEnd)-pos(el.dataset.phaseStart);
  el.style.display=room>el.textContent.length*12+8?'':'none';
 }
 for(const el of figure.querySelectorAll('[data-at]')){
  const e=eventMap.get(el.dataset.event),y=e?ys.get(e.track):Number(el.dataset.y),x=pos(el.dataset.at);
  if(el.tagName==='g'){el.style.display=y===undefined?'none':'';if(y!==undefined)el.setAttribute('transform',`translate(${x},${y})`);}
  else{el.setAttribute('x',x);if(el.classList.contains('event-label')){
   // Event labels live outside row groups, so follow the corresponding identity.
   const original=Number(el.dataset.y)+17,tid=model.tracks.find((t,i)=>y0+i*row===original)?.id;
   el.style.display=narrow||tid&&!ys.has(tid)?'none':'';
   if(tid&&ys.has(tid))el.setAttribute('y',ys.get(tid)-17);
  }}
 }
 for(const path of figure.querySelectorAll('[data-from]')){
  const a=eventMap.get(path.dataset.from),b=eventMap.get(path.dataset.to);
  if(!ys.has(a.track)||!ys.has(b.track))continue;
  const xa=pos(a.at),xb=pos(b.at),ya=ys.get(a.track),yb=ys.get(b.track),m=(xa+xb)/2;
  path.setAttribute('d',`M${xa},${ya} C${m},${ya} ${m},${yb} ${xb},${yb}`);
 }
 const axis=figure.querySelector('.timeline-axis');axis.replaceChildren();
 const ns='http://www.w3.org/2000/svg',ticks=narrow?2:6;
 for(let i=0;i<=(figure.dataset.timeKnown==='true'?ticks:-1);i++){
  const t=max*i/ticks,x=pos(t),line=document.createElementNS(ns,'line'),label=document.createElementNS(ns,'text');
  for(const [k,v] of Object.entries({x1:x,x2:x,y1:119,y2:h-76,class:'grid decor',opacity:'.5'}))line.setAttribute(k,v);
  for(const [k,v] of Object.entries({x,y:145,'text-anchor':'middle',class:'secondary muted'}))label.setAttribute(k,v);
  label.textContent=`${Number((t/60).toFixed(1))}分`;axis.append(line,label);
 }
 if(figure.dataset.timeKnown!=='true'){
  const label=document.createElementNS(ns,'text');label.setAttribute('x',left);label.setAttribute('y',145);label.textContent='时间未定位';axis.append(label);
 }
 figure.querySelectorAll('.footer').forEach(el=>el.style.display='none');
 refresh();
}
function save(){window.openai?.setWidgetState?.({modelContent:{event:selected||null},privateContent:{event:selected,collapsed:[...collapsed]}}).catch(()=>{});}
select.addEventListener('change',()=>{
 selected=select.value;const item=items.get(selected);if(item)collapsed.delete(item.track.split('.')[0]);
 for(const id of activeSet()){const event=eventMap.get(id);if(event)collapsed.delete(event.track.split('.')[0]);}
 layout();save();
});
for(const button of root.querySelectorAll('[data-main]'))button.addEventListener('click',()=>{
 const id=button.dataset.main;if(collapsed.has(id))collapsed.delete(id);else collapsed.add(id);layout();save();
});
figure.addEventListener('click',event=>{
 const mark=event.target.closest('[data-event],[data-segment]');
 if(mark){select.value=mark.dataset.event||'span:'+mark.dataset.segment;select.dispatchEvent(new Event('change'));}
});
window.addEventListener('openai:set_globals',event=>{
 const state=event.detail?.globals?.widgetState?.privateContent,next=state?.event;
 if(typeof next==='string'&&(next===''||items.has(next))){selected=next;if(Array.isArray(state.collapsed))collapsed=new Set(state.collapsed);layout();}
});
new ResizeObserver(layout).observe(root.querySelector('[data-figure]'));layout();
