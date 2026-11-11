from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from runtime import codex_preprint as p
from tests.test_codex_preprint import spec


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'.cache')
        self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'book';self.n=0
        s=spec();s['initial_state']={'fixture':'immutable history','slots':1,'document':'unavailable','private_b':'b-only'}
        s['frozen_world_keys']=['fixture']
        s['world_rules']={'mutable_keys':['slots','document'], 'monotone_decreasing':['slots']}
        s['directors']=[{'id':'tests','reads':['fixture','slots'],'writes':['slots']},
                        {'id':'access','reads':['document','private_b'],'writes':['document']}]
        s['actors'][0]['materials']={'patch':{'title':'Own patch','text':'retains a wrapper','origin':'explicit fiction'},
            'contract':{'title':'Ownership excerpt','text':'Fiction: storage is reused.','origin':'fiction fixture','access':'world','access_key':'document'}}
        s['actors'][0]['working_profile']={'basis':'fiction','experience':['app patch'],'working_knowledge':['callbacks'],'unestablished':['storage lifetime']}
        s['perturbation_defs']=[{'id':'d-pride','origin':{'kind':'D','id':'jo'},'targets':['jo'],
            'scope':'own hesitation','trigger':'public challenge','release':'bounded admission','message':'You want to defend the patch.', 'max_reactions':1}]
        p.initialize(self.root,s)

    def event(self,e):
        self.n+=1;e={'source_ref':'explicit synthetic fixture',**e}
        if e['kind'] in {'speech','action','inner','inner_reply'}:
            e={'packet_sha256':p.actor_packet(self.root,e['actor'],'inner' if e['kind']=='inner' else 'outward')['packet_sha256'],'executor':'synthetic',**e}
        elif e['kind']=='world':
            e={'packet_sha256':p.director_packet(self.root,e['director'])['packet_sha256'],'executor':'synthetic',**e}
        elif e['kind']=='perturbation':
            e={'packet_sha256':p.actor_packet(self.root,'jo','inner')['packet_sha256'],'executor':'synthetic',**e}
        return p.append_event(self.root,e,expected_revision=p.load(self.root)['revision'],operation_id='op-'+str(self.n))

    def world(self,changes,director='tests',**extra):
        return self.event({'kind':'world','director':director,'decision':'apply','proposal':'fixture update','reason':'fixture','changes':changes,**extra})

    def test_owned_material_read_and_failure_are_not_delivered_to_other_actor(self):
        view=p.actor_packet(self.root,'jo')['view'];self.assertNotIn('text',view['owned_materials']['patch'])
        self.event({'kind':'action','actor':'jo','text':'Jo opens the two documents.','reads':['patch','contract']})
        own=p.actor_packet(self.root,'jo')['view'];other=json.dumps(p.actor_packet(self.root,'len'))
        self.assertEqual(own['owned_materials']['patch']['text'],'retains a wrapper')
        self.assertNotIn('text',own['owned_materials']['contract'])
        self.assertIn('UNAVAILABLE',json.dumps(own));self.assertNotIn('UNAVAILABLE',other)
        with self.assertRaisesRegex(ValueError,'undeclared material'):
            self.event({'kind':'action','actor':'len','text':'Len steals a document.','reads':['patch']})
        self.world({'document':'available'},director='access')
        self.event({'kind':'action','actor':'jo','text':'Jo reads the excerpt.','reads':['contract']})
        self.world({'document':'unavailable'},director='access')
        self.assertEqual(p.actor_packet(self.root,'jo')['view']['owned_materials']['contract']['text'],'Fiction: storage is reused.')

    def test_frozen_history_territories_and_budget_prevent_real_counterexample(self):
        for changes in ({'fixture':'new cause'},{'slots':99},{'document':'available'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.world(changes)
        self.world({'slots':0})
        with self.assertRaises(ValueError):self.world({'slots':1})
        view=p.director_packet(self.root,'tests')['view'];self.assertNotIn('private_b',view['world'])
        with self.assertRaisesRegex(ValueError,'stale'):
            self.world({},packet_sha256='old')

    def test_d_cannot_affect_another_mind_and_stops_after_finite_feedback(self):
        origin={'kind':'D','id':'jo'}
        self.event({'kind':'perturbation','perturbation_id':'d-pride','operation':'activate','origin':origin})
        self.assertIn('defend',json.dumps(p.actor_packet(self.root,'jo')))
        self.assertNotIn('defend',json.dumps(p.actor_packet(self.root,'len')))
        a=self.event({'kind':'speech','actor':'len','text':'What did you actually test?'})['event_id']
        self.event({'kind':'perturbation','perturbation_id':'d-pride','operation':'react','origin':origin,'basis_event_ids':[a],'message':'Admitting the gap feels exposing.'})
        b=self.event({'kind':'speech','actor':'jo','text':'I have not checked that.'})['event_id']
        with self.assertRaisesRegex(ValueError,'budget'):
            self.event({'kind':'perturbation','perturbation_id':'d-pride','operation':'react','origin':origin,'basis_event_ids':[b],'message':'again'})
        self.event({'kind':'perturbation','perturbation_id':'d-pride','operation':'resolve','origin':origin,'basis_event_ids':[b],'outcome':'Gap spoken; no new experience acquired.'})
        self.assertNotIn('current_conditions',p.actor_packet(self.root,'jo')['view'])
        with self.assertRaisesRegex(ValueError,'cannot keep'):
            self.event({'kind':'perturbation','perturbation_id':'d-pride','operation':'react','origin':origin,'basis_event_ids':[b],'message':'forever'})

    def test_profile_is_portrayal_not_permission_to_reason_or_fake_measurements(self):
        v=p.actor_packet(self.root,'jo')['view'];self.assertIn('not a knowledge-token',v['portrayal_scope'])
        self.assertIn('invented prior experience',v['portrayal_scope'])
        bad=deepcopy(p.load(self.root)['spec']);bad['perturbation_defs'][0]['targets']=['len']
        with self.assertRaisesRegex(ValueError,'own character'):p.initialize(self.root.parent/'bad',bad)
