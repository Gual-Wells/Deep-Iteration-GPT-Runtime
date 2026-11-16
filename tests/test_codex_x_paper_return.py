"""Full synthetic task/paper/file-return journeys; no service is contacted."""
import json
from pathlib import Path
import unittest

from runtime import codex_delivery as delivery
from runtime import codex_paper as paper
from runtime.codex_foundation import propose_foundation, confirm_foundation
from runtime.codex_lifecycle import load_lifecycle
from runtime.codex_return import seal_return
from runtime.codex_session import create_session, task_delivery_policy
from tests.test_codex_delivery import registry
from tests.test_codex_paper import PaperFixture


class XPaperBase(PaperFixture):
    pin = '0.9.0@'+'a'*40
    invocation = 'DIGRP:produce the synthetic complete paper'

    def initialize_options(self):
        self.task = self.base/'core-task'
        request = self.base/'request.txt'; request.write_text(self.invocation,encoding='utf-8')
        targets = self.base/'targets.json'; targets.write_text(json.dumps(registry()),encoding='utf-8')
        create_session(self.task,request=request,p_run=self.pin,visits_path=self.base/'visits.jsonl',
                       run_id='synthetic-x-paper',destinations=targets)
        fields = 'goal results scope granularity basis dependencies approach resources completion'.split()
        propose_foundation(self.task,{'brief':{k:'Synthetic '+k+' fixture' for k in fields},'questions':[]},
                           reason='Isolated behavior fixture')
        confirm_foundation(self.task,revision=1,user_text=self.invocation,source=request.as_posix())
        self.policy = task_delivery_policy(self.task)
        return {'task_root':self.task}

    def return_input(self, files):
        path = self.base/'final-return.json'
        value = {'schema_version':2,'result':'Synthetic final result','key_changes':'Synthetic behavior',
                 'work_process':'| Time | Work |\n| --- | --- |\n| Not a real run | Synthetic check |',
                 'verification_limits':'No real sender or learner','parameters':'Synthetic parameters only',
                 'decisions':[],'unhandled':[],'sources':[],
                 'artifacts':[{'label':p.name,'path':str(p)} for p in files]}
        path.write_text(json.dumps(value),encoding='utf-8')
        return path

    def reserve(self):
        candidate = paper.inspect(self.root)['candidate_id']
        self.identity = {k:self.policy[k] for k in ('account','recipient')}
        self.identity.update(account_confirmed=True,recipient_confirmed=True,binding_basis='native-self-entry')
        self.identity_file = self.base/'identity.json'
        self.identity_file.write_text(json.dumps({'identity':self.identity}),encoding='utf-8')
        prepared = delivery.prepare(self.task,{'candidate_id':candidate,'files':[str(self.pdfs[0])],
            'policy':self.policy,'authorization_source_ref':'fixture-user-1'},operation_id='prepare-paper')
        marked = delivery.mark_sending(self.task,{'delivery_id':prepared['delivery_id'],
            'identity':self.identity,'identity_evidence':str(self.identity_file)},operation_id='reserve-paper')
        return candidate, marked

    def synthetic_readback(self, candidate, marked):
        message = {'structuredContent':{'id':'synthetic-message-1','label_ids':['SENT'],
            'payload':{'headers':[{'name':'From','value':self.policy['account']},
                                  {'name':'To','value':self.policy['recipient']}],
                       'parts':[{'filename':self.pdfs[0].name,'mime_type':'application/pdf',
                                 'body':{'size':self.pdfs[0].stat().st_size}}]}}}
        sent = self.base/'send.json'; back = self.base/'readback.json'
        sent.write_text(json.dumps({'structuredContent':{'id':'synthetic-message-1'}}),encoding='utf-8')
        back.write_text(json.dumps(message),encoding='utf-8')
        receipt = {k:self.policy[k] for k in ('target','channel','account','recipient','transport')}
        receipt.update(candidate_id=candidate,attempt_id=marked['attempt_id'],identity=self.identity,
            evidence_kind='gmail-api',message_id='synthetic-message-1',readback_result=message,
            readback={'completed':True,'attempt_correlated':True},
            identity_evidence=str(self.identity_file),send_evidence=str(sent),readback_evidence=str(back))
        return receipt


