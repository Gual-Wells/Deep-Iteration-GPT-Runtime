from runtime.clock_probe import ClockSnapshot
from runtime.protocol_authority import ProtocolIdentity,ProtocolAuthority
from runtime.routing import RouteReceipt,AUTHORITATIVE_REPOSITORY
from runtime.invocation_surface import classify_surface
from runtime.task_startup import start_task

SHA='a'*40

def authority():
    r=RouteReceipt(AUTHORITATIVE_REPOSITORY,'stable',SHA,'manifest.json','b'*64,'VERSION','c'*64)
    p=ProtocolIdentity('digr-v5.0','5.0.0-alpha.3',AUTHORITATIVE_REPOSITORY,SHA)
    return ProtocolAuthority(r,p)

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
