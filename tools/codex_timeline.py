#!/usr/bin/env python3
"""Render explicit DIGR time/identity facts; never infer a trace from counters."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from runtime.codex_timeline import read,render_svg,fragment

def main(argv=None):
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--format',choices=('svg','fragment'),default='svg')
    parser.add_argument('--width',type=int,default=1440)
    parser.add_argument('--theme',choices=('light','dark'),default='light')
    parser.add_argument('--focus',help='show relationships around one event')
    args=parser.parse_args(argv)
    try:
        data=read(args.input)
        result=fragment(data) if args.format=='fragment' else render_svg(data,args.width,args.theme,args.focus)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(result+'\n',encoding='utf-8',newline='\n')
        print(json.dumps({'output':str(args.out.resolve()),'mode':data['mode'],
                          'identity_rows':len(data['tracks']),'responsibility_or_time_certified':False},ensure_ascii=False))
        return 0
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
