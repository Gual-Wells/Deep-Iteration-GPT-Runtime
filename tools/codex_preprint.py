#!/usr/bin/env python3
"""Record and inspect English-Spoken-Preprint. Native Codex creates the agents."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from runtime import codex_preprint as p
from runtime.codex_preprint_export import export,verify_export
from runtime.codex_preprint_sources import archive_sources,audit_sources


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    init=commands.add_parser('init');init.add_argument('--spec',required=True,type=Path);init.add_argument('--out',required=True,type=Path)
    packet=commands.add_parser('packet');packet.add_argument('--root',required=True,type=Path);packet.add_argument('--actor',required=True);packet.add_argument('--channel',choices=('outward','inner'),default='outward')
    director=commands.add_parser('director');director.add_argument('--root',required=True,type=Path);director.add_argument('--id',required=True)
    packet.add_argument('--out',type=Path,help='save the exact bounded packet to a new UTF-8 file')
    director.add_argument('--out',type=Path,help='save the exact bounded packet to a new UTF-8 file')
    show=commands.add_parser('inspect');show.add_argument('--root',required=True,type=Path);show.add_argument('--creator',action='store_true')
    for name in ('record','annotate'):
        sub=commands.add_parser(name);sub.add_argument('--root',required=True,type=Path)
        sub.add_argument('--input',required=True,type=Path);sub.add_argument('--expected-revision',required=True,type=int);sub.add_argument('--operation-id',required=True)
    publish=commands.add_parser('publish');publish.add_argument('--root',required=True,type=Path);publish.add_argument('--out',required=True,type=Path)
    verify=commands.add_parser('verify');verify.add_argument('--root',required=True,type=Path);verify.add_argument('--edition',required=True,type=Path)
    archive=commands.add_parser('archive');archive.add_argument('--root',required=True,type=Path);archive.add_argument('--source-base',required=True,type=Path);archive.add_argument('--out',required=True,type=Path)
    audit=commands.add_parser('audit-sources');audit.add_argument('--root',required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        if args.command=='init':result=p.initialize(args.out,p.read(args.spec))
        elif args.command=='packet':result=p.actor_packet(args.root,args.actor,args.channel)
        elif args.command=='director':result=p.director_packet(args.root,args.id)
        elif args.command=='publish':result=export(args.root,args.out)
        elif args.command=='verify':result=verify_export(args.root,args.edition)
        elif args.command=='archive':result=archive_sources(args.root,args.source_base,args.out)
        elif args.command=='audit-sources':result=audit_sources(args.root)
        elif args.command=='inspect':
            state=p.load(args.root)
            result=state if args.creator else {'id':state['spec']['id'],'title':state['spec']['title'],'revision':state['revision'],
                'events':len(state['events']),'actors':[{'id':a['id'],'name':a['name']} for a in state['spec']['actors']],
                'inner_channels':len(state['spec']['actors']),'learner_evidence':len(state['learner_evidence']),
                'scope':'summary only; use explicit actor packet or creator view'}
        else:
            operation={'record':p.append_event,'annotate':p.annotate}[args.command]
            result=operation(args.root,p.read(args.input),expected_revision=args.expected_revision,operation_id=args.operation_id)
        if args.command in {'packet','director'} and args.out:
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with args.out.open('x',encoding='utf-8',newline='\n') as f:
                f.write(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
            result={**result,'saved_to':args.out.resolve().as_posix()}
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        if args.command=='verify' and result['status']!='CURRENT':return 2
        if args.command in {'archive','audit-sources'} and not result['valid']:return 2
        return 0
    except (ValueError,TypeError,KeyError,OSError) as error:
        print('Preprint: '+str(error),file=sys.stderr);return 2


if __name__=='__main__':
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
