from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]

def loadj(p):
    try: return json.loads((ROOT/p).read_text(encoding='utf-8'))
    except Exception as e: errors.append(f"JSON invalid {p}: {e}"); return {}

manifest=loadj('manifest.json')
if (ROOT/'VERSION').read_text(encoding='utf-8').strip()!=manifest.get('version'):
    errors.append('VERSION != manifest.version')
if manifest.get('version')!='2.2.0' or manifest.get('protocol')!='digr-v2.2':
    errors.append('unexpected version/protocol')

paths=[]
paths += [manifest.get('entrypoint','')]
paths += manifest.get('global_invariants',[])
paths += manifest.get('core_sequence',[])
paths += list(manifest.get('objectives',{}).values())
paths += list(manifest.get('stages',{}).values())
paths += [manifest.get('routing',''),manifest.get('default_profile',''),manifest.get('fallback_core','')]
paths += list(manifest.get('schemas',{}).values())
for p in paths:
    if not p or not (ROOT/p).is_file(): errors.append(f'missing manifest path: {p}')

for p in manifest.get('schemas',{}).values(): loadj(p)

local=(ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt').read_text(encoding='utf-8')
if len(local)>5000: errors.append(f'local personalization too long: {len(local)} chars')

active_scan=['manifest.json','entry/DEEP_ITERATION_ENTRY.md','core/85_RUNTIME_REPORT.md','bootstrap/LOCAL_FALLBACK_CORE.md','local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt']
legacy=['return_execution_evidence_then_final_result','85_EXECUTION_EVIDENCE_REPORT','execution-evidence.schema.json']
for p in active_scan:
    t=(ROOT/p).read_text(encoding='utf-8')
    for needle in legacy:
        if needle in t: errors.append(f'legacy active reference {needle} in {p}')

pol=manifest.get('policies',{})
required=['show_prompt_iteration_count','show_final_optimized_prompt','show_evolution_metrics','show_redo_count','show_actual_workflow_chain','show_queries_and_sources_used','return_final_result_then_runtime_report','do_not_return_legacy_execution_evidence_block']
for k in required:
    if pol.get(k) is not True: errors.append(f'policy not enabled: {k}')

if errors:
    print('FAIL')
    for e in errors: print('-',e)
    sys.exit(1)
print('PASS')
print('version:',manifest['version'])
print('protocol:',manifest['protocol'])
print('manifest referenced paths:',len(paths))
print('local personalization chars:',len(local))
