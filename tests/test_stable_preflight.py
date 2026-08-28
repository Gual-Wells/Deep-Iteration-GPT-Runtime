import tempfile
import unittest
from pathlib import Path

from runtime.capabilities import (
    CapabilityMode, HostCapabilities, MonotonicClockCapability,
    negotiate_capabilities,
)
from runtime.effective_contract import EffectiveContract,SourceContract,SourceDisposition
from runtime.host_adapter import (
    HostAdapter, PreflightBlockedError, PreflightStatus, preflight_invocation,
)
from runtime.parameter_resolution import ParameterResolution,ResolutionStatus,resolve_stable_parameter_surface
from runtime.repository_transport import RepositoryTransportSession
from runtime.repository_transport import FRESHNESS_IMMUTABLE, RouteAcquisitionError, TransportResponse
from runtime.run_lifecycle import RunPhase
from tests.helpers import FakeClock
from tests.test_repository_transport import FakeFetcher


def enforced_capabilities():
    return HostCapabilities(
        final_gate=True,
        persistent_workspace=True,
        monotonic_clock=MonotonicClockCapability.CONTINUOUS,
        repository_transport=True,
        source_tools=True,
        isolation_max=3,
    )


class TestStableProfiles(unittest.TestCase):
    def test_standard_profile_defaults(self):
        r=resolve_stable_parameter_surface(None)
        self.assertEqual(r.status,ResolutionStatus.RESOLVED)
        self.assertEqual((r.N,r.T_seconds,r.R,r.B,r.D_s,r.L_e),(2,0,1,0,0,1))
        self.assertEqual((r.S.n,r.S.t_seconds,r.S.r,r.S.b),(0,0,0,0))

    def test_compact_hard_minimum_and_soft_target(self):
        hard=resolve_stable_parameter_surface('(10min)')
        soft=resolve_stable_parameter_surface('(target=10min)')
        explicit=resolve_stable_parameter_surface('(min=10min)')
        self.assertEqual((hard.T_seconds,hard.B),(600,1))
        self.assertEqual((explicit.T_seconds,explicit.B),(600,1))
        self.assertEqual((soft.T_seconds,soft.B),(600,0))

    def test_legacy_alpha4_unique_parse_is_only_compatibility_path(self):
        r=resolve_stable_parameter_surface('(1,10min,2,1,S(3,5min,4),D(0),L(1))')
        self.assertEqual(r.status,ResolutionStatus.RESOLVED)
        self.assertEqual((r.N,r.T_seconds,r.R,r.B,r.D_s),(1,600,2,1,0))
        self.assertTrue(any('legacy T/B accepted' in x for x in r.diagnostics))

    def test_hard_zero_is_rejected(self):
        for surface in ('(min=0min)','(N=2,T=0min,R=1,B=1)','(B=1)','(S(b=1))'):
            self.assertEqual(resolve_stable_parameter_surface(surface).status,ResolutionStatus.INVALID)

    def test_legacy_partial_surfaces_receive_concrete_stable_defaults(self):
        cases={
            '(N=5)':(5,0,1,0,0,1),
            '(D(1),L(2))':(2,0,1,0,1,2),
            '(1,10s,1,1)':(1,10,1,1,0,1),
        }
        for surface,expected in cases.items():
            with self.subTest(surface=surface):
                result=resolve_stable_parameter_surface(surface)
                self.assertEqual(result.status,ResolutionStatus.RESOLVED)
                result.require_stable_ready()
                self.assertEqual((result.N,result.T_seconds,result.R,result.B,result.D_s,result.L_e),expected)
                self.assertEqual((result.S.n,result.S.t_seconds,result.S.r,result.S.b),(0,0,0,0))

    def test_explicit_source_hard_time_is_concrete(self):
        result=resolve_stable_parameter_surface('(S(t=10s,b=1))')
        self.assertEqual(result.status,ResolutionStatus.RESOLVED)
        self.assertEqual((result.S.n,result.S.t_seconds,result.S.r,result.S.b),(0,10,0,1))
        result.require_stable_ready()

    def test_parameter_receipt_rejects_malformed_numeric_state(self):
        good=resolve_stable_parameter_surface(None).to_dict()
        for path,value in ((('T_seconds',),-1),(('T_seconds',),float('nan')),(('S','n'),-1),(('S','b'),2)):
            with self.subTest(path=path,value=value):
                bad={**good,'S':dict(good['S'])}
                target=bad
                for key in path[:-1]:target=target[key]
                target[path[-1]]=value
                with self.assertRaises((TypeError,ValueError)):
                    ParameterResolution.from_dict(bad)

    def test_source_policy_is_deterministic(self):
        auto=resolve_stable_parameter_surface('(source=auto)')
        required=resolve_stable_parameter_surface('(source=required)')
        off=resolve_stable_parameter_surface('(source=off)')
        self.assertEqual((auto.source_policy,required.source_policy,off.source_policy),('auto','required','off'))
        self.assertEqual(ParameterResolution.from_dict(required.to_dict()),required)
        self.assertEqual((off.S.n,off.S.t_seconds,off.S.r,off.S.b),(0,0,0,0))
        self.assertNotEqual(resolve_stable_parameter_surface('(source=off,S(1))').status,ResolutionStatus.RESOLVED)
        self.assertEqual(resolve_stable_parameter_surface('(source=unknown)').status,ResolutionStatus.INVALID)


