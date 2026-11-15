#!/usr/bin/env node
/* Render local Markdown to reviewable raster pages. No network assets or bundled private paths.
 * Required: --input --output-dir --node-modules --mathjax-script --mathjax-font-dir
 *           --font-regular (and preferably --font-bold).
 * Example arguments are intentionally path-neutral; use --help for the complete interface.
 */
'use strict';
const fs=require('fs');
const path=require('path');
const crypto=require('crypto');
const {pathToFileURL}=require('url');

function parseArgs(argv){
 const args={};
 for(let i=0;i<argv.length;i++){
  if(!argv[i].startsWith('--'))throw Error('Expected an option, got '+argv[i]);
  const key=argv[i].slice(2);
  if(['help','diagnostic','fixed-height','light','layout-only','invert-formula-images'].includes(key))args[key]=true;
  else{if(i+1>=argv.length||argv[i+1].startsWith('--'))throw Error('Missing value for --'+key);args[key]=argv[++i];}
 }
 return args;
}
function escaped(s,i){let n=0;while(i>0&&s[--i]==='\\')n++;return n%2===1;}
function protectMath(source){
 const maths=[],issues=[];let result='',i=0,fence=null;
 while(i<source.length){
  if(i===0||source[i-1]==='\n'){
   const lineEnd=source.indexOf('\n',i);const end=lineEnd<0?source.length:lineEnd+1;
   const line=source.slice(i,end);const m=line.match(/^ {0,3}(`{3,}|~{3,})/);
   if(m){if(!fence)fence={char:m[1][0],count:m[1].length};else if(m[1][0]===fence.char&&m[1].length>=fence.count)fence=null;result+=line;i=end;continue;}
   if(fence){result+=line;i=end;continue;}
  }
  if(source[i]==='`'&&!escaped(source,i)){
   let n=1;while(source[i+n]==='`')n++;const close=source.indexOf('`'.repeat(n),i+n);
   if(close>=0){result+=source.slice(i,close+n);i=close+n;continue;}
  }
  let open='',close='',display=false;
  if(!escaped(source,i)&&source.startsWith('\\[',i)){open='\\[';close='\\]';display=true;}
  else if(!escaped(source,i)&&source.startsWith('\\(',i)){open='\\(';close='\\)';}
  else if(source[i]==='$'&&!escaped(source,i)){display=source[i+1]==='$';open=display?'$$':'$';close=open;}
  if(!open){result+=source[i++];continue;}
  let j=i+open.length,end=-1;
  while(j<source.length){
   if(!display&&source[j]==='\n')break;
   if(source.startsWith(close,j)&&!escaped(source,j)&&(close!=='$'||source[j+1]!=='$')){end=j;break;}
   j++;
  }
  if(end<0){if(open!=='$')issues.push({kind:'unclosed-math-delimiter',delimiter:open,line:source.slice(0,i).split('\n').length});result+=source[i++];continue;}
  const tex=source.slice(i+open.length,end).trim();
  if(!tex){result+=source.slice(i,end+close.length);i=end+close.length;continue;}
  const id=maths.length;maths.push({id,tex,display,line:source.slice(0,i).split('\n').length,delimiter:open});
  const token='PAPERMATHSLOTZZ'+id+'ZZEND';
  result+=display?'\n\n<div class="formula" data-math-id="'+id+'">'+token+'</div>\n\n':token;
  i=end+close.length;
 }
 return {markdown:result,maths,issues};
}
function displayLayout(tex){
 const labels=[];let body='',cursor=0;const tag=/\\tag\*?\s*\{/g;let match;
 while((match=tag.exec(tex))){let depth=1,j=tag.lastIndex;for(;j<tex.length&&depth;j++){if(tex[j]==='{'&&!escaped(tex,j))depth++;else if(tex[j]==='}'&&!escaped(tex,j))depth--;}if(depth)break;body+=tex.slice(cursor,match.index);labels.push(tex.slice(tag.lastIndex,j-1));cursor=j;tag.lastIndex=j;}
 body+=tex.slice(cursor);
 let depth=0,environment=0,start=0;const pieces=[];
 for(let i=0;i<body.length;i++){
  if(body.startsWith('\\begin{',i))environment++;
  else if(body.startsWith('\\end{',i))environment--;
  if(body[i]==='{'&&!escaped(body,i))depth++;else if(body[i]==='}'&&!escaped(body,i))depth--;
  if(depth===0&&environment===0&&body.startsWith('\\qquad',i)){pieces.push(body.slice(start,i));start=i+6;i+=5;}
 }
 if(pieces.length){pieces.push(body.slice(start));body='\\begin{gathered}'+pieces.join('\\\\')+'\\end{gathered}';}
 return {tex:body,labels,splitAtQquad:pieces.length>0};
}
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const digest=s=>crypto.createHash('sha256').update(s).digest('hex');
const help=`Render local Markdown, preserving inline/display math and local images.
Required:
 --input FILE --output-dir DIR --node-modules DIR
 --mathjax-script FILE --mathjax-font-dir DIR --font-regular FILE
Optional:
 --font-bold FILE             Local bold font; otherwise use regular font without synthesis.
 --title TEXT --browser-channel NAME --browser-executable FILE
 --page-width 780 --page-height 1260 --font-size 32 --preview-width 390
 --device-scale 2 --min-math-scale 0.875 --table-mode auto|rows|cards
 --temp-dir DIR --fixed-height --light --invert-formula-images
 --diagnostic                Capture known layout problems; output is marked NEEDS_REVIEW.
 --layout-only               Inspect layout without capturing raster pages.
 --capture-pages RANGES      Capture selected source pages, e.g. 1-8,30-40.
Default output uses equal page widths and content-dependent heights. Remote requests are blocked.
Long expressions needing source line breaks are reported; diagnostic mode may shrink them further.
The report establishes file/layout facts, not mathematical correctness or learning.`;

async function main(){
 const a=parseArgs(process.argv.slice(2));if(a.help){console.log(help);return;}
 const required=['input','output-dir','node-modules','mathjax-script','mathjax-font-dir','font-regular'];
 for(const key of required)if(!a[key])throw Error('Required --'+key+'\n'+help);
 const input=path.resolve(a.input),out=path.resolve(a['output-dir']);
 const settings={width:Number(a['page-width']||780),height:Number(a['page-height']||1260),font:Number(a['font-size']||32),preview:Number(a['preview-width']||390),scale:Number(a['device-scale']||2),minMathScale:Number(a['min-math-scale']||0.875),tableMode:a['table-mode']||'auto',diagnostic:!!a.diagnostic,variableHeight:!a['fixed-height'],light:!!a.light,invertFormulaImages:!!a['invert-formula-images']};
 for(const key of ['width','height','font','preview','scale'])if(!(settings[key]>0))throw Error('Invalid positive number: '+key);
 if(!['auto','rows','cards'].includes(settings.tableMode))throw Error('Invalid --table-mode');
 for(const key of ['input','mathjax-script','mathjax-font-dir','font-regular'])if(!fs.existsSync(path.resolve(a[key])))throw Error('Missing '+key+': '+a[key]);
 if(a['font-bold']&&!fs.existsSync(path.resolve(a['font-bold'])))throw Error('Missing bold font');
 fs.mkdirSync(out,{recursive:true});const shots=path.join(out,'pages');fs.mkdirSync(shots,{recursive:true});
 const temp=path.resolve(a['temp-dir']||path.join(out,'browser-tmp'));fs.mkdirSync(temp,{recursive:true});
 process.env.TEMP=temp;process.env.TMP=temp;process.env.TMPDIR=temp;
 const modules=path.resolve(a['node-modules']);const {marked}=require(path.join(modules,'marked'));const {chromium}=require(path.join(modules,'playwright'));
 const source=fs.readFileSync(input,'utf8');const protectedSource=protectMath(source);const maths=protectedSource.maths;
 let content=marked.parse(protectedSource.markdown,{gfm:true});
 let labelMathCount=0;
 content=content.replace(/PAPERMATHSLOTZZ(\d+)ZZEND/g,(_,id)=>{
  const item=maths[+id];if(!item.display)return '<span class="inline-math" data-math-id="'+id+'">\\('+esc(item.tex)+'\\)</span>';
  const layout=displayLayout(item.tex);item.layout_tex=layout.tex;item.labels=layout.labels;item.split_at_qquad=layout.splitAtQquad;
  return '\\['+esc(layout.tex)+'\\]'+layout.labels.map(label=>{const hasMath=/\\/.test(label);if(hasMath)labelMathCount++;return '<div class="formula-label">'+(hasMath?'\\('+esc(label)+'\\)':esc(label))+'</div>';}).join('');
 });
 content=content.replace(/\bsrc=(['"])([^'"]+)\1/g,(all,q,src)=>/^[A-Za-z]:[\\/]/.test(src)?'src='+q+pathToFileURL(src).href+q:all);
 content=content.replace(/<script\b[^>]*>[\s\S]*?<\/script\s*>/gi,'');
 const pad=44,top=77,bottom=65,contentWidth=settings.width-2*pad,contentHeight=settings.height-top-bottom;
 if(contentWidth<240||contentHeight<300)throw Error('Page dimensions leave too little content space');
 const title=a.title||(source.match(/^#\s+(.+)$/m)||[])[1]||path.basename(input,path.extname(input));
 const fontURL=p=>pathToFileURL(path.resolve(p)).href;
 const config={tex:{inlineMath:[['\\(','\\)']],displayMath:[['\\[','\\]']],processEscapes:true},chtml:{fontURL:fontURL(a['mathjax-font-dir']),mtextInheritFont:true},options:{enableMenu:false}};
 const bg=settings.light?'#fff':'#000',fg=settings.light?'#111':'#f5f5f5',muted=settings.light?'#555':'#c9c9c9';
 const css=`
@font-face{font-family:PaperSans;src:url('${fontURL(a['font-regular'])}');font-weight:400;font-display:block}
@font-face{font-family:PaperSans;src:url('${fontURL(a['font-bold']||a['font-regular'])}');font-weight:700;font-display:block}
*{box-sizing:border-box}html,body{margin:0;background:${bg};color:${fg};font-family:PaperSans,sans-serif;font-size:${settings.font}px;line-height:1.62;font-synthesis:none}
#source,#measure{width:${contentWidth}px}#source{margin:0 ${pad}px}#measure{position:absolute;left:-10000px;top:0}
h1{font-size:1.31em;line-height:1.38;margin:0 0 23px}h2{font-size:1.16em;line-height:1.4;margin:24px 0 20px}h3{font-size:1.06em;line-height:1.5;margin:22px 0 18px}h4,h5,h6{font-size:1em;margin:20px 0 17px;line-height:1.5}p{margin:0 0 23px;overflow-wrap:break-word}a{color:inherit}strong{font-weight:700}
ul,ol{margin:0 0 22px;padding-left:1.15em}li{padding-left:.1em;margin:0 0 12px}li p{margin-bottom:12px}blockquote{margin:0 0 23px;padding-left:19px;border-left:3px solid #666}pre{margin:0 0 23px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:.88em;line-height:1.55}code{font-family:Consolas,monospace;font-size:.91em}pre code{font-size:1em}hr{border:0;border-top:1px solid #666;margin:20px 0}
.formula{font-size:${settings.font}px;line-height:1.3;margin:7px 0 21px;text-align:center}.formula mjx-container[display=true]{margin:0!important}.formula-label{font-size:${settings.font*.875}px;line-height:1.5;margin-top:8px;color:${muted};overflow-wrap:break-word}mjx-container{color:${fg}!important}
.asset{margin:14px 0 19px;line-height:0;text-align:center}.asset img{display:block;margin:auto;max-width:100%;height:auto;object-fit:contain}.math-image img{${settings.invertFormulaImages&&!settings.light?'filter:grayscale(1) invert(1);':''}}
table{width:100%;border-collapse:collapse;font-size:.94em;line-height:1.55;margin:0 0 22px}.table-row-fragment{margin-bottom:0;table-layout:fixed}.table-row-fragment.table-last-row{margin-bottom:22px}th,td{padding:9px 6px;border-bottom:1px solid #555;text-align:left;vertical-align:top;overflow-wrap:break-word}thead{font-weight:700}.table-card{border-top:1px solid #555;padding:12px 0 6px;margin-bottom:22px}.table-field{margin:0 0 15px}.field-label{display:block;font-weight:700;font-size:.91em;color:${muted};margin-bottom:3px}.field-body{display:block;font-size:.94em}.table-legend{font-size:.88em;line-height:1.5;margin:0 0 16px;color:${muted}}.table-legend>*{display:inline}.table-legend>*+*::before{content:' / '}
.group{display:flow-root}.page{position:relative;width:${settings.width}px;height:${settings.height}px;padding:${top}px ${pad}px ${bottom}px;background:${bg};overflow:hidden;margin:20px 0}.page-content{width:${contentWidth}px;height:${contentHeight}px;display:flow-root}.running{position:absolute;left:${pad}px;right:${pad}px;top:22px;line-height:26px;font-size:19px;color:${muted};border-bottom:1px solid #444;padding-bottom:9px;display:flex;justify-content:space-between;gap:22px}.running span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.running span:first-child{max-width:42%}.running span:last-child{max-width:58%}.footer{position:absolute;left:${pad}px;right:${pad}px;bottom:20px;font-size:19px;line-height:24px;color:${muted};border-top:1px solid #444;padding-top:9px;display:flex;justify-content:space-between;gap:20px}.footer span:first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
`;
 const htmlPath=path.join(out,'source.html');fs.writeFileSync(htmlPath,`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><base href="${pathToFileURL(path.dirname(input)+path.sep).href}"><title>${esc(title)}</title><style>${css}</style><script>window.MathJax=${JSON.stringify(config)}</script><script src="${fontURL(a['mathjax-script'])}"></script></head><body><article id="source">${content}</article><div id="measure"></div><main id="pages"></main></body></html>`);
 const report={schema_version:1,input,source_sha256:digest(source),renderer_sha256:digest(fs.readFileSync(__filename)),output_dir:out,title,settings,math_inputs:maths,math_count:maths.length,math_parse_issues:protectedSource.issues,request_failures:[],remote_requests:[],screenshots:[]};
 fs.writeFileSync(path.join(out,'render-report.json'),JSON.stringify({...report,status:'STARTED'},null,2));
 const launch={headless:true,viewport:{width:settings.width+40,height:settings.height+60},deviceScaleFactor:settings.scale,args:['--allow-file-access-from-files','--disable-crash-reporter','--disable-dev-shm-usage','--disk-cache-dir='+path.join(temp,'cache')],env:{...process.env,TEMP:temp,TMP:temp,TMPDIR:temp}};
 if(a['browser-channel'])launch.channel=a['browser-channel'];if(a['browser-executable'])launch.executablePath=path.resolve(a['browser-executable']);
 const context=await chromium.launchPersistentContext(path.join(temp,'profile'),launch);
 try{
  await context.route(/^https?:\/\//,route=>{report.remote_requests.push(route.request().url());return route.abort('blockedbyclient');});
  const page=context.pages()[0]||await context.newPage();page.on('requestfailed',r=>report.request_failures.push({url:r.url(),error:r.failure()?.errorText}));
  await page.goto(pathToFileURL(htmlPath).href,{waitUntil:'domcontentloaded',timeout:60000});
  await page.waitForFunction(()=>window.MathJax?.startup?.promise,{timeout:60000});await page.evaluate(()=>MathJax.startup.promise);await page.evaluate(()=>document.fonts.ready);
  report.preparation=await page.evaluate(async({contentWidth,contentHeight,settings,maths})=>{
   const errors=[...document.querySelectorAll('mjx-merror')].map(e=>({text:e.textContent,id:e.closest('[data-math-id]')?.dataset.mathId}));
   const images=[];for(const img of document.images){try{await img.decode();}catch{}const p=img.closest('p');if(p)p.classList.add('asset');if(p&&(/(?:原式|公式|equation|formula)/i.test(img.alt)||/(?:^|[/_-])eq[-_]?\d/i.test(img.getAttribute('src')||'')))p.classList.add('math-image');const h=img.naturalHeight,w=img.naturalWidth;const scale=Math.min(1,contentWidth/w,contentHeight*.72/h);img.style.width=(w*scale)+'px';img.style.height=(h*scale)+'px';images.push({src:img.src,alt:img.alt,width:w,height:h,renderWidth:w*scale,renderHeight:h*scale,restrictedByHeight:h*scale>=contentHeight*.72-1,loaded:!!(img.complete&&w)});}
   const fits=[],changed=[];for(const el of document.querySelectorAll('.formula')){const math=el.querySelector('mjx-math');if(!math)continue;const w=math.getBoundingClientRect().width,scale=Math.min(1,(contentWidth-6)/w);if(scale<1){el.style.fontSize=(settings.font*scale)+'px';changed.push(el);}fits.push({id:+el.dataset.mathId,width:w,scale,needsSourceBreak:scale<settings.minMathScale,equivalentPreviewFontPx:settings.font*scale*settings.preview/settings.width});}
   // Inherited CJK text is measured in pixels by CHTML. Re-typesetting after a font change
   // refreshes that measurement; merely changing a parent's font-size can leave overflowing text.
   if(changed.length){MathJax.typesetClear(changed);for(const el of changed){const item=maths[+el.dataset.mathId];el.replaceChildren(document.createTextNode('\\['+item.layout_tex+'\\]'));for(const label of item.labels||[]){const caption=document.createElement('div');caption.className='formula-label';caption.textContent=/\\/.test(label)?'\\('+label+'\\)':label;el.append(caption);}}await MathJax.typesetPromise(changed);await document.fonts.ready;}
   for(const fit of fits){const el=document.querySelector('.formula[data-math-id="'+fit.id+'"]');fit.renderedWidth=el.querySelector('mjx-math').getBoundingClientRect().width;}
   const inlineOverflow=[...document.querySelectorAll('.inline-math')].filter(el=>el.getBoundingClientRect().width>contentWidth).map(el=>({id:+el.dataset.mathId,width:el.getBoundingClientRect().width}));
   return {errors,images,fits,inlineOverflow,mathContainers:document.querySelectorAll('mjx-container').length,fonts:[...document.fonts].map(f=>({family:f.family,weight:f.weight,status:f.status}))};
  },{contentWidth,contentHeight,settings,maths});
  const fatal=report.math_parse_issues.length||report.preparation.errors.length||report.preparation.images.some(x=>!x.loaded)||report.preparation.mathContainers!==maths.length+labelMathCount||report.remote_requests.length||report.request_failures.length;
  const wide=report.preparation.fits.filter(x=>x.needsSourceBreak).length+report.preparation.inlineOverflow.length;
  if(fatal||wide&&!settings.diagnostic){report.status=fatal?'FAILED_ASSETS_OR_MATH':'NEEDS_SOURCE_LINE_BREAKS';fs.writeFileSync(path.join(out,'render-report.json'),JSON.stringify(report,null,2));throw Error(report.status+'; inspect '+path.join(out,'render-report.json'));}
  report.layout=await page.evaluate(({contentWidth,contentHeight,settings,title,pad,top,bottom})=>{
   const source=document.querySelector('#source'),measure=document.querySelector('#measure');const norm=s=>s.replace(/\s+/g,'');let serial=0;
   const tracked=[...source.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,pre,th,td')];
   for(const el of tracked)el.dataset.sourceUnit=String(serial++);
   const expected=new Map(tracked.map(el=>[el.dataset.sourceUnit,norm(el.textContent)]));const expectedOrder=tracked.map(el=>el.dataset.sourceUnit);
   const originalImages=[...source.querySelectorAll('img')].map(i=>i.getAttribute('src'));
   const splits=[],tables=[],issues=[];const cleanRepeat=el=>{el.dataset.repeat='true';el.removeAttribute('data-source-unit');for(const n of el.querySelectorAll('[data-source-unit]'))n.removeAttribute('data-source-unit');return el;};
   const height=el=>{measure.append(el);const h=el.getBoundingClientRect().height;el.remove();return h;};
   const partsOfParagraph=el=>{
    const tokens=[];
    const walk=node=>{if(node.nodeType===Node.TEXT_NODE){for(const s of (node.textContent.match(/[^。！？；\n]+[。！？；\n]?|[。！？；\n]/g)||[]))tokens.push(document.createTextNode(s));}
     else if(node.nodeType===Node.ELEMENT_NODE){if(node.tagName==='MJX-CONTAINER'||node.classList.contains('inline-math'))tokens.push(node.cloneNode(true));else{const old=tokens.length;for(const c of node.childNodes)walk(c);const child=tokens.splice(old);for(const token of child){const w=node.cloneNode(false);w.removeAttribute('data-source-unit');w.append(token);tokens.push(w);}}}};
    for(const node of el.childNodes)walk(node);const parts=[];let p=el.cloneNode(false);measure.append(p);
    for(const token of tokens){p.append(token);if(p.getBoundingClientRect().height>contentHeight-12&&p.childNodes.length>1){token.remove();parts.push(p);p.remove();p=el.cloneNode(false);p.append(token);measure.append(p);}}
    if(p.childNodes.length)parts.push(p);p.remove();splits.push({type:'paragraph',unit:el.dataset.sourceUnit,parts:parts.length});return parts;
   };
   const tableParts=table=>{
    const head=table.tHead;const headers=[...(head?.rows[0]?.cells||[])];const headerTemplates=headers.map(h=>h.cloneNode(true));const tableWidth=table.getBoundingClientRect().width;const widths=headers.map(h=>h.getBoundingClientRect().width/tableWidth*100);const bodyRows=[...table.tBodies].flatMap(b=>[...b.rows]);const cols=Math.max(headers.length,...bodyRows.map(r=>r.cells.length));const texts=bodyRows.flatMap(r=>[...r.cells].map(c=>c.textContent.length));
    const useCards=settings.tableMode==='cards'||settings.tableMode==='auto'&&(cols>=4||cols>=3&&(Math.max(0,...texts)>65||headers.some(h=>h.getBoundingClientRect().width<settings.font*3)));
    const record={index:tables.length,columns:cols,rows:bodyRows.length,mode:useCards?'cards':'rows'};tables.push(record);const parts=[];
    if(useCards){
     const legend=document.createElement('div');legend.className='table-legend';for(const h of headers){const s=document.createElement('span');s.dataset.sourceUnit=h.dataset.sourceUnit;s.append(...h.childNodes);legend.append(s);}if(headers.length)parts.push(legend);
     for(let rowIndex=0;rowIndex<bodyRows.length;rowIndex++){
      const card=document.createElement('div');card.className='table-card';card.dataset.table=String(record.index);card.dataset.row=String(rowIndex);
      [...bodyRows[rowIndex].cells].forEach((cell,i)=>{const field=document.createElement('div');field.className='table-field';const label=document.createElement('span');label.className='field-label';label.dataset.repeat='true';if(headerTemplates[i])label.append(...headerTemplates[i].cloneNode(true).childNodes);else label.textContent=String(i+1);const body=document.createElement('div');body.className='field-body';body.dataset.sourceUnit=cell.dataset.sourceUnit;body.append(...cell.childNodes);field.append(label,body);card.append(field);});
      if(height(card)>contentHeight-15){const fields=[...card.children];for(const field of fields){const section=document.createElement('div');section.className='table-card';section.dataset.table=String(record.index);section.dataset.row=String(rowIndex);section.append(field);parts.push(section);}splits.push({type:'table-card-fields',table:record.index,row:rowIndex,parts:fields.length});}else parts.push(card);
     }
    }else{
     bodyRows.forEach((row,i)=>{const part=document.createElement('table');part.className='table-row-fragment'+(i===bodyRows.length-1?' table-last-row':'');part.dataset.table=String(record.index);part.dataset.row=String(i);if(widths.length){const cg=document.createElement('colgroup');for(const width of widths){const col=document.createElement('col');col.style.width=width+'%';cg.append(col);}part.append(cg);}if(head)part.append(i===0?head:cleanRepeat(head.cloneNode(true)));const body=document.createElement('tbody');body.append(row);part.append(body);parts.push(part);});
    }
    return parts;
   };
   const units=[];
   for(const el of [...source.children]){
    if(el.tagName==='TABLE'){units.push(...tableParts(el));continue;}
    if(el.tagName==='OL'||el.tagName==='UL'){let n=Number(el.getAttribute('start')||1);for(const li of [...el.children]){const list=el.cloneNode(false);if(el.tagName==='OL')list.start=n++;list.append(li);units.push(list);}continue;}
    if(el.tagName==='PRE'&&height(el)>contentHeight-12){const lines=el.textContent.match(/[^\n]*\n|[^\n]+$/g)||[];let pre=el.cloneNode(false),code=document.createElement('code');pre.append(code);measure.append(pre);const pieces=[];for(const line of lines){code.textContent+=line;if(pre.getBoundingClientRect().height>contentHeight-12&&code.textContent.length>line.length){code.textContent=code.textContent.slice(0,-line.length);pieces.push(pre);pre.remove();pre=el.cloneNode(false);code=document.createElement('code');code.textContent=line;pre.append(code);measure.append(pre);}}if(code.textContent)pieces.push(pre);pre.remove();units.push(...pieces);splits.push({type:'code-lines',unit:el.dataset.sourceUnit,parts:pieces.length});continue;}
    if(el.tagName==='P'&&!el.querySelector('img')&&height(el)>contentHeight-12)units.push(...partsOfParagraph(el));else units.push(el);
   }
   const groups=[];let pending=[];
   const add=els=>{const group=document.createElement('div');group.className='group';group.dataset.group=String(groups.length);for(const el of els)group.append(el);const h=height(group);if(h>contentHeight+1&&els.length>1){issues.push({kind:'oversized-semantic-group',height:h,text:group.textContent.slice(0,180)});if(!settings.diagnostic)throw Error('Oversized semantic group: '+group.textContent.slice(0,120));const last=els.pop();add(els);add([last]);return;}if(h>contentHeight+1)issues.push({kind:'oversized-unit',height:h,text:group.textContent.slice(0,180)});groups.push(group);};
   for(let i=0;i<units.length;i++){
    const child=units[i];if(/^H[1-6]$/.test(child.tagName)||child.tagName==='HR'){pending.push(child);continue;}
    const els=[...pending,child];pending=[];
    if(child.classList.contains('table-legend')&&units[i+1]?.classList.contains('table-card'))els.push(units[++i]);
    else if(child.classList.contains('asset')){if(units[i+1]?.tagName==='P')els.push(units[++i]);if(units[i+1]?.tagName==='P'&&/^(?:原图|原式|期刊|预印本|图\s*\d|式\s*[（(]?\d)/.test(els.at(-1).textContent.trim())&&height(child)+height(els.at(-1))+height(units[i+1])<contentHeight-70)els.push(units[++i]);}
    else if(child.classList.contains('formula')&&units[i+1]?.tagName==='P')els.push(units[++i]);
    else if(child.tagName==='P'&&/[:：]$/.test(child.textContent.trim())&&units[i+1]?.classList.contains('formula')){els.push(units[++i]);if(units[i+1]?.tagName==='P')els.push(units[++i]);}
    else if(child.tagName==='P'&&child.textContent.length<170&&/(?:[:：]$|如下图|下图|见图)/.test(child.textContent.trim())&&units[i+1]?.classList.contains('asset')){els.push(units[++i]);if(units[i+1]?.tagName==='P')els.push(units[++i]);}
    add(els);
   }
   if(pending.length)add(pending);
   const pages=document.querySelector('#pages');let current,section='正文';
   const newPage=()=>{const sheet=document.createElement('section');sheet.className='page';sheet.dataset.page=String(pages.children.length+1);const header=document.createElement('header');header.className='running';const left=document.createElement('span'),right=document.createElement('span');left.textContent=title;right.textContent=section;header.append(left,right);const inner=document.createElement('div');inner.className='page-content';const footer=document.createElement('footer');footer.className='footer';const fleft=document.createElement('span'),fright=document.createElement('span');fleft.textContent='';footer.append(fleft,fright);sheet.append(header,inner,footer);pages.append(sheet);current=inner;};newPage();
   for(const group of groups){const hs=group.querySelectorAll('h2,h3,h4');if(hs.length)section=hs[hs.length-1].textContent;const table=group.querySelector('table.table-row-fragment');let removedHead=null;if(table&&current.querySelector('table[data-table="'+table.dataset.table+'"]')&&table.tHead?.hasAttribute('data-repeat')){removedHead=table.tHead;removedHead.remove();}current.append(group);if(group.getBoundingClientRect().bottom>current.getBoundingClientRect().bottom+1&&current.children.length>1){group.remove();if(removedHead)table.insertBefore(removedHead,table.tBodies[0]);newPage();current.append(group);}}
   const sheets=[...pages.children];sheets.forEach((s,i)=>s.querySelector('.footer span:last-child').textContent=(i+1)+' / '+sheets.length);
   const overflow=[],details=[],headings=[],links=[];let headingSerial=0;
   for(let i=0;i<sheets.length;i++){
    const sheet=sheets[i],area=sheet.querySelector('.page-content').getBoundingClientRect();const gs=[...sheet.querySelectorAll('.group')];const contentBottom=gs.at(-1)?.getBoundingClientRect().bottom-area.top||0;const pageHeight=settings.variableHeight?Math.ceil(Math.max(280,contentBottom+top+bottom)):settings.height;sheet.style.height=pageHeight+'px';
    const box=sheet.getBoundingClientRect(),footerTop=sheet.querySelector('.footer').getBoundingClientRect().top;
    for(const el of sheet.querySelectorAll('.group,mjx-math,img,pre,table')){const r=el.getBoundingClientRect();if(r.right>area.right+2||r.left<area.left-2||r.bottom>footerTop-1)overflow.push({page:i+1,tag:el.tagName,mathId:el.closest('[data-math-id]')?.dataset.mathId,text:el.textContent.slice(0,100),left:r.left-area.left,right:r.right-area.right,bottom:r.bottom-footerTop});}
    for(const h of sheet.querySelectorAll('h1,h2,h3,h4,h5,h6')){if(!h.id)h.id='paper-heading-'+(++headingSerial);headings.push({id:h.id,text:h.textContent,level:+h.tagName[1],page:i+1,y:h.getBoundingClientRect().top-box.top});}
    for(const a of sheet.querySelectorAll('a[href]')){const r=a.getBoundingClientRect();links.push({page:i+1,href:a.getAttribute('href'),text:a.textContent,rect:[r.left-box.left,r.top-box.top,r.right-box.left,r.bottom-box.top]});}
    details.push({page:i+1,width:settings.width,height:pageHeight,contentBottom,section:sheet.querySelector('.running span:last-child').textContent,groups:gs.map(g=>+g.dataset.group),math_ids:[...sheet.querySelectorAll('.formula[data-math-id]')].map(e=>+e.dataset.mathId),images:[...sheet.querySelectorAll('img')].filter(e=>!e.closest('[data-repeat]')).map(e=>({src:e.src,alt:e.alt}))});
   }
   const actualNodes=[...pages.querySelectorAll('[data-source-unit]')].filter(n=>!n.closest('[data-repeat]'));const actual=new Map(),order=[];for(const el of actualNodes){const id=el.dataset.sourceUnit;if(!actual.has(id)){actual.set(id,'');order.push(id);}actual.set(id,actual.get(id)+norm(el.textContent));}
   const missing=[],changed=[];for(const [id,text]of expected){if(!actual.has(id))missing.push(id);else if(actual.get(id)!==text)changed.push({id,before:text.slice(0,100),after:actual.get(id).slice(0,100)});}
   const actualImages=[...pages.querySelectorAll('img')].filter(n=>!n.closest('[data-repeat]')).map(i=>i.getAttribute('src'));
   const integrity={source_units:expected.size,output_units:actual.size,missing,changed,unitOrderPreserved:JSON.stringify(expectedOrder)===JSON.stringify(order),imagesPreserved:JSON.stringify(originalImages)===JSON.stringify(actualImages)};
   if(missing.length||changed.length||!integrity.unitOrderPreserved||!integrity.imagesPreserved)issues.push({kind:'content-integrity',...integrity});
   source.remove();measure.remove();return {pages:sheets.length,details,headings,links,tables,splits,issues,overflow,integrity};
  },{contentWidth,contentHeight,settings,title,pad,top,bottom});
  const broken=report.layout.overflow.length||report.layout.issues.length;
  report.status=wide||broken?'NEEDS_REVIEW':'RENDERED';
  fs.writeFileSync(path.join(out,'render-report.json'),JSON.stringify(report,null,2));
  if(broken&&!settings.diagnostic)throw Error('Layout/content issues; inspect render-report.json');
  if(a['layout-only']){fs.writeFileSync(path.join(out,'rendered.html'),await page.content());fs.writeFileSync(path.join(out,'render-report.json'),JSON.stringify({...report,capture_status:'NOT_REQUESTED'},null,2));console.log(JSON.stringify({status:report.status,pages:report.layout.pages,math:maths.length,images:report.preparation.images.length,wide_math:wide,issues:report.layout.issues.length,overflow:report.layout.overflow.length,report:path.join(out,'render-report.json')}));return;}
  let capturePages=Array.from({length:report.layout.pages},(_,i)=>i+1);
  if(a['capture-pages']){capturePages=[];for(const part of a['capture-pages'].split(',')){const m=part.trim().match(/^(\d+)(?:-(\d+))?$/);if(!m)throw Error('Invalid --capture-pages');const start=+m[1],end=+(m[2]||m[1]);for(let p=start;p<=end;p++)capturePages.push(p);}if(!capturePages.length||capturePages.some((p,i)=>p<1||p>report.layout.pages||i&&p<=capturePages[i-1]))throw Error('Capture pages must be ascending unique ranges within the layout');}
  for(let n=0;n<capturePages.length;n++){
   const i=capturePages[n]-1;
   const file=path.join(shots,'page-'+String(i+1).padStart(4,'0')+'.png');await page.locator('.page').nth(i).screenshot({path:file,animations:'disabled',timeout:60000});report.screenshots.push({page:i+1,file,sha256:digest(fs.readFileSync(file)),css_width:report.layout.details[i].width,css_height:report.layout.details[i].height});
   if((n+1)%20===0||n+1===capturePages.length)console.log(JSON.stringify({captured:n+1,requested:capturePages.length,source_pages:report.layout.pages,status:report.status}));
  }
  fs.writeFileSync(path.join(out,'rendered.html'),await page.content());
  fs.writeFileSync(path.join(out,'render-report.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({status:report.status,pages:report.layout.pages,math:maths.length,images:report.preparation.images.length,wide_math:wide,issues:report.layout.issues.length,overflow:report.layout.overflow.length,report:path.join(out,'render-report.json')}));
 }catch(error){if(!report.layout&&report.status===undefined)report.status='FAILED';report.error=error.message;fs.writeFileSync(path.join(out,'render-report.json'),JSON.stringify(report,null,2));throw error;}
 finally{await context.close();}
}
if(require.main===module)main().catch(e=>{console.error(e.message);process.exitCode=1;});
module.exports={protectMath,displayLayout,parseArgs};
