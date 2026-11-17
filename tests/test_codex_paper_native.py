"""Synthetic source, public-ledger and PDF contracts; no model or mail call."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from runtime import codex_consult as consult
from runtime import codex_paper as paper
from runtime.codex_session import create_session
from tests.test_codex_paper import PARAMETERS, PdfWriter


ROOT = Path(__file__).resolve().parents[1]


class NativePaperFixture:
    def setUp(self):
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='paper-native-test-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.task, self.batch, self.root = self.fixture(getattr(self, 'core_version', '0.11.0'))
        self.source = self.base / 'original.pdf'
        writer = PdfWriter()
        writer.add_blank_page(width=210 * 72 / 25.4, height=297 * 72 / 25.4)
        with self.source.open('wb') as stream:
            writer.write(stream)
        self.mutate(paper.register_source, {'id': 'original', 'path': str(self.source),
            'pages': 1, 'identity': 'Synthetic original source, not a real paper'}, 'source')
        self.mapping = {'mapping_contract': paper.NATIVE_MAPPING_CONTRACT,
            'coverage': [
                {'id': 'request', 'anchor': {'source': 'original', 'page': 1, 'label': 'system event'},
                 'location': 'A request through the machine', 'disposition': 'explained'},
                {'id': 'proof', 'anchor': {'source': 'original', 'page': 1, 'label': 'theorem and caveat'},
                 'location': 'Why the contradiction matters', 'disposition': 'context',
                 'note': 'Synthetic source-derived note; no fixed content category is required.'}]}
        self.markdown = self.base / 'guide.md'
        self.markdown.write_text('## A request through the machine\nSynthetic exposition.\n\n'
                                 '## Why the contradiction matters\nSynthetic argument.\n', encoding='utf-8')
        self.qa = self.base / 'qa.json'
        self.qa.write_text(json.dumps({'pages': 1, 'rendered_pages': 1, 'formula_errors': [],
                                      'overflow': [], 'missing_images': []}), encoding='utf-8')
        self.review = self.base / 'review.md'
        self.review.write_text('Synthetic fixture only; not evidence of actual paper fidelity or visual review.',
                               encoding='utf-8')
        self.payload = {'markdown': str(self.markdown), 'pdfs': [str(self.source)],
            'qa': str(self.qa), 'review': str(self.review),
            'responsibility_report': deepcopy(PARAMETERS)}

    def fixture(self, version):
        folder = self.base / version
        folder.mkdir()
        request = folder / 'request.txt'
        request.write_text('DIGRP：synthetic paper authoring fixture', encoding='utf-8')
        task = folder / 'task'
        pin = version + '@' + 'c' * 40
        create_session(task, request=request, p_run=pin, visits_path=folder / 'visits', run_id=version)
        batch = folder / 'batch'
        paper.initialize(batch, p_run=pin, authorization=request, source_ref='synthetic-user', task_root=task)
        root = Path(paper.add_paper(batch, paper_id='first', title='Synthetic source', line='M01',
            owner='native-host', parameters=PARAMETERS)['paper_root'])
        return task, batch, root

    def mutate(self, operation, payload, operation_id):
        return operation(self.root, payload, expected_revision=paper._load(self.root)['revision'],
                         operation_id=operation_id)

    def mapped(self):
        self.mutate(paper.map_paper, self.mapping, 'map')

    def public_exchange(self, exchange_id='paper-public', *, root=None, status='COMPLETE'):
        """Construct a labelled historical fixture using the real request preparer.

        No service is contacted and this helper does not claim real Sonnet work.
        """
        input_path = self.base / (exchange_id + '-input.txt')
        input_path.write_text('Synthetic actual request: choose the paper-specific questions and reading route.',
                              encoding='utf-8')
        consult.prepare_request(self.task, input_path=input_path, exchange_id=exchange_id,
                                paper_root=root or self.root, max_tokens=256)
        directory = self.task / 'consult' / 'exchanges' / exchange_id
        public = b'SYNTHETIC PUBLIC FIXTURE: begin with the system event, then explain the surprising contradiction.\n'
        (directory / 'public.md').write_bytes(public)
        path = directory / 'attempt.json'
        attempt = json.loads(path.read_text(encoding='utf-8'))
        attempt.update(transport_status='RESPONDED', public_status=status,
                       public_sha256=sha256(public).hexdigest(), public_byte_length=len(public),
                       response_model=consult.DEFAULT_MODEL,
                       billing_status='UNKNOWN', reserved_usd=.1)
        path.write_text(json.dumps(attempt, ensure_ascii=False), encoding='utf-8')
        return directory

    def candidate(self, exchange_id='paper-public', operation_id='candidate'):
        self.payload['consultation'] = {'exchange_id': exchange_id,
            'scope': 'Synthetic public direction applies; this is not a provider or teaching result.'}
        return self.mutate(paper.prepare_candidate, self.payload, operation_id)


@unittest.skipUnless(PdfWriter, 'configured Python with pypdf required')
class NativePaperTests(NativePaperFixture, unittest.TestCase):
    def test_flat_source_map_allows_paper_specific_chapters_without_role_or_category_arrays(self):
        self.mapped()
        directory = self.public_exchange()
        self.candidate()
        value = paper._load(self.root)
        self.assertEqual(value['mapping'], self.mapping)
        self.assertEqual(value['authoring_contract'], 'sonnet-native-v1')
        self.assertEqual(value['mapping_contract'], 'source-bound-native-v1')
        self.assertEqual(value['candidate']['consultation']['exchange_id'], 'paper-public')
        self.assertEqual(value['candidate']['consultation']['model_identity'], {
            'status': 'CONFIRMED', 'requested_model': consult.DEFAULT_MODEL,
            'response_model': consult.DEFAULT_MODEL})
        self.assertEqual(value['candidate']['consultation']['guidance']['sha256'],
                         sha256((directory / 'public.md').read_bytes()).hexdigest())
        before = (self.root / 'paper.json').read_bytes()
        self.assertEqual(paper.inspect(self.root)['status'], 'READY_LOCAL')
        self.assertEqual((self.root / 'paper.json').read_bytes(), before)

    def test_coverage_retains_source_bounds_unique_ids_and_real_manuscript_locations(self):
        for label, change, message in [
                ('page', lambda m: m['coverage'][0]['anchor'].update(page=2), 'physical page'),
                ('duplicate', lambda m: m['coverage'].append(deepcopy(m['coverage'][0])), 'duplicate coverage'),
                ('legacy-parts', lambda m: m.update(parts={part: 'Unused' for part in paper.PARTS}), 'legacy parts')]:
            invalid = deepcopy(self.mapping)
            change(invalid)
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, message):
                self.mutate(paper.map_paper, invalid, label)
        self.mapped()
        self.public_exchange()
        self.markdown.write_text('## A request through the machine\nOnly one mapped heading.\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'absent from Markdown'):
            self.candidate()

    def test_handwritten_guidance_and_partial_or_other_paper_public_are_not_authoring(self):
        self.mapped()
        hand = self.base / 'self-written-guidance.md'
        hand.write_text('This caller-written file is not a ledger exchange.', encoding='utf-8')
        self.payload['consultation'] = {'guidance': str(hand), 'source_ref': 'self-claim', 'scope': 'Synthetic'}
        with self.assertRaisesRegex(ValueError, 'exchange_id'):
            self.mutate(paper.prepare_candidate, self.payload, 'handwritten')
        self.public_exchange('partial', status='PARTIAL')
        with self.assertRaisesRegex(ValueError, 'COMPLETE'):
            self.candidate('partial', 'partial-candidate')
        other = Path(paper.add_paper(self.batch, paper_id='other', title='Another synthetic paper',
            line='M02', owner='another-native-host', parameters=PARAMETERS)['paper_root'])
        self.public_exchange('other-public', root=other)
        with self.assertRaisesRegex(ValueError, 'scope differs'):
            self.candidate('other-public', 'other-candidate')

    def test_same_public_work_can_support_real_revision_and_billing_update_without_new_signoff(self):
        self.mapped()
        directory = self.public_exchange()
        self.candidate()
        first = paper.inspect(self.root)['candidate_id']
        attempt_path = directory / 'attempt.json'
        attempt = json.loads(attempt_path.read_text(encoding='utf-8'))
        attempt.update(billing_status='KNOWN', known_cost_usd=.02, reserved_usd=0)
        attempt_path.write_text(json.dumps(attempt), encoding='utf-8')
        self.assertEqual(paper.inspect(self.root)['status'], 'READY_LOCAL')
        self.assertEqual(paper.inspect(self.root)['candidate_id'], first)
        self.markdown.write_text(self.markdown.read_text(encoding='utf-8') + '\nA checked local correction.\n',
                                 encoding='utf-8')
        self.assertEqual(paper.inspect(self.root)['status'], 'STALE_OR_UNAVAILABLE')
        self.candidate(operation_id='revised-candidate')
        self.assertNotEqual(paper.inspect(self.root)['candidate_id'], first)
        self.assertEqual(paper._load(self.root)['candidate']['consultation']['exchange_id'], 'paper-public')
        (directory / 'public.md').write_text('Changed public original', encoding='utf-8')
        self.assertEqual(paper.inspect(self.root)['status'], 'STALE_OR_UNAVAILABLE')

    def test_missing_or_wrong_observed_model_cannot_be_sonnet_authorship_but_public_and_cost_remain(self):
        self.mapped()
        for exchange_id, model in [('missing-model', None), ('wrong-model', 'openai/gpt-5')]:
            with self.subTest(exchange=exchange_id):
                directory = self.public_exchange(exchange_id)
                attempt_path = directory / 'attempt.json'
                attempt = json.loads(attempt_path.read_text(encoding='utf-8'))
                if model is None:
                    attempt.pop('response_model')
                else:
                    attempt['response_model'] = model
                attempt_path.write_text(json.dumps(attempt), encoding='utf-8')
                public_before = (directory / 'public.md').read_bytes()
                observed = consult.inspect_exchange(self.task, exchange_id)
                self.assertEqual(observed['exchange']['public_status'], 'COMPLETE')
                self.assertEqual(observed['public_integrity'], 'MATCH')
                self.assertEqual(observed['paper_model_identity']['status'], 'UNCONFIRMED')
                with self.assertRaisesRegex(ValueError, 'model identity is unconfirmed'):
                    self.candidate(exchange_id, exchange_id + '-candidate')
                self.assertEqual((directory / 'public.md').read_bytes(), public_before)
                self.assertEqual(consult.inspect_exchange(self.task, exchange_id)['exchange']['reserved_usd'], .1)
                self.assertEqual(paper.inspect(self.root)['status'], 'DRAFT')
        directory = self.public_exchange('confirmed-model')
        self.candidate('confirmed-model', 'confirmed-model-candidate')
        self.assertEqual(paper.inspect(self.root)['status'], 'READY_LOCAL')
        attempt_path = directory / 'attempt.json'
        attempt = json.loads(attempt_path.read_text(encoding='utf-8'))
        attempt['response_model'] = 'openai/gpt-5'
        attempt_path.write_text(json.dumps(attempt), encoding='utf-8')
        self.assertEqual(consult.inspect_exchange(self.task, 'confirmed-model')['public_integrity'], 'MATCH')
        self.assertEqual(paper.inspect(self.root)['status'], 'STALE_OR_UNAVAILABLE')

    def test_new_installation_initializes_old_pins_with_their_exact_content_contracts(self):
        for version, addon in [('0.10.0', '0.4.0'), ('0.9.0', '0.3.0')]:
            with self.subTest(version=version):
                task, batch, root = self.fixture(version)
                index = paper._read(batch / 'batch.json')
                value = paper._load(root)
                self.assertEqual(index['addon_version'], addon)
                self.assertEqual(value['addon_version'], addon)
                self.assertNotIn('authoring_contract', index)
                self.assertNotIn('authoring_contract', value)
                if version == '0.10.0':
                    self.assertEqual(value['mapping_contract'], 'integrated-functions-v1')
                    session = paper._read(task / 'session.json')
                    self.assertEqual(session['consult_addons'][0]['version'], '0.4.0')


@unittest.skipUnless(PdfWriter, 'configured Python with pypdf required')
class NativePaperPatchTests(NativePaperFixture, unittest.TestCase):
    core_version = '0.11.1'

    def test_patch_public_work_binds_candidate_and_continues_the_same_scope(self):
        self.mapped()
        self.public_exchange()
        self.candidate()
        self.assertEqual(paper.inspect(self.root)['status'], 'READY_LOCAL')
        scope = paper._load(self.root)['candidate']['consultation']['authoring_scope']
        self.assertEqual(scope['addon_version'], getattr(self, 'addon_version', '0.5.1'))
        followup = self.base / 'followup.txt'
        followup.write_text('Synthetic next source request in this same paper.', encoding='utf-8')
        result = consult.prepare_request(self.task, input_path=followup,
                                         exchange_id='patch-followup', continue_from='paper-public',
                                         paper_root=self.root, max_tokens=256)
        self.assertEqual(result['exchange']['authoring_scope'], scope)
        request = json.loads(Path(result['request_path']).read_text(encoding='utf-8'))
        self.assertTrue(any(message['role'] == 'assistant' and 'SYNTHETIC PUBLIC FIXTURE' in message['content']
                            for message in request['messages']))


class LogicalNativePaperTests(NativePaperPatchTests):
    core_version = '0.12.0'
    addon_version = '0.5.2'


class LiveRelayNativePaperTests(NativePaperPatchTests):
    core_version = '0.12.1'
    addon_version = '0.5.3'


if __name__ == '__main__':
    unittest.main()
