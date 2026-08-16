from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def fail(msg): print(f'FAIL: {msg}'); raise SystemExit(1)

def main():
    if (ROOT/'VERSION').read_text().strip()!='4.1.0': fail('VERSION')
    m=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    if m.get('protocol')!='digr-v4.1' or m.get('version')!='4.1.0': fail('manifest version/protocol')
    if m.get('bootstrap_entry')!='bootstrap/BOOTSTRAP.md': fail('bootstrap_entry')
    if m.get('routing_schema')!=1: fail('routing_schema')
    for bad in ('repository_gate','repository_loader','local_fallback_core'):
        if bad in m: fail(f'legacy control-plane field remains: {bad}')
    for rel in [m['bootstrap_entry'],m['entrypoint'],m['help'],*m['core'],*m['deterministic_helpers']]:
        if not (ROOT/rel).is_file(): fail(f'missing {rel}')
    for rel in ('DIGR_EXECUTION_GATE.md','bootstrap/REPOSITORY_ONLY_LOADER.md','runtime/bootstrap_gate.py','schemas/bootstrap-gate.schema.json','bootstrap/LOCAL_FALLBACK_CORE.md'):
        if (ROOT/rel).exists(): fail(f'obsolete control-plane artifact remains: {rel}')
    for p in (ROOT/'schemas').glob('*.json'):
        d=json.loads(p.read_text(encoding='utf-8'))
        if '$id' not in d: fail(f'schema id missing {p.name}')
    primary=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').read_bytes()
    free=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FREE_GO.txt').read_bytes()
    if primary!=free: fail('primary/Free-Go router byte drift')
    text=primary.decode('utf-8')
    if len(text)>1500: fail(f'router too long: {len(text)}')
    for token in ('候选路由键','Gual-Wells/Deep-Iteration-GPT-Runtime','stable','40','manifest.json','bootstrap_entry','entrypoint','core','权威委托'):
        if token not in text: fail(f'router missing {token}')
    for bad in ('DIGR_EXECUTION_GATE','clock','monotonic','P_target','B=0','L(1)','Mature Gambit','DIGR（N/实际N','proof'):
        if bad in text: fail(f'router duplicates versioned semantic {bad}')
    for rel in ('runtime/routing.py','runtime/task_startup.py','runtime/source_aggregate.py','runtime/isolation_checks.py','tools/build_release.py'):
        if not (ROOT/rel).exists(): fail(f'missing {rel}')
    print('DIGR 4.1.0 routing/authority contract: OK')
if __name__=='__main__': main()
