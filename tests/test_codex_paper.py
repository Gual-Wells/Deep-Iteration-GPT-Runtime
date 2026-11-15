"""Synthetic, isolated behavior checks: no real Gmail, papers or learner records."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from runtime import codex_paper as p
from runtime.codex_transport import CodexAcquisition
from runtime.repository_transport import TransportResponse

try:
    from pypdf import PdfWriter
except ImportError:
    PdfWriter = None

PARAMETERS = {'N': 2, 'T': '0min', 'R': 1, 'B': 0,
              'S': {'n': 0, 't': '0min', 'r': 0, 'b': 0}, 'D': 0, 'V': 0, 'L': 3}


@unittest.skipIf(PdfWriter is None, 'PDF fixture page verification needs pypdf')
class PaperLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.auth = self.base / 'actual-test-user.txt'; self.auth.write_text('Synthetic authorization fixture')
        self.batch = self.base / 'batch'
        p.initialize(self.batch, p_run='0.8.4@' + 'a' * 40, authorization=self.auth,
                     source_ref='fixture-user-1', recipient='reader@example.test')
        self.root = Path(p.add_paper(self.batch, paper_id='first', title='Synthetic Paper',
            line='M01', owner='fixture-native-host', parameters=PARAMETERS)['paper_root'])
        self.source = self.base / 'source.pdf'; self.pdf(self.source)
        p.register_source(self.root, {'id': 'journal', 'path': str(self.source),
            'pages': 1, 'identity': 'synthetic source version'}, expected_revision=0, operation_id='source')
        self.mapping = {'parts': dict(zip(p.PARTS, ['World', 'Notation', 'Reasoning', 'Experiments', 'Return reading'])),
            'assumptions': [], 'claims': [], 'chains': [], 'experiments': [],
            'coverage': [{'id': 'section-1', 'anchor': {'source': 'journal', 'page': 1, 'label': 'section'},
                          'location': 'Reasoning', 'disposition': 'explained'}]}
        p.map_paper(self.root, self.mapping, expected_revision=1, operation_id='map')
        self.md = self.base / 'guide.md'
        self.md.write_text('\n'.join('## ' + h + '\nActual synthetic test text.' for h in self.mapping['parts'].values()))
        self.qa = self.base / 'qa.json'; self.qa.write_text(json.dumps({'pages': 2, 'rendered_pages': 2,
            'formula_errors': [], 'overflow': [], 'missing_images': []}))
        self.review = self.base / 'review.md'; self.review.write_text('Synthetic native review fixture, not real reading evidence.')
        self.pdfs = [self.base / 'volume-1.pdf', self.base / 'volume-2.pdf']
        for path in self.pdfs:
            self.pdf(path)
        self.payload = {'markdown': str(self.md), 'pdfs': [str(x) for x in self.pdfs],
            'qa': str(self.qa), 'review': str(self.review), 'responsibility_report': {'N': 2, 'R': 1, 'D': 0, 'V': 0}}
        p.prepare_candidate(self.root, self.payload, expected_revision=2, operation_id='candidate')

    @staticmethod
    def pdf(path):
        writer = PdfWriter(); writer.add_blank_page(width=300, height=400)
        with path.open('wb') as output:
            writer.write(output)

    def mutation(self, operation, payload, op_id):
        return operation(self.root, payload, expected_revision=p.inspect(self.root)['revision'], operation_id=op_id)

    def receipt(self, number):
        sent = self.base / ('sent-' + str(number) + '.json')
        back = self.base / ('read-' + str(number) + '.json')
        sent.write_text(json.dumps({'synthetic_message_id': str(number)})); back.write_text(sent.read_text())
        path = self.pdfs[number - 1]
        return {'candidate_id': p.inspect(self.root)['candidate_id'], 'message_id': 'fixture-' + str(number),
            'recipient': 'reader@example.test', 'label_ids': ['SENT'],
            'attachments': [{'filename': path.name, 'bytes': path.stat().st_size}],
            'authorization_source_ref': 'fixture-user-1', 'send_evidence': str(sent), 'readback_evidence': str(back)}

    def test_independent_paper_return_requires_every_volume_and_keeps_parent_open(self):
        other = p.add_paper(self.batch, paper_id='second', title='Second paper', line='M02',
                            owner='another-native-host', parameters=PARAMETERS)
        p.record_delivery(self.root, self.receipt(1), expected_revision=3, operation_id='sent-1')
        self.assertEqual(p.inspect(self.root)['status'], 'READY')
        body = self.base / 'return.md'; body.write_text('Synthetic paper return')
        with self.assertRaisesRegex(ValueError, 'complete current Gmail'):
            self.mutation(p.return_paper, {'body': str(body)}, 'too-early')
        self.mutation(p.record_delivery, self.receipt(2), 'sent-2')
        self.assertEqual(p.inspect(self.root)['status'], 'SENT_VERIFIED')
        self.mutation(p.return_paper, {'body': str(body)}, 'returned')
        result = p.summarize(self.batch)
        self.assertEqual(result['papers'][0]['status'], 'RETURNED')
        self.assertEqual(p.inspect(other['paper_root'])['revision'], 0)
        self.assertFalse(result['all_papers_returned'])
        self.assertTrue(result['parent_lifecycle_unchanged'])

    def test_wrong_recipient_draft_and_wrong_attachment_do_not_count_as_sent(self):
        for field, value in [('recipient', 'someone-else@example.test'), ('label_ids', ['DRAFT']),
                             ('attachments', [{'filename': 'volume-1.pdf', 'bytes': 1}])]:
            receipt = self.receipt(1); receipt[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.mutation(p.record_delivery, receipt, 'wrong-' + field)
        self.assertEqual(p.inspect(self.root)['status'], 'READY')

    def test_changed_guide_cannot_reuse_review_or_old_delivery(self):
        receipt = self.receipt(1)
        self.md.write_text(self.md.read_text() + '\nNew actual content')
        self.assertEqual(p.inspect(self.root)['status'], 'STALE_OR_UNAVAILABLE')
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.mutation(p.record_delivery, receipt, 'stale-send')
        self.mutation(p.prepare_candidate, self.payload, 'reviewed-new-edition')
        self.assertNotEqual(p.inspect(self.root)['candidate_id'], receipt['candidate_id'])
        with self.assertRaisesRegex(ValueError, 'exact reviewed'):
            self.mutation(p.record_delivery, receipt, 'old-mail-new-edition')

    def test_image_and_readback_evidence_changes_are_visible(self):
        image = self.base / 'figure.png'; image.write_bytes(b'synthetic image fixture')
        self.md.write_text(self.md.read_text() + '\n![original figure](figure.png)')
        self.mutation(p.prepare_candidate, self.payload, 'with-figure')
        image.write_bytes(b'changed figure')
        self.assertEqual(p.inspect(self.root)['status'], 'STALE_OR_UNAVAILABLE')
        self.mutation(p.prepare_candidate, self.payload, 'changed-figure-reviewed')
        receipt = self.receipt(1); self.mutation(p.record_delivery, receipt, 'sent-with-figure')
        Path(receipt['readback_evidence']).write_text('different readback facts')
        self.assertEqual(p.inspect(self.root)['status'], 'STALE_OR_UNAVAILABLE')

    def test_paper_revision_conflict_and_idempotent_retry(self):
        cursor = {'position': 'one equation', 'next_action': 'explain next step', 'basis': 'synthetic pause'}
        revision = p.inspect(self.root)['revision']
        first = p.checkpoint(self.root, cursor, expected_revision=revision, operation_id='pause')
        retry = p.checkpoint(self.root, cursor, expected_revision=revision, operation_id='pause')
        self.assertTrue(retry['idempotent_replay']); self.assertEqual(first['revision'], retry['revision'])
        with self.assertRaisesRegex(ValueError, 'revision conflict'):
            p.checkpoint(self.root, cursor, expected_revision=revision, operation_id='another-pause')
        with self.assertRaisesRegex(ValueError, 'different content'):
            self.mutation(p.checkpoint, {**cursor, 'position': 'different'}, 'pause')

    def test_resume_prioritizes_uncertain_send_and_only_lists_remaining_volumes(self):
        cursor = {'position': 'volume one send response was uncertain',
            'next_action': 'reconcile Gmail SENT before any resend', 'basis': 'synthetic timeout',
            'pending_delivery': {'attempt_id': 'fixture-attempt-1', 'outcome': 'uncertain',
                                 'pdf_names': ['volume-1.pdf']}}
        self.mutation(p.checkpoint, cursor, 'uncertain')
        self.assertIn('reconcile uncertain Gmail send', p.inspect(self.root)['next_action'])
        # A different volume's confirmed receipt cannot consume the first send.
        self.mutation(p.record_delivery, self.receipt(2), 'other-volume-sent')
        self.assertIn('reconcile uncertain Gmail send', p.inspect(self.root)['next_action'])
        self.mutation(p.checkpoint, {'position': 'another reading position',
            'next_action': 'continue a section', 'basis': 'synthetic navigation'}, 'other-cursor')
        self.assertIn('reconcile uncertain Gmail send', p.inspect(self.root)['next_action'])
        self.mutation(p.record_delivery, self.receipt(1), 'uncertain-reconciled')
        self.assertEqual(p.inspect(self.root)['status'], 'SENT_VERIFIED')
        self.assertIsNone(p.inspect(self.root)['unresolved_delivery_attempt'])

    def test_pending_correction_after_return_prevents_false_batch_completion(self):
        self.mutation(p.record_delivery, self.receipt(1), 'sent-1')
        progress = p.inspect(self.root)['delivery_progress']
        self.assertEqual(progress['verified_count'], 1)
        self.assertEqual(progress['remaining'], ['volume-2.pdf'])
        self.assertIn('volume-2.pdf', p.inspect(self.root)['next_action'])
        self.mutation(p.record_delivery, self.receipt(2), 'sent-2')
        body = self.base / 'return.md'; body.write_text('Synthetic paper return')
        self.mutation(p.return_paper, {'body': str(body)}, 'returned')
        self.assertTrue(p.summarize(self.batch)['all_papers_returned'])
        self.mutation(p.checkpoint, {'position': 'new correction received',
            'next_action': 'revise the explanation and deliver a new edition',
            'basis': 'synthetic actual new user correction'}, 'new-correction')
        result = p.summarize(self.batch)
        self.assertFalse(result['all_papers_returned'])
        self.assertEqual(result['pending_saved_steps'], ['first'])
        self.assertIn('revise the explanation', result['papers'][0]['next_action'])

    def test_mapping_cannot_cross_source_pages_or_hide_wrong_reader_order_in_toc(self):
        mapping = deepcopy(self.mapping); mapping['coverage'][0]['anchor']['page'] = 2
        with self.assertRaisesRegex(ValueError, 'physical page'):
            self.mutation(p.map_paper, mapping, 'out-of-range')
        mapping = deepcopy(self.mapping)
        mapping['claims'] = [{'id': 'C1', 'anchor': mapping['coverage'][0]['anchor'],
            'location': 'World', 'basis': 'author claim', 'chains': ['not-existing']}]
        with self.assertRaisesRegex(ValueError, 'unknown chains'):
            self.mutation(p.map_paper, mapping, 'broken-proof-link')
        self.md.write_text('World Notation Reasoning Experiments Return reading\n' +
            '\n'.join('## ' + h for h in ['World', 'Reasoning', 'Notation', 'Experiments', 'Return reading']))
        with self.assertRaisesRegex(ValueError, 'reader order'):
            self.mutation(p.prepare_candidate, self.payload, 'toc-cannot-fix-order')


class PinnedAddonTests(unittest.TestCase):
    def fixture(self, corrupt=False):
        files = {'paper/VERSION': b'0.1.0\n', 'paper/PROTOCOL.md': b'Pinned protocol',
                 '.agents/skills/digr-paper/SKILL.md': b'Pinned skill'}
        manifest = {'version': '0.1.0', 'protocol': 'digrp-codex-1', 'version_path': 'paper/VERSION',
            'entrypoint': 'paper/PROTOCOL.md', 'skill': '.agents/skills/digr-paper/SKILL.md',
            'file_sha256': {path: sha256(raw).hexdigest() for path, raw in files.items()}}
        raw = json.dumps(manifest).encode(); files['paper/manifest.json'] = raw
        core = {'paper_addon': {'version': '0.1.0', 'manifest': 'paper/manifest.json', 'sha256': sha256(raw).hexdigest()}}
        base = CodexAcquisition('b' * 40, '0.8.4', 'execution', core, {}, ())
        requests = []
        def fetch(request):
            requests.append(request.url)
            path = request.url.split('/' + base.sha + '/')[1]
            body = b'changed' if corrupt and path.endswith('PROTOCOL.md') else files[path]
            return TransportResponse(request.url, 200, body, 'github_connector', 'immutable_sha')
        return base, fetch, requests

    def test_addon_continues_one_sha_without_mutable_head_read(self):
        base, fetch, requests = self.fixture()
        result = p.acquire_addon(base, fetch=fetch)
        self.assertEqual(result['sha'], base.sha)
        self.assertFalse(result['new_live_ref_resolution'])
        self.assertEqual(len(requests), 4)
        self.assertTrue(all('/' + base.sha + '/' in url for url in requests))

    def test_addon_rejects_changed_member_or_missing_core_execution(self):
        base, fetch, _ = self.fixture(corrupt=True)
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            p.acquire_addon(base, fetch=fetch)
        base, fetch, _ = self.fixture()
        from dataclasses import replace
        with self.assertRaisesRegex(ValueError, 'complete pinned core'):
            p.acquire_addon(replace(base, stage='startup'), fetch=fetch)


if __name__ == '__main__':
    unittest.main()
