"""Check growing Paper Pool snapshots without supplied research data."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import tempfile
import unittest

from runtime import codex_paper_pool as legacy, codex_paper_pool_index as index
from test_codex_paper_pool_catalog import example


class IndexedPaperPoolTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.binding = self.root / 'paper-pool.json'
        self.database = self.root / 'paper-pool.sqlite3'
        self.first = example('P0001', 'MIMO scheduling', ['句子甲 x。', 'Edge computing affects wireless latency.'],
                             '队列建模')
        self.sources = [self.write(role, [row]) for role, row in zip(legacy.SOURCES, self.first)]
        self.legacy = legacy.bind_catalog(self.binding, *self.sources)
        self.initial = index.migrate(self.database, self.binding)

    def write(self, name, records):
        path = self.root / f'{name}.jsonl'
        path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in records), encoding='utf-8')
        return path

    def author(self, identity, keyword):
        return example(identity, f'Paper about {keyword}',
                       [f'{keyword} informs the design.', 'An experimentally distinct sample.'],
                       '性能调度')[0]

    def test_migration_keeps_identity_and_rank_for_short_and_multilingual_queries(self):
        self.assertEqual(self.initial['corpus_fingerprint'], self.legacy['corpus_fingerprint'])
        for terms in (['MIMO'], ['甲'], ['x'], ['句子'], ['边缘计算', '时延'], ['队列'], ['no-match']):
            with self.subTest(terms=terms):
                before = legacy.search_catalog(self.binding, terms)
                current = index.search(self.database, terms)
                self.assertEqual(current['total_matches'], before['total_matches'])
                for result in current['results']:
                    locator = result['evidence']['locator']
                    self.assertEqual(locator.pop('batch'), 1)
                    self.assertEqual(locator.pop('abstract_file_sha256'), self.legacy['source_sha256']['abstracts'])
                self.assertEqual(current['results'], before['results'])

    def test_abstract_only_append_preserves_old_snapshots_and_can_be_retried(self):
        batch = self.write('new', [self.author('P5001', 'growing')])
        latest = index.append(self.database, abstracts=batch)
        self.assertEqual(latest['counts'], {'papers': 2, 'abstracts': 2, 'parents': 1, 'extractions': 1})
        self.assertNotEqual(latest['corpus_fingerprint'], self.initial['corpus_fingerprint'])
        previous = index.search(self.database, ['growing'], fingerprint=self.initial['corpus_fingerprint'])
        self.assertEqual(previous['total_matches'], 0)
        self.assertEqual(index.search(self.database, ['growing'])['results'][0]['paper_id'], 'P5001')
        self.assertEqual(index.show(self.database, 'P5001')['paper']['derived']['nine_dimensions'], {})
        self.assertEqual(index.show(self.database, 'P5001')['paper']['evidence']['locator']['batch'], 2)
        with self.assertRaisesRegex(ValueError, 'selected snapshot'):
            index.show(self.database, 'P5001', self.initial['corpus_fingerprint'])
        replay = index.append(self.database, abstracts=batch)
        self.assertTrue(replay['already_present'])
        self.assertEqual(replay['corpus_fingerprint'], latest['corpus_fingerprint'])
        self.assertEqual(replay['appended'], 0)

    def test_rejecting_a_late_duplicate_rolls_back_every_record_and_index_entry(self):
        batch = self.write('mixed', [self.author('P6000', 'phantomneedle'), self.author('P0001', 'conflict')])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            index.append(self.database, abstracts=batch)
        self.assertEqual(index.check(self.database)['corpus_fingerprint'], self.initial['corpus_fingerprint'])
        self.assertEqual(index.search(self.database, ['phantomneedle'])['total_matches'], 0)

    def test_archived_evidence_is_indexed_and_audit_detects_later_source_changes(self):
        self.assertTrue(index.audit(self.database)['source_hashes_verified'])
        self.sources[0].write_text('modified outside ingestion\n', encoding='utf-8')
        self.assertIn('wireless latency', index.show(self.database, 'P0001')['paper']['evidence']['abstract'])
        with self.assertRaisesRegex(ValueError, 'indexed snapshot'):
            index.audit(self.database)

    def test_concurrent_retry_imports_one_batch(self):
        batch = self.write('same', [self.author('P5001', 'parallel')])
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: index.append(self.database, abstracts=batch), range(2)))
        self.assertEqual(sorted(item['appended'] for item in results), [0, 1])
        self.assertEqual(index.check(self.database)['batches'], 2)
