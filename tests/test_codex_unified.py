"""Offline unified entry, real request-scope duties and retained old contracts."""
from __future__ import annotations
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from runtime import codex_consult as consult, codex_collaboration as collaboration, codex_paper as paper
from runtime.codex_lifecycle import ingest_message, handle_message
from runtime.codex_session import create_session, session_report
import test_codex_consult as fixtures
import test_codex_split as split_fixtures


class UnifiedDIGRTests(unittest.TestCase):
    file = fixtures.ConsultPublicRuntimeTests.file
    config = fixtures.ConsultPublicRuntimeTests.config
    facts = fixtures.ConsultPublicRuntimeTests.facts
    stop_server = fixtures.ConsultPublicRuntimeTests.stop_server
    plan = split_fixtures.NativeSplitTests.plan

    def setUp(self):
        fixtures.ConsultPublicRuntimeTests.setUp(self)
        self.original = self.file('plain-user.txt', 'DIGR：完成这份当前任务，按实际用途协作。\n')
        self.root = self.folder / 'unified'
        self.pin = '0.14.0@' + 'e' * 40
        create_session(self.root, request=self.original, p_run=self.pin)

    def prepare(self, label, **kw):
        kw.setdefault('max_tokens', 16000)
        return consult.prepare_request(self.root, input_path=self.input, materials=[self.material], exchange_id=label, **kw)

    def call(self, label, *, endpoint='normal', plan=True, model=None, **kwargs):
        with patch.dict(os.environ, {'DIGR_TEST_CONSULT_KEY': fixtures.SECRET}):
            return consult.call_once(self.root, label, facts=self.facts(model=model or consult.DEFAULT_MODEL),
                ceiling_usd=.20, config_path=self.config(endpoint), split_path=self.plan(label) if plan else None, **kwargs)

    def selection(self, text, ref):
        value=ingest_message(self.root, source=self.file(ref+'.txt',text), source_ref=ref)
        handle_message(self.root,message_id=value['message_id'],action='continue',reason='Apply actual synthetic selection')

    def paper_scope(self, version='0.6.0'):
        batch=self.folder/'paper-batch'
        value=paper.initialize(batch,p_run=self.pin,authorization=self.original,source_ref='actual-whole-paper-product',task_root=self.root)
        self.assertEqual(value['addon_version'], version)
        item=paper.add_paper(batch,paper_id='source',title='Synthetic complete source',line='M01',owner='fixture',
            parameters={'N':2,'R':1,'D':0,'V':0,'L':3,'T':'0min','B':0,'S':{'n':0,'r':0,'t':'0min','b':0}})
        return Path(item['paper_root'])

    def test_all_spellings_share_one_new_profile_and_preserve_original_input(self):
        for invocation in ('DIGR','DIGRC','DIGRP'):
            task=self.folder/invocation
            source=self.file(invocation+'-user.txt',invocation+'：synthetic scope')
            value=create_session(task,request=source,p_run=self.pin)
            self.assertEqual(value['execution_profile']['mode'],'DIGR')
            self.assertEqual(value['initial_invocation']['invocation_key'],invocation)
            self.assertEqual((task/'REQUEST.txt').read_bytes(),source.read_bytes())
            self.assertIsNone(session_report(task)['consult'])
        self.assertEqual(self.server.post_calls,[])

    def test_plain_entry_derives_common_duties_before_any_send_without_credentials(self):
        with patch.object(consult,'_config',side_effect=AssertionError('credential read')):
            result=self.prepare('plain')
        contract=result['collaboration']
        self.assertTrue(contract['sonnet_selected'])
        self.assertFalse(contract['sonnet_observed'])
        self.assertEqual(contract['content_relationship'],'SONNET_CONTENT_GUIDANCE')
        self.assertIn('codex/SPLIT.md',contract['protocols'])
        self.assertIn('public_relay',contract['engineering'])
        self.assertEqual(result['sonnet_model_identity']['status'],'UNCONFIRMED')
        self.assertFalse(contract['fee_authorization'])
        self.assertEqual(session_report(self.root)['consult']['totals']['exchange_count'],1)
        with self.assertRaisesRegex(ValueError,'native Codex Split'):
            self.call('plain',plan=False)
        self.assertEqual(self.server.post_calls,[])

    def test_later_sonnet_selection_does_not_restart_or_rewrite_the_task(self):
        self.selection('现在让Sonnet参与当前内容；其余要求保留。','later-sonnet')
        result=self.prepare('later')
        request=json.loads(Path(result['request_path']).read_text(encoding='utf-8'))
        self.assertIn('现在让Sonnet参与当前内容',request['messages'][-1]['content'])
        self.assertEqual((self.root/'REQUEST.txt').read_bytes(),self.original.read_bytes())
        self.assertEqual(result['exchange']['input_ref']['message_id'],1)
        self.assertEqual(session_report(self.root)['session']['execution_profile']['mode'],'DIGR')

    def test_actual_common_sonnet_identity_and_public_events_are_recorded(self):
        self.prepare('identity')
        events=[]
        result=self.call('identity',endpoint='paper-model-confirmed',on_public_event=events.append)
        self.assertEqual(result['sonnet_model_identity']['status'],'CONFIRMED')
        self.assertTrue(result['collaboration']['sonnet_observed'])
        self.assertEqual(result['split']['integrity'],'MATCH')
        self.assertIn('public_delta',[event['event'] for event in events])
        self.assertEqual(len(self.server.post_calls),1)

    def test_translation_is_common_collaboration_without_guide_scope(self):
        self.input.write_text('Translate this original literally. Do not add a guide or commentary.',encoding='utf-8')
        result=self.prepare('translation')
        self.assertIsNone(result['collaboration']['paper_scope'])
        self.assertNotIn('paper/PROTOCOL.md',result['collaboration']['protocols'])
        request=json.loads(Path(result['request_path']).read_text(encoding='utf-8'))
        self.assertNotEqual(request['messages'][0]['content'],consult._LOGICAL_PAPER_SYSTEM)
        self.assertFalse((self.folder/'paper-batch').exists())

    def test_stable_paper_scope_is_registered_for_formal_content(self):
        self.pin = '1.0.0@' + 'e' * 40
        self.root = self.folder / 'stable-paper-task'
        self.original = self.file('stable-paper-user.txt', 'DIGR:: Prepare this complete paper guide.')
        create_session(self.root, request=self.original, p_run=self.pin)
        scope = self.paper_scope(version=paper.VERSION)
        result = self.prepare('stable-paper', paper_root=scope)
        self.assertEqual(result['exchange']['authoring_scope']['addon_version'], '0.6.1')
        self.assertEqual(result['collaboration']['claude_layer'], 'CONTENT')
        self.assertEqual(self.server.post_calls, [])

    def test_plain_entry_paper_and_later_generic_work_keep_separate_scopes(self):
        scope=self.paper_scope()
        authored=self.prepare('guide',paper_root=scope)
        self.assertEqual(authored['collaboration']['content_relationship'],'SONNET_NATIVE_PAPER')
        self.assertIn('paper/PROTOCOL.md',authored['collaboration']['protocols'])
        generic=self.prepare('generic-after-paper')
        self.assertIsNone(generic['collaboration']['paper_scope'])
        self.assertNotIn('authoring_scope',generic['exchange'])
        self.assertNotIn('SELECTED PAPER AND SOURCE DIRECTORY',Path(generic['request_path']).read_text(encoding='utf-8'))
        self.assertEqual(session_report(self.root)['session']['execution_profile']['mode'],'DIGR')

    def test_other_model_has_an_ordinary_relationship(self):
        result=self.prepare('other',model='openai/explicit-other-model')
        self.assertFalse(result['collaboration']['sonnet_selected'])
        self.assertEqual(result['collaboration']['content_relationship'],'ORDINARY_CONTENT_COLLABORATION')
        request=json.loads(Path(result['request_path']).read_text(encoding='utf-8'))
        self.assertEqual(request['messages'][0]['content'],consult._ORDINARY_COLLAB_SYSTEM)
        self.assertNotIn('sonnet_model_identity',result)

    def test_model_switch_updates_relation_but_retains_exact_public_history(self):
        self.prepare('sonnet-origin')
        first=self.call('sonnet-origin',endpoint='paper-model-confirmed')
        public=Path(first['public_path']).read_bytes().decode('utf-8')
        result=self.prepare('ordinary-next',continue_from='sonnet-origin',model='openai/explicit-other-model')
        request=json.loads(Path(result['request_path']).read_text(encoding='utf-8'))
        self.assertEqual(request['messages'][0]['content'],consult._ORDINARY_COLLAB_SYSTEM)
        self.assertIn({'role':'assistant','content':public},request['messages'])
        self.assertIn('system_contract_transition',result['exchange'])
        self.assertEqual(result['collaboration']['content_relationship'],'ORDINARY_CONTENT_COLLABORATION')
        self.call('ordinary-next',model='openai/explicit-other-model')
        again=self.prepare('sonnet-again',continue_from='ordinary-next')
        self.assertEqual(again['collaboration']['content_relationship'],'SONNET_CONTENT_GUIDANCE')
        self.assertIn('system_contract_transition',again['exchange'])

    def test_later_disable_invalidates_prepared_send_and_releases_no_fee(self):
        self.prepare('before-disable')
        plan=self.plan('before-disable')
        self.selection('后续不再调用外部模型，由Codex继续当前任务。','disable-external')
        with patch.dict(os.environ,{'DIGR_TEST_CONSULT_KEY':fixtures.SECRET}):
            with self.assertRaisesRegex(ValueError,'current user input'):
                consult.call_once(self.root,'before-disable',facts=self.facts(),ceiling_usd=.20,
                    config_path=self.config('normal'),split_path=plan)
        result=consult.inspect_exchange(self.root,'before-disable')
        self.assertEqual(result['exchange']['billing_status'],'NOT_ATTEMPTED')
        self.assertEqual(result['totals']['unresolved_reserved_usd'],0)
        self.assertEqual(self.server.post_calls,[])

    def test_derived_contract_cannot_be_edited_to_skip_sonnet_requirements(self):
        self.prepare('tamper')
        directory,attempt,_=consult._load(self.root,'tamper')
        attempt['collaboration_contract']['sonnet_selected']=False
        consult._write(directory/'attempt.json',attempt)
        with self.assertRaisesRegex(ValueError,'collaboration model/scope contract changed'):
            consult.inspect_exchange(self.root,'tamper')
        self.assertEqual(self.server.post_calls,[])

    def test_old_native_pins_do_not_silently_acquire_unified_admission(self):
        for version in ('0.12.1','0.13.0'):
            task=self.folder/('old-'+version)
            value=create_session(task,request=self.original,p_run=version+'@'+'a'*40)
            self.assertEqual(value['execution_profile']['mode'],'NATIVE')
            with self.assertRaisesRegex(ValueError,'explicitly initialized'):
                consult.prepare_request(task,input_path=self.input)
            self.assertIsNone(collaboration.requirements(value['P_run'],consult.DEFAULT_MODEL,None))


if __name__=='__main__':
    unittest.main()
