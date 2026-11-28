"""Paper Pool catalog tests use synthetic abstracts and analyst notes."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from runtime import codex_paper_pool as pool


def example(identity, title, sentences, statement, *, provenance='author_abstract'):
    abstract = ' '.join(sentences)
    source_sha = sha256(abstract.encode('utf-8')).hexdigest()
    start, chunks = 0, []
    for number, sentence in enumerate(sentences, 1):
        end = start + len(sentence)
        chunks.append({'n': number, 'offset': [start, end], 'text': sentence})
        start = end + 1
    metadata = {
        'id': identity,
        'paper_id': 'publication-' + identity,
        'title': title,
        'source_url': f'https://example.test/papers/{identity}',
        'publication_date': '2026-01-01',
        'topic': 'wireless systems',
        'archive_path': 'fixture.json.gz',
        'archive_row': int(identity[1:]),
    }
    dimensions = {name: {'status': 'evidence_missing', 'reason': 'No author-abstract evidence.',
                         'components': []}
                  for name in pool.DIMENSIONS}
    dimensions['modeling'] = {
        'status': 'populated',
        'components': [{'statement': statement, 'provenance': provenance,
                        'author_sentence_ids': [2], 'offsets': [chunks[1]['offset']]}],
    }
    return (
        {**metadata, 'abstract': abstract, 'abstract_sha256': source_sha, 'chunks': chunks},
        {**metadata, 'author_abstract_sha256': source_sha, 'genotype': dimensions},
        {**metadata, 'abstract_sha256': source_sha, 'source_level': 'author_abstract',
         'type': 'M', 'type_description': 'mathematical model',
         'original_relation': 'Estimating errors with a queue model.',
         'scope_or_limit': 'The model describes one queue.',
         'transfer_or_specific_disposition': 'Use the bound before deciding whether to retry.',
         'anchors': [chunks[1]]},
    )


class PaperPoolCatalogTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.base = Path(folder.name)
        self.binding = self.base / 'pool.json'
        self.paths = [self.base / f'{role}.jsonl' for role in pool.SOURCES]
        first = example('P0001', 'Pilot-aided MIMO scheduling',
                        ['Pilot-aided scheduling reduces estimation errors.',
                         'A model of edge computing determines the latency.'],
                        '边缘计算中的时延控制', provenance='analyst_inference')
        second = example('P0002', 'A Mimosa plant radio',
                         ['A transmitter monitors plant health.',
                          'The system uses equally spaced pilots without MIMO processing.'],
                         '采样量随装置变化')
        self.rows = [[first[0], second[0]], [second[1], first[1]], [first[2], second[2]]]
        self.write_rows()

    def write_rows(self, rows=None):
        for path, records in zip(self.paths, rows if rows is not None else self.rows):
            path.write_text(''.join(json.dumps(record, ensure_ascii=False) + '\n' for record in records),
                            encoding='utf-8')

    def bind(self):
        return pool.bind_catalog(self.binding, *self.paths)

    def test_binding_joins_by_id_and_lookup_reproduces_the_author_abstract(self):
        source_bytes = {path: path.read_bytes() for path in self.paths}
        bound = self.bind()
        self.assertEqual(pool.check_catalog(self.binding), bound)
        self.assertEqual(bound['counts'], {'papers': 2, 'abstracts': 2, 'parents': 2, 'extractions': 2})
        self.assertEqual(bound['scope'], 'author_abstract')
        self.assertNotIn(str(self.base), json.dumps(bound))

        shown = pool.show_paper(self.binding, 'p0001')
        self.assertEqual(shown['corpus_fingerprint'], bound['corpus_fingerprint'])
        record = shown['paper']
        self.assertEqual(record['paper_id'], 'P0001')
        self.assertEqual(record['publication_id'], 'publication-P0001')
        self.assertEqual(record['source_url'], 'https://example.test/papers/P0001')
        evidence = record['evidence']
        self.assertEqual(evidence['locator']['line'], 1)
        self.assertEqual(evidence['locator']['abstract_sha256'],
                         sha256(evidence['abstract'].encode('utf-8')).hexdigest())
        for chunk in evidence['chunks'] + evidence['excerpts']:
            start, end = chunk['offset']
            self.assertEqual(evidence['abstract'][start:end], chunk['text'])
        component = record['derived']['nine_dimensions']['modeling']['components'][0]
        self.assertEqual(component['provenance'], 'analyst_inference')
        self.assertEqual(component['statement'], '边缘计算中的时延控制')
        self.assertEqual(source_bytes, {path: path.read_bytes() for path in self.paths})

    def test_search_ranks_title_matches_and_preserves_source_coverage(self):
        report = self.bind()
        result = pool.search_catalog(self.binding, ['MIMO'], limit=1)
        self.assertEqual(result['corpus_fingerprint'], report['corpus_fingerprint'])
        self.assertEqual((result['returned'], result['total_matches']), (1, 2))
        self.assertEqual(result['results'][0]['paper_id'], 'P0001')
        self.assertEqual(result['results'][0]['matches'], [{'term': 'MIMO', 'fields': ['title']}])

        result = pool.search_catalog(self.binding, ['pilot aided', 'EDGE COMPUTING', 'pilot-aided'])
        self.assertEqual(result['query'], ['pilot aided', 'EDGE COMPUTING'])
        self.assertEqual(result['total_matches'], 1)
        hit = result['results'][0]
        self.assertEqual(hit['paper_id'], 'P0001')
        excerpts = hit['evidence']['excerpts']
        self.assertEqual({term for excerpt in excerpts for term in excerpt['matched_terms']},
                         {'pilot aided', 'EDGE COMPUTING'})
        self.assertEqual(pool.search_catalog(self.binding, ['mimos'])['returned'], 0)

    def test_search_exposes_chinese_and_mixed_language_match_provenance(self):
        self.bind()
        hit = pool.search_catalog(self.binding, ['时延控制', 'MIMO'])['results'][0]
        self.assertEqual(hit['matches'], [
            {'term': '时延控制', 'fields': ['nine_dimensions.modeling']},
            {'term': 'MIMO', 'fields': ['title']},
        ])
        comment = hit['derived']['nine_dimensions'][0]
        self.assertEqual(comment['matched_terms'], ['时延控制'])
        self.assertEqual(comment['provenance'], 'analyst_inference')
        evidence = hit['evidence']['excerpts'][0]
        self.assertEqual(evidence['n'], comment['author_sentence_ids'][0])
        self.assertEqual(evidence['offset'], comment['offsets'][0])
        self.assertEqual(evidence['matched_terms'], [])

    def test_bilingual_variant_discloses_actual_terms_in_the_unchanged_quotation(self):
        self.bind()
        result = pool.search_catalog(self.binding, ['边缘计算'])
        self.assertEqual(result['total_matches'], 1)
        hit = result['results'][0]
        self.assertEqual(hit['matches'], [{
            'term': '边缘计算', 'fields': ['author_abstract', 'nine_dimensions.modeling'],
            'matched_variants': {'author_abstract': ['edge computing']},
        }])
        quotation = hit['evidence']['excerpts'][0]
        self.assertEqual(quotation['text'], 'A model of edge computing determines the latency.')
        self.assertEqual(quotation['matched_variants'], {'边缘计算': ['edge computing']})

    def test_zero_result_is_a_valid_read_and_malformed_request_is_an_error(self):
        bound = self.bind()
        search = pool.search_catalog(self.binding, ['边缘计算', 'qzxnonexistent'])
        self.assertEqual(search['corpus_fingerprint'], bound['corpus_fingerprint'])
        self.assertEqual((search['returned'], search['total_matches'], search['results']), (0, 0, []))
        for terms in ([], ['   '], ['+++']):
            with self.subTest(terms=terms), self.assertRaises(pool.PaperPoolCatalogError):
                pool.search_catalog(self.binding, terms)
        with self.assertRaisesRegex(pool.PaperPoolCatalogError, 'positive integer'):
            pool.search_catalog(self.binding, ['MIMO'], limit=0)
        with self.assertRaisesRegex(pool.PaperPoolCatalogError, 'no record'):
            pool.show_paper(self.binding, 'P9999')

    def test_exact_byte_changes_require_an_explicit_rebind(self):
        bound = self.bind()
        row_bytes = self.paths[0].read_bytes()
        self.paths[0].write_bytes(row_bytes.replace(b'{', b'{ ', 1))
        for action in (pool.check_catalog, lambda path: pool.search_catalog(path, ['MIMO']),
                       lambda path: pool.show_paper(path, 'P0001')):
            with self.assertRaisesRegex(pool.PaperPoolCatalogError, 'bound snapshot'):
                action(self.binding)
        rebound = self.bind()
        self.assertNotEqual(rebound['corpus_fingerprint'], bound['corpus_fingerprint'])
        self.assertEqual(rebound, pool.check_catalog(self.binding))

    def test_rejects_duplicates_before_publishing_a_binding(self):
        rows = deepcopy(self.rows)
        rows[1].append(deepcopy(rows[1][0]))
        self.write_rows(rows)
        with self.assertRaisesRegex(pool.PaperPoolCatalogError, 'duplicate Paper Pool ID P0002'):
            self.bind()
        self.assertFalse(self.binding.exists())

        rows = deepcopy(self.rows)
        for records in rows:
            for record in records:
                record['paper_id'] = 'ambiguous-publication'
        self.write_rows(rows)
        with self.assertRaisesRegex(pool.PaperPoolCatalogError, 'duplicate publication ID'):
            self.bind()
        self.assertFalse(self.binding.exists())

        rows = deepcopy(self.rows)
        for field in ('abstract', 'abstract_sha256', 'chunks'):
            rows[0][1][field] = rows[0][0][field]
        self.write_rows(rows)
        with self.assertRaisesRegex(pool.PaperPoolCatalogError, 'duplicate abstract SHA-256'):
            self.bind()

    def test_rejects_inconsistent_inventory_metadata_hashes_and_anchors(self):
        invalid = (
            (1, 0, 'id', 'P0003', 'inventory differs'),
            (2, 0, 'title', 'Another paper', 'disagrees on title'),
            (1, 0, 'author_abstract_sha256', '0' * 64, 'author_abstract_sha256'),
            (0, 0, 'abstract', 'An alleged replacement.', 'abstract SHA-256 mismatch'),
            (2, 0, 'anchors', [{'n': 2, 'offset': [0, 5], 'text': 'wrong'}], 'extraction anchor'),
        )
        for role, index, key, value, expected in invalid:
            with self.subTest(key=key):
                rows = deepcopy(self.rows)
                rows[role][index][key] = value
                self.write_rows(rows)
                with self.assertRaisesRegex(pool.PaperPoolCatalogError, expected):
                    self.bind()
                self.assertFalse(self.binding.exists())
        rows = deepcopy(self.rows)
        rows[1][1]['genotype']['modeling']['components'][0]['offsets'] = [[0, 5]]
        self.write_rows(rows)
        with self.assertRaisesRegex(pool.PaperPoolCatalogError, 'component anchors'):
            self.bind()

    def test_invalid_rebind_preserves_previously_valid_binding(self):
        self.bind()
        payload = self.binding.read_bytes()
        invalid_extraction = self.base / 'invalid.jsonl'
        invalid_extraction.write_text('{}\n', encoding='utf-8')
        with self.assertRaises(pool.PaperPoolCatalogError):
            pool.bind_catalog(self.binding, *self.paths[:2], invalid_extraction)
        self.assertEqual(self.binding.read_bytes(), payload)
        self.assertEqual(pool.check_catalog(self.binding)['counts']['papers'], 2)

    def test_rejects_dangerous_local_path_without_opening_it(self):
        source = self.base / 'link' / 'abstracts.jsonl'
        actual_stat = Path.lstat
        reparse = SimpleNamespace(st_mode=stat.S_IFDIR,
                                  st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)

        def fake_stat(path):
            if path == source.parent:
                return reparse
            self.assertNotEqual(path, source)
            return actual_stat(path)

        with patch.object(Path, 'lstat', fake_stat), patch.object(pool.codex_io, 'read_bytes') as read:
            with self.assertRaisesRegex(pool.PaperPoolCatalogError, 'reparse paths'):
                pool.bind_catalog(self.binding, source, *self.paths[1:])
            read.assert_not_called()
        with self.assertRaisesRegex(pool.PaperPoolCatalogError, 'paths must be distinct'):
            pool.bind_catalog(self.paths[0], *self.paths)
