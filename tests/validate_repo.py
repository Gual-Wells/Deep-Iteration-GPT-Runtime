from __future__ import annotations
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='5.0.0-alpha.10'
CORE=[
 'core/00_RESULT_SOVEREIGNTY.md','core/10_INVOCATION_AND_U0.md','core/20_EFFECTIVE_CONTRACT.md',
 'core/25_RUN_SESSION_AND_EXTERNAL_MEMORY.md','core/40_NATIVE_EVOLUTION.md',
 'core/60_FORMAL_ACTIVE_TIME.md','core/80_STOP_AND_PROOF.md'
]
def fail(msg):print(f'FAIL: {msg}');raise SystemExit(1)
def read(rel):return (ROOT/rel).read_text(encoding='utf-8')
def main():
    if read('VERSION').strip()!=VERSION:fail('VERSION')
    m=json.loads(read('manifest.json'))
    if m.get('version')!=VERSION or m.get('protocol')!='digr-v5.0':fail('manifest identity')
    if m.get('core')!=CORE:fail('contracted core authority')
    if m.get('execution_bundle',{}).get('members')!=[m['entrypoint'],*CORE]:fail('bundle member contract')
    d=m.get('defaults',{})
    if (d.get('B'),d.get('b'),d.get('D_s'))!=(0,0,0):fail('lightweight defaults')
    if 's' in d.get('semantic_completion',[]):fail('omitted D still semantically forced')
    if 'runtime/runtime_package.py' not in m.get('deterministic_helpers',[]):fail('runtime package verifier missing')
    p=m.get('policies',{})
    for k in (
      'single_runtime_package_attestation_replaces_per_helper_verification',
      'runtime_package_verifier_binds_bundle_members_to_git_tree',
      'ordinary_resume_uses_fast_path','full_workspace_audit_is_anomaly_fallback_or_explicit',
      'state_transition_does_not_force_global_checkpoint','soft_timing_does_not_force_work_lease',
      'derived_latest_cache_is_unindexed','journal_reindex_is_batched','compact_D_completion_preferred',
      'source_disposition_is_semantic_necessity_decision','omitted_D_defaults_zero',
      'reliability_cost_must_not_scale_by_repeated_full_history_scans'):
        if p.get(k) is not True:fail(f'policy {k}')
    rd=m.get('runtime_distribution',{})
    if 'single_pinned_verifier' not in rd.get('identity_verification',''):fail('package attestation identity')
    if 'git_tree' not in rd.get('attestation_scope',''):fail('git tree attestation scope')
    layout=json.loads(read('workspace/layout-v2.json'))
    if 'protocol-load.json' not in layout.get('required_genesis_files',[]):fail('protocol load not genesis-required')
    required=[m['bootstrap_index'],m['bootstrap_entry'],*m['startup_slice'],m['entrypoint'],m['help'],m['workspace_spec'],m['execution_bundle']['path'],rd['workflow_path'],*CORE,*m['deterministic_helpers']]
    for rel in dict.fromkeys(required):
        if not (ROOT/rel).is_file():fail(f'missing path {rel}')
    for path in sorted((ROOT/'schemas').glob('*.json')):
        obj=json.loads(path.read_text(encoding='utf-8'))
        if obj.get('$schema')!='https://json-schema.org/draft/2020-12/schema':fail(f'schema draft {path.name}')
    primary=read('local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt')
    for token in ('精确大写 ASCII `DIGR`','【任务工作防火墙】','bootstrap_index','startup_slice','package-level attestation verifier'):
        if token not in primary:fail(f'router missing {token}')
    for bad in ('B=0','B=1','D=0','Formal Active','LiveDIGRRun'):
        if bad in primary:fail(f'router copied versioned semantics {bad}')
    rs=read('runtime/run_session.py')
    for token in ('recover_run_workspace_fast','complete_d_intervention_compact','index_existing_many'):
        if token not in rs:fail(f'run-session contraction missing {token}')
    if 'self.checkpoint()\n\n    def open_work_lease' in rs:fail('transition still checkpoints globally')
    wp=read('runtime/workspace.py')
    for token in ('write_cache_json','_is_derived_cache_path','index_existing_many'):
        if token not in wp:fail(f'workspace contraction missing {token}')
    pkg=read('runtime/runtime_package.py')
    for token in ('attest_runtime_package','RUNTIME-INDEX.json','execution bundle member differs from authoritative Git blob'):
        if token not in pkg:fail(f'package verifier missing {token}')
    bundle=json.loads(read(m['execution_bundle']['path']))
    if bundle.get('version')!=VERSION or [x.get('path') for x in bundle.get('members',[])]!=m['execution_bundle']['members']:fail('generated bundle identity')
    for item in bundle['members']:
        data=(ROOT/item['path']).read_bytes()
        if item.get('byte_length')!=len(data) or item.get('sha256')!=hashlib.sha256(data).hexdigest() or item.get('content')!=data.decode('utf-8'):fail(f'bundle drift {item["path"]}')
    for path in sorted(ROOT.rglob('*.py')):
        if '__pycache__' in path.parts:continue
        try:ast.parse(path.read_text(encoding='utf-8'),filename=str(path),feature_version=(3,10))
        except Exception as exc:fail(f'Python 3.10 parse failure {path.relative_to(ROOT)}: {exc}')
    print('DIGR 5.0.0-alpha.10 liveness-contraction candidate: OK')
if __name__=='__main__':main()
