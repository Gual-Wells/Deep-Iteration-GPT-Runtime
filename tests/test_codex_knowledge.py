from copy import deepcopy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from runtime import codex_knowledge as k


class KnowledgePoolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        k.initialize(self.root,runtime_pin='0.7.0@'+'a'*40,repository='example/private-learning')
        self.source=self.root/'paper.txt'
        self.source.write_text('Tasks arrive at the beginning of a slot.\nA queue stores ready computational work.\nHidden background.',encoding='utf-8')
        self.analysis={'session_id':'paper-a-s1',
            'paper':{'id':'paper-a','title':'Fixture A','file':'paper.txt',
                     'source_sha256':k.file_digest(self.source),'pages':1},
            'concepts':[
                {'id':'compute.work','label':'Work','definition':'Amount of computational work.',
                 'aliases':[],'prerequisites':[]},
                {'id':'queue.work','label':'Queue','definition':'Ready computational work waiting for service.',
                 'aliases':['backlog'],'prerequisites':['compute.work']},
                {'id':'hidden.background','label':'Unshown background','definition':'A background concept not offered.',
                 'aliases':[],'prerequisites':[]}],
            'occurrences':[
                {'key':'work','concept_id':'compute.work','page':1,'quote':'Tasks arrive at the beginning of a slot.',
                 'usage':'Work is made ready at slot start.','assumptions':['slot-start arrival']},
                {'key':'queue','concept_id':'queue.work','page':1,'quote':'A queue stores ready computational work.',
                 'usage':'This paper uses a discrete ready-work queue.','role':'local ready workload'},
                {'key':'hidden','concept_id':'hidden.background','page':1,'quote':'Hidden background.',
                 'usage':'Not in this questionnaire.'}],
            'questions':[
                {'item_id':'A1','group':'System','label':'Work and arrival','occurrence_keys':['work']},
                {'item_id':'A2','group':'Dynamics','label':'Discrete ready-work queue','occurrence_keys':['queue']}]}

    def tearDown(self):self.tmp.cleanup()

    def ingest(self):
        return k.ingest(self.root,self.analysis,expected_revision=0,operation_id='ingest-a')

    def response(self,selected=('A2',)):
        packet=k.resume(self.root)
        return {'session_id':packet['session_id'],'questionnaire_sha256':packet['questionnaire_sha256'],
                'selected_ids':list(selected),'response_text':'Fixture user: A2',
                'response_ref':'synthetic fixture, not a real user reply'}

    def test_select_teach_finish_and_fresh_read_preserve_distinctions(self):
        self.ingest();payload=self.response()
        k.select(self.root,payload,expected_revision=1,operation_id='select-a')
        pool=k.load(self.root)
        pooled=[pool['occurrences'][oid]['concept_id'] for oid in pool['pool_members']]
        self.assertEqual(pooled,['compute.work'])
        self.assertNotIn('hidden.background',pooled)
        packet=k.resume(self.root)
        self.assertEqual([x['learning']['status'] for x in packet['items']],['unassessed','unassessed'])
        explanation={k1:payload[k1] for k1 in ('session_id','questionnaire_sha256')}
        explanation.update(item_id='A2',source_ref='synthetic assistant message',delivered=True,
                           text='At 0.9 seconds the new six units arrive; only one unit can be served before 1 second.')
        k.record(self.root,explanation,kind='explanation',expected_revision=2,operation_id='explain-a')
        self.assertEqual(k.resume(self.root)['items'][1]['learning']['status'],'explained_not_assessed')
        close={k1:payload[k1] for k1 in ('session_id','questionnaire_sha256')}
        close['source_ref']='synthetic fixture close instruction'
        k.finish(self.root,close,expected_revision=3,operation_id='finish-a')
        reloaded=k.resume(Path(str(self.root)),'paper-a-s1')
        self.assertEqual(reloaded['status'],'closed')
        self.assertEqual(len(k.load(self.root)['pool_members']),2)
        self.assertEqual(reloaded['items'][1]['learning']['evidence'],[])

    def test_same_request_replays_before_stale_revision_and_rejects_key_reuse(self):
        first=self.ingest()
        self.source.unlink()  # A retry must return the committed receipt, not re-ingest bytes.
        second=k.ingest(self.root,self.analysis,expected_revision=0,operation_id='ingest-a')
        self.assertTrue(second['replayed']);self.assertEqual(first['revision'],second['revision'])
        changed=deepcopy(self.analysis);changed['paper']['title']='Different operation'
        with self.assertRaisesRegex(ValueError,'reused'):
            k.ingest(self.root,changed,expected_revision=1,operation_id='ingest-a')
        self.assertEqual(k.load(self.root)['revision'],1)

    def test_source_bytes_quote_and_page_fail_without_partial_mutation(self):
        for variant,pattern in [('bytes','SHA256'),('quote','quote not found'),('page','page')]:
            a=deepcopy(self.analysis)
            if variant=='bytes':a['paper']['source_sha256']='0'*64
            if variant=='quote':a['occurrences'][0]['quote']='not present in source'
            if variant=='page':a['occurrences'][0]['page']=2
            before=(self.root/'pool.json').read_bytes()
            with self.assertRaisesRegex(ValueError,pattern):
                k.ingest(self.root,a,expected_revision=0,operation_id='invalid-'+variant)
            self.assertEqual((self.root/'pool.json').read_bytes(),before)

    def test_wrong_question_revision_and_prepared_lesson_are_rejected(self):
        self.ingest();p=self.response();p['questionnaire_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'questionnaire'):
            k.select(self.root,p,expected_revision=1,operation_id='wrong-question')
        p=self.response()
        with self.assertRaisesRegex(ValueError,'revision conflict'):
            k.select(self.root,p,expected_revision=0,operation_id='stale-revision')
        k.select(self.root,p,expected_revision=1,operation_id='select-a')
        p.update(item_id='A2',delivered=False,text='Prepared, not sent',source_ref='fixture draft')
        with self.assertRaisesRegex(ValueError,'not a delivered'):
            k.record(self.root,p,kind='explanation',expected_revision=2,operation_id='draft-only')
        self.assertEqual(k.resume(self.root)['items'][1]['learning']['status'],'unassessed')

    def test_scoped_evidence_does_not_transfer_by_concept_name(self):
        self.ingest();p=self.response()
        k.select(self.root,p,expected_revision=1,operation_id='select-a')
        evidence={k1:p[k1] for k1 in ('session_id','questionnaire_sha256')}
        evidence.update(item_id='A2',kind='application_observation',source_ref='synthetic response',
                        statement='Idle service cannot be saved for work arriving later.',
                        ability='Explain the late-arrival counterexample',representation='timeline with units')
        k.record(self.root,evidence,kind='evidence',expected_revision=2,operation_id='evidence-a')
        other=deepcopy(self.analysis);other['session_id']='paper-b-s1';other['paper']['id']='paper-b'
        other['occurrences'][1]['usage']='Continuous stochastic server queue; not the prior discrete queue.'
        k.ingest(self.root,other,expected_revision=3,operation_id='ingest-b')
        packet=k.resume(self.root)
        self.assertEqual(packet['items'][1]['learning']['status'],'unassessed')
        self.assertTrue(packet['items'][0]['related_pool_uses'])
        self.assertEqual(k.resume(self.root,'paper-a-s1')['items'][1]['learning']['evidence'][0]['representation'],
                         'timeline with units')

    def test_concept_correction_preserves_old_offered_meaning(self):
        self.ingest();p=self.response(selected=())
        k.select(self.root,p,expected_revision=1,operation_id='skip-all')
        old=deepcopy(k.load(self.root)['concepts']['queue.work'])
        replacement={key:old[key] for key in ('id','label','definition','aliases','prerequisites')}
        replacement['definition']='Corrected current definition with an explicitly different scope.'
        correction={'concept_id':'queue.work','expected_content_sha256':old['content_sha256'],
                    'replacement':replacement,'reason':'Fixture correction','source_ref':'synthetic new source'}
        k.revise_concept(self.root,correction,expected_revision=2,operation_id='correct-queue')
        packet=k.resume(self.root)
        self.assertTrue(packet['items'][1]['current_definition_differs'])
        self.assertEqual(packet['items'][1]['offered_context'][0]['concept_snapshot']['definition'],old['definition'])
        member=next(m for oid,m in k.load(self.root)['pool_members'].items()
                    if k.load(self.root)['occurrences'][oid]['concept_id']=='queue.work')
        self.assertEqual(member['introductions'][0]['item_snapshot']['label'],'Discrete ready-work queue')

    def test_source_version_is_explicit_and_old_session_stays_readable(self):
        self.ingest();a=deepcopy(self.analysis)
        self.source.write_text(self.source.read_text(encoding='utf-8')+'\nRevised source.',encoding='utf-8')
        a['paper']['source_sha256']=k.file_digest(self.source);a['session_id']='paper-a-s2'
        with self.assertRaisesRegex(ValueError,'version changed'):
            k.ingest(self.root,a,expected_revision=1,operation_id='unannounced-source')
        a['new_source_version']=True
        k.ingest(self.root,a,expected_revision=1,operation_id='source-v2')
        self.assertEqual(k.resume(self.root,'paper-a-s1')['source_status'],'older_frozen_source')
        self.assertEqual(len(k.load(self.root)['papers']['paper-a']['sources']),2)

    def test_atomic_replace_failure_and_lock_conflict_preserve_authority(self):
        before=(self.root/'pool.json').read_bytes()
        with patch('runtime.codex_knowledge.os.replace',side_effect=OSError('injected before commit')):
            with self.assertRaises(OSError):self.ingest()
        self.assertEqual((self.root/'pool.json').read_bytes(),before)
        (self.root/'.pool.lock').write_text('{"pid":1,"token":"fixture"}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'locked'):self.ingest()
        self.assertEqual((self.root/'pool.json').read_bytes(),before)
        (self.root/'.pool.lock').unlink()

    def test_tampering_and_public_runtime_data_binding_are_rejected(self):
        raw=k.read_json(self.root/'pool.json');raw['revision']=30
        (self.root/'pool.json').write_text(json.dumps(raw),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'integrity'):k.load(self.root)
        with self.assertRaisesRegex(ValueError,'public runtime'):
            k.initialize(self.root/'other',runtime_pin='0.7.0@'+'a'*40,repository=k.RUNTIME_REPOSITORY)

    def test_markdown_multiselection_preserves_question_identity(self):
        self.ingest();text=k.questionnaire_markdown(self.root)
        text=text.replace('- [ ] A1','- [x] A1').replace('- [ ] A2','- [x] A2')
        selection=k.parse_selection_markdown(text)
        self.assertEqual(selection['selected_ids'],['A1','A2'])
        self.assertEqual(selection['questionnaire_sha256'],k.resume(self.root)['questionnaire_sha256'])

    def test_alias_and_usage_search_discovers_candidates_without_merging(self):
        self.ingest()
        result=k.search(self.root,'BACKLOG')
        self.assertEqual([x['concept_id'] for x in result['shown']],['queue.work'])
        self.assertEqual(k.search(self.root,'discrete ready-work')['total_matches'],1)
        self.assertEqual(len(k.load(self.root)['concepts']),3)
        self.assertEqual(k.load(self.root)['evidence'],{})

    def test_v1_import_retains_raw_claims_without_mastery_promotion(self):
        old={'schema_version':1,'concepts':[{'concept_id':'queue.work','names':{'zh':'队列'},
                'learner':{'state':'verified','explanation_requested':False,'evidence_refs':[]}}]}
        k.migrate_legacy(self.root,old,expected_revision=0,operation_id='legacy')
        p=k.load(self.root)
        self.assertEqual(p['legacy_import']['original'],old)
        self.assertEqual(p['evidence'],{})
        self.assertEqual(p['pool_members'],{})
        self.assertIn('unverified',p['legacy_import']['status_claims'])

    def test_reselection_and_close_retire_old_cursor_without_learning_claims(self):
        self.ingest();p=self.response()
        k.select(self.root,p,expected_revision=1,operation_id='select-a')
        cursor={key:p[key] for key in ('session_id','questionnaire_sha256')}
        cursor.update(summary='Continue A2 notation',next_action='Explain A2',source_ref='synthetic pause')
        k.checkpoint(self.root,cursor,expected_revision=2,operation_id='pause-a')
        self.assertEqual(k.resume(self.root)['continuation']['next_action'],'Explain A2')
        k.select(self.root,self.response(('A1',)),expected_revision=3,operation_id='reselect-a')
        packet=k.resume(self.root)
        self.assertIsNone(packet['continuation'])
        self.assertEqual(len(packet['continuation_history']),1)
        self.assertNotIn('Explain A2',k.current_card(self.root))
        cursor.update(summary='Now A1',next_action='Explain A1')
        k.checkpoint(self.root,cursor,expected_revision=4,operation_id='pause-b')
        close={key:p[key] for key in ('session_id','questionnaire_sha256')}
        close['source_ref']='synthetic close'
        k.finish(self.root,close,expected_revision=5,operation_id='finish-a')
        self.assertIsNone(k.resume(self.root)['continuation'])
        self.assertIn('session closed',k.current_card(self.root))
        self.assertIn('历史记录已保留',k.current_card(self.root))
        self.assertEqual(k.load(self.root)['evidence'],{})
        before=(self.root/'pool.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'closed session'):
            k.checkpoint(self.root,cursor,expected_revision=6,operation_id='closed-pause')
        self.assertEqual((self.root/'pool.json').read_bytes(),before)

    def test_empty_answer_and_historical_source_remain_visible_on_card(self):
        self.ingest()
        self.assertIn('尚未收到本次多选',k.current_card(self.root))
        k.select(self.root,self.response(()),expected_revision=1,operation_id='empty-answer')
        self.assertIn('本次明确未请求解释',k.current_card(self.root))
        self.assertNotIn('尚未收到本次多选',k.current_card(self.root))
        self.assertIn('可结束或明确改选',k.current_card(self.root))
        a=deepcopy(self.analysis);new_source=self.root/'new.txt'
        new_source.write_text(self.source.read_text(encoding='utf-8')+'\nNew version.',encoding='utf-8')
        a.update(session_id='paper-a-s2',new_source_version=True)
        a['paper'].update(file='new.txt',source_sha256=k.file_digest(new_source))
        k.ingest(self.root,a,expected_revision=2,operation_id='new-version')
        self.assertTrue(k.resume(self.root,'paper-a-s1')['source_bytes_match'])
        self.assertIn('历史冻结版本',k.current_card(self.root,'paper-a-s1'))

    def test_cli_use_correction_preserves_frozen_question_and_evidence(self):
        self.ingest();p=self.response(())
        k.select(self.root,p,expected_revision=1,operation_id='skip-a')
        frozen=deepcopy(k.load(self.root)['sessions']['paper-a-s1']['questionnaire'])
        oid=frozen['items'][1]['occurrence_ids'][0]
        evidence={key:p[key] for key in ('session_id','questionnaire_sha256')}
        evidence.update(item_id='A2',kind='self_report',source_ref='synthetic reply',
                        statement='I can describe this old timeline',ability='Describe old example',representation='timeline')
        k.record(self.root,evidence,kind='evidence',expected_revision=2,operation_id='old-evidence')
        correction={'occurrence_id':oid,'replacement':{'usage':'Corrected: ready work in this discrete model.',
                    'supporting_quotes':[{'page':1,'quote':'Tasks arrive at the beginning of a slot.'}]},
                    'reason':'Fixture source re-read','source_ref':'synthetic correction source'}
        inp=self.root/'use-correction.json';inp.write_text(json.dumps(correction),encoding='utf-8')
        cli=Path(__file__).resolve().parents[1]/'tools/codex_knowledge.py'
        r=subprocess.run([sys.executable,'-B',str(cli),'--pool',str(self.root),'revise-use','--input',str(inp),
            '--expected-revision','3','--operation-id','correct-use'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(r.returncode,0,r.stderr)
        replacement=json.loads(r.stdout)['result']['replacement_id']
        self.assertEqual(k.load(self.root)['sessions']['paper-a-s1']['questionnaire'],frozen)
        self.assertIn(replacement,k.load(self.root)['pool_members'])
        self.assertEqual(k.show_use(self.root,oid)['current_id'],replacement)
        self.assertEqual(k.show_use(self.root,replacement)['learning']['status'],'unassessed')
        self.assertEqual(len(k.show_use(self.root,oid)['learning']['evidence']),1)
        self.assertEqual(k.resume(self.root)['items'][1]['use_corrections'][0]['current_id'],replacement)
        before=(self.root/'pool.json').read_bytes()
        correction.update(occurrence_id=replacement,replacement={'quote':'Invented quote absent from source'})
        with self.assertRaisesRegex(ValueError,'quote not found'):
            k.revise_use(self.root,correction,expected_revision=4,operation_id='bad-correction')
        self.assertEqual((self.root/'pool.json').read_bytes(),before)

    def test_real_cli_correction_and_checkpoint_change_the_snapshot(self):
        self.ingest()
        old=k.load(self.root)['concepts']['queue.work']
        replacement={key:old[key] for key in ('id','label','definition','aliases','prerequisites')}
        replacement['definition']='A corrected shared definition, with history.'
        payload={'concept_id':'queue.work','expected_content_sha256':old['content_sha256'],
                 'replacement':replacement,'reason':'Fixture correction','source_ref':'fixture source'}
        inp=self.root/'correction.json';inp.write_text(json.dumps(payload),encoding='utf-8')
        cli=Path(__file__).resolve().parents[1]/'tools/codex_knowledge.py'
        result=subprocess.run([sys.executable,'-B',str(cli),'--pool',str(self.root),'revise-concept',
            '--input',str(inp),'--expected-revision','1','--operation-id','cli-correction'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['action'],'revise-concept')
        self.assertEqual(k.load(self.root)['revision'],2)
        self.assertEqual(k.load(self.root)['concepts']['queue.work']['definition'],replacement['definition'])
        packet=k.resume(self.root)
        cursor={'session_id':packet['session_id'],'questionnaire_sha256':packet['questionnaire_sha256'],
                'summary':'Fixture paused at one notation step','next_action':'Map one symbol to the same event',
                'source_ref':'synthetic pause instruction'}
        k.checkpoint(self.root,cursor,expected_revision=2,operation_id='cursor')
        self.assertIn(cursor['summary'],k.current_card(self.root))
        self.assertEqual(k.load(self.root)['evidence'],{})


if __name__=='__main__':unittest.main()
