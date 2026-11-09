from copy import deepcopy
import json,os,re,subprocess,sys,tempfile,unittest
from pathlib import Path
from xml.etree import ElementTree
from runtime import codex_timeline as t

ROOT=Path(__file__).resolve().parents[1]

class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.data=t.read(ROOT/'codex/examples/visual-return/pipeline.json')

    def mini(self):
        return {'schema_version':1,'mode':'illustration','title':'Unknown timestamps',
            'axis_domain':'main','tracks':[{'id':'M01','kind':'M','segments':[]}],
            'events':[{'id':key,'track':'M01','at':at,'kind':'note','label':key} for key,at in [('a',100),('b',None),('c',50)]],
            'links':[]}

    def test_complete_examples_and_portable_svg(self):
        for name in ('pipeline','unknown-time','multi-main'):
            data=t.read(ROOT/f'codex/examples/visual-return/{name}.json')
            xml=ElementTree.fromstring(t.render_svg(data))
            self.assertEqual(len(xml.findall(".//{*}g[@data-track]")),len(data['tracks']))
            self.assertIn('结构示意',t.render_svg(data))
        multi=t.read(ROOT/'codex/examples/visual-return/multi-main.json')
        self.assertIn('M01.N01',[x['id'] for x in multi['tracks']])
        self.assertIn('M02.N01',[x['id'] for x in multi['tracks']])
        self.assertTrue(all(fact.startswith('M01｜') for fact in t.highlighted_facts(multi)))

    def test_causal_order_across_unknown_bridge(self):
        data=self.mini();data['links']=[{'from':'a','to':'b','kind':'message'},{'from':'b','to':'c','kind':'handling'}]
        with self.assertRaisesRegex(ValueError,'transitive'):t.validate(data)
        data['links'][0]['kind']='reference';t.validate(data)
        data['links'][0]['kind']='correlation';t.validate(data)

    def test_same_external_domain_is_comparable_without_axis_location(self):
        data=self.mini();data['events']=data['events'][:2]
        data['events'][0].update(at=20,domain='external')
        data['events'][1].update(at=10,domain='external')
        data['links']=[{'from':'a','to':'b','kind':'message'}]
        with self.assertRaisesRegex(ValueError,'backwards'):t.validate(data)
        data['events'][1]['domain']='another-clock';t.validate(data)
        self.assertIsNone(t.position(data,data['events'][0],'at'))

    def test_causal_cycles_and_broken_scope_rejected(self):
        data=self.mini();data['events'][2]['at']=None
        data['links']=[{'from':'a','to':'b','kind':'message'},{'from':'b','to':'a','kind':'handling'}]
        with self.assertRaisesRegex(ValueError,'cycle'):t.validate(data)
        data=self.mini();data['tracks'][0]['id']='M02';data['events']=[]
        data['tracks'].append({'id':'M01.N01','kind':'N','segments':[]})
        with self.assertRaisesRegex(ValueError,'scope'):t.validate(data)

    def test_unknowns_have_a_readable_outlet_and_no_inferred_interval(self):
        data=t.read(ROOT/'codex/examples/visual-return/unknown-time.json')
        frag=t.fragment(data)
        self.assertIn('区间不完整',frag)
        self.assertIn('span:M01.N03-segment-0',frag)
        self.assertIn('已记录关系',frag)
        self.assertIn('已记录关系',t.render_svg(data))
        self.assertIn('区间不完整',t.render_svg(data))
        data=self.mini()
        for event in data['events']:event['at']=None
        svg=t.render_svg(data)
        self.assertIn('时间未定位',svg)
        self.assertNotIn('>0分<',svg)

    def test_optional_metadata_shape_and_nonfinite_time_rejected(self):
        for target in (self.data['events'][0],self.data['tracks'][0]['segments'][0]):
            target['artifact_versions']='A@1'
            with self.assertRaisesRegex(ValueError,'list of strings'):t.validate(self.data)
            target['artifact_versions']=[]
        self.data['tracks'][0]['unhandled']='not a list'
        with self.assertRaisesRegex(ValueError,'list of strings'):t.validate(self.data)
        self.data['tracks'][0]['unhandled']=[]
        self.data['events'][0]['at']=float('nan')
        with self.assertRaisesRegex(ValueError,'time'):t.validate(self.data)

    def test_recorded_data_requires_sources_and_a_zoned_origin(self):
        self.data['mode']='recorded';self.data['origin']='2026-11-10T00:00:00'
        with self.assertRaisesRegex(ValueError,'timezone'):t.validate(self.data)
        self.data['origin']='2026-11-10T00:00:00+08:00'
        with self.assertRaisesRegex(ValueError,'source_ref'):t.validate(self.data)

    def test_markup_and_json_data_are_not_executable_instructions(self):
        text='</script><script>alert("unsafe")</script>'
        self.data['events'][0]['label']=text
        frag=t.fragment(self.data)
        payload=re.search(r'<script type="application/json" data-model>(.*?)</script>',frag,re.S).group(1)
        self.assertEqual(json.loads(payload)['events'][0]['label'],text)
        self.assertNotIn(text,payload)
        self.data['events'][0]['at']=None
        ElementTree.fromstring(t.render_svg(self.data))

    def test_real_cli_utf8_and_failed_input_does_not_produce_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);inp=root/'data.json';out=root/'diagram.svg'
            inp.write_text(json.dumps(self.data,ensure_ascii=False),encoding='utf-8')
            cli=ROOT/'tools/codex_timeline.py'
            env={**os.environ,'PYTHONUTF8':'0','PYTHONIOENCODING':'ascii'}
            args=[sys.executable,'-B',str(cli),'--input',str(inp),'--out',str(out)]
            r=subprocess.run(args,capture_output=True,env=env)
            self.assertEqual(r.returncode,0,r.stderr.decode('utf-8'))
            self.assertEqual(json.loads(r.stdout)['mode'],'illustration')
            out.unlink();self.data['events'][0]['artifact_versions']='invalid'
            inp.write_text(json.dumps(self.data),encoding='utf-8')
            r=subprocess.run(args,capture_output=True,env=env)
            self.assertEqual(r.returncode,2)
            self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
