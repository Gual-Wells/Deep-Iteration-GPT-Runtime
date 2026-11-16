#!/usr/bin/env python3
"""Inspect the FINAL PDF, including A4 geometry, text/order, fonts and previews.

No GUI browser is read or controlled. Spread PNGs are views of separate pages;
this tool never makes a two-pages-in-one-page delivery PDF.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import math
import logging
import unicodedata
from collections import Counter

def normalized(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC',s)).replace('\u200b','').replace('\ufeff','')

def inspect(pdf, report_path=None, preview_dir=None, pages=None, width=900,
            spread_pairs=None, screen_width=1920, screen_height=1080):
    from pypdf import PdfReader
    import pypdfium2 as pdfium
    from PIL import Image, ImageDraw, ImageChops
    import pdfplumber
    pdf=Path(pdf).resolve()
    production=json.loads(Path(report_path).read_text(encoding='utf-8')) if report_path else {}
    reader=PdfReader(str(pdf))
    rendering=pdfium.PdfDocument(str(pdf))
    result={'format':'digrp-pdf-inspection-1','pdf':str(pdf),
            'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),
            'bytes':pdf.stat().st_size,'pages':len(reader.pages),
            'geometry':[],'formula_errors':[],'overflow':[],
            'missing_images':[],'text_pages':[],'font_objects':[],
            'image_objects':[],'previews':[],'rendered_pages':0,'rendered_page_numbers':[],
            'rendered_ink':[],
            'scope':'Offline final-PDF rendering and structure; GUI Chrome not tested.'}
    texts=[]
    parser_warnings=Counter()
    class WarningCounter(logging.Handler):
        def emit(self, record): parser_warnings[record.getMessage()]+=1
    warning_handler=WarningCounter()
    pdf_logger=logging.getLogger('pdfminer')
    pdf_logger.addHandler(warning_handler)
    pdf_logger.propagate=False
    seen_fonts=set()
    with pdfplumber.open(str(pdf)) as doc:
        for idx,(page,pl) in enumerate(zip(reader.pages,doc.pages)):
            w,h=float(page.mediabox.width),float(page.mediabox.height)
            a4=abs(w-595.2756)<0.8 and abs(h-841.8898)<0.8
            result['geometry'].append({'page':idx+1,'width_pt':w,'height_pt':h,
                                       'a4_portrait':a4,'rotation':int(page.get('/Rotate',0))})
            if not a4 or page.get('/Rotate',0):
                result['overflow'].append({'kind':'non-a4-portrait','page':idx+1})
            tp=rendering[idx].get_textpage()
            top_mm=production.get('settings',{}).get('topMm',0)
            bottom_mm=production.get('settings',{}).get('bottomMm',0)
            text=tp.get_text_bounded(0,bottom_mm*72/25.4,w,h-top_mm*72/25.4)
            texts.append(text)
            chars=pl.chars
            sizes={};usage=Counter()
            for c in chars:
                key=round(float(c.get('size',0)),2)
                sizes[key]=sizes.get(key,0)+1
                usage[(c.get('fontname',''),key)]+=1
                if c['x0'] < -1 or c['x1']>w+1 or c['top'] < -1 or c['bottom']>h+1:
                    result['overflow'].append({'kind':'text-outside-page','page':idx+1,'char':c.get('text'),'font':c.get('fontname'),'box':[c['x0'],c['top'],c['x1'],c['bottom']],'basis':'extracted font metrics; compare rendered page for stretched-glyph metadata errors'})
            result['text_pages'].append({'page':idx+1,'characters':len(text),
                                         'cjk':len(re.findall(r'[\u3400-\u9fff]',text)),
                                         'font_sizes':sizes,'font_usage':[{'font':f,'size_pt':s,'characters':n} for (f,s),n in usage.items()],
                                         'vector_objects':len(pl.curves)+len(pl.lines)+len(pl.rects),
                                         'images':len(pl.images)})
            for name,ref in (page.get('/Resources',{}).get('/Font',{}) or {}).items():
                f=ref.get_object();key=str(f.get('/BaseFont',name))
                if key in seen_fonts: continue
                seen_fonts.add(key)
                descendants=f.get('/DescendantFonts',[])
                descriptor=f.get('/FontDescriptor')
                if not descriptor and descendants:
                    descriptor=descendants[0].get_object().get('/FontDescriptor')
                d=descriptor.get_object() if descriptor else {}
                result['font_objects'].append({'font':key,'subtype':str(f.get('/Subtype')),
                                               'embedded':any(k in d for k in ['/FontFile','/FontFile2','/FontFile3']) or bool(f.get('/CharProcs')),
                                               'embedding_kind':'glyph-programs' if f.get('/CharProcs') else 'font-file',
                                               'to_unicode':'/ToUnicode' in f})
            for image in pl.images:
                result['image_objects'].append({'page':idx+1,'box':[image['x0'],image['top'],image['x1'],image['bottom']],
                                                'pixel_size':image.get('srcsize'),
                                                'page_area_fraction':round((image['x1']-image['x0'])*(image['bottom']-image['top'])/(w*h),4)})
    result['searchable_text']=sum(p['cjk'] for p in result['text_pages'])>50
    result['all_a4_portrait']=all(x['a4_portrait'] and not x['rotation'] for x in result['geometry'])
    result['full_page_raster_only_pages']=[p['page'] for p in result['text_pages'] if p['cjk']<10 and any(i['page']==p['page'] and i['page_area_fraction']>.78 for i in result['image_objects'])]
    def outlines(nodes,level=1):
        for node in nodes:
            if isinstance(node,list):yield from outlines(node,level+1)
            else:
                try:yield {'title':str(node.title),'page':reader.get_destination_page_number(node)+1,'level':level}
                except Exception:pass
    result['outline']=list(outlines(reader.outline))
    result['link_annotations']=sum(1 for p in reader.pages for a in p.get('/Annots',[]) if a.get_object().get('/Subtype')=='/Link')
    result['parser_warnings']=dict(parser_warnings)
    if report_path:
        result['production_report']=str(Path(report_path).resolve())
        if production.get('pdf',{}).get('sha256')!=result['sha256']:
            result['overflow'].append({'kind':'pdf-report-sha-mismatch'})
        joined=normalized('\n'.join(texts))
        cursor=0;found=[];missing=[];checked_runs=0
        for unit in production.get('preparation',{}).get('reading_order',[]):
            runs=[normalized(r) for r in unit.get('text_runs',[unit['text']])]
            runs=[r for r in runs if len(r)>=3]
            if not runs:continue
            checked_runs+=len(runs);all_found=True
            for needle in runs:
                at=joined.find(needle,cursor)
                if at<0:
                    all_found=False
                    hints=[i+1 for i,t in enumerate(texts) if needle[:min(18,len(needle))] in normalized(t)]
                    missing.append({'id':unit['id'],'kind':unit['kind'],'text':needle,'page_hints':hints})
                    break
                cursor=at+len(needle)
            if all_found:found.append(unit['id'])
        result['reading_order']={'method':'PDFium body-bounded text in extraction order; NFKC and whitespace normalization, exact ordered normal-text runs','checked_units':len(found)+len(missing),'checked_runs':checked_runs,'matched_in_order':len(found),'missing_or_reordered':missing}
        result['missing_images']=[i for i in production.get('preparation',{}).get('images',[]) if not i.get('loaded')]
        result['formula_errors']=production.get('math_parse_issues',[])+production.get('preparation',{}).get('mathErrors',[])
        result['font_configuration']=production.get('settings')
    if preview_dir:
        destination=Path(preview_dir).resolve();destination.mkdir(parents=True,exist_ok=True)
        selected=pages or sorted(set([1,min(2,len(reader.pages)),max(1,len(reader.pages)//2),len(reader.pages)]))
        for number in selected:
            if not 1<=number<=len(reader.pages): raise ValueError('Preview page out of range')
            page=rendering[number-1]
            im=page.render(scale=width/page.get_width()).to_pil().convert('RGB')
            target=destination/f'page-{number:04}.png';im.save(target)
            gray=im.convert('L');ink=gray.point(lambda v:255 if v<245 else 0);box=ink.getbbox()
            result['rendered_ink'].append({'page':number,'pixel_size':[im.width,im.height],'ink_bbox':list(box) if box else None,'blank':box is None,'ink_touches_page_edge':bool(box and (box[0]<2 or box[1]<2 or box[2]>im.width-2 or box[3]>im.height-2))})
            result['previews'].append({'kind':'page','pages':[number],'file':str(target),'width':im.width,'height':im.height,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
        for pair in spread_pairs or [(1,min(2,len(reader.pages)))]:
            if pair[0]==pair[1]: continue
            if any(not 1<=n<=len(reader.pages) for n in pair):raise ValueError('Spread page out of range')
            source_pages=[rendering[n-1] for n in pair]
            for mode in ['fit-width','whole-spread']:
                gap=18
                scale=(screen_width-gap)/sum(p.get_width() for p in source_pages)
                if mode=='whole-spread':scale=min(scale,screen_height/max(p.get_height() for p in source_pages))
                ims=[p.render(scale=scale).to_pil().convert('RGB') for p in source_pages]
                canvas=Image.new('RGB',(sum(i.width for i in ims)+gap,max(i.height for i in ims)),(218,222,225))
                x=0
                for im in ims:canvas.paste(im,(x,0));x+=im.width+gap
                target=destination/f'spread-{pair[0]:04}-{pair[1]:04}-{mode}.png';canvas.save(target)
                result['previews'].append({'kind':mode,'pages':list(pair),'file':str(target),'width':canvas.width,'height':canvas.height,'target_screen':[screen_width,screen_height]})
        result['rendered_page_numbers']=sorted(set(n for p in result['previews'] for n in p['pages']))
        result['rendered_pages']=len(result['rendered_page_numbers'])
    result['status']='INSPECTED'
    if not result['all_a4_portrait'] or not result['searchable_text'] or result['overflow'] or result['formula_errors'] or result['missing_images'] or result.get('reading_order',{}).get('missing_or_reordered'):
        result['status']='NEEDS_REVIEW'
    return result

def parse_pages(s):
    if not s:return None
    nums=[]
    for bit in s.split(','):
        ends=[int(x) for x in bit.split('-')]
        nums.extend(range(ends[0],ends[-1]+1))
    return sorted(set(nums))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdf',required=True);p.add_argument('--report');p.add_argument('--output')
    p.add_argument('--preview-dir');p.add_argument('--preview-pages');p.add_argument('--preview-width',type=int,default=900)
    p.add_argument('--render-all',action='store_true',help='Actually render every final-PDF page, not a self-reported count')
    p.add_argument('--normalize-a4',action='store_true',help='Explicitly normalize MediaBox/CropBox without rescaling content; update PDF report identity')
    p.add_argument('--spread-pairs',help='e.g. 2-3,24-25')
    p.add_argument('--screen-width',type=int,default=1920);p.add_argument('--screen-height',type=int,default=1080)
    a=p.parse_args()
    if a.normalize_a4:
        from pypdf import PdfReader,PdfWriter
        from pypdf.generic import RectangleObject
        pdf=Path(a.pdf).resolve();old_hash=hashlib.sha256(pdf.read_bytes()).hexdigest()
        reader=PdfReader(pdf)
        # This mutation corrects Chromium's sub-point A4 print rounding only.
        # It is not a paper-size converter: a different page/crop would be clipped.
        for number,page in enumerate(reader.pages,1):
            media,crop=page.mediabox,page.cropbox
            nominal=(abs(float(media.width)-595.275590551)<=1 and abs(float(media.height)-841.88976378)<=1)
            origin=abs(float(media.left))<=1 and abs(float(media.bottom))<=1
            same_crop=all(abs(float(x)-float(y))<=1 for x,y in zip(media,crop))
            if not nominal or not origin or not same_crop or int(page.get('/Rotate',0))!=0:
                reader.close()
                raise ValueError(f'--normalize-a4 refused page {number}: requires nominal portrait A4, zero rotation, and an unchanged normal CropBox')
        writer=PdfWriter();writer.clone_document_from_reader(reader)
        for page in writer.pages:
            box=RectangleObject([0,0,595.275590551,841.88976378])
            page.mediabox=box;page.cropbox=RectangleObject(box)
        temporary=pdf.with_name(pdf.name+'.normalized.tmp')
        with temporary.open('wb') as f:writer.write(f)
        writer.close();reader.close()
        temporary.replace(pdf)
        if a.report:
            rp=Path(a.report);pr=json.loads(rp.read_text(encoding='utf-8'))
            pr['page_box_normalization']={'before_sha256':old_hash,'media_box_pt':[595.275590551,841.88976378],'content_rescaled':False}
            pr['pdf']['sha256']=hashlib.sha256(pdf.read_bytes()).hexdigest();pr['pdf']['bytes']=pdf.stat().st_size
            rp.write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
    pairs=[tuple(int(n) for n in bit.split('-')) for bit in a.spread_pairs.split(',')] if a.spread_pairs else None
    pages=parse_pages(a.preview_pages)
    if a.render_all:
        if not a.preview_dir:p.error('--render-all requires --preview-dir')
        from pypdf import PdfReader
        pages=list(range(1,len(PdfReader(a.pdf).pages)+1))
    result=inspect(a.pdf,a.report,a.preview_dir,pages,a.preview_width,pairs,a.screen_width,a.screen_height)
    target=Path(a.output or str(Path(a.pdf).with_suffix('.inspection.json')))
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    order=result.get('reading_order',{})
    print(json.dumps({'status':result['status'],'pages':result['pages'],'bytes':result['bytes'],'searchable':result['searchable_text'],'a4':result['all_a4_portrait'],'checked_units':order.get('checked_units'),'missing_units':len(order.get('missing_or_reordered',[])),'outline_entries':len(result['outline']),'inspection':str(target)},ensure_ascii=True))

if __name__=='__main__':main()
