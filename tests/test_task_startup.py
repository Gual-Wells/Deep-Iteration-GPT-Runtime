import unittest
from runtime.clock_probe import ClockSnapshot
from runtime.protocol_authority import ProtocolIdentity, ProtocolAuthority
from runtime.routing import RouteReceipt, AUTHORITATIVE_REPOSITORY
from runtime.task_startup import ClockReadiness, TaskStartupReceipt

SHA='a'*40

def authority():
    r=RouteReceipt(AUTHORITATIVE_REPOSITORY,'stable',SHA,'manifest.json','b'*64)
    p=ProtocolIdentity('digr-v4.1','4.1.0',AUTHORITATIVE_REPOSITORY,SHA)
    return ProtocolAuthority(r,p)

class TestTaskStartup(unittest.TestCase):
    def snap(self,n,session='s',boot=None): return ClockSnapshot('p',session,boot,n,n)

    def test_ready_before_u0(self):
        c=ClockReadiness(self.snap(1),self.snap(2))
        t=TaskStartupReceipt(authority(),c)
        self.assertTrue(t.clock.ready); self.assertFalse(t.u0_frozen)

    def test_u0_already_frozen_rejected(self):
        c=ClockReadiness(self.snap(1),self.snap(2))
        with self.assertRaises(ValueError): TaskStartupReceipt(authority(),c,True)

    def test_unverifiable_clock_rejected(self):
        with self.assertRaises(ValueError): ClockReadiness(self.snap(2,'a'),self.snap(3,'b'))
        with self.assertRaises(ValueError): ClockReadiness(self.snap(4),self.snap(3))

    def test_startup_is_version_semantic_not_routing_record(self):
        self.assertNotIn('clock',RouteReceipt.__dataclass_fields__)

if __name__=='__main__': unittest.main()
