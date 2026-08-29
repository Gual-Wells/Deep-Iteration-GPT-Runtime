from __future__ import annotations
import ast,hashlib,json,re
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1];VERSION='5.0.0-Berta2';PACKAGE_VERSION='5.0.0.dev2+berta2';HEX64=re.compile(r'^[0-9a-f]{64}$')
def fail(message):print('FAIL:',message);raise SystemExit(1)
def read(rel):return (ROOT/rel).read_text(encoding='utf-8')
def digest(data):return hashlib.sha256(data).hexdigest()
def refs(obj,owner):
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k=='$ref' and isinstance(v,str) and '://' not in v and not v.startswith('#'):
                rel=v.split('#',1)[0]
                if rel and not (ROOT/'schemas'/rel).is_file():fail(f'{owner} missing ref {rel}')
            refs(v,owner)
    elif isinstance(obj,list):
        for v in obj:refs(v,owner)
def main():
    d=json.loads(read('runtime-descriptor.json'));m=json.loads(read('manifest.json'))
    if set(d)!={'schema','protocol','version','package_version','surface','engine_api','minimum_adapter','artifacts'}:fail('descriptor core fields')
    if (d['schema'],d['protocol'],d['version'],d['package_version'])!=('digr-runtime-descriptor/v1','digr-v5.0',VERSION,PACKAGE_VERSION):fail('descriptor identity')
    if read('VERSION').strip()!=VERSION or m.get('version')!=VERSION or m.get('protocol')!=d['protocol'] or m.get('navigation_authority') is not True:fail('pinned navigation identity')
    if m.get('bootstrap_entry')!='entry/STARTUP.md' or m.get('startup_slice')!=['entry/STARTUP.md']:fail('sole self-contained startup slice')
    if d.get('surface',{}).get('navigation_authority')!='manifest.json' or d.get('surface',{}).get('load_phase')!='after_verified_startup_slice':fail('descriptor navigation role')
    adapter=d.get('minimum_adapter',{});expected_adapter={'repository':'Gual-Wells/Deep-Iteration-GPT-Runtime','ref':'stable','descriptor_path':'runtime-descriptor.json','navigation_source':'manifest.json','activation':'after_pinned_startup_classifies_EXECUTING','artifact_integrity':'sha256_and_byte_length','execution_set_integrity':'ordered_member_count_and_execution_set_sha256'}
    if any(adapter.get(k)!=v for k,v in expected_adapter.items()):fail('descriptor minimum adapter locator/integrity')
    api=d.get('engine_api',{});expected_api={'preflight':'digr.preflight','commit_delivery':'digr.commit_delivery','preflight_binding':'runtime.host_adapter.HostAdapter.preflight','start_binding':'runtime.host_adapter.HostAdapter.start','commit_delivery_binding':'runtime.run_session.LiveDIGRRun.commit_delivery','enforced_host_integration':'required_for_canonical_attestation','execution_without_host':'MODEL_NATIVE','canonical_attestation':'requires_verified_host_enforcement'}
    if any(api.get(k)!=v for k,v in expected_api.items()):fail('descriptor logical/Python API binding')
    if f'version = "{PACKAGE_VERSION}"' not in read('pyproject.toml'):fail('PEP 440 package version mapping')
    for retired in ('defaults','parameters','time_states','policies','philosophy','release','routing'):
        if retired in m:fail(f'manifest retains execution semantics: {retired}')
    artifacts=d['artifacts']
    for name,item in artifacts.items():
        path=ROOT/item['path'];data=path.read_bytes()
        if not path.is_file() or item['byte_length']!=len(data) or item['sha256']!=digest(data) or not HEX64.fullmatch(item['sha256']):fail(f'descriptor artifact {name}')
    bundle=json.loads((ROOT/artifacts['execution_bundle']['path']).read_text(encoding='utf-8'));rows=[{k:x[k] for k in ('path','sha256','byte_length')} for x in bundle['members']]
    canonical=json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    if artifacts['execution_bundle']['member_count']!=len(rows) or artifacts['execution_bundle']['execution_set_sha256']!=digest(canonical):fail('execution set gate')
    expected=[m['entrypoint'],*m['core']]
    if m['execution_bundle'].get('members')!=expected:fail('manifest execution member declaration')
    if [x['path'] for x in bundle['members']]!=expected:fail('execution member order')
    for item in bundle['members']:
        data=(ROOT/item['path']).read_bytes()
        if (item['sha256'],item['byte_length'],item['content'])!=(digest(data),len(data),data.decode('utf-8')):fail(f'bundle member {item["path"]}')
    paths=[m['runtime_descriptor'],m['bootstrap_entry'],*m['startup_slice'],m['model_protocol_source'],m['entrypoint'],m['help'],m['workspace_spec'],m['execution_bundle']['path'],*m['core'],*m['deterministic_helpers'],*m['schemas'].values()]
    for rel in paths:
        p=PurePosixPath(rel)
        if '\\' in rel or rel.startswith('/') or any(x in ('','.','..') for x in p.parts):fail(f'unsafe manifest path {rel}')
        if not (ROOT/rel).is_file():fail(f'missing manifest path {rel}')
    for p in sorted((ROOT/'schemas').glob('*.json')):
        obj=json.loads(p.read_text(encoding='utf-8'))
        if obj.get('$schema')!='https://json-schema.org/draft/2020-12/schema' or obj.get('$id')!=f'https://gual-wells.github.io/Deep-Iteration-GPT-Runtime/schemas/{p.name}':fail(f'schema metadata {p.name}')
        refs(obj,p.name)
    compact=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').read_bytes();free=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FREE_GO.txt').read_bytes();standalone=(ROOT/'CHATGPT_LOCAL_PERSONALIZATION.txt').read_bytes();full=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FULL.txt').read_bytes()
    if compact!=free or compact!=standalone or len(compact.decode())>1500:fail('compact personalization equality/size')
    sentinel=b'<!-- DIGR_LOCAL_PERSONALIZATION_END -->\n'
    if not compact.endswith(sentinel) or not full.endswith(sentinel):fail('personalization sentinel')
    model=(ROOT/'dist/MODEL_PROTOCOL.md').read_bytes()
    if not (2000<=len(model)<=5000) or b'digr.preflight' not in model or b'digr.commit_delivery' not in model:fail('compact model protocol')
    if (ROOT/'dist/HELP.zh-CN.md').read_bytes()!=(ROOT/'entry/HELP.md').read_bytes():fail('help distribution drift')
    current='\n'.join(read(x) for x in ('entry/STARTUP.md','entry/HELP.md','entry/MODEL_PROTOCOL_SOURCE.md','core/11_PARAMETER_FORMAT_AND_RESOLUTION.md','core/15_SEMANTIC_DEFAULT_COMPLETION.md','core/20_EFFECTIVE_CONTRACT.md'))
    if 'zero_disables_D' in current or 'semantically complete missing' in current:fail('retired stable semantics')
    router=compact.decode('utf-8')
    for required in ('只去掉开头空白','真实仓库获取','`stable` branch 的当前 HEAD','/branches/stable','/git/ref/heads/stable','manifest.json','VERSION','startup_slice','没有尝试本身不是路由失败'):
        if required not in router:fail(f'local routing contract missing {required}')
    for forbidden in ('digr.preflight','digr.commit_delivery','DIGR~','DELIVERED','N=2','R=1'):
        if forbidden in router:fail(f'local layer duplicates execution semantics: {forbidden}')
    for p in ROOT.rglob('*.py'):
        if '__pycache__' in p.parts:continue
        try:ast.parse(p.read_text(encoding='utf-8'),filename=str(p),feature_version=(3,10))
        except Exception as exc:fail(f'Python 3.10 parse {p.relative_to(ROOT)}: {exc}')
    for p in ROOT.rglob('*'):
        if not p.is_file() or '__pycache__' in p.parts:continue
        if p.suffix.lower() not in {'.py','.md','.txt','.json','.toml'} and p.name!='VERSION':continue
        if b'\r' in p.read_bytes():fail(f'CR line ending {p.relative_to(ROOT)}')
    print('DIGR 5.0.0-Berta2 pinned-manifest repository: OK')
if __name__=='__main__':main()
