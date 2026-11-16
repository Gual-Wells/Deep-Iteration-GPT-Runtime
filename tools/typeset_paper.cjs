#!/usr/bin/env node
/* Local Markdown -> standard portrait PDF. Browser-native pagination, real text,
 * local font/path mathematics, original-color figures. No network, screenshots, mail,
 * or private runtime paths are embedded in this tool. */
'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {pathToFileURL}=require('url');
const {protectMath,displayLayout}=require('./render_paper.cjs');
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function argsOf(argv){const a={};for(let i=0;i<argv.length;i++){if(!argv[i].startsWith('--'))throw Error('Expected option: '+argv[i]);const k=argv[i].slice(2);if(['help','diagnostic','layout-only','allow-internal-labels','no-chapter-breaks','no-keep-math-explanation','toc','no-toc','split-at-qquad'].includes(k))a[k]=true;else{if(!argv[i+1]||argv[i+1].startsWith('--'))throw Error('Missing value: --'+k);a[k]=argv[++i];}}return a;}
const help=`Typeset local Markdown as ONE searchable A4 portrait PDF.
Required: --input FILE --output-dir DIR --node-modules DIR
          --mathjax-script LOCAL_TEX_CHTML_OR_SVG_FULL_JS --font-regular FONT
Optional: --output FILE.pdf --font-bold FONT --font-heading FONT --font-heading-bold FONT
 --title TEXT --running-title TEXT --math-output svg|chtml --mathjax-font-dir LOCAL_WOFF_DIR
 --browser-channel chrome|msedge --browser-executable FILE --temp-dir DIR
 --body-pt 13.5 --min-body-pt 12 --math-pt 13.5 --min-math-pt 12
 --caption-pt 11 --caption-leading-pt 16 --table-pt 11 --code-pt 11 --line-height 1.5407407407
 --page-width-mm 210 --page-height-mm 297
 --margin-inner-mm 26 --margin-outer-mm 22 --margin-top-mm 23 --margin-bottom-mm 25
 --max-image-height-mm N --no-chapter-breaks --no-keep-math-explanation
 --toc --no-toc --toc-pages INSPECTION_JSON
 --diagnostic --layout-only --allow-internal-labels --split-at-qquad
Display spacing is preserved by default; opt into qquad splitting only for a
reviewed layout. Code size is explicit; identifiers are not forcibly broken.
No automatic text/math shrinking. Images may ENLARGE to the printable area;
height-limited images and effective DPI are reported for author review.
The PDF remains single-page portrait; two-page previews are made from the final
PDF by inspect_paper.py. A headless authoring run is not a GUI Chrome-view test.`;

