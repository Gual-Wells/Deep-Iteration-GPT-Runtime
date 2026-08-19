import unittest
from runtime.invocation_surface import classify_surface,InvocationKind

class TestInvocationSurface(unittest.TestCase):
    def test_canonical_and_partial_forms_execute(self):
        for text in ('DIGR：任务','  深度迭代（R=5）：任务','DIGR(N=3,S(n=2)):task','DIGR （R=2）： x','DIGR（1,10min,1):任务'):
            x=classify_surface(text); self.assertIsNotNone(x,text); self.assertEqual(x.kind,InvocationKind.EXECUTING,text); self.assertTrue(x.task_raw.strip())
    def test_help_is_exact_surface(self):
        for text in ('DIGR/help',' DIGR /help',' 深度迭代/help '): self.assertEqual(classify_surface(text).kind,InvocationKind.HELP)
        self.assertIsNone(classify_surface('digr/help'))
    def test_native_sovereignty_return(self):
        for text in ('DIGR是什么？','DIGR这个设计合理吗？','DIGR（R=3）这种格式怎么样？','深度迭代这个名字如何？','DIGR'):
            x=classify_surface(text); self.assertIsNotNone(x); self.assertEqual(x.kind,InvocationKind.NATIVE,text)
    def test_invalid_only_broken_invocation_shape(self):
        for text in ('DIGR：','DIGR(R=3：任务','深度迭代（R=2：任务'):
            x=classify_surface(text); self.assertIsNotNone(x); self.assertEqual(x.kind,InvocationKind.INVALID,text)
    def test_non_candidate_is_none(self):
        for t in ('讨论一下 DIGR','digr：任务','Digr: task','DiGr: task'):
            self.assertIsNone(classify_surface(t),t)
    def test_surface_does_not_parse_parameter_semantics(self):
        x=classify_surface('DIGR(1,1,1)：任务'); self.assertEqual(x.kind,InvocationKind.EXECUTING); self.assertEqual(x.parameter_surface,'(1,1,1)')
    def test_message_digest_changes(self): self.assertNotEqual(classify_surface('DIGR：a').raw_message_sha256,classify_surface('DIGR：b').raw_message_sha256)
    def test_task_body_is_not_punctuation_normalized(self):
        x=classify_surface('DIGR（1，10min，1）：正文（，：）'); self.assertEqual(x.task_raw,'正文（，：）')
if __name__=='__main__': unittest.main()
