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


class PaperFixture:
    legacy = False
    pdf_count = 1
    pin = '0.8.4@' + 'a' * 40

    def initialize_options(self):
        return {'recipient':'reader@example.test'}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.auth = self.base / 'actual-test-user.txt'; self.auth.write_text('Synthetic authorization fixture')
        self.batch = self.base / 'batch'
        p.initialize(self.batch, p_run=self.pin, authorization=self.auth,
                     source_ref='fixture-user-1', **self.initialize_options())
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
        self.qa = self.base / 'qa.json'; self.qa.write_text(json.dumps({'pages': self.pdf_count, 'rendered_pages': self.pdf_count,
            'formula_errors': [], 'overflow': [], 'missing_images': []}))
        self.review = self.base / 'review.md'; self.review.write_text('Synthetic native review fixture, not real reading evidence.')
        self.pdfs = ([self.base / ('volume-' + str(n) + '.pdf') for n in range(1, self.pdf_count + 1)]
                     if self.legacy else [self.base / 'paper-complete.pdf'])
        for path in self.pdfs:
            self.pdf(path)
        self.payload = {'markdown': str(self.md), 'pdfs': [str(x) for x in self.pdfs],
            'qa': str(self.qa), 'review': str(self.review), 'responsibility_report': {'N': 2, 'R': 1, 'D': 0, 'V': 0}}
        if self.legacy:
            self.legacy_candidate_fixture()
        else:
            p.prepare_candidate(self.root, self.payload, expected_revision=2, operation_id='candidate')

    def pdf(self, path, *, sizes=None, rotation=None, crop=None):
        sizes = sizes or ([(300, 400)] if self.legacy else [(210 * 72 / 25.4, 297 * 72 / 25.4)])
        writer = PdfWriter()
        for width, height in sizes:
            page = writer.add_blank_page(width=width, height=height)
            if rotation:
                page.rotate(rotation)
            if crop:
                page.cropbox.upper_right = crop
        with path.open('wb') as output:
            writer.write(output)

    def legacy_candidate_fixture(self):
        # A stored 0.1 shape, not a backwards mode in the 0.2 write API. The
        # real 0.1 producer's two-volume record is also exercised privately.
        files = [p._file(self.root, self.md, 'markdown'),
                 *(p._file(self.root, path, 'pdf') for path in self.pdfs),
                 p._file(self.root, self.qa, 'qa'), p._file(self.root, self.review, 'review')]
        candidate = {'mapping_digest': p._digest(self.mapping), 'files': files,
                     'responsibility_report': deepcopy(self.payload['responsibility_report'])}
        candidate['id'] = p._digest(candidate)
        value = p._load(self.root)
        value.update(addon_version='0.1.0', candidate=candidate, revision=3)
        value['operations']['candidate'] = {
            'fingerprint': p._digest({'action': 'candidate', 'payload': self.payload}),
            'result': {'paper_id': 'first', 'revision': 3, 'action': 'candidate'}}
        p._write(self.root / 'paper.json', value)
        batch = p._read(self.batch / 'batch.json'); batch['addon_version'] = '0.1.0'
        p._write(self.batch / 'batch.json', batch)

    def upgrade_payload(self):
        path = self.base / 'paper-complete.pdf'
        self.pdf(path, sizes=[(210 * 72 / 25.4, 297 * 72 / 25.4)])
        self.pdfs = [path]; self.payload['pdfs'] = [str(path)]
        self.qa.write_text(json.dumps({'pages': 1, 'rendered_pages': 1,
            'formula_errors': [], 'overflow': [], 'missing_images': []}))

    def legacy_history_fixture(self):
        value = p._load(self.root)
        value['deliveries'] = []
        for number in range(1, len(self.pdfs) + 1):
            facts = self.receipt(number)
            value['deliveries'].append({
                'candidate_id': value['candidate']['id'], 'message_id': facts['message_id'],
                'recipient': facts['recipient'], 'attachments': facts['attachments'],
                'evidence': [p._file(self.root, facts[key], key) for key in ('send_evidence', 'readback_evidence')],
                'authorization_source_ref': facts['authorization_source_ref'],
                'observation_scope': 'SYNTHETIC stored 0.1 readback facts'})
        body = self.base / 'legacy-return.md'; body.write_text('SYNTHETIC stored 0.1 return')
        value['returns'] = [{'candidate_id': value['candidate']['id'],
            'body': p._file(self.root, body, 'paper_return'), 'parent_lifecycle_unchanged': True, 'at_ns': 1}]
        value['revision'] += len(self.pdfs) + 1
        p._write(self.root / 'paper.json', value)

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


