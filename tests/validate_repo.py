from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def need(path):
    p=ROOT/path
    if not p.exists(): errors.append(f'missing: {path}')
    return p
m=json.loads(need('manifest.json').read_text(encoding='utf-8'))
if m.get('version')!='2.3.0': errors.append('manifest version != 2.3.0')
if m.get('protocol')!='digr-v2.3': errors.append('protocol != digr-v2.3')
if (ROOT/'VERSION').read_text(encoding='utf-8').strip()!='2.3.0': errors.append('VERSION mismatch')
for p in m.get('global_invariants',[])+m.get('core_sequence',[]): need(p)
for p in m.get('objectives',{}).values(): need(p)
for p in m.get('stages',{}).values(): need(p)
for p in m.get('schemas',{}).values(): need(p)
need(m['entrypoint']); need(m['routing']); need(m['fallback_core']); need('runtime/protocol_pin.py')
ref=m.get('complexity_reference',{})
if ref.get('model')!='GPT-5.6 Sol' or ref.get('reasoning_mode')!='high': errors.append('T reference model mismatch')
if not ref.get('no_fixed_time_tiers'): errors.append('fixed tier regression')
if not ref.get('no_programmatic_workload_mapping'): errors.append('programmatic workload regression')
if not ref.get('early_stop_requires_semantic_budget_adequacy_check'): errors.append('missing T stop gate')
# Static semantic regression scan in active protocol/docs, excluding historical migration/research notes/changelog.
active=[ROOT/'README.md', ROOT/'core/15_INVOCATION_BUDGETS.md', ROOT/'core/18_T_COMPLEXITY_CALIBRATION.md', ROOT/'docs/T_COMPLEXITY_SEMANTICS.md', ROOT/'local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt']
for p in active:
    t=p.read_text(encoding='utf-8')
    if '≤10m' in t or '>10m–30m' in t: errors.append(f'legacy tier mapping in {p.relative_to(ROOT)}')
parser=(ROOT/'runtime/reference_parser.py').read_text(encoding='utf-8')
if 'complexity_budget_raw' not in parser: errors.append('parser does not preserve raw T')
if 'normalized_minutes' in parser or 'Focused' in parser or 'Analytical' in parser: errors.append('parser interprets T programmatically')
# JSON syntax
for p in (ROOT/'schemas').glob('*.json'):
    try: json.loads(p.read_text(encoding='utf-8'))
    except Exception as e: errors.append(f'invalid json {p.name}: {e}')
if errors:
    print('DIGR 2.3 validation FAILED')
    for e in errors: print('-',e)
    sys.exit(1)
print('DIGR 2.3 validation OK')