class TestStablePreflight(unittest.TestCase):
    def test_candidates_pin_before_every_surface_classification(self):
        cases={
            'DIGR讨论':(PreflightStatus.NATIVE,False),
            'DIGRAPH':(PreflightStatus.NATIVE,False),
            'DIGR/help':(PreflightStatus.HELP,True),
            'DIGR：':(PreflightStatus.INVALID,False),
            'DIGR(R=1)':(PreflightStatus.INVALID,False),
            'DIGR(1)：x':(PreflightStatus.NEEDS_CORRECTION,False),
        }
        for message,(status,additional_fetch_required) in cases.items():
            f=FakeFetcher(source_kind='github_connector')
            adapter=HostAdapter(RepositoryTransportSession(f),enforced_capabilities())
            receipt=adapter.preflight(message)
            self.assertEqual(receipt.status,status,message)
            self.assertTrue(receipt.startup_acquisition_performed,message)
            self.assertEqual(receipt.additional_artifact_fetch_required,additional_fetch_required,message)
            self.assertEqual(len(f.requests),4,message)
            self.assertEqual(receipt.repository_binding.route.pinned_commit,'a'*40)
            self.assertEqual([x.path for x in receipt.repository_binding.startup_files],['entry/STARTUP.md'])
            if status is PreflightStatus.NATIVE:
                self.assertEqual(receipt.native_message,message)
                self.assertEqual(receipt.to_dict()['native_message'],message)

    def test_non_candidate_is_the_only_zero_network_path(self):
        f=FakeFetcher();adapter=HostAdapter(RepositoryTransportSession(f),enforced_capabilities())
        self.assertIsNone(adapter.preflight('ordinary chat'))
        self.assertEqual(f.requests,[])

    def test_public_preflight_helper_cannot_bypass_repository_startup(self):
        with self.assertRaisesRegex(ValueError,'verified repository startup'):
            preflight_invocation('DIGR是什么？',capabilities=enforced_capabilities())

    def test_ready_preflight_has_pinned_route_evidence(self):
        f=FakeFetcher(source_kind='github_connector');adapter=HostAdapter(RepositoryTransportSession(f),enforced_capabilities())
        receipt=adapter.preflight('DIGR(10min)：x')
        self.assertEqual(receipt.status,PreflightStatus.READY)
        self.assertTrue(receipt.startup_acquisition_performed)
        self.assertTrue(receipt.additional_artifact_fetch_required)
        self.assertEqual(receipt.source_policy,'auto')
        self.assertEqual(receipt.to_dict()['source_policy'],'auto')
        self.assertEqual(len(f.requests),4)
        self.assertEqual(receipt.to_dict()['repository_binding']['route']['manifest_path'],'manifest.json')

    def test_adapter_networks_and_creates_run_only_after_ready(self):
        f=FakeFetcher(source_kind='github_connector')
        adapter=HostAdapter(RepositoryTransportSession(f),enforced_capabilities())
        with tempfile.TemporaryDirectory() as td:
            result=adapter.start('DIGR(target=10min)：x',workspace_parent=Path(td),snapshot_fn=FakeClock(),run_id='digr-stable01')
            self.assertEqual(len(f.requests),6)
            self.assertTrue(f.requests[4].url.endswith('/runtime-descriptor.json'))
            self.assertTrue(f.requests[5].url.endswith('/dist/EXECUTION_PROTOCOL.json'))
            self.assertEqual(result.run.phase.phase,RunPhase.PARAMETER_RESOLVED)
            self.assertEqual((result.run.parameters.T_seconds,result.run.parameters.B),(600,0))
            self.assertEqual(result.route_binding.route.pinned_commit,'a'*40)
            self.assertEqual(result.run.startup.authority.route.manifest_path,'manifest.json')
            self.assertEqual(result.run.startup.authority.route.version_path,'VERSION')
            self.assertEqual(
                result.protocol.receipt.manifest_sha256,
                result.run.startup.authority.route.manifest_sha256,
            )
            self.assertTrue(result.run.workspace.path('preflight-receipt.json').is_file())
            self.assertTrue(result.run.workspace.path('capability-negotiation.json').is_file())
            self.assertEqual(result.run.workspace.read_json('capability-negotiation.json')['mode'],'ENFORCED')
            self.assertFalse(any(p.name.startswith('.digr-genesis-') for p in Path(td).iterdir()))

    def test_bundle_failure_happens_before_genesis(self):
        class BrokenBundle(FakeFetcher):
            def __call__(self,req):
                if 'dist/EXECUTION_PROTOCOL.json' in req.url:
                    self.requests.append(req)
                    return TransportResponse(req.url,503,b'',self.source_kind,FRESHNESS_IMMUTABLE)
                return super().__call__(req)
        adapter=HostAdapter(RepositoryTransportSession(BrokenBundle(source_kind='github_connector')),enforced_capabilities())
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RouteAcquisitionError):
                adapter.start('DIGR：x',workspace_parent=Path(td),snapshot_fn=FakeClock(),run_id='digr-stable02')
            self.assertEqual(list(Path(td).iterdir()),[])

    def test_blocked_preflight_cannot_create_run(self):
        f=FakeFetcher(source_kind='github_connector');adapter=HostAdapter(RepositoryTransportSession(f),HostCapabilities())
        with self.assertRaises(PreflightBlockedError) as cm: adapter.start('DIGR：x')
        self.assertEqual(cm.exception.receipt.status,PreflightStatus.UNSUPPORTED)
        self.assertEqual(len(f.requests),4)

    def test_help_is_three_verified_reads_and_never_creates_run(self):
        f=FakeFetcher(source_kind='github_connector')
        adapter=HostAdapter(RepositoryTransportSession(f),HostCapabilities())
        artifact=adapter.help('DIGR/help')
        self.assertEqual(len(f.requests),5)
        self.assertEqual(
            [r.purpose for r in f.requests],
            ['stable_branch_primary_r1','pinned:manifest.json','pinned:VERSION',
             'pinned:entry/STARTUP.md','pinned:entry/HELP.md'],
        )
        self.assertIn('DIGR Help',artifact.text)

    def test_staged_failure_never_exposes_canonical_run(self):
        class FailAtClock(FakeClock):
            def __init__(self,fail_at): super().__init__();self.calls=0;self.fail_at=fail_at
            def __call__(self):
                current=self.calls;self.calls+=1
                if current==self.fail_at: raise RuntimeError('clock failure')
                return super().__call__()
        for fail_at,run_id in ((3,'digr-stagefail'),(4,'digr-resumefail')):
            f=FakeFetcher(source_kind='github_connector')
            adapter=HostAdapter(RepositoryTransportSession(f),enforced_capabilities())
            with tempfile.TemporaryDirectory() as td:
                with self.assertRaises(Exception):
                    adapter.start('DIGR：x',workspace_parent=Path(td),snapshot_fn=FailAtClock(fail_at),run_id=run_id)
                self.assertFalse((Path(td)/run_id).exists())
                self.assertFalse(any(p.name.startswith('.digr-genesis-') for p in Path(td).iterdir()))

    def test_source_off_contract_and_required_contract_are_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            adapter=HostAdapter(RepositoryTransportSession(FakeFetcher(source_kind='github_connector')),enforced_capabilities())
            off=adapter.start('DIGR(source=off)：x',workspace_parent=Path(td),snapshot_fn=FakeClock(),run_id='digr-sourceoff').run
            off.freeze_u0()
            good=EffectiveContract(2,0,1,0,SourceContract(0,0,0,0),0,1,SourceDisposition.WAIVED,'source disabled')
            off.freeze_contract(good)
        with tempfile.TemporaryDirectory() as td:
            adapter=HostAdapter(RepositoryTransportSession(FakeFetcher(source_kind='github_connector')),enforced_capabilities())
            off=adapter.start('DIGR(source=off)：x',workspace_parent=Path(td),snapshot_fn=FakeClock(),run_id='digr-sourceoff-bad').run
            off.freeze_u0()
            bad=EffectiveContract(2,0,1,0,SourceContract(0,0,0,0),0,1,SourceDisposition.REQUIRED,None)
            with self.assertRaisesRegex(ValueError,'source=off'):
                off.freeze_contract(bad)
        with tempfile.TemporaryDirectory() as td:
            adapter=HostAdapter(RepositoryTransportSession(FakeFetcher(source_kind='github_connector')),enforced_capabilities())
            required=adapter.start('DIGR(source=required)：x',workspace_parent=Path(td),snapshot_fn=FakeClock(),run_id='digr-sourcereq').run
            required.freeze_u0()
            bad=EffectiveContract(2,0,1,0,SourceContract(0,0,0,0),0,1,SourceDisposition.WAIVED,'incorrect waiver')
            with self.assertRaisesRegex(ValueError,'source=required'):
                required.freeze_contract(bad)