class LocalPaperReturnTests(XPaperBase,unittest.TestCase):
    def test_no_x_returns_locally_without_gmail_and_parent_stays_active(self):
        self.assertEqual(paper.inspect(self.root)['status'],'READY_LOCAL')
        with self.assertRaisesRegex(ValueError,'no-X'):
            paper.record_delivery(self.root,{},expected_revision=3,operation_id='forbidden-mail')
        body = self.base/'complete.md'; body.write_text('Synthetic local completion')
        paper.return_paper(self.root,{'body':str(body)},expected_revision=3,operation_id='local-return')
        self.assertEqual(paper.inspect(self.root)['status'],'RETURNED')
        self.assertEqual(load_lifecycle(self.task)['status'],'ACTIVE')
        self.assertFalse((self.task/'delivery.json').exists())
        self.assertEqual(seal_return(self.task,self.return_input(self.pdfs))['current_receipt'],'READY_UNCLOSED')


class ExternalPaperReturnTests(XPaperBase,unittest.TestCase):
    invocation = 'DIGRP(X=Gmail):produce the synthetic complete paper'

    def test_x_requires_reserved_verified_exact_complete_pdf_before_paper_and_core_return(self):
        body = self.base/'complete.md'; body.write_text('Synthetic delivered completion')
        with self.assertRaises(ValueError):
            paper.return_paper(self.root,{'body':str(body)},expected_revision=3,operation_id='too-soon')
        with self.assertRaisesRegex(ValueError,'X file delivery is incomplete'):
            seal_return(self.task,self.return_input(self.pdfs))
        candidate, marked = self.reserve()
        self.assertTrue(paper.inspect(self.root)['unresolved_delivery_attempt'])
        with self.assertRaises(ValueError):
            paper.record_delivery(self.root,{'candidate_id':candidate,'message_id':'invented'},
                                  expected_revision=3,operation_id='bypass-ledger')
        receipt = self.synthetic_readback(candidate,marked)
        delivery.reconcile(self.task,{'delivery_id':marked['delivery_id'],'attempt_id':marked['attempt_id'],
            'outcome':'sent','receipt':receipt},operation_id='readback-paper')
        paper.record_delivery(self.root,{'candidate_id':candidate,'delivery_id':marked['delivery_id']},
                              expected_revision=3,operation_id='record-parent-delivery')
        self.assertEqual(paper.inspect(self.root)['status'],'SENT_VERIFIED')
        paper.return_paper(self.root,{'body':str(body)},expected_revision=4,operation_id='paper-return')
        self.assertEqual(paper.inspect(self.root)['status'],'RETURNED')
        self.assertEqual(load_lifecycle(self.task)['status'],'ACTIVE')
        self.assertEqual(seal_return(self.task,self.return_input(self.pdfs))['current_receipt'],'READY_UNCLOSED')

    def test_same_message_fresh_proof_repairs_evidence_without_resending_or_invalidating_paper(self):
        candidate, marked = self.reserve(); receipt = self.synthetic_readback(candidate,marked)
        payload = {'delivery_id':marked['delivery_id'],'attempt_id':marked['attempt_id'],'outcome':'sent','receipt':receipt}
        delivery.reconcile(self.task,payload,operation_id='first-proof')
        paper.record_delivery(self.root,{'candidate_id':candidate,'delivery_id':marked['delivery_id']},
                              expected_revision=3,operation_id='record-proof')
        body = self.base/'complete.md'; body.write_text('Synthetic completion')
        paper.return_paper(self.root,{'body':str(body)},expected_revision=4,operation_id='return')
        original = Path(receipt['readback_evidence']); fresh = self.base/'fresh-readback.json'
        fresh.write_bytes(original.read_bytes()); original.unlink()
        self.assertEqual(paper.inspect(self.root)['status'],'STALE_OR_UNAVAILABLE')
        receipt['readback_evidence'] = str(fresh)
        delivery.reconcile(self.task,payload,operation_id='refresh-same-message-proof')
        self.assertEqual(paper.inspect(self.root)['status'],'RETURNED')
        current = delivery.inspect(self.task)['deliveries'][0]
        self.assertEqual(len(current['attempts']),1)
        self.assertTrue(current['history_issues'])


if __name__ == '__main__':
    unittest.main()
