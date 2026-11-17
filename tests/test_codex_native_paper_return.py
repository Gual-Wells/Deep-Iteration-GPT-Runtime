"""Complete native-paper/local-X return paths with labelled synthetic evidence."""
import json
from pathlib import Path
import unittest

from runtime import codex_delivery as delivery
from runtime import codex_paper as paper
from runtime.codex_foundation import propose_foundation, confirm_foundation
from runtime.codex_lifecycle import load_lifecycle
from runtime.codex_return import close_return, seal_return
from runtime.codex_session import create_session, task_delivery_policy
from tests.test_codex_delivery import registry
from tests.test_codex_paper import PARAMETERS, PdfWriter
from tests.test_codex_paper_native import NativePaperFixture
from tests.test_codex_x_paper_return import XPaperBase


class NativeReturnFixture(NativePaperFixture):
    external = False

    def fixture(self, version):
        folder = self.base / version
        folder.mkdir()
        request = folder / 'request.txt'
        text = ('DIGRP(X):' if self.external else 'DIGRP:') + 'Synthetic native paper fixture; no service call.'
        request.write_text(text, encoding='utf-8')
        task = folder / 'task'
        targets = folder / 'targets.json'
        targets.write_text(json.dumps(registry()), encoding='utf-8')
        pin = version + '@' + 'c' * 40
        metadata = create_session(task, request=request, p_run=pin, visits_path=folder / 'visits',
                                  run_id='synthetic-native-return', destinations=targets)
        self.assertEqual(metadata['execution_profile']['paper_authoring_contract'], 'sonnet-native-v1')
        fields = 'goal results scope granularity basis dependencies approach resources completion'.split()
        propose_foundation(task, {'brief': {k: 'Synthetic '+k for k in fields}, 'questions': []},
                           reason='Synthetic complete public path fixture')
        confirm_foundation(task, revision=1, user_text=text, source=request.as_posix())
        batch = folder / 'batch'
        paper.initialize(batch, p_run=pin, authorization=request, source_ref='fixture-user-1', task_root=task)
        root = Path(paper.add_paper(batch, paper_id='first', title='Synthetic native paper', line='M01',
                                   owner='synthetic-host', parameters=PARAMETERS)['paper_root'])
        self.policy = task_delivery_policy(task)
        return task, batch, root

    def ready(self):
        self.mapped()
        self.public_exchange()
        self.candidate()
        self.pdfs = [self.source]

    return_input = XPaperBase.return_input
    reserve = XPaperBase.reserve
    synthetic_readback = XPaperBase.synthetic_readback


@unittest.skipUnless(PdfWriter, 'configured Python with pypdf required')
class NativeLocalReturnTests(NativeReturnFixture, unittest.TestCase):
    def test_native_arbitrary_chapters_return_locally_and_parent_closes_only_at_final_return(self):
        self.ready()
        self.assertNotIn('parts', paper._load(self.root)['mapping'])
        self.assertEqual(paper.inspect(self.root)['status'], 'READY_LOCAL')
        body = self.base / 'completion.md'
        body.write_text('Synthetic whole-paper local completion.', encoding='utf-8')
        self.mutate(paper.return_paper, {'body': str(body)}, 'paper-return')
        self.assertEqual(paper.inspect(self.root)['status'], 'RETURNED')
        self.assertEqual(load_lifecycle(self.task)['status'], 'ACTIVE')
        self.assertFalse((self.task/'delivery.json').exists())
        self.assertEqual(seal_return(self.task, self.return_input(self.pdfs))['current_receipt'], 'READY_UNCLOSED')
        self.assertEqual(close_return(self.task, reason='Synthetic final return selected')['current_receipt'], 'CLOSED')


@unittest.skipUnless(PdfWriter, 'configured Python with pypdf required')
class NativeExternalReturnTests(NativeReturnFixture, unittest.TestCase):
    external = True

    def test_native_authoring_and_exact_single_pdf_share_one_parent_gmail_transaction(self):
        self.ready()
        body = self.base / 'completion.md'
        body.write_text('Synthetic whole-paper external completion.', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.mutate(paper.return_paper, {'body': str(body)}, 'too-soon')
        with self.assertRaisesRegex(ValueError, 'X file delivery is incomplete'):
            seal_return(self.task, self.return_input(self.pdfs))
        candidate, marked = self.reserve()
        receipt = self.synthetic_readback(candidate, marked)
        delivery.reconcile(self.task, {'delivery_id': marked['delivery_id'], 'attempt_id': marked['attempt_id'],
                                      'outcome': 'sent', 'receipt': receipt}, operation_id='synthetic-readback')
        self.mutate(paper.record_delivery, {'candidate_id': candidate, 'delivery_id': marked['delivery_id']},
                    'paper-delivery')
        self.mutate(paper.return_paper, {'body': str(body)}, 'paper-return')
        self.assertEqual(paper.inspect(self.root)['status'], 'RETURNED')
        self.assertEqual(load_lifecycle(self.task)['status'], 'ACTIVE')
        self.assertEqual(len(delivery.inspect(self.task)['deliveries'][0]['attempts']), 1)
        self.assertEqual(seal_return(self.task, self.return_input(self.pdfs))['current_receipt'], 'READY_UNCLOSED')
        self.assertEqual(close_return(self.task, reason='Synthetic final return selected')['current_receipt'], 'CLOSED')
