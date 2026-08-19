from __future__ import annotations
import ast
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERSION='5.0.0-alpha.2'
INTERFACES={
    'routing_schema':2,
    'invocation_surface_schema':2,
    'parameter_resolution_schema':1,
    'run_session_schema':2,
    'workspace_schema':2,
    'clock_journal_schema':1,
    'event_receipt_schema':2,
}


def fail(msg: str) -> None:
    print(f'FAIL: {msg}')
    raise SystemExit(1)


def read_text(rel: str) -> str:
    try:
        return (ROOT/rel).read_text(encoding='utf-8')
    except Exception as exc:
        fail(f'unreadable UTF-8 text {rel}: {exc}')


def check_local_refs(obj, owner: str) -> None:
    if isinstance(obj, dict):
        for k,v in obj.items():
            if k=='$ref' and isinstance(v,str) and '://' not in v and not v.startswith('#'):
                rel=v.split('#',1)[0]
                if rel and not (ROOT/'schemas'/rel).is_file():
                    fail(f'{owner} references missing schema {rel}')
            check_local_refs(v,owner)
    elif isinstance(obj,list):
        for v in obj:check_local_refs(v,owner)


def main() -> None:
    if read_text('VERSION').strip()!=VERSION:fail('VERSION')
    m=json.loads(read_text('manifest.json'))
    if m.get('protocol')!='digr-v5.0' or m.get('version')!=VERSION:fail('manifest version/protocol')
    for k,v in INTERFACES.items():
        if m.get(k)!=v:fail(f'manifest interface {k}')
    if m.get('startup_slice')!=['bootstrap/BOOTSTRAP.md','entry/STARTUP.md']:fail('startup_slice')
    if m.get('workspace_spec')!='workspace/layout-v2.json':fail('workspace_spec')
    if m.get('routing',{}).get('candidate_match')!='lstrip_prefix; DIGR_exact_uppercase; remainder_unvalidated':fail('exact-uppercase candidate route metadata')
    if m.get('routing',{}).get('candidate_route_keys')!=['DIGR','深度迭代']:fail('candidate route keys')

    required_paths=[m['bootstrap_entry'],*m['startup_slice'],m['entrypoint'],m['help'],m['workspace_spec'],*m['core'],*m['deterministic_helpers']]
    for rel in dict.fromkeys(required_paths):
        if not (ROOT/rel).is_file():fail(f'missing manifest path {rel}')
    if len(m['core'])!=len(set(m['core'])):fail('duplicate core path')
    if len(m['deterministic_helpers'])!=len(set(m['deterministic_helpers'])):fail('duplicate deterministic helper')

    obsolete=(
        'DIGR_EXECUTION_GATE.md','bootstrap/REPOSITORY_ONLY_LOADER.md','runtime/bootstrap_gate.py',
        'schemas/bootstrap-gate.schema.json','bootstrap/LOCAL_FALLBACK_CORE.md','runtime/source_aggregate.py',
        'schemas/runtime-state.schema.json','schemas/invocation.schema.json','workspace/layout-v1.json',
        'docs/PROTOCOL_SPEC_5.0.0-alpha.1.md',
    )
    for rel in obsolete:
        if (ROOT/rel).exists():fail(f'obsolete Alpha1/legacy artifact {rel}')

    schema_ids=set()
    for p in sorted((ROOT/'schemas').glob('*.json')):
        try:d=json.loads(p.read_text(encoding='utf-8'))
        except Exception as exc:fail(f'invalid schema JSON {p.name}: {exc}')
        if d.get('$schema')!='https://json-schema.org/draft/2020-12/schema':fail(f'schema draft metadata {p.name}')
        expected=f'https://gual-wells.github.io/Deep-Iteration-GPT-Runtime/schemas/{p.name}'
        if d.get('$id')!=expected:fail(f'schema id {p.name}')
        if d['$id'] in schema_ids:fail(f'duplicate schema id {p.name}')
        schema_ids.add(d['$id']);check_local_refs(d,p.name)

    layout=json.loads(read_text(m['workspace_spec']))
    if layout.get('schema_version')!=2:fail('workspace layout schema_version')
    if 'state/artifact-index.json' not in layout.get('required_genesis_files',[]):fail('artifact index not genesis-required')
    if 'state/run-phase.json' not in layout.get('required_genesis_files',[]):fail('run phase not genesis-required')
    art=layout.get('artifact_schemas',{})
    for spec in art.values():
        rel=spec.split('#',1)[0]
        if not (ROOT/rel).is_file():fail(f'workspace artifact schema missing {rel}')
    if art.get('dictator/packets/*.json')!='schemas/isolation-packet.schema.json':fail('D packet artifacts not mapped')
    if art.get('state/gaps/*-r*.json')!='schemas/completion-gap.schema.json':fail('completion gap history not mapped')
    for pat in ('state/run-phase-r*.json','state/strategy-r*.json','state/candidate-r*.json','state/est-*-r*.json','sources/*/state-r*.json'):
        if pat not in art:fail(f'revision history artifact family not mapped: {pat}')

    primary=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').read_bytes()
    free=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FREE_GO.txt').read_bytes()
    full=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FULL.txt').read_bytes()
    if primary!=free:fail('primary/free router drift')
    try:text=primary.decode('utf-8');full_text=full.decode('utf-8')
    except UnicodeDecodeError:fail('local personalization is not UTF-8')
    if len(text)>1500:fail(f'compact router too long: {len(text)} chars')
    for token in (
        '精确大写 ASCII `DIGR`','`digr`、`Digr` 等不路由','宽捕获','NATIVE','原始消息交还普通 ChatGPT',
        'Gual-Wells/Deep-Iteration-GPT-Runtime','https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime',
        '/git/ref/heads/stable','/contents/{PATH}?ref={SHA}','manifest.json','VERSION','startup_slice','entrypoint','core[]','manifest.help','40 位 SHA','同一 SHA',
        'DIGR 路由失败：未取得仓库运行协议',
    ):
        if token not in text:fail(f'router missing {token}')
    for bad in ('monotonic','LiveDIGRRun','P_target','B=0','b=0','L(1)','Mature Gambit','Formal Active','proof'):
        if bad in text:fail(f'compact router duplicates versioned execution semantics: {bad}')
    for token in ('Expanded Routing Reference','Candidate response','Canonical locator and immutable pin','Staged navigation','Authority boundary and failure','NATIVE'):
        if token not in full_text:fail(f'full router reference missing {token}')
    if 'B=0' in full_text:fail('full local reference copies versioned execution defaults')

    help_text=read_text('entry/HELP.md')
    for token in ('## 1. Calling DIGR','## 2. Parameters','## 3. Format, omission and ambiguity','## 4. What execution does','## 5. Time and stopping','## 6. Return format'):
        if token not in help_text:fail(f'help missing section {token}')
    for token in ('`DIGR` is exact uppercase ASCII','a bare number','Strategy','NATIVE','?'):
        if token not in help_text:fail(f'help missing user-level rule {token}')

    # The release claims Python >=3.10, so every Python file must parse under
    # that grammar rather than only under the builder's current interpreter.
    for p in sorted(ROOT.rglob('*.py')):
        if any(x in p.parts for x in ('.git','__pycache__')):continue
        try:ast.parse(p.read_text(encoding='utf-8'),filename=str(p),feature_version=(3,10))
        except Exception as exc:fail(f'Python 3.10 parse failure {p.relative_to(ROOT)}: {exc}')

    # Text release files are canonical UTF-8/LF. This also prevents platform
    # newline drift from defeating deterministic builds.
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or any(x in p.parts for x in ('.git','__pycache__')):continue
        if p.suffix.lower() not in {'.py','.md','.txt','.json'} and p.name not in {'VERSION'}:continue
        raw=p.read_bytes()
        if b'\r' in raw:fail(f'CR line ending in {p.relative_to(ROOT)}')
        try:raw.decode('utf-8')
        except UnicodeDecodeError:fail(f'non-UTF8 text {p.relative_to(ROOT)}')

    for rel in (
        'docs/PRE_RELEASE_BASELINE.md','docs/CLOCK_RELIABILITY.md','docs/RUN_SESSION_ARCHITECTURE.md',
        'docs/MIGRATION_FROM_4.1.1.md','docs/PROTOCOL_SPEC_5.0.0-alpha.2.md','docs/TEST_MATRIX.md',
        'docs/ENGINEERING_VALIDATION_LOG.md',
    ):
        if not (ROOT/rel).is_file():fail(f'missing release documentation {rel}')
    smoke=read_text('examples/PERSONALIZATION_FRESH_CHAT_SMOKE_TEST.md')
    if 'If stable points to 4.1' in smoke or 'apply this 4.1 clock rule' in read_text('examples/HARD_TIMING_READINESS.md'):
        fail('stale 4.1 current-flow example')
    if '`digr/help` → route attempt' in read_text('examples/ROUTER_CANDIDATE_MATCHING.md'):
        fail('stale case-insensitive router example')

    print('DIGR 5.0.0-alpha.2 corrected integration baseline: OK')

if __name__=='__main__':main()
