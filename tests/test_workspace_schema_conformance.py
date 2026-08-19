import fnmatch
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from runtime.candidate_store import CandidateSnapshot
from runtime.effective_contract import EffectiveContract, SourceContract, SourceDisposition
from runtime.est_store import ESTSnapshot
from runtime.evidence_index import EvidenceRecord
from runtime.interval_ledger import WorkState
from runtime.isolation_checks import IsolationFacts
from runtime.run_session import LiveDIGRRun
from runtime.strategy_store import StrategyState
from tests.helpers import FakeClock, authority

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / 'schemas'


def registry_and_schemas():
    registry = Registry()
    by_rel = {}
    for path in sorted(SCHEMAS.glob('*.json')):
        schema = json.loads(path.read_text(encoding='utf-8'))
        registry = registry.with_resource(schema['$id'], Resource.from_contents(schema))
        by_rel[f'schemas/{path.name}'] = schema
    return registry, by_rel


def best_schema(rel: str, mapping: dict[str, str]):
    matches = [(pattern, schema) for pattern, schema in mapping.items() if fnmatch.fnmatch(rel, pattern)]
    if not matches:
        return None
    # Prefer the pattern with fewer wildcards, then the larger literal surface.
    return sorted(matches, key=lambda x: (x[0].count('*'), -len(x[0])))[0]


class TestWorkspaceSchemaConformance(unittest.TestCase):
    def build_full_workspace(self, td):
        c = FakeClock()
        run = LiveDIGRRun.start(authority(), 'DIGR(D,L(2)):x', Path(td), c, run_id='digr-12345678')
        run.resolve_parameters(); run.freeze_u0('x')
        run.freeze_contract(EffectiveContract(1, 0, 1, 0, SourceContract(1, 0, 1, 0), 1, 2, SourceDisposition.REQUIRED))
        run.transition(WorkState.MAIN, c())
        run.save_strategy(StrategyState(0, 'task model', 'primary route', ('alternative',), 'source route', 'validate', 'tools'))
        run.record_main_evolution('architecture changed', 'implemented', 'better')
        run.save_candidate(CandidateSnapshot(0, 'candidate'))
        run.record_main_reentry(0, 'challenge', 'rerun', 'retained', retained=True)
        run.est.save(ESTSnapshot('MAIN', 0, ('fact',), ('decision',), (), ('question',), ('primary route',), (), ('updated',), 0, 0))
        run.evidence.add(EvidenceRecord('E1', 'test', 'local:test', 'test evidence'))
        run.completion.open_gap('G1', 'verify integration', True)
        run.completion.close_gap('G1', 'verified')

        run.open_source('S1', 'research source')
        run.transition(WorkState.SOURCE, c(), active_source_ids=('S1',))
        run.record_source_evolution('S1', 'finding', 'searched', 'found')
        run.record_source_reentry('S1', 0, 'cross-check', 'independent check', 'retained', retained=True)
        run.close_source('S1', 'sufficient')

        run.transition(WorkState.MAIN, c())
        inp = run.write_d_packet('D1-in', 'input', {'task': 'controlled subset'})
        l2 = IsolationFacts(True, True, True, True, True)
        run.add_isolation_facts('iso2', l2, input_packet_ref=inp)
        run.create_d_intervention('D1', 'iso2', 'orthogonal test'); run.decree_d('D1', 'execute')
        run.transition(WorkState.D_EXCLUSIVE, c()); run.record_d_execution('D1', 'isolated execution')
        out = run.write_d_packet('D1-out', 'output', {'finding': 'no counterexample'})
        run.record_d_result('D1', 'result', output_packet_ref=out)
        run.transition(WorkState.MAIN, c())
        run.reintegrate_d('D1', accepted='none', rejected='counterexample', main_consequence='retain route')
        run.completion.assess('ready')
        run.finish_time(c()); run.write_run_summary()
        return run

    def test_every_persisted_artifact_family_has_schema_and_instance_conforms(self):
        registry, schemas = registry_and_schemas()
        layout = json.loads((ROOT / 'workspace/layout-v2.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as td:
            run = self.build_full_workspace(td)
            unmatched = []
            failures = []
            for path in sorted(p for p in run.workspace.root.rglob('*') if p.is_file()):
                rel = path.relative_to(run.workspace.root).as_posix()
                match = best_schema(rel, layout['artifact_schemas'])
                if match is None:
                    unmatched.append(rel); continue
                _, schema_rel = match
                schema = schemas[schema_rel]
                values = ([json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
                          if rel.endswith('.ndjson') else [json.loads(path.read_text(encoding='utf-8'))])
                validator = Draft202012Validator(schema, registry=registry)
                for i, value in enumerate(values):
                    errors = list(validator.iter_errors(value))
                    if errors:
                        failures.append((rel, i, [e.message for e in errors[:4]]))
            self.assertEqual(unmatched, [], f'unmapped workspace artifact families: {unmatched}')
            self.assertEqual(failures, [], f'workspace/schema drift: {failures}')


if __name__ == '__main__':
    unittest.main()