@unittest.skipIf(PdfWriter is None, 'PDF fixture page verification needs pypdf')
class PaperLifecycleTests(PaperFixture, unittest.TestCase):

    def test_independent_paper_return_requires_current_mail_and_keeps_parent_open(self):
        other = p.add_paper(self.batch, paper_id='second', title='Second paper', line='M02',
                            owner='another-native-host', parameters=PARAMETERS)
        body = self.base / 'return.md'; body.write_text('Synthetic paper return')
        with self.assertRaisesRegex(ValueError, 'complete current Gmail'):
            self.mutation(p.return_paper, {'body': str(body)}, 'too-early')
        self.mutation(p.record_delivery, self.receipt(1), 'sent-1')
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
        self.upgrade_payload()
        self.mutation(p.prepare_candidate, self.payload, 'reviewed-new-edition')
        self.assertNotEqual(p.inspect(self.root)['candidate_id'], receipt['candidate_id'])
        with self.assertRaisesRegex(ValueError, 'exact reviewed'):
            self.mutation(p.record_delivery, receipt, 'old-mail-new-edition')

    def test_image_and_readback_evidence_changes_are_visible(self):
        image = self.base / 'figure.png'; image.write_bytes(b'synthetic image fixture')
        self.md.write_text(self.md.read_text() + '\n![original figure](figure.png)')
        self.upgrade_payload()
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

    def test_resume_keeps_uncertain_complete_pdf_send_across_a_new_reading_cursor(self):
        cursor = {'position': 'volume one send response was uncertain',
            'next_action': 'reconcile Gmail SENT before any resend', 'basis': 'synthetic timeout',
            'pending_delivery': {'attempt_id': 'fixture-attempt-1', 'outcome': 'uncertain',
                                 'pdf_names': ['paper-complete.pdf']}}
        self.mutation(p.checkpoint, cursor, 'uncertain')
        self.assertIn('reconcile uncertain Gmail send', p.inspect(self.root)['next_action'])
        self.mutation(p.checkpoint, {'position': 'another reading position',
            'next_action': 'continue a section', 'basis': 'synthetic navigation'}, 'other-cursor')
        self.assertIn('reconcile uncertain Gmail send', p.inspect(self.root)['next_action'])
        self.mutation(p.record_delivery, self.receipt(1), 'uncertain-reconciled')
        self.assertEqual(p.inspect(self.root)['status'], 'SENT_VERIFIED')
        self.assertIsNone(p.inspect(self.root)['unresolved_delivery_attempt'])

    def test_pending_correction_after_return_prevents_false_batch_completion(self):
        progress = p.inspect(self.root)['delivery_progress']
        self.assertEqual(progress['verified_count'], 0)
        self.assertEqual(progress['remaining'], ['paper-complete.pdf'])
        self.assertIn('paper-complete.pdf', p.inspect(self.root)['next_action'])
        self.mutation(p.record_delivery, self.receipt(1), 'sent-1')
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
        self.upgrade_payload()
        self.md.write_text('World Notation Reasoning Experiments Return reading\n' +
            '\n'.join('## ' + h for h in ['World', 'Reasoning', 'Notation', 'Experiments', 'Return reading']))
        with self.assertRaisesRegex(ValueError, 'reader order'):
            self.mutation(p.prepare_candidate, self.payload, 'toc-cannot-fix-order')


