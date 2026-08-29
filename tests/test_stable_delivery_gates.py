import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from runtime.candidate_store import CandidateSnapshot
from runtime.delivery import DeliveryEnvelope,DeliveryGateError
from runtime.effective_contract import EffectiveContract,SourceContract,SourceDisposition
from runtime.execution_protocol import (
    ExecutingProtocolLoadReceipt,ProtocolMemberReceipt,execution_set_sha256,
    verify_descriptor_execution_bundle,verify_execution_bundle,
)
from runtime.interval_ledger import WorkState
from runtime.protocol_authority import ProtocolAuthority,ProtocolIdentity
from runtime.routing import AUTHORITATIVE_REPOSITORY,RouteReceipt
from runtime.run_lifecycle import RunPhase
from runtime.run_recovery import verify_run_workspace
from runtime.run_session import LiveDIGRRun
from runtime.strategy_store import StrategyState
from tests.helpers import (
    FakeClock,persist_enforced_host_receipts,stable_invocation_for_contract,
    stable_preflight_parameters,
)

SHA='a'*40
VERSION='5.0.0-Berta2'
PATHS=('entry/E.md','core/A.md')
FILES=(('entry/E.md',b'# entry\n'),('core/A.md',b'# core\n'))
MANIFEST={
    'version':VERSION,'protocol':'digr-v5.0','entrypoint':'entry/E.md','core':['core/A.md'],
    'execution_bundle':{'path':'bundle/EXECUTION_PROTOCOL.json','schema':1,'members':list(PATHS)},
}
MANIFEST_BYTES=(json.dumps(MANIFEST,sort_keys=True,separators=(',',':'))+'\n').encode()
VERSION_BYTES=(VERSION+'\n').encode()


def authority():
    route=RouteReceipt(
        AUTHORITATIVE_REPOSITORY,'stable',SHA,'manifest.json',
        hashlib.sha256(MANIFEST_BYTES).hexdigest(),'VERSION',hashlib.sha256(VERSION_BYTES).hexdigest(),
    )
    ident=ProtocolIdentity('digr-v5.0',VERSION,AUTHORITATIVE_REPOSITORY,SHA)
    return ProtocolAuthority(route,ident)


def protocol_bundle():
    members=[]
    for path,data in FILES:
        members.append({
            'path':path,'sha256':hashlib.sha256(data).hexdigest(),
            'byte_length':len(data),'content':data.decode(),
        })
    raw=(json.dumps({
        'schema_version':1,'version':VERSION,'protocol':'digr-v5.0','members':members,
    },sort_keys=True,separators=(',',':'))+'\n').encode()
    return verify_execution_bundle(raw,commit_sha=SHA,manifest_bytes=MANIFEST_BYTES,expected_paths=PATHS)