async function main(){
 const a=argsOf(process.argv.slice(2));if(a.help){console.log(help);return;}
 for(const k of ['input','output-dir','node-modules','mathjax-script','font-regular'])if(!a[k])throw Error('Required --'+k+'\n'+help);
 const input=path.resolve(a.input),out=path.resolve(a['output-dir']);
 for(const k of ['input','mathjax-script','font-regular'])if(!fs.existsSync(path.resolve(a[k])))throw Error('Missing --'+k+': '+a[k]);
 const num=(k,d)=>{const n=Number(a[k]??d);if(!(n>0))throw Error('Invalid --'+k);return n;};
 const settings={mathOutput:a['math-output']||'chtml',bodyPt:num('body-pt',13.5),minBodyPt:num('min-body-pt',12),mathPt:num('math-pt',a['body-pt']||13.5),minMathPt:num('min-math-pt',12),captionPt:num('caption-pt',11),captionLeadingPt:num('caption-leading-pt',16),tablePt:num('table-pt',11),lineHeight:num('line-height',20.8/13.5),widthMm:num('page-width-mm',210),heightMm:num('page-height-mm',297),innerMm:num('margin-inner-mm',26),outerMm:num('margin-outer-mm',22),topMm:num('margin-top-mm',23),bottomMm:num('margin-bottom-mm',25),chapterBreaks:!a['no-chapter-breaks'],keepMathExplanation:!a['no-keep-math-explanation']};
 settings.codePt=num('code-pt',11);settings.splitAtQquad=!!a['split-at-qquad'];
 if(!['svg','chtml'].includes(settings.mathOutput))throw Error('Invalid --math-output');
 if(settings.mathOutput==='chtml'&&(!a['mathjax-font-dir']||!fs.existsSync(path.resolve(a['mathjax-font-dir']))))throw Error('CHTML requires existing --mathjax-font-dir');
 if(settings.bodyPt<settings.minBodyPt||settings.mathPt<settings.minMathPt)throw Error('Configured body/math size is below its explicit floor');
 settings.toc=!a['no-toc'];settings.forceToc=!!a.toc;
 let tocPages={};if(a['toc-pages']){const old=JSON.parse(fs.readFileSync(path.resolve(a['toc-pages']),'utf8'));for(const h of old.outline||[])if(!(h.title in tocPages))tocPages[h.title]=h.page;}
 const mm=96/25.4,cw=(settings.widthMm-settings.innerMm-settings.outerMm)*mm,ch=(settings.heightMm-settings.topMm-settings.bottomMm)*mm;
 if(cw<300||ch<500)throw Error('Margins leave insufficient printable area');
 settings.maxImageMm=num('max-image-height-mm',(ch/mm)*0.82);
 fs.mkdirSync(out,{recursive:true});const temp=path.resolve(a['temp-dir']||path.join(out,'browser-tmp'));fs.mkdirSync(temp,{recursive:true});
 process.env.TEMP=temp;process.env.TMP=temp;process.env.TMPDIR=temp;
 const {marked}=require(path.join(path.resolve(a['node-modules']),'marked'));
 const {chromium}=require(path.join(path.resolve(a['node-modules']),'playwright'));
 const source=fs.readFileSync(input,'utf8'),protectedSource=protectMath(source),maths=protectedSource.maths;
 let content=marked.parse(protectedSource.markdown,{gfm:true});
 content=content.replace(/PAPERMATHSLOTZZ(\d+)ZZEND/g,(_,s)=>{const m=maths[+s];if(!m.display)return '<span class="inline-math" data-math-id="'+m.id+'">\\('+esc(m.tex)+'\\)</span>';const d=displayLayout(m.tex,{splitAtQquad:settings.splitAtQquad});m.layout_tex=d.tex;m.labels=d.labels;m.split_at_qquad=d.splitAtQquad;return '\\['+esc(d.tex)+'\\]'+d.labels.map(x=>'<div class="formula-label">'+esc(x)+'</div>').join('');});
 content=content.replace(/\bsrc=(['"])([^'"]+)\1/g,(all,q,src)=>/^[A-Za-z]:[\\/]/.test(src)?'src='+q+pathToFileURL(src).href+q:all).replace(/<script\b[^>]*>[\s\S]*?<\/script\s*>/gi,'');
 const title=a.title||(source.match(/^#\s+(.+)$/m)||[])[1]||path.basename(input,path.extname(input));
 const running=a['running-title']||[...title].slice(0,24).join('');
 const fontURL=p=>pathToFileURL(path.resolve(p)).href;
 const config={tex:{inlineMath:[['\\(','\\)']],displayMath:[['\\[','\\]']],processEscapes:true},svg:{fontCache:'local',mtextInheritFont:true},chtml:{mtextInheritFont:true,...(a['mathjax-font-dir']?{fontURL:fontURL(a['mathjax-font-dir'])}:{})},options:{enableMenu:false}};
 const css=`
@font-face{font-family:PaperSerif;src:url('${fontURL(a['font-regular'])}');font-weight:${a['font-bold']?'400':'100 900'};font-display:block}
${a['font-bold']?`@font-face{font-family:PaperSerif;src:url('${fontURL(a['font-bold'])}');font-weight:700;font-display:block}`:''}
${a['font-heading']?`@font-face{font-family:PaperHeading;src:url('${fontURL(a['font-heading'])}');font-weight:400;font-display:block}@font-face{font-family:PaperHeading;src:url('${fontURL(a['font-heading-bold']||a['font-heading'])}');font-weight:700;font-display:block}`:''}
*{box-sizing:border-box}html{background:#fff;color:#17212b}body{width:${cw}px;margin:0;font-family:PaperSerif,serif;font-size:${settings.bodyPt}pt;line-height:${settings.lineHeight};font-synthesis:none}
@page{size:${settings.widthMm}mm ${settings.heightMm}mm;margin:${settings.topMm}mm ${settings.outerMm}mm ${settings.bottomMm}mm ${settings.innerMm}mm;@top-left{content:'${running.replaceAll("'","\\'")}';font-family:PaperSerif;font-size:8.5pt;color:#53606b}@bottom-center{content:counter(page) ' / ' counter(pages);font-family:PaperSerif;font-size:9pt;color:#53606b}}
@page:left{margin-left:${settings.outerMm}mm;margin-right:${settings.innerMm}mm}@page:right{margin-left:${settings.innerMm}mm;margin-right:${settings.outerMm}mm}
h1,h2,h3,h4,h5,h6{font-family:${a['font-heading']?'PaperHeading,sans-serif':'PaperSerif,serif'};font-weight:700;line-height:1.35;text-align:left;break-after:avoid-page;page-break-after:avoid;margin:1.1em 0 .5em;color:#153f51}
h1{font-size:23pt;margin:.2em 0 .65em}h2{font-size:19pt;border-bottom:1pt solid #9bb0b8;padding-bottom:.22em}h3{font-size:15.5pt}h4{font-size:13.5pt}h5,h6{font-size:${settings.bodyPt}pt}
p{margin:.45em 0 .65em;text-align:justify;text-justify:inter-ideograph;line-break:strict;overflow-wrap:break-word;orphans:3;widows:3}
li{margin:.25em 0;orphans:2;widows:2}ul,ol{padding-left:1.55em}a{color:inherit;text-decoration:underline;text-decoration-thickness:.5pt}blockquote{margin:.65em 0;padding:.2em .8em;border-left:2pt solid #8da7b0;color:#3b4c58}
code{font-family:Consolas,monospace;font-size:.88em;overflow-wrap:anywhere}pre{white-space:pre-wrap;font-size:${settings.codePt}pt;line-height:1.5;background:#f1f4f5;padding:.7em;border:.4pt solid #d2dce0;orphans:3;widows:3}pre code{font-size:1em;display:block;white-space:normal;overflow-wrap:normal;word-break:normal}.code-line{display:block;white-space:pre-wrap;min-height:1.5em}.code-atom{white-space:nowrap}
.formula{font-size:${settings.mathPt}pt;text-align:center;margin:.7em 0 .3em;break-inside:avoid-page;page-break-inside:avoid}.formula mjx-container[display=true]{margin:0!important}.inline-math{white-space:nowrap}.formula-label{font-size:${settings.captionPt}pt;text-align:right;color:#4f5f68;margin-top:.25em;line-height:${settings.captionLeadingPt}pt}
.math-explanation,.figure-unit{break-inside:avoid-page;page-break-inside:avoid}.math-lead,.figure-lead{break-after:avoid-page;page-break-after:avoid}.math-explanation>p{margin-top:.25em}.asset{text-align:center!important;margin:.8em 0 .2em}.asset img{display:block;margin:0 auto;object-fit:contain;image-rendering:auto;filter:none!important}.caption{font-size:${settings.captionPt}pt;line-height:${settings.captionLeadingPt}pt;color:#44515c;text-align:left;break-before:avoid-page;margin:.2em 0 .7em}
table{width:100%;border-collapse:collapse;font-size:${settings.tablePt}pt;line-height:1.55;margin:.7em 0;table-layout:fixed}thead{display:table-header-group}tfoot{display:table-footer-group}tr{break-inside:avoid-page;page-break-inside:avoid}th,td{border:.5pt solid #c6d0d5;padding:.35em .45em;vertical-align:top;overflow-wrap:anywhere;text-align:left}th{background:#edf3f5;font-weight:700}table p{margin:0;text-align:left}hr{border:0;border-top:.5pt solid #c6d0d5;margin:1em 0}
svg{overflow:visible}mjx-container{max-width:100%}.chapter{display:block}.chapter+.chapter{${settings.chapterBreaks?'break-before:page;page-break-before:always;':''}}
.frontmatter{page:frontmatter;break-after:page}.contents{margin-top:1.5em}.contents ol{list-style:none;padding:0}.contents li{display:flex;align-items:baseline;gap:1em;border-bottom:.4pt dotted #b7c5cc;padding:.5em 0}.contents a{flex:1;text-decoration:none}.contents .toc-page{min-width:3em;text-align:right;font-variant-numeric:tabular-nums}.contents h2{font-size:17pt}
@page frontmatter{@top-right{content:'阅读目录';font-family:PaperSerif;font-size:8.5pt;color:#53606b}}
`;
 const html='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><base href="'+pathToFileURL(path.dirname(input)+path.sep).href+'"><title>'+esc(title)+'</title><style>'+css+'</style><script>window.MathJax='+JSON.stringify(config)+'</script><script src="'+fontURL(a['mathjax-script'])+'"></script></head><body><main id="flow">'+content+'</main></body></html>';
 const htmlPath=path.join(out,'source.html');fs.writeFileSync(htmlPath,html);
 const fontFiles={};for(const k of ['font-regular','font-bold','font-heading','font-heading-bold'])if(a[k]){const p=path.resolve(a[k]);if(!fs.existsSync(p))throw Error('Missing --'+k);fontFiles[k]={file:p,bytes:fs.statSync(p).size,sha256:sha(fs.readFileSync(p))};}
 const report={format:'digrp-typeset-1',engine:'chromium-native-paged',source:{file:input,sha256:sha(Buffer.from(source))},title,settings,font_files:fontFiles,maths,math_parse_issues:protectedSource.issues,remote_requests:[],request_failures:[],status:'PREPARING',pdf:null};
 const save=()=>fs.writeFileSync(path.join(out,'typeset-report.json'),JSON.stringify(report,null,2));save();
 const launch={headless:true,args:['--allow-file-access-from-files','--disable-crash-reporter','--disable-dev-shm-usage','--disk-cache-dir='+path.join(temp,'cache')],env:{...process.env,TEMP:temp,TMP:temp,TMPDIR:temp}};
 if(a['browser-channel'])launch.channel=a['browser-channel'];if(a['browser-executable'])launch.executablePath=path.resolve(a['browser-executable']);
 const browser=await chromium.launch(launch);
 try{
  report.browser_version=browser.version();const context=await browser.newContext({viewport:{width:Math.ceil(cw),height:1000}});
  await context.route(/^https?:\/\//,r=>{report.remote_requests.push(r.request().url());return r.abort('blockedbyclient');});
  const page=await context.newPage();page.on('requestfailed',r=>report.request_failures.push({url:r.url(),error:r.failure()?.errorText}));
  await page.emulateMedia({media:'print'});await page.goto(pathToFileURL(htmlPath).href,{waitUntil:'domcontentloaded',timeout:60000});
  await page.waitForFunction(()=>window.MathJax?.startup?.promise,{timeout:60000});await page.evaluate(()=>MathJax.startup.promise);await page.evaluate(()=>document.fonts.ready);
  report.preparation=await page.evaluate(async({cw,ch,settings,running,title,tocPages})=>{
   const flow=document.querySelector('#flow'),norm=s=>s.replace(/\s+/g,'');
   // Preserve source bytes while wrapping only between code atoms. CSS alone
   // may split operators such as right-- at a hyphen even with normal wrapping.
   const codeLineBoxes=[];
   for(const code of flow.querySelectorAll('pre>code')){
    const before=code.textContent,lines=before.split('\n'),fragment=document.createDocumentFragment();
    for(let i=0;i<lines.length;i++){
     if(i===lines.length-1&&!lines[i]&&before.endsWith('\n'))break;
     const line=document.createElement('span');line.className='code-line';
     for(const part of lines[i].split(/(\s+)/)){
      if(/^[\x21-\x7e]+$/.test(part)){const atom=document.createElement('span');atom.className='code-atom';atom.textContent=part;line.append(atom);}
      else line.append(document.createTextNode(part));
     }
     const indent=(lines[i].match(/^ */)||[''])[0].length+2;
     line.style.paddingLeft=indent+'ch';line.style.textIndent='-'+indent+'ch';fragment.append(line);
     if(i<lines.length-1)fragment.append(document.createTextNode('\n'));
    }
    code.replaceChildren(fragment);codeLineBoxes.push({text_preserved:before===code.textContent,source_lines:lines.length-(before.endsWith('\n')?1:0)});
   }
   if(codeLineBoxes.some(x=>!x.text_preserved))throw Error('Code carrier changed source text');
   let zeroStrokeSuppressed=0;
   if(settings.mathOutput==='svg')for(const e of flow.querySelectorAll('mjx-container svg g,mjx-container svg path')){
    if(parseFloat(getComputedStyle(e).strokeWidth)===0&&getComputedStyle(e).stroke!=='none'){e.style.stroke='none';zeroStrokeSuppressed++;}
   }
   const withoutMath=node=>{const c=node.cloneNode(true);for(const e of c.querySelectorAll('.formula,.inline-math,mjx-container,.formula-label,.generated'))e.remove();return c.textContent;};
   const textRuns=node=>{let current='',runs=[];const walk=n=>{if(n.nodeType===Node.TEXT_NODE){current+=n.textContent;return;}if(n.nodeType!==Node.ELEMENT_NODE)return;if(n.matches('.formula,.inline-math,mjx-container,.formula-label')){if(current.trim())runs.push(current);current='';return;}for(const c of n.childNodes)walk(c);};walk(node);if(current.trim())runs.push(current);return runs;};
   const linearBefore=norm(withoutMath(flow));
   let unitNo=0;const readingOrder=[];
   for(const el of flow.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,pre,th,td')){if(el.matches('li')&&el.querySelector('p')||el.matches('p')&&el.closest('td,th,li'))continue;const text=withoutMath(el).trim();el.dataset.sourceUnit=String(unitNo++);readingOrder.push({id:el.dataset.sourceUnit,kind:el.tagName.toLowerCase(),text,text_runs:textRuns(el)});}
   const roleLeaks=readingOrder.filter(x=>/(^|[^A-Za-z0-9])[mM][1-5]([^A-Za-z0-9]|$)/.test(x.text));
   const images=[];for(const img of flow.querySelectorAll('img')){try{await img.decode();}catch{}const w=img.naturalWidth,h=img.naturalHeight,scale=Math.min(cw/(w||1),(settings.maxImageMm*96/25.4)/(h||1));img.style.width=(w*scale)+'px';img.style.height=(h*scale)+'px';img.closest('p')?.classList.add('asset');images.push({src:img.src,alt:img.alt,natural_width:w,natural_height:h,width_px:w*scale,height_px:h*scale,effective_dpi:96/scale,height_limited:h*scale>=settings.maxImageMm*96/25.4-1,loaded:!!(img.complete&&w)});}
   // Keep figures with their actual caption; leave the following discussion free.
   for(const p of [...flow.querySelectorAll('p.asset')]){const next=p.nextElementSibling,group=document.createElement('div');group.className='figure-unit';p.before(group);group.append(p);if(next?.tagName==='P'&&(next.querySelector('em')||/^(期刊|原图|原式|预印本|图\s*\d)/.test(next.textContent.trim()))){next.classList.add('caption');group.append(next);}}
   // Attach only the first necessary sentence, not an arbitrarily long paragraph.
   const leadOf=p=>{const walker=document.createTreeWalker(p,NodeFilter.SHOW_TEXT);let n;while(n=walker.nextNode()){if(n.parentElement.closest('.inline-math,mjx-container,code'))continue;const m=n.textContent.match(/[。！？]/);if(m){const end=m.index+1,range=document.createRange();range.setStart(p,0);range.setEnd(n,end);const first=p.cloneNode(false);first.removeAttribute('data-source-unit');first.dataset.fragmentOf=p.dataset.sourceUnit||'';first.append(range.extractContents());return first;}}return null;};
   if(settings.keepMathExplanation)for(const f of [...flow.querySelectorAll('.formula')]){const next=f.nextElementSibling;if(next?.tagName!=='P'||next.querySelector('img'))continue;const group=document.createElement('div');group.className='math-explanation';f.before(group);group.append(f);const lead=leadOf(next);if(lead){group.append(lead);if(!next.textContent.trim())next.remove();}else group.append(next);}
   for(const f of flow.querySelectorAll('.math-explanation,.formula')){const previous=f.previousElementSibling;if(previous?.tagName==='P')previous.classList.add('math-lead');}
   for(const f of flow.querySelectorAll('.figure-unit')){const previous=f.previousElementSibling;if(previous?.tagName==='P'&&/[:：]$|下图|如下图/.test(previous.textContent.trim()))previous.classList.add('figure-lead');}
   // Named pages give static per-chapter headers without unsupported string-set.
   const nodes=[...flow.children],front=[];let section=null,index=0;const chapters=[];
   const useToc=settings.toc&&(settings.forceToc||nodes.filter(n=>n.tagName==='H2').length>=4);
   for(const node of nodes){if(node.tagName==='H2'){section=document.createElement('section');section.className='chapter';section.dataset.chapter=String(index);const name='chapter'+index++;section.style.page=name;node.id=node.id||name;const text=node.textContent.trim();chapters.push({name,title:text,anchor:node.id});flow.append(section);if(front.length&&!useToc)section.append(...front.splice(0));section.append(node);}else if(section)section.append(node);else front.push(node);}
   if(useToc){const face=document.createElement('section');face.className='frontmatter';face.append(...front.splice(0));const nav=document.createElement('nav');nav.className='contents generated';const h=document.createElement('h2');h.textContent='阅读目录';nav.append(h);const list=document.createElement('ol');for(const c of chapters){const li=document.createElement('li'),link=document.createElement('a'),num=document.createElement('span');link.href='#'+c.anchor;link.textContent=c.title;num.className='toc-page';num.textContent=tocPages[c.title]||'\u2007\u2007';li.append(link,num);list.append(li);}nav.append(list);face.append(nav);flow.prepend(face);}
   if(front.length){section=document.createElement('section');section.className='chapter';section.dataset.chapter='0';section.style.page='chapter0';section.append(...front);flow.append(section);chapters.push({name:'chapter0',title});}
   const q=s=>'"'+s.replaceAll('\\','\\\\').replaceAll('"','\\"')+'"';let named='';
   for(const chapter of chapters){const short=[...chapter.title].slice(0,26).join('');named+='@page '+chapter.name+'{@top-right{content:'+q(short)+';font-family:PaperSerif;font-size:8.5pt;color:#53606b;text-align:right}}';}
   const style=document.createElement('style');style.textContent=named;document.head.append(style);
   const mathErrors=[...flow.querySelectorAll('mjx-merror,[data-mjx-error]')].map(e=>({id:e.closest('[data-math-id]')?.dataset.mathId,text:e.textContent}));
   const wideMath=[];for(const el of flow.querySelectorAll('.formula,.inline-math')){const mj=el.querySelector('mjx-container');if(!mj)continue;const svg=mj.querySelector('svg'),r=(svg||mj).getBoundingClientRect();if(r.width>cw+1)wideMath.push({id:+el.dataset.mathId,width:r.width,available:cw,display:el.classList.contains('formula')});}
   const oversized=[...flow.querySelectorAll('.math-explanation,.figure-unit,tr,pre')].map(e=>({tag:e.tagName,kind:e.className,height:e.getBoundingClientRect().height,text:e.textContent.slice(0,90)})).filter(x=>x.height>ch+1);
   const overflowing=[...flow.querySelectorAll('table,pre,img,.formula')].map(e=>({tag:e.tagName,width:Math.max(e.getBoundingClientRect().width,e.scrollWidth),text:e.textContent.slice(0,70)})).filter(x=>x.width>cw+1);
   const metrics=[...flow.querySelectorAll('[data-math-id]')].slice(0,12).map(e=>{const c=e.querySelector('mjx-container'),s=c&&getComputedStyle(c),svg=c?.querySelector('svg'),vb=svg?.viewBox.baseVal,r=svg?.getBoundingClientRect();return {id:+e.dataset.mathId,font_family:s?.fontFamily,font_size:s?.fontSize,font_weight:s?.fontWeight,svg_stroke:svg?.querySelector('g')?.getAttribute('stroke-width'),svg_variants:svg?[...svg.querySelectorAll('path[id]')].slice(0,8).map(p=>p.id):[],svg_em_equivalent_pt:vb?.width?r.width/vb.width*1000*72/96:null};});
   return {mathjax_version:MathJax.version,math_output_actual:[...new Set([...flow.querySelectorAll('mjx-container')].map(e=>e.getAttribute('jax')?.toLowerCase()))],zero_width_svg_strokes_suppressed:zeroStrokeSuppressed,code_line_boxes:codeLineBoxes,math_metrics:metrics,mathErrors,wideMath,oversized,overflowing,images,roleLeaks,chapters,reading_order:readingOrder,integrity:{linear_text_preserved:linearBefore===norm(withoutMath(flow)),math_order:[...flow.querySelectorAll('[data-math-id]')].map(e=>+e.dataset.mathId)},math_containers:flow.querySelectorAll('mjx-container').length,svg_count:flow.querySelectorAll('mjx-container svg').length,fonts:[...document.fonts].map(f=>({family:f.family,weight:f.weight,status:f.status})),body_font:getComputedStyle(document.body).fontFamily};
  },{cw,ch,settings,running,title,tocPages});
  const prep=report.preparation;
  if(maths.length&&prep.math_output_actual.some(x=>x!==settings.mathOutput))throw Error('Loaded MathJax output does not match --math-output: '+prep.math_output_actual.join(','));
  const fatal=report.math_parse_issues.length+prep.mathErrors.length+prep.images.filter(i=>!i.loaded).length+report.remote_requests.length+report.request_failures.length+(!prep.integrity.linear_text_preserved?1:0);
  const needs=prep.wideMath.length+prep.oversized.length+prep.overflowing.length+(!a['allow-internal-labels']?prep.roleLeaks.length:0);
  report.status=fatal?'FAILED_INPUT_OR_ASSETS':needs?'NEEDS_SOURCE_REVIEW':'LAID_OUT';
  fs.writeFileSync(path.join(out,'rendered.html'),await page.content());save();
  if(fatal||needs&&!a.diagnostic)throw Error(report.status+'; inspect typeset-report.json');
  if(!a['layout-only']){const pdf=path.resolve(a.output||path.join(out,'paper.pdf'));fs.mkdirSync(path.dirname(pdf),{recursive:true});await page.pdf({path:pdf,preferCSSPageSize:true,printBackground:true,displayHeaderFooter:false,tagged:true,outline:true,timeout:120000});report.pdf={file:pdf,bytes:fs.statSync(pdf).size,sha256:sha(fs.readFileSync(pdf))};report.status=needs?'PDF_NEEDS_REVIEW':'PDF_CREATED';save();}
  console.log(JSON.stringify({status:report.status,engine:report.engine,pdf:report.pdf,maths:maths.length,images:prep.images.length,chapters:prep.chapters.length,issues:needs,report:path.join(out,'typeset-report.json')}));
 }catch(e){report.error=e.message;save();throw e;}finally{await browser.close();}
}
if(require.main===module)main().catch(e=>{console.error(e.stack||e.message);process.exitCode=1;});
module.exports={argsOf,main};