@unittest.skipIf(PdfWriter is None, 'PDF fixture page verification needs pypdf')
class SinglePdfPaperTests(PaperFixture, unittest.TestCase):
    def test_qa_hash_and_needs_review_cannot_be_reused_after_pdf_postprocessing(self):
        qa = json.loads(self.qa.read_text())
        qa.update(sha256=sha256(self.pdfs[0].read_bytes()).hexdigest(), status='NEEDS_REVIEW')
        self.qa.write_text(json.dumps(qa))
        with self.assertRaisesRegex(ValueError, 'still needs review'):
            self.mutation(p.prepare_candidate, self.payload, 'uncleared-inspection')
        qa['status'] = 'INSPECTED'; self.qa.write_text(json.dumps(qa))
        self.mutation(p.prepare_candidate, self.payload, 'cleared-fixture-review')
        previous = p.inspect(self.root)['candidate_id']
        with self.pdfs[0].open('ab') as stream:
            stream.write(b'\n%SYNTHETIC postprocess changes final identity\n')
        with self.assertRaisesRegex(ValueError, 'QA PDF hash differs'):
            self.mutation(p.prepare_candidate, self.payload, 'stale-before-postprocess')
        qa['sha256'] = sha256(self.pdfs[0].read_bytes()).hexdigest()
        self.qa.write_text(json.dumps(qa))
        self.mutation(p.prepare_candidate, self.payload, 'actual-final-identity-reviewed')
        self.assertNotEqual(p.inspect(self.root)['candidate_id'], previous)

    def test_one_complete_pdf_one_message_and_independent_return(self):
        value = p._load(self.root)
        self.assertEqual(value['candidate']['addon_version'], '0.2.0')
        self.assertEqual(value['candidate']['delivery_contract'], p.SINGLE_PDF_CONTRACT)
        self.assertEqual(value['candidate']['pdf_geometry']['profile'], 'A4')
        extra = self.base / 'part-two.pdf'; self.pdf(extra)
        with self.assertRaisesRegex(ValueError, 'one complete PDF'):
            self.mutation(p.prepare_candidate, {**self.payload, 'pdfs': [str(self.pdfs[0]), str(extra)]}, 'split')
        receipt = self.receipt(1)
        self.mutation(p.record_delivery, receipt, 'one-message')
        self.assertEqual(p.inspect(self.root)['status'], 'SENT_VERIFIED')
        revision = p.inspect(self.root)['revision']
        replay = p.record_delivery(self.root, receipt, expected_revision=3, operation_id='one-message')
        self.assertTrue(replay['idempotent_replay'])
        self.assertEqual(p.inspect(self.root)['revision'], revision)
        with self.assertRaisesRegex(ValueError, 'already has a Gmail message'):
            self.mutation(p.record_delivery, {**receipt, 'message_id': 'another-real-send'}, 'duplicate-send')
        with self.assertRaisesRegex(ValueError, 'one complete PDF attachment'):
            self.mutation(p.record_delivery, {**receipt, 'attachments': receipt['attachments'] * 2}, 'duplicate-attachment')
        other = p.add_paper(self.batch, paper_id='second', title='Second synthetic paper', line='M02',
                            owner='another-native-host', parameters=PARAMETERS)
        body = self.base / 'return.md'; body.write_text('SYNTHETIC one-paper return')
        self.mutation(p.return_paper, {'body': str(body)}, 'returned')
        self.assertEqual(p.inspect(self.root)['status'], 'RETURNED')
        self.assertEqual(p.inspect(other['paper_root'])['revision'], 0)
        self.assertFalse(p.summarize(self.batch)['all_papers_returned'])

    def test_actual_geometry_rejects_phone_spreads_crop_and_wrong_page_count(self):
        a4 = (210 * 72 / 25.4, 297 * 72 / 25.4)
        cases = [
            ('variable-phone', [(390, 600), (390, 350)], None, 2),
            ('spread', [(2 * a4[0], a4[1])], None, 1),
            ('arbitrary-portrait', [(300, 400)], None, 1),
            ('mixed-sheets', [a4, (612, 792)], None, 2),
            ('phone-crop', [a4], (390, 629), 1),
            ('false-qa-count', [a4, a4], None, 1),
        ]
        original_qa = self.qa.read_text()
        for label, sizes, crop, reported_pages in cases:
            with self.subTest(label=label):
                path = self.base / (label + '.pdf'); self.pdf(path, sizes=sizes, crop=crop)
                self.qa.write_text(json.dumps({'pages': reported_pages, 'rendered_pages': reported_pages,
                    'formula_errors': [], 'overflow': [], 'missing_images': []}))
                with self.assertRaises(ValueError):
                    self.mutation(p.prepare_candidate, {**self.payload, 'pdfs': [str(path)]}, label)
        self.qa.write_text(original_qa)
        self.assertEqual(p.inspect(self.root)['status'], 'READY')
        fake = self.base / 'fake.pdf'; fake.write_bytes(b'%PDF-1.4\nsynthetic fake header, not an actual PDF')
        with self.assertRaisesRegex(ValueError, 'actual PDF'):
            self.mutation(p.prepare_candidate, {**self.payload, 'pdfs': [str(fake)]}, 'fake-pdf')

    def test_other_named_sheet_requires_explicit_profile_and_rotation_is_effective(self):
        letter = self.base / 'letter.pdf'; self.pdf(letter, sizes=[(612, 792)])
        with self.assertRaisesRegex(ValueError, 'standard portrait A4'):
            self.mutation(p.prepare_candidate, {**self.payload, 'pdfs': [str(letter)]}, 'implicit-letter')
        self.mutation(p.prepare_candidate, {**self.payload, 'pdfs': [str(letter)], 'page_profile': 'Letter'}, 'explicit-letter')
        self.assertEqual(p._load(self.root)['candidate']['pdf_geometry']['profile'], 'Letter')
        with self.assertRaisesRegex(ValueError, 'supported named'):
            self.mutation(p.prepare_candidate, {**self.payload, 'page_profile': 'arbitrary-portrait'}, 'arbitrary-profile')
        rotated = self.base / 'effective-a4.pdf'
        self.pdf(rotated, sizes=[(297 * 72 / 25.4, 210 * 72 / 25.4)], rotation=90)
        self.mutation(p.prepare_candidate, {**self.payload, 'pdfs': [str(rotated)]}, 'effective-portrait')
        self.assertEqual(p._load(self.root)['candidate']['pdf_geometry']['orientation'], 'portrait')

    def test_old_one_pdf_receipt_does_not_become_a_new_version_receipt(self):
        self.legacy_candidate_fixture()
        old_receipt = self.receipt(1)
        self.legacy_history_fixture()
        before = (self.root / 'paper.json').read_bytes()
        old = p._load(self.root)
        self.assertEqual(p.inspect(self.root)['status'], 'RETURNED')
        self.assertEqual((self.root / 'paper.json').read_bytes(), before)
        self.mutation(p.prepare_candidate, self.payload, 'new-review-same-artifacts')
        current = p._load(self.root)
        self.assertNotEqual(current['candidate']['id'], old_receipt['candidate_id'])
        self.assertEqual(current['addon_version'], '0.1.0')
        self.assertEqual((current['deliveries'], current['returns']), (old['deliveries'], old['returns']))
        self.assertEqual(p.inspect(self.root)['status'], 'READY')
        with self.assertRaisesRegex(ValueError, 'exact reviewed'):
            self.mutation(p.record_delivery, old_receipt, 'old-mail-new-contract')


