import importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_release',ROOT/'tools/build_release.py');br=importlib.util.module_from_spec(spec);spec.loader.exec_module(br)
P=ROOT/br.COMPACT_PERSONALIZATION;F=ROOT/br.FREE_GO_PERSONALIZATION;FULL=ROOT/br.FULL_PERSONALIZATION;S=ROOT/br.STANDALONE_PERSONALIZATION

class TestPersonalization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):br.write_personalizations(ROOT);cls.text=P.read_text(encoding='utf-8');cls.full=FULL.read_text(encoding='utf-8')
    def test_single_template_and_byte_equality(self):
        self.assertEqual(P.read_bytes(),F.read_bytes());self.assertEqual(P.read_bytes(),S.read_bytes());self.assertTrue((ROOT/br.PERSONALIZATION_TEMPLATE).is_file())
    def test_terminal_sentinel_and_compact_size(self):
        self.assertLessEqual(len(self.text),2500)
        for t in (self.text,self.full):self.assertTrue(t.endswith(br.CONFIG_SENTINEL));self.assertEqual(t.count(br.CONFIG_SENTINEL.strip()),1)
    def test_broad_capture_has_no_local_surface_semantics(self):
        for x in ('只去掉开头空白','精确大写 ASCII `DIGR`','精确 `深度迭代`','必须先路由','真实仓库获取','不判断 task/help/参数/标点','pinned startup protocol','NATIVE'):
            self.assertIn(x,self.text)
        for x in ('digr.preflight','digr.commit_delivery','DIGR~','DELIVERED','canonical proof','N=2','R=1','V(o)'):
            self.assertNotIn(x,self.text)
    def test_pinned_manifest_transport_order(self):
        for x in ('`stable` branch 的当前 HEAD','/branches/stable','/git/ref/heads/stable','SHA 必须一致','manifest.json','VERSION','startup_slice','entrypoint','core[]','没有尝试本身不是路由失败'):
            self.assertIn(x,self.text)
        self.assertLess(self.text.index('manifest.json'),self.text.index('startup_slice'))
    def test_full_explains_same_boundary(self):
        for x in ('宽候选捕获','当前 mutable ref 获取','同 SHA 启动','失败边界','不要在本地判断','使用 REST'):
            self.assertIn(x,self.full)

if __name__=='__main__':unittest.main()
