from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from runtime import codex_preprint as p

ROOT=Path(__file__).resolve().parents[1]


def spec():
    return {'id':'constructed-fixture','title':'Constructed fixture, not a user scene',
        'public_scene':'A bookshop is closing. Two strangers are present.',
        'actors':[{'id':'jo','name':'Jo','outward':{'voice':'dry'},'inner':{'pressure':'pride'},'own_background':['Private Jo-only promise.']},
                  {'id':'len','name':'Len','outward':{'voice':'warm'},'inner':{'pressure':'fear'},'own_background':['Private Len-only battery.']}],
        'directors':[{'id':'world','interest':'time and small disruptions'}],
        'initial_state':{'backstage_ferry':'cancelled'}}


class PreprintTests(unittest.TestCase):
    def setUp(self):
        cache=ROOT/'.cache';cache.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='esp-test-',dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'episode';p.initialize(self.root,spec());self.op=0

    def event(self,event):
        self.op+=1
        if event['kind'] in {'speech','action','inner','inner_reply'}:
            channel='inner' if event['kind']=='inner' else 'outward'
            event={'packet_sha256':p.actor_packet(self.root,event['actor'],channel)['packet_sha256'],
                'executor':'constructed-independent-context',**event}
        event={'source_ref':'constructed-fixture-source',**event}
        return p.append_event(self.root,event,expected_revision=p.load(self.root)['revision'],operation_id='op-'+str(self.op))

    def test_packets_keep_world_and_other_minds_out(self):
        jo=p.actor_packet(self.root,'jo')['view'];as_text=json.dumps(jo)
        self.assertIn('Private Jo-only',as_text)
        self.assertNotIn('Private Len-only',as_text)
        self.assertNotIn('backstage_ferry',as_text)
        self.assertNotIn('world',jo)
        self.assertNotIn('revision',jo)
        director=json.dumps(p.director_packet(self.root,'world')['view'])
        self.assertNotIn('Private Jo-only',director)

    def test_invisible_changes_do_not_leak_or_stale_a_character_view(self):
        before=p.actor_packet(self.root,'len')
        self.event({'kind':'world','proposal':'An unseen cancellation','decision':'apply','reason':'Constructed world fact',
                    'changes':{'backstage_ferry':'delayed'},'percepts':[{'to':['jo'],'text':'A cancellation message arrives.'}]})
        self.assertEqual(p.actor_packet(self.root,'len'),before)
        self.assertIn('cancellation message',json.dumps(p.actor_packet(self.root,'jo')))
        self.assertNotIn('delayed',json.dumps(p.actor_packet(self.root,'jo')))

    def test_native_submission_is_stale_only_after_a_new_visible_input(self):
        packet=p.actor_packet(self.root,'jo')
        self.event({'kind':'speech','actor':'len','text':'Could I record here?','audience':['public']})
        with self.assertRaisesRegex(ValueError,'stale'):
            self.event({'kind':'speech','actor':'jo','text':'Yes.', 'packet_sha256':packet['packet_sha256']})
        self.assertEqual(len(p.load(self.root)['events']),1)

    def test_speech_does_not_create_furniture_fulfil_promises_or_rewrite_world(self):
        before=deepcopy(p.load(self.root)['world'])
        self.event({'kind':'speech','actor':'jo','text':'You can use the back table.'})
        self.event({'kind':'speech','actor':'len','text':'I will be packed up before seven.'})
        self.assertEqual(p.load(self.root)['world'],before)
        with self.assertRaisesRegex(ValueError,'does not certify'):
            self.event({'kind':'speech','actor':'jo','text':'A spare battery exists.','changes':{'battery':True}})

    def test_inner_and_outward_reply_are_pair_private_and_bidirectional(self):
        before=p.actor_packet(self.root,'len')
        self.event({'kind':'inner','actor':'jo','text':'Private fictional self-respect; not hidden model reasoning.',
                    'audience':['public']})
        self.assertIn('fictional self-respect',json.dumps(p.actor_packet(self.root,'jo','outward')))
        self.assertIn('fictional self-respect',json.dumps(p.actor_packet(self.root,'jo','inner')))
        self.assertNotIn('fictional self-respect',json.dumps(p.actor_packet(self.root,'len')))
        self.event({'kind':'inner_reply','actor':'jo','text':'I heard you, but I will offer them the table.',
                    'audience':['public']})
        outward=p.actor_packet(self.root,'jo','outward')['view']['observed']
        inner=p.actor_packet(self.root,'jo','inner')['view']['observed']
        self.assertEqual([e['from_channel'] for e in inner],['inner','outward'])
        self.assertEqual([e['authored_by_self'] for e in outward],[False,True])
        self.assertEqual([e['authored_by_self'] for e in inner],[True,False])
        self.assertEqual(p.actor_packet(self.root,'len'),before)
        self.assertNotIn('offer them',json.dumps(p.director_packet(self.root,'world')))
        self.assertTrue(all(e['audience']==['creator'] for e in p.load(self.root)['events']))

    def test_submissions_require_actual_source_executor_and_current_visible_packet(self):
        before=(self.root/'preprint.json').read_bytes()
        event={'kind':'speech','actor':'jo','text':'We can talk here.',
               'source_ref':'constructed source','executor':'constructed native context',
               'packet_sha256':p.actor_packet(self.root,'jo')['packet_sha256']}
        for field in ('source_ref','executor','packet_sha256'):
            payload=dict(event);payload.pop(field)
            with self.subTest(field=field),self.assertRaises(ValueError):
                p.append_event(self.root,payload,expected_revision=0,operation_id='missing-'+field)
            self.assertEqual((self.root/'preprint.json').read_bytes(),before)

    def test_user_participation_is_not_an_event_path(self):
        before=(self.root/'preprint.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'invalid event kind'):
            self.event({'kind':'human','actor':'jo','text':'A user tries to take the role.'})
        self.assertEqual((self.root/'preprint.json').read_bytes(),before)

    def test_unapplied_world_proposal_cannot_arrive_as_a_perception(self):
        before=(self.root/'preprint.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'unapplied'):
            self.event({'kind':'world','proposal':'A dramatic flood','decision':'retain','reason':'Not selected',
                        'percepts':[{'to':['public'],'text':'Water enters.'}]})
        self.assertEqual((self.root/'preprint.json').read_bytes(),before)

    def test_language_uses_actual_spans_without_inventing_learner_evidence(self):
        event=self.event({'kind':'speech','actor':'len','text':'I will start straight away.'})
        payload={'resources':[{'event_id':event['event_id'],'surface':'straight away','meaning':'without delay',
            'function':'commit to immediate action','register':'this fictional conversation','frequency_status':'not checked'}]}
        p.annotate(self.root,payload,expected_revision=p.load(self.root)['revision'],operation_id='annotation')
        self.assertEqual(p.load(self.root)['learner_evidence'],[])
        claimed=deepcopy(payload);claimed['resources'][0]['learner_mastery']=True
        with self.assertRaisesRegex(ValueError,'do not create learner mastery'):
            p.annotate(self.root,claimed,expected_revision=p.load(self.root)['revision'],operation_id='invented-mastery')
        payload['resources'][0]['surface']='a phrase never spoken'
        with self.assertRaisesRegex(ValueError,'absent'):
            p.annotate(self.root,payload,expected_revision=p.load(self.root)['revision'],operation_id='bad-annotation')

    def test_retry_revision_and_lock_do_not_lose_actual_results(self):
        event={'kind':'world','proposal':'Keep the weather','decision':'decline','reason':'No need','source_ref':'constructed'}
        a=p.append_event(self.root,event,expected_revision=0,operation_id='same')
        b=p.append_event(self.root,event,expected_revision=0,operation_id='same')
        self.assertEqual(a['event_id'],b['event_id']);self.assertTrue(b['retried'])
        before=(self.root/'preprint.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'reused with different content'):
            p.append_event(self.root,{**event,'reason':'Changed meaning'},expected_revision=1,operation_id='same')
        self.assertEqual((self.root/'preprint.json').read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'revision conflict'):
            p.append_event(self.root,event,expected_revision=0,operation_id='new')
        (self.root/'.writer.lock').write_text('{"pid":1,"token":"someone"}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'writer lock'):
            p.append_event(self.root,event,expected_revision=1,operation_id='locked')
        self.assertTrue((self.root/'.writer.lock').exists())

    def test_unrecorded_snapshot_changes_are_detected(self):
        state=json.loads((self.root/'preprint.json').read_text(encoding='utf-8'))
        state['world']['backstage_ferry']='silently changed'
        (self.root/'preprint.json').write_text(json.dumps(state),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'changed outside a recorded operation'):
            p.load(self.root)

    def test_world_authors_receive_public_observations_without_private_minds(self):
        self.event({'kind':'world','decision':'apply','proposal':'Separate perceptions','reason':'Fixture',
                    'percepts':[{'to':['public'],'text':'A shutter rattles.'},{'to':['jo'],'text':'A private notification.'}]})
        self.event({'kind':'inner','actor':'jo','text':'I want to leave alone.'})
        view=json.dumps(p.director_packet(self.root,'world'))
        self.assertIn('A shutter rattles.',view)
        self.assertNotIn('private notification',view)
        self.assertNotIn('leave alone',view)


if __name__=='__main__':unittest.main()