class TestStableCapabilities(unittest.TestCase):
    def test_truthful_modes(self):
        params=resolve_stable_parameter_surface(None)
        self.assertEqual(negotiate_capabilities(enforced_capabilities(),params).mode,CapabilityMode.ENFORCED)
        advisory=HostCapabilities(True,True,MonotonicClockCapability.SESSION_ONLY,True,True,3)
        self.assertEqual(negotiate_capabilities(advisory,params).mode,CapabilityMode.ADVISORY)
        self.assertEqual(negotiate_capabilities(HostCapabilities(),params).mode,CapabilityMode.PROMPT_ONLY)

    def test_no_final_interposer_is_not_enforced(self):
        caps=HostCapabilities(False,True,MonotonicClockCapability.CONTINUOUS,True,True,3)
        result=negotiate_capabilities(caps,resolve_stable_parameter_surface(None))
        self.assertEqual(result.mode,CapabilityMode.ADVISORY)
        self.assertTrue(any('final-output interposer' in x for x in result.reasons))

    def test_d_zero_makes_l_cap_nonblocking(self):
        caps=HostCapabilities(True,True,MonotonicClockCapability.CONTINUOUS,True,True,1)
        params=resolve_stable_parameter_surface('(profile=standard,D(0),L(3))')
        self.assertEqual(negotiate_capabilities(caps,params).mode,CapabilityMode.ENFORCED)

    def test_positive_d_above_l_cap_is_unsupported(self):
        caps=HostCapabilities(True,True,MonotonicClockCapability.CONTINUOUS,True,True,1)
        params=resolve_stable_parameter_surface('(profile=standard,D(1),L(3))')
        result=negotiate_capabilities(caps,params)
        self.assertEqual(result.mode,CapabilityMode.PROMPT_ONLY)
        self.assertTrue(any('exceeds host isolation cap' in x for x in result.reasons))

    def test_source_required_without_tools_blocks_but_off_does_not(self):
        caps=HostCapabilities(True,True,MonotonicClockCapability.CONTINUOUS,True,False,3)
        required=negotiate_capabilities(caps,resolve_stable_parameter_surface('(source=required)'))
        off=negotiate_capabilities(caps,resolve_stable_parameter_surface('(source=off)'))
        auto=negotiate_capabilities(caps,resolve_stable_parameter_surface('(source=auto)'))
        self.assertEqual(required.mode,CapabilityMode.PROMPT_ONLY)
        self.assertEqual(off.mode,CapabilityMode.ENFORCED)
        self.assertEqual(auto.mode,CapabilityMode.ENFORCED)

    def test_explicit_source_minima_require_source_tools(self):
        caps=HostCapabilities(True,True,MonotonicClockCapability.CONTINUOUS,True,False,3)
        for surface in ('(S(n=1))','(S(t=5s,b=1))'):
            with self.subTest(surface=surface):
                result=negotiate_capabilities(caps,resolve_stable_parameter_surface(surface))
                self.assertEqual(result.mode,CapabilityMode.PROMPT_ONLY)
                self.assertTrue(any('source tools' in reason for reason in result.reasons))

    def test_hard_source_time_requires_continuous_clock(self):
        caps=HostCapabilities(True,True,MonotonicClockCapability.SESSION_ONLY,True,True,3)
        result=negotiate_capabilities(caps,resolve_stable_parameter_surface('(S(t=5s,b=1))'))
        self.assertEqual(result.mode,CapabilityMode.PROMPT_ONLY)
        self.assertTrue(any('hard source-time' in reason for reason in result.reasons))


if __name__=='__main__': unittest.main()