class TestStableDeliveryGates(unittest.TestCase):
    def prepare(self,td,*,message=None,contract=None,clock=None,add_candidate=True,assess=True,candidate_bytes=b'payload',host_authority=True,source_tools=True):
        c=clock or FakeClock()
        contract=contract or EffectiveContract(
            0,0,0,0,SourceContract(0,0,0,0),0,1,
            SourceDisposition.WAIVED,'original closed task',
        )
        if message is None:message=stable_invocation_for_contract(contract)
        resolved=stable_preflight_parameters(message)
        run=LiveDIGRRun.start(authority(),message,Path(td),c,run_id='digr-stable-0001')
        run.bind_protocol_load(protocol_bundle().receipt)
        self.assertEqual(run.bind_preflight_parameters(resolved).status.value,'RESOLVED')
        if host_authority:persist_enforced_host_receipts(run,source_tools=source_tools)
        run.freeze_u0('x')
        run.freeze_contract(contract)
        run.transition(WorkState.MAIN,c())
        run.save_strategy(StrategyState(0,'task model','route'))
        if add_candidate:
            if candidate_bytes is None:run.save_candidate(CandidateSnapshot(0,'summary only'))
            else:run.save_candidate_bytes(candidate_bytes,summary='candidate')
        if assess:run.completion.assess('semantic completion checked')
        run.finish_time(c())
        return run,c

    def test_receipt_binds_exact_manifest_member_set(self):
        complete=protocol_bundle().receipt
        self.assertEqual(complete.verify_complete_members(),PATHS)
        bad=complete.to_dict();bad['members']=bad['members'][:1]
        with self.assertRaisesRegex(ValueError,'complete manifest execution set'):
            ExecutingProtocolLoadReceipt.from_dict(bad)

    def test_identity_only_incomplete_receipt_cannot_bind(self):
        legacy=ExecutingProtocolLoadReceipt(
            1,SHA,hashlib.sha256(MANIFEST_BYTES).hexdigest(),VERSION,'digr-v5.0','bundle',
            'bundle/EXECUTION_PROTOCOL.json','d'*64,
            (ProtocolMemberReceipt('entry/E.md','e'*64,1),),
        )
        with tempfile.TemporaryDirectory() as td:
            c=FakeClock();run=LiveDIGRRun.start(authority(),'DIGR：x',Path(td),c,run_id='digr-stable-0001')
            with self.assertRaisesRegex(ValueError,'lacks bound manifest bytes'):
                run.bind_protocol_load(legacy)
            self.assertFalse(run.workspace.path('protocol-load.json').exists())

    def test_stable_u0_is_exact_raw_invocation_task(self):
        with tempfile.TemporaryDirectory() as td:
            raw_task='  原始题目，保留尾空白  \n'
            message='DIGR：'+raw_task;resolved=stable_preflight_parameters(message)
            c=FakeClock();run=LiveDIGRRun.start(
                authority(),message,Path(td),c,run_id='digr-stable-0001',
            )
            run.bind_protocol_load(protocol_bundle().receipt);run.bind_preflight_parameters(resolved)
            with self.assertRaisesRegex(ValueError,'exactly equal'):
                run.freeze_u0(raw_task.strip())
            with self.assertRaisesRegex(ValueError,'exactly equal'):
                run.freeze_u0('  改写后的题目  \n')
            self.assertFalse(run.workspace.path('U0.json').exists())
            frozen=run.freeze_u0()
            self.assertEqual(frozen.text,raw_task)
            self.assertEqual(frozen.sha256,hashlib.sha256(raw_task.encode('utf-8')).hexdigest())
            self.assertEqual(run.workspace.read_json('U0.json')['text'],raw_task)

    def test_descriptor_receipt_cannot_self_attest_with_one_member(self):
        members=[]
        receipts=[]
        for path,data in FILES:
            receipt=ProtocolMemberReceipt(path,hashlib.sha256(data).hexdigest(),len(data))
            receipts.append(receipt)
            members.append({**receipt.to_dict(),'content':data.decode()})
        bundle_bytes=(json.dumps({
            'schema_version':1,'version':VERSION,'protocol':'digr-v5.0','members':members,
        },sort_keys=True,separators=(',',':'))+'\n').encode()
        descriptor={
            'schema':'digr-runtime-descriptor/v1','version':VERSION,'protocol':'digr-v5.0',
            'artifacts':{'execution_bundle':{
                'path':'bundle/EXECUTION_PROTOCOL.json',
                'sha256':hashlib.sha256(bundle_bytes).hexdigest(),
                'byte_length':len(bundle_bytes),'member_count':len(receipts),
                'execution_set_sha256':execution_set_sha256(receipts),
            }},
        }
        descriptor_bytes=(json.dumps(descriptor,sort_keys=True,separators=(',',':'))+'\n').encode()
        complete=verify_descriptor_execution_bundle(
            bundle_bytes,commit_sha=SHA,descriptor_bytes=descriptor_bytes,
        ).receipt
        self.assertEqual(complete.verify_complete_members(),PATHS)

        # The pinned descriptor commits the full ordered set.  A receipt that
        # preserves its container claim but drops all except one member must
        # fail eagerly instead of treating its own member list as authority.
        truncated=complete.to_dict();truncated['members']=truncated['members'][:1]
        with self.assertRaisesRegex(ValueError,'member count disagrees'):
            ExecutingProtocolLoadReceipt.from_dict(truncated)

        wrong_container=complete.to_dict();wrong_container['container_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'container digest disagrees'):
            ExecutingProtocolLoadReceipt.from_dict(wrong_container)

    def test_unmet_minima_becomes_incomplete_and_never_proves(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(
                1,0,0,0,SourceContract(0,0,0,0),0,1,
                SourceDisposition.WAIVED,'closed task',
            )
            final=b'not enough evolution';run,_=self.prepare(td,contract=contract,candidate_bytes=final)
            with self.assertRaises(DeliveryGateError) as cm:
                run.commit_delivery(final)
            self.assertIn('N_MINIMUM',cm.exception.unmet)
            self.assertEqual(run.phase.phase,RunPhase.INCOMPLETE)
            self.assertFalse(run.workspace.path('final/delivery.bin').exists())
            self.assertFalse(run.workspace.path('final/stable-proof.json').exists())
            with self.assertRaises(DeliveryGateError):run.render_proof()

    def test_missing_semantic_assessment_or_candidate_blocks_delivery(self):
        for add_candidate,assess,expected in ((True,False,'SEMANTIC_ASSESSMENT_MISSING'),(False,True,'FINAL_CANDIDATE_MISSING')):
            with self.subTest(expected=expected),tempfile.TemporaryDirectory() as td:
                run,_=self.prepare(td,add_candidate=add_candidate,assess=assess,candidate_bytes=b'payload')
                with self.assertRaises(DeliveryGateError) as cm:run.commit_delivery(b'payload')
                self.assertIn(expected,cm.exception.unmet)
                self.assertEqual(run.phase.phase,RunPhase.INCOMPLETE)

    def test_missing_or_advisory_host_authority_blocks_delivery(self):
        with tempfile.TemporaryDirectory() as td:
            run,_=self.prepare(td,host_authority=False)
            with self.assertRaises(DeliveryGateError) as cm:run.commit_delivery(b'payload')
            self.assertIn('PREFLIGHT_RECEIPT_INVALID',cm.exception.unmet)
            self.assertEqual(run.phase.phase,RunPhase.INCOMPLETE)
        with tempfile.TemporaryDirectory() as td:
            run,_=self.prepare(td)
            capability=run.workspace.read_json('capability-negotiation.json')
            capability['mode']='ADVISORY';capability['reasons']=['final output is not interposed']
            run.workspace.write_json(
                'capability-negotiation.json',capability,kind='capability-negotiation',
            )
            with self.assertRaises(DeliveryGateError) as cm:run.commit_delivery(b'payload')
            self.assertIn('CANONICAL_DELIVERY_NOT_ENFORCED',cm.exception.unmet)
            self.assertEqual(run.phase.phase,RunPhase.INCOMPLETE)

    def test_source_tools_gate_depends_on_final_source_contract(self):
        waived=EffectiveContract(
            0,0,0,0,SourceContract(0,0,0,0),0,1,
            SourceDisposition.WAIVED,'auto source semantically waived',
        )
        with tempfile.TemporaryDirectory() as td:
            run,_=self.prepare(td,contract=waived,source_tools=False)
            run.commit_delivery(b'payload')
            self.assertEqual(run.phase.phase,RunPhase.DELIVERED)

        required=EffectiveContract(
            0,0,0,0,SourceContract(0,0,0,0),0,1,
            SourceDisposition.REQUIRED,
        )
        with tempfile.TemporaryDirectory() as td:
            run,_=self.prepare(td,contract=required,source_tools=False)
            with self.assertRaises(DeliveryGateError) as cm:run.commit_delivery(b'payload')
            self.assertIn('REQUIRED_SOURCE_TOOLS_UNAVAILABLE',cm.exception.unmet)
            self.assertEqual(run.phase.phase,RunPhase.INCOMPLETE)

    def test_hard_time_flag_requires_positive_target(self):
        with self.assertRaisesRegex(ValueError,'B=1 requires'):
            EffectiveContract(0,0,0,1,SourceContract(0,0,0,0),0,1,SourceDisposition.WAIVED,'closed')
        with self.assertRaisesRegex(ValueError,'S.b=1 requires'):
            EffectiveContract(0,0,0,0,SourceContract(0,0,0,1),0,1,SourceDisposition.REQUIRED)

    def test_session_only_clock_is_canonical_only_without_resume(self):
        with tempfile.TemporaryDirectory() as td:
            run,_=self.prepare(td,candidate_bytes=b'one session')
            capability=run.workspace.read_json('capability-negotiation.json')
            capability['monotonic_clock']='SESSION_ONLY'
            run.workspace.write_json('capability-negotiation.json',capability,kind='capability-negotiation')
            run.commit_delivery(b'one session')
            self.assertEqual(run.phase.phase,RunPhase.DELIVERED)
        with tempfile.TemporaryDirectory() as td:
            run,_=self.prepare(td,candidate_bytes=b'resumed')
            capability=run.workspace.read_json('capability-negotiation.json')
            capability['monotonic_clock']='SESSION_ONLY'
            run.workspace.write_json('capability-negotiation.json',capability,kind='capability-negotiation')
            resumed=LiveDIGRRun.resume(run.workspace.root,run.run_id,FakeClock(start=10_000_000_000,session='next',boot='boot-test'))
            with self.assertRaises(DeliveryGateError) as cm:
                resumed.commit_delivery(b'resumed')
            self.assertIn('SESSION_ONLY_CLOCK_RESUMED',cm.exception.unmet)
            self.assertEqual(resumed.phase.phase,RunPhase.INCOMPLETE)

    def test_exact_payload_and_candidate_are_bound_before_canonical_proof(self):
        with tempfile.TemporaryDirectory() as td:
            payload='最终作品：潮汐把月光折成一封信。'.encode()
            run,_=self.prepare(td,candidate_bytes=payload)
            with self.assertRaises(DeliveryGateError):run.render_proof()
            envelope=run.commit_delivery(payload,media_type='text/plain; charset=utf-8')
            self.assertEqual(run.phase.phase,RunPhase.DELIVERED)
            self.assertEqual(envelope.schema_version,2)
            self.assertRegex(envelope.terminal_state_sha256,r'^[0-9a-f]{64}$')
            self.assertTrue(run.workspace.terminal_sealed)
            self.assertEqual(run.workspace.read_json('state/terminal-seal.json')['binding_sha256'],envelope.digest)
            self.assertEqual(envelope.payload_sha256,hashlib.sha256(payload).hexdigest())
            self.assertEqual(run.workspace.path(envelope.payload_path).read_bytes(),payload)
            self.assertEqual(envelope.candidate_revision,run.candidates.current.revision)
            self.assertEqual(envelope.candidate_digest,run.candidates.current.digest)
            self.assertEqual(
                envelope.preflight_receipt_sha256,
                run.workspace.artifact_record('preflight-receipt.json').sha256,
            )
            self.assertEqual(
                envelope.capability_negotiation_sha256,
                run.workspace.artifact_record('capability-negotiation.json').sha256,
            )
            proof=run.workspace.read_json('final/stable-proof.json')
            self.assertEqual(proof['delivery'],envelope.final_binding)
            self.assertTrue(run.render_proof().startswith('DIGR（'))
            self.assertEqual(run.commit_delivery(payload,media_type='text/plain; charset=utf-8'),envelope)
            with self.assertRaises(ValueError):run.commit_delivery(b'different',media_type='text/plain; charset=utf-8')

    def test_old_candidate_payload_cannot_be_delivered_as_current_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            contract=EffectiveContract(0,0,0,0,SourceContract(0,0,0,0),0,1,SourceDisposition.WAIVED,'closed task')
            message=stable_invocation_for_contract(contract);clock=FakeClock()
            run=LiveDIGRRun.start(authority(),message,Path(td),clock,run_id='digr-current-candidate')
            run.bind_protocol_load(protocol_bundle().receipt);run.bind_preflight_parameters(stable_preflight_parameters(message))
            persist_enforced_host_receipts(run);run.freeze_u0('x');run.freeze_contract(contract)
            run.transition(WorkState.MAIN,clock());run.save_strategy(StrategyState(0,'task model','route'))
            old=run.save_candidate_bytes(b'OLD',summary='old')
            run.save_candidate_bytes(b'NEW',summary='new',artifact_refs=old.artifact_refs)
            run.completion.assess('done');run.finish_time(clock())
            with self.assertRaises(DeliveryGateError) as cm:run.commit_delivery(b'OLD')
            self.assertIn('FINAL_PAYLOAD_NOT_BOUND_TO_CANDIDATE',cm.exception.unmet)
            self.assertEqual(run.phase.phase,RunPhase.INCOMPLETE)

    def test_payload_tamper_invalidates_delivery_and_proof(self):
        with tempfile.TemporaryDirectory() as td:
            run,_=self.prepare(td,candidate_bytes=b'exact payload');run.commit_delivery(b'exact payload')
            run.workspace.path('final/delivery.bin').write_bytes(b'tampered')
            self.assertFalse(run.delivery_ready())
            with self.assertRaises(ValueError):run.render_proof()

    def test_coordinated_summary_reindex_cannot_forge_delivery(self):
        with tempfile.TemporaryDirectory() as td:
            run,_=self.prepare(td,candidate_bytes=b'exact payload');envelope=run.commit_delivery(b'exact payload')
            summary=run.workspace.read_json(envelope.run_summary_path)
            summary['delivery_ready']=False
            with self.assertRaisesRegex(RuntimeError,'terminal workspace is sealed'):
                run.workspace.write_json(envelope.run_summary_path,summary,kind='run-summary')
            self.assertTrue(run.delivery_ready())

    def test_recovery_rejects_deleted_or_tampered_host_receipts(self):
        with tempfile.TemporaryDirectory() as td:
            run,_=self.prepare(td);run.commit_delivery(b'payload')
            run.workspace.path('preflight-receipt.json').unlink()
            with self.assertRaises(ValueError):
                verify_run_workspace(run.workspace.root,run.run_id)
        with tempfile.TemporaryDirectory() as td:
            run,_=self.prepare(td);run.commit_delivery(b'payload')
            preflight=run.workspace.read_json('preflight-receipt.json');preflight['warnings']=['tampered after delivery']
            with self.assertRaisesRegex(RuntimeError,'terminal workspace is sealed'):
                run.workspace.write_json('preflight-receipt.json',preflight,kind='preflight-receipt')

    def test_coordinated_capability_downgrade_cannot_forge_delivery(self):
        with tempfile.TemporaryDirectory() as td:
            run,_=self.prepare(td);envelope=run.commit_delivery(b'payload')
            capability=run.workspace.read_json('capability-negotiation.json')
            capability['mode']='ADVISORY';capability['reasons']=['downgraded after delivery']
            with self.assertRaisesRegex(RuntimeError,'terminal workspace is sealed'):
                run.workspace.write_json('capability-negotiation.json',capability,kind='capability-negotiation')
            self.assertTrue(verify_run_workspace(run.workspace.root,run.run_id)['integrity_ok'])

    def test_summary_only_candidate_cannot_bind_final_payload(self):
        with tempfile.TemporaryDirectory() as td:
            run,_=self.prepare(td,candidate_bytes=None)
            # Legacy summary-only snapshots remain readable but are not
            # sufficient evidence for exact delivery.
            with self.assertRaises(DeliveryGateError) as cm:run.commit_delivery(b'payload')
            self.assertIn('FINAL_PAYLOAD_NOT_BOUND_TO_CANDIDATE',cm.exception.unmet)

    def test_abort_reaches_terminal_state_when_clock_read_fails(self):
        class DiesAfterGenesis(FakeClock):
            def __call__(self):
                if self.n>=300_000_000:raise RuntimeError('clock unavailable')
                return super().__call__()
        with tempfile.TemporaryDirectory() as td:
            c=DiesAfterGenesis();run=LiveDIGRRun.start(authority(),'DIGR：x',Path(td),c,run_id='digr-stable-0001')
            receipt=run.abort_protocol_load('bundle unavailable')
            self.assertEqual(run.phase.phase,RunPhase.ABORTED)
            self.assertIn('clock unavailable',receipt['clock_evidence_error'])


if __name__=='__main__':unittest.main()
