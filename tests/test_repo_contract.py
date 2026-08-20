import json,unittest
from pathlib import Path
from runtime.workspace import WORKSPACE_SCHEMA_VERSION,REQUIRED_GENESIS_FILES,STATE_DIRECTORIES
ROOT=Path(__file__).resolve().parents[1]

class TestRepoContract(unittest.TestCase):
    def test_version_manifest_and_corrected_interfaces(self):
        self.assertEqual((ROOT/'VERSION').read_text().strip(),'5.0.0-alpha.4');m=json.loads((ROOT/'manifest.json').read_text());self.assertEqual(m['version'],'5.0.0-alpha.4');self.assertEqual(m['protocol'],'digr-v5.0');self.assertEqual(m['workspace_spec'],'workspace/layout-v2.json');self.assertEqual(m['clock_journal_schema'],1);self.assertEqual((m['routing_schema'],m['repository_transport_schema'],m['run_session_schema'],m['workspace_schema'],m['event_receipt_schema']),(4,3,4,2,2));self.assertEqual(m['invocation_surface_schema'],2);self.assertEqual(m['parameter_resolution_schema'],1)
    def test_two_stage_startup_is_manifested(self):
        m=json.loads((ROOT/'manifest.json').read_text());self.assertEqual(m['startup_slice'],['bootstrap/BOOTSTRAP.md','entry/STARTUP.md']);self.assertEqual(m['execution_bundle']['path'],'bundle/EXECUTION_PROTOCOL.json');self.assertEqual(m['execution_bundle']['members'],[m['entrypoint'],*m['core']]);t=(ROOT/'entry/STARTUP.md').read_text();self.assertIn('NATIVE | HELP | INVALID | EXECUTING',t);self.assertIn('before parameter resolution, U0 or substantive task work',t);self.assertIn('ExecutingProtocolLoadReceipt',t);self.assertIn('aborts the born run',t)
    def test_run_lifecycle_is_reliability_not_planner(self):
        t=(ROOT/'core/25_RUN_SESSION_AND_EXTERNAL_MEMORY.md').read_text();self.assertIn('GENESIS',t);self.assertIn('PARAMETER_RESOLVED',t);self.assertIn('ABORTED',t);self.assertIn('do not plan task work',t)
    def test_strategy_genesis_and_mutability(self):
        t=(ROOT/'core/35_STRATEGY_AND_CANDIDATE_STATE.md').read_text();self.assertIn('Freeze commitments, never freeze strategy',t);self.assertIn('Strategy Genesis',t);self.assertIn('next_step',t);self.assertIn('Candidate',t)
    def test_source_presumption_and_single_time_chain(self):
        t=(ROOT/'core/50_SOURCE_EVOLUTION.md').read_text();self.assertIn('REQUIRED',t);self.assertIn('WAIVED',t);self.assertIn('active_source_ids',t);self.assertIn('parallel',t.lower())
        self.assertFalse((ROOT/'runtime/source_aggregate.py').exists())
    def test_formal_time_and_cross_session_strictness(self):
        t=(ROOT/'core/60_FORMAL_ACTIVE_TIME.md').read_text();
        for x in ('MAIN','SOURCE','D_EXCLUSIVE','META','IDLE','Observed duration','hard-verifiable duration','same provider','non-empty boot identity','?'):self.assertIn(x,t)
    def test_d_l_reintegrated(self):
        t=(ROOT/'core/77_ISOLATION_LEVELS.md').read_text();self.assertIn('L_target',t);self.assertIn('L_cap',t);self.assertIn('L_actual',t);self.assertIn('Input Packet',t);self.assertIn('Output Packet',t);self.assertIn('background',t)
        d=(ROOT/'core/75_DISRUPTIVE_GAMBIT.md').read_text();self.assertIn('proposal',d.lower());self.assertIn('Decree',d);self.assertIn('reintegration',d.lower());self.assertIn('Candidate',d)
    def test_workspace_layout_v2_matches_runtime_constants(self):
        d=json.loads((ROOT/'workspace/layout-v2.json').read_text());self.assertEqual(d['schema_version'],WORKSPACE_SCHEMA_VERSION);self.assertEqual(tuple(d['required_genesis_files']),REQUIRED_GENESIS_FILES);self.assertEqual(tuple(d['state_directories']),STATE_DIRECTORIES)
    def test_help_is_canonical_zh_cn_professional_reference(self):
        t=(ROOT/'entry/HELP.md').read_text();
        for x in ('## 1. 调用与路由','## 2. 参数解析顺序与缺省规则','## 3. 参数参考','## 4. Effective Contract 与来源策略','## 5. N / R / D / L','## 6. 时间与停止','## 7. 执行链与启动成本','## 8. 输出与 canonical proof','## 9. 版本与权威'):
            self.assertIn(x,t)
        for x in ('`B=0`、`b=0`、`L(1)`','SourceDisposition','`REQUIRED`','`D(0)`','soft target','hard lower bound','actual duration 向下取整到完整秒','NATIVE'):
            self.assertIn(x,t)
    def test_pre_release_baseline_documented(self):
        t=(ROOT/'docs/PRE_RELEASE_BASELINE.md').read_text();self.assertIn('corrected integration baseline',t.lower());self.assertIn('mother-base',t);self.assertIn('Change discipline',t);self.assertIn('clock-journal',t)
    def test_removed_alpha1_overlap_artifacts(self):
        for rel in ('schemas/runtime-state.schema.json','schemas/invocation.schema.json','workspace/layout-v1.json','runtime/source_aggregate.py'):
            self.assertFalse((ROOT/rel).exists(),rel)
if __name__=='__main__':unittest.main()
