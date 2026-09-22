from __future__ import annotations
import ast,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERSION='5.0.0-alpha.7'
INTERFACES={
    'routing_schema':4,'repository_transport_schema':3,'invocation_surface_schema':2,
    'parameter_resolution_schema':2,'run_session_schema':5,'workspace_schema':2,
    'clock_journal_schema':1,'event_receipt_schema':2,'execution_commitment_schema':1,
    'execution_attempt_schema':1,'runtime_distribution_schema':1,
}

def fail(msg):
    print(f'FAIL: {msg}');raise SystemExit(1)

def read(rel):return (ROOT/rel).read_text(encoding='utf-8')

def main():
    if read('VERSION').strip()!=VERSION:fail('VERSION')
    m=json.loads(read('manifest.json'))
    if m.get('version')!=VERSION or m.get('protocol')!='digr-v5.0':fail('manifest identity')
    for k,v in INTERFACES.items():
        if m.get(k)!=v:fail(f'interface {k}')
    if m.get('bootstrap_index')!='bootstrap/INDEX.md':fail('bootstrap index')
    if m.get('startup_slice')!=['bootstrap/INDEX.md','bootstrap/BOOTSTRAP.md','entry/STARTUP.md']:fail('startup slice')
    if m.get('workspace_spec')!='workspace/layout-v2.json':fail('workspace spec')

    # Public Alpha 7 parameter/time surface.
    if 'L_e' in m.get('defaults',{}) or 'L' in m.get('parameters',{}):fail('public L remains in manifest')
    ts=m.get('time_states',{})
    if ts.get('D_EXCLUSIVE',{}).get('T') is not True or ts.get('D_EXCLUSIVE',{}).get('t') is not False:
        fail('D_EXCLUSIVE must count T and not t')
    if m.get('defaults',{}).get('B')!=1 or m.get('defaults',{}).get('b')!=1:fail('B/b defaults')

    required_policies=(
        'route_requires_actual_acquisition_attempt','repository_transport_is_host_bridge_not_execution_semantics',
        'bootstrap_index_precedes_startup','implemented_repository_helpers_are_real_execution_facilities',
        'router_task_work_firewall_until_startup_ready','startup_reading_is_not_execution',
        'execute_before_interpret_for_declared_operational_components','implementation_identity_precedes_semantic_equivalence',
        'declared_implementation_substitution_forbidden_until_actual_failure','component_interrogation_precedes_declared_helper_operation',
        'accepted_execution_commitment_constrains_next_relevant_action','implementation_delivery_is_first_class_startup_requirement',
        'runtime_artifact_members_verify_against_pinned_git_tree','no_identity_preserving_delivery_path_fails_closed',
        'D_zero_means_no_minimum_not_disabled','D_exclusive_counts_T_not_t','public_L_parameter_removed',
        'internal_D_isolation_fixed_to_L1','formal_work_lease_required_for_cross_host_attribution',
        'unleased_formal_cross_host_gap_is_preserved_not_dropped','hard_time_requires_complete_semantic_time_coverage',
        'source_work_lease_carries_active_source_binding','finalization_admission_precedes_ledger_finish',
        'FINISHED_requires_delivery_ready',
    )
    for k in required_policies:
        if m.get('policies',{}).get(k) is not True:fail(f'policy {k}')

    eb=m.get('execution_bundle');rd=m.get('runtime_distribution')
    if not isinstance(eb,dict) or eb.get('members')!=[m['entrypoint'],*m['core']]:fail('execution bundle metadata')
    if not isinstance(rd,dict) or rd.get('artifact_name_template')!='digr-runtime-{SHA}':fail('runtime distribution')
    required=[m['bootstrap_index'],m['bootstrap_entry'],*m['startup_slice'],m['entrypoint'],m['help'],m['workspace_spec'],eb['path'],rd['workflow_path'],*m['core'],*m['deterministic_helpers']]
    for rel in dict.fromkeys(required):
        if not (ROOT/rel).is_file():fail(f'missing path {rel}')

    # Schemas.
    for p in sorted((ROOT/'schemas').glob('*.json')):
        try:d=json.loads(p.read_text(encoding='utf-8'))
        except Exception as exc:fail(f'invalid schema {p.name}: {exc}')
        if d.get('$schema')!='https://json-schema.org/draft/2020-12/schema':fail(f'schema draft {p.name}')
        if d.get('$id')!=f'https://gual-wells.github.io/Deep-Iteration-GPT-Runtime/schemas/{p.name}':fail(f'schema id {p.name}')
    ps=json.loads(read('schemas/parameter-resolution.schema.json'))
    ec=json.loads(read('schemas/effective-contract.schema.json'))
    if 'L_e' in ps.get('properties',{}) or 'L_e' in ec.get('properties',{}):fail('L remains in public schema')
    if 'L_mismatch_blocks_delivery' in ec.get('properties',{}):fail('L mismatch remains in contract')

    # Local router remains version-neutral; Alpha 7 semantics stay repository-side.
    primary=read('local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt')
    full=read('local-personalization/CHATGPT_LOCAL_PERSONALIZATION_FULL.txt')
    if not 1500 < len(primary) <= 5000:fail('Plus router length')
    for token in ('精确大写 ASCII `DIGR`','NATIVE','bootstrap_index','startup_slice','【任务工作防火墙】','【执行优先/防穿透】','semantic equivalence ≠ implementation identity'):
        if token not in primary:fail(f'router missing {token}')
    for bad in ('B=0','b=0','B=1','b=1','L(1)','Formal Active'):
        if bad in primary:fail(f'router copied execution semantics {bad}')
    for token in ('Expanded Routing / Transparency / Execution-Integrity Reference','Execute-before-interpret and implementation delivery'):
        if token not in full:fail(f'full router missing {token}')

    index=read(m['bootstrap_index'])
    for token in ('Reality model','Machine topology','Truth-source map','Structure-closed, intelligence-open','Execute-before-interpret inoculation','Implementation delivery reality'):
        if token not in index:fail(f'INDEX missing {token}')

    help_text=read('entry/HELP.md')
    for token in ('## 1. 调用与路由','## 2. 参数解析顺序与缺省规则','## 3. 参数参考','## 4. Effective Contract 与来源策略','## 5. N / R / D','## 6. 时间与停止','## 7. 执行链与启动成本','## 8. 输出与 canonical proof','## 9. 版本与权威','work lease','coverage gap','D_EXCLUSIVE'):
        if token not in help_text:fail(f'help missing {token}')
    if 'N / R / D / L' in help_text or 'L(target)/L(actual)' in help_text or '`L(1)`' in help_text:fail('help exposes public L')

    # Alpha 7 implementation invariants.
    rs=read('runtime/run_session.py')
    for token in ('open_work_lease','derive_work_timeline','preview_finish','finalization admission denied','FINISHED is forbidden when delivery readiness is false','make_isolation_receipt(receipt_id,1'):
        if token not in rs:fail(f'run-session invariant missing {token}')
    cj=read('runtime/clock_journal.py')
    for token in ('WORK_LEASE_OPEN','CoverageGap','derive_work_timeline','lease_open'):
        if token not in cj:fail(f'clock journal invariant missing {token}')
    il=read('runtime/interval_ledger.py')
    for token in ('WorkState.D_EXCLUSIVE','T_coverage_complete','unattributed_T_ns','preview_finish'):
        if token not in il:fail(f'ledger invariant missing {token}')
    if 'L_target:' in read('runtime/proof.py') or "L_target=contract" in read('runtime/proof.py'):fail('proof still exposes L')

    # Python 3.10 and UTF-8/LF release hygiene.
    for p in sorted(ROOT.rglob('*.py')):
        if any(x in p.parts for x in ('.git','__pycache__')):continue
        try:ast.parse(p.read_text(encoding='utf-8'),filename=str(p),feature_version=(3,10))
        except Exception as exc:fail(f'Python 3.10 parse failure {p.relative_to(ROOT)}: {exc}')
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or any(x in p.parts for x in ('.git','__pycache__')):continue
        if p.suffix.lower() not in {'.py','.md','.txt','.json'} and p.name!='VERSION':continue
        raw=p.read_bytes()
        if b'\r' in raw:fail(f'CR line ending {p.relative_to(ROOT)}')
        try:raw.decode('utf-8')
        except UnicodeDecodeError:fail(f'non-UTF8 {p.relative_to(ROOT)}')

    for rel in ('docs/PRE_RELEASE_BASELINE.md','docs/CLOCK_RELIABILITY.md','docs/RUN_SESSION_ARCHITECTURE.md','docs/PROTOCOL_SPEC_5.0.0-alpha.6.md','docs/PROTOCOL_SPEC_5.0.0-alpha.7.md','docs/TEST_MATRIX.md'):
        if not (ROOT/rel).is_file():fail(f'missing release doc {rel}')

    # Execution bundle is exact generated transport.
    bundle=json.loads(read(eb['path']))
    if bundle.get('schema_version')!=1 or bundle.get('version')!=VERSION or bundle.get('protocol')!='digr-v5.0':fail('bundle identity')
    members=bundle.get('members')
    if [x.get('path') for x in members]!=eb['members']:fail('bundle member order')
    for item in members:
        data=(ROOT/item['path']).read_bytes()
        if item.get('byte_length')!=len(data) or item.get('sha256')!=hashlib.sha256(data).hexdigest() or item.get('content')!=data.decode('utf-8'):
            fail(f'bundle drift {item["path"]}')

    print('DIGR 5.0.0-alpha.7 formal-time continuity / internal-L1 baseline: OK')

if __name__=='__main__':main()
