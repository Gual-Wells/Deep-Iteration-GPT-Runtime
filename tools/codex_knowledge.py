#!/usr/bin/env python3
"""Manage a private DIGR paper knowledge pool. No models, web server or automatic grading."""
from __future__ import annotations
import argparse,json,os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from runtime import codex_knowledge as k
MUTATION_ACTIONS=('ingest','select','explanation','evidence','finish','migrate-v1','revise-concept','revise-use','checkpoint')


def main(argv=None):
    # This command's text/JSON interface is UTF-8 even in a Windows GBK parent.
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pool',required=True,type=Path)
    sub=parser.add_subparsers(dest='action',required=True)
    init=sub.add_parser('init');init.add_argument('--runtime-pin',required=True);init.add_argument('--repository',required=True)
    for name in MUTATION_ACTIONS:
        p=sub.add_parser(name);p.add_argument('--input',required=True,type=Path)
        p.add_argument('--expected-revision',required=True,type=int);p.add_argument('--operation-id',required=True)
    for name in ('resume','questionnaire','card'):
        p=sub.add_parser(name);p.add_argument('--session');p.add_argument('--out',type=Path)
        if name=='resume':
            p.add_argument('--related-limit',type=int,default=3);p.add_argument('--items')
    for name in ('validate','check-sources'):sub.add_parser(name)
    marked=sub.add_parser('select-md');marked.add_argument('--input',required=True,type=Path)
    marked.add_argument('--source-ref',required=True);marked.add_argument('--operation-id',required=True)
    search=sub.add_parser('search');search.add_argument('--query',required=True)
    search.add_argument('--limit',type=int,default=10)
    search.add_argument('--uses-limit',type=int,default=3)
    use=sub.add_parser('show-use');use.add_argument('--id',required=True)
    args=parser.parse_args(argv)
    try:
        if args.action=='init':
            value=k.initialize(args.pool,runtime_pin=args.runtime_pin,repository=args.repository)
            result={'schema_version':value['schema_version'],'revision':value['revision'],'binding':value['binding']}
        elif args.action in MUTATION_ACTIONS:
            payload=k.read_json(args.input);kw=dict(expected_revision=args.expected_revision,operation_id=args.operation_id)
            if args.action in ('explanation','evidence'):
                result=k.record(args.pool,payload,kind=args.action,**kw)
            else:result={'ingest':k.ingest,'select':k.select,'finish':k.finish,
                         'migrate-v1':k.migrate_legacy,'revise-concept':k.revise_concept,
                         'revise-use':k.revise_use,'checkpoint':k.checkpoint}[args.action](args.pool,payload,**kw)
        elif args.action=='select-md':
            text=args.input.read_text(encoding='utf-8-sig');payload=k.parse_selection_markdown(text)
            expected=payload.pop('expected_revision');payload.update(response_text=text,response_ref=args.source_ref)
            result=k.select(args.pool,payload,expected_revision=expected,operation_id=args.operation_id)
        elif args.action=='resume':result=k.resume(args.pool,args.session,related_limit=args.related_limit,
                                                  item_ids=args.items.split(',') if args.items else None)
        elif args.action=='card':result=k.current_card(args.pool,args.session)
        elif args.action=='questionnaire':result=k.questionnaire_markdown(args.pool,args.session)
        elif args.action=='check-sources':result=k.check_sources(args.pool)
        elif args.action=='search':result=k.search(args.pool,args.query,args.limit,args.uses_limit)
        elif args.action=='show-use':result=k.show_use(args.pool,args.id)
        elif args.action=='validate':
            value=k.load(args.pool);result={'valid':True,'schema_version':value['schema_version'],'revision':value['revision']}
        else:raise ValueError('unhandled command')
        output=result if isinstance(result,str) else json.dumps(result,ensure_ascii=False,indent=2)
        if getattr(args,'out',None):
            args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(output+'\n',encoding='utf-8')
            print(json.dumps({'output':str(args.out)},ensure_ascii=False))
        else:print(output)
        return 0
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print(json.dumps({'error':str(exc),'mutations_not_assumed':True},ensure_ascii=False),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