@unittest.skipIf(PdfWriter is None, 'PDF fixture page verification needs pypdf')
class LegacyPaperReadOnlyTests(PaperFixture, unittest.TestCase):
    legacy = True
    pdf_count = 2

    def setUp(self):
        super().setUp()
        self.legacy_history_fixture()

    def test_stored_two_message_return_is_read_without_modifying_legacy_bytes(self):
        before = (self.root / 'paper.json').read_bytes()
        result = p.inspect(self.root)
        self.assertEqual(result['status'], 'RETURNED')
        self.assertEqual(result['delivery_progress']['volume_count'], 2)
        self.assertEqual(result['delivery_contract'], p.LEGACY_CONTRACT)
        self.assertEqual((self.root / 'paper.json').read_bytes(), before)

    def test_current_writer_rejects_new_delivery_or_return_on_old_candidate(self):
        before = (self.root / 'paper.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'history is read-only'):
            self.mutation(p.record_delivery, {**self.receipt(1), 'message_id': 'new-send'}, 'new-legacy-send')
        body = self.base / 'new-return.md'; body.write_text('SYNTHETIC disallowed old-candidate return')
        with self.assertRaisesRegex(ValueError, 'history is read-only'):
            self.mutation(p.return_paper, {'body': str(body)}, 'new-legacy-return')
        self.assertEqual((self.root / 'paper.json').read_bytes(), before)

    def test_settled_old_uncertain_send_stays_context_not_new_delivery(self):
        value = p._load(self.root)
        old_candidate = value['candidate']['id']
        old_pdf = next(f for f in value['candidate']['files'] if f['kind'] == 'pdf')
        cursor = {'position': 'old send was resolved', 'next_action': 'old reading context',
            'basis': 'SYNTHETIC prior reconciliation', 'pending_delivery': {
                'attempt_id': 'old-attempt', 'candidate_id': old_candidate, 'outcome': 'uncertain',
                'pdf_names': [old_pdf['filename']], 'volumes': [old_pdf]}}
        value['cursor'] = cursor; p._write(self.root / 'paper.json', value)
        self.assertIsNone(p.inspect(self.root)['unresolved_delivery_attempt'])
        old = p._load(self.root)
        self.upgrade_payload()
        self.mutation(p.prepare_candidate, self.payload, 'current-complete-review')
        current = p._load(self.root)
        self.assertEqual((current['cursor'], current['deliveries'], current['returns']),
                         (cursor, old['deliveries'], old['returns']))
        result = p.inspect(self.root)
        self.assertEqual(result['status'], 'READY')
        self.assertEqual(result['delivery_progress']['verified_count'], 0)
        self.assertIsNone(result['unresolved_delivery_attempt'])


class PinnedAddonTests(unittest.TestCase):
    def fixture(self, corrupt=False, *, version='0.1.0', include_design=True):
        files = {'paper/VERSION': (version + '\n').encode(), 'paper/PROTOCOL.md': b'Pinned protocol',
                 '.agents/skills/digr-paper/SKILL.md': b'Pinned skill'}
        if version != '0.1.0' and include_design:
            files['paper/PDF_DESIGN.md'] = b'Pinned desktop one-page design contract'
        manifest = {'version': version, 'protocol': 'digrp-codex-1', 'version_path': 'paper/VERSION',
            'entrypoint': 'paper/PROTOCOL.md', 'skill': '.agents/skills/digr-paper/SKILL.md',
            'file_sha256': {path: sha256(raw).hexdigest() for path, raw in files.items()}}
        if version != '0.1.0' and include_design:
            manifest['pdf_design'] = 'paper/PDF_DESIGN.md'
        raw = json.dumps(manifest).encode(); files['paper/manifest.json'] = raw
        core = {'paper_addon': {'version': version, 'manifest': 'paper/manifest.json', 'sha256': sha256(raw).hexdigest()}}
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

    def test_current_addon_acquires_design_spec_from_same_pin_and_requires_it(self):
        base, fetch, requests = self.fixture(version='0.2.0')
        result = p.acquire_addon(base, fetch=fetch)
        self.assertIn('paper/PDF_DESIGN.md', result['files'])
        self.assertTrue(all('/' + base.sha + '/' in url for url in requests))
        base, fetch, _ = self.fixture(version='0.2.0', include_design=False)
        with self.assertRaisesRegex(ValueError, 'required protocol member'):
            p.acquire_addon(base, fetch=fetch)

    def test_refresh_binds_the_actual_pdf_design_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            members = {'paper/VERSION': p.VERSION + '\n', 'paper/PROTOCOL.md': 'Synthetic protocol',
                'paper/DATA.md': 'Synthetic data contract', 'paper/PDF_DESIGN.md': 'Synthetic desktop design',
                '.agents/skills/digr-paper/SKILL.md': 'Synthetic skill',
                '.agents/skills/digr-paper/agents/openai.yaml': 'Synthetic configuration'}
            for name, text in members.items():
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding='utf-8')
            (root / 'codex').mkdir(); (root / 'codex/manifest.json').write_text('{}', encoding='utf-8')
            p.refresh_addon(root)
            manifest = p._read(root / 'paper/manifest.json')
            self.assertEqual(manifest['pdf_design'], 'paper/PDF_DESIGN.md')
            self.assertEqual(manifest['file_sha256']['paper/PDF_DESIGN.md'],
                             sha256((root / 'paper/PDF_DESIGN.md').read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
