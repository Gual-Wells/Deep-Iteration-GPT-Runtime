import hashlib,json
from pathlib import Path

from runtime.clock_probe import ClockSnapshot
from runtime.protocol_authority import ProtocolIdentity,ProtocolAuthority
from runtime.routing import RouteReceipt,AUTHORITATIVE_REPOSITORY
from runtime.invocation_surface import classify_surface
from runtime.parameter_resolution import complete_native_parameters,parameter_profile,resolve_stable_parameter_surface
from runtime.task_startup import start_task
from runtime.execution_protocol import receipt_from_individual_files

SHA='a'*40
ROOT=Path(__file__).resolve().parents[1]

def stable_invocation_for_contract(contract,task='x'):
    """Create an explicit Berta2 test surface with no semantic completion."""
    seconds=lambda value:format(float(value),'.15g')+'s'
    s=contract.S
    source_policy='required' if getattr(contract.source_disposition,'value',contract.source_disposition)=='REQUIRED' else 'off'
    return (
        f'DIGR(source={source_policy},N={contract.N},T={seconds(contract.T_seconds)},R={contract.R},B={contract.B},'
        f'S(n={s.n},t={seconds(s.t_seconds)},r={s.r},b={s.b}),'
        f'D({contract.D_s}),V({getattr(contract,"V_o",0)}),L({contract.L_e}))：{task}'
    )

def stable_preflight_parameters(message):
    """Resolve the exact Berta2 parameter receipt before a low-level test run."""
    surface=classify_surface(message)
    result=resolve_stable_parameter_surface(surface.parameter_surface)
    if result.missing_parameters:
        defaults={
            'N':2,'T_seconds':1 if result.B==1 else 0,'R':1,
            'S.n':0,'S.t_seconds':1 if result.S.b==1 else 0,'S.r':0,
            'D_s':0,'V_o':0,
        }
        completion={}
        source={}
        for name in result.missing_parameters:
            if name.startswith('S.'):source[name[2:]]=defaults[name]
            else:completion[name]=defaults[name]
        if source:completion['S']=source
        result=complete_native_parameters(result,completion)
    result.require_stable_ready()
    return result

def _repository_protocol_fixture():
    manifest_bytes=(ROOT/'manifest.json').read_bytes()
    version_bytes=(ROOT/'VERSION').read_bytes()
    manifest=json.loads(manifest_bytes.decode('utf-8'))
    paths=(manifest['entrypoint'],*manifest['core'])
    files=tuple((path,(ROOT/path).read_bytes()) for path in paths)
    return manifest,manifest_bytes,version_bytes,paths,files

def authority():
    manifest,manifest_bytes,version_bytes,_,_=_repository_protocol_fixture()
    r=RouteReceipt(
        AUTHORITATIVE_REPOSITORY,'stable',SHA,'manifest.json',hashlib.sha256(manifest_bytes).hexdigest(),
        'VERSION',hashlib.sha256(version_bytes).hexdigest(),
    )
    p=ProtocolIdentity(manifest['protocol'],version_bytes.decode('utf-8').strip(),AUTHORITATIVE_REPOSITORY,SHA)
    return ProtocolAuthority(r,p)

def protocol_load_receipt():
    _,manifest_bytes,_,paths,files=_repository_protocol_fixture()
    return receipt_from_individual_files(
        commit_sha=SHA,manifest_bytes=manifest_bytes,expected_paths=paths,files=files,
    ).receipt

def persist_enforced_host_receipts(run,*,source_tools=True):
    """Persist deterministic test evidence for the stable host delivery gate."""
    if run.parameters is None:
        raise RuntimeError('resolve parameters before persisting host receipts')
    invocation=run.startup.invocation.to_dict()
    route=run.startup.authority.route.to_dict()
    profile=parameter_profile(run.startup.invocation.parameter_surface)
    warnings=[
        item for item in run.parameters.diagnostics
        if not item.startswith('profile:')
        and not item.startswith('time-policy:')
        and not item.startswith('source-policy:')
    ]
    preflight={
        'schema_version':1,'status':'READY',
        'raw_message_sha256':invocation['raw_message_sha256'],'kind':invocation['kind'],
        'alias':invocation['alias'],'task_raw':invocation.get('task_raw'),
        'parameter_surface':invocation.get('parameter_surface'),'profile':profile,
        'corrections':[],'warnings':warnings,'startup_acquisition_performed':True,
        'additional_artifact_fetch_required':True,
        'source_policy':run.parameters.source_policy,'native_message':None,
        'repository_binding':{
            'schema_version':1,'route':route,
            'startup_files':[
                {'path':route['manifest_path'],'sha256':route['manifest_sha256'],'byte_length':1},
            ],
            'attempts':[
                {
                    'seq':1,'purpose':'test-pinned-startup','request_url':'https://example.test/pinned',
                    'source_kind':'github_connector','freshness':'immutable_sha','status':200,
                    'success':True,'response_sha256':route['manifest_sha256'],
                    'commit_sha':route['pinned_commit'],'failure':None,
                },
            ],
        },
    }
    capability={
        'mode':'ENFORCED','execution_mode':'HOST_ENFORCED','attestation_level':'CANONICAL',
        'final_gate':True,'persistent_workspace':True,
        'monotonic_clock':'CONTINUOUS','repository_transport':True,
        'source_tools':source_tools,'isolation_max':3,'viewpoint_max':8,'reasons':[],
    }
    preflight_sha=run.workspace.write_json(
        'preflight-receipt.json',preflight,kind='preflight-receipt',
    )
    capability_sha=run.workspace.write_json(
        'capability-negotiation.json',capability,kind='capability-negotiation',
    )
    return preflight_sha,capability_sha

class FakeClock:
    def __init__(self, start=0, step=100_000_000, provider='test', session='same', boot='boot-test'):
        self.n=start; self.step=step; self.provider=provider; self.session=session; self.boot=boot
    def __call__(self):
        n=self.n; self.n+=self.step
        return ClockSnapshot(self.provider,self.session,self.boot,n,n)
    def at(self,ns): return ClockSnapshot(self.provider,self.session,self.boot,ns,ns)

def startup(clock=None,message='DIGR：任务'):
    clock=clock or FakeClock()
    inv=classify_surface(message)
    return start_task(authority(),inv,clock),clock
