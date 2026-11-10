from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest

from runtime import codex_preprint as p
from runtime import codex_preprint_sources as sources

ROOT = Path(__file__).resolve().parents[1]


class PreprintSourceTests(unittest.TestCase):
    def setUp(self):
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='esp-source-test-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.base = self.work / 'evidence'
        self.base.mkdir()
        self.root = self.work / 'book'
        self.out = self.work / 'archive'
        self.spec = {'id': 'constructed-source-fixture', 'title': 'Constructed, not native evidence',
                     'public_scene': 'A shop is closing.',
                     'actors': [{'id': 'jo', 'name': 'Jo', 'outward': 'Dry', 'inner': 'Pride'},
                                {'id': 'len', 'name': 'Len', 'outward': 'Warm', 'inner': 'Fear'}]}
        p.initialize(self.root, self.spec)
        self.serial = 0
        self.first = self.native('The door’s still open—come in.', save_input=False)
        self.second = self.native('It is cold outside.', save_input=True, absolute=True, kind='inner')

    def write_json(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def native(self, text, save_input=False, absolute=False, kind='speech', root=None, source_ref=None, base=None):
        self.serial += 1
        root = root or self.root
        base = base or self.base
        packet = p.actor_packet(root, 'jo', 'inner' if kind == 'inner' else 'outward')
        name = 'return-' + str(self.serial) + '.json'
        self.write_json(base / name, {'actual_native_return': text, 'executor': 'constructed-context'})
        ref = source_ref or ((base / name).as_posix() if absolute else name)
        event = {'kind': kind, 'actor': 'jo', 'text': text, 'executor': 'constructed-context',
                 'source_ref': ref, 'packet_sha256': packet['packet_sha256']}
        if save_input:
            input_name = 'input-' + str(self.serial) + '.json'
            self.write_json(base / input_name, packet)
            event['input_ref'] = input_name
        return p.append_event(root, event, expected_revision=p.load(root)['revision'],
                              operation_id='fixture-' + str(self.serial))

    def archive(self):
        return sources.archive_sources(self.root, self.base, self.out)

    def archive_bytes(self, root):
        manifest = p.read(root / sources.MANIFEST)
        names = {'preprint.json', sources.MANIFEST} | {r['path'] for r in manifest['records'].values()}
        return {name: (root / name).read_bytes() for name in names}

    def test_continued_work_copy_rearchives_old_and_new_records_with_old_base_offline(self):
        self.archive()
        original = self.archive_bytes(self.out)
        continued = self.work / 'continued-work-copy'
        for name, data in original.items():
            target = continued / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        offline = self.work / 'old-base-offline'
        for path in (self.base, offline):
            self.assertTrue(path.resolve().is_relative_to(self.work.resolve()))
        self.base.rename(offline)
        new_base = self.work / 'new-evidence'
        new_base.mkdir()
        self.write_json(new_base / 'return-1.json', {'actual_native_return': 'An external replacement must lose.',
                                                   'executor': 'constructed-context'})
        new_event = self.native('I can close the door now.', save_input=True, root=continued, base=new_base)
        stale = sources.audit_sources(continued)
        self.assertEqual(stale['status'], 'INVALID_ARCHIVE')
        self.assertIn('binding mismatch', stale['errors'][0])
        next_out = self.work / 'continued-archive'
        result = sources.archive_sources(continued, new_base, next_out)
        self.assertTrue(result['valid'])
        self.assertEqual(result['native_return_text_checked'],
                         [self.first['event_id'], self.second['event_id'], new_event['event_id']])
        self.assertEqual(result['saved_packet_checked'], [self.second['event_id'], new_event['event_id']])
        self.assertEqual(len(result['reused_local_refs']), 3)
        self.assertEqual([x['event_id'] for x in result['missing_inputs']], [self.first['event_id']])
        self.assertEqual(self.archive_bytes(self.out), original)
        self.assertEqual((continued / sources.MANIFEST).read_bytes(), original[sources.MANIFEST])
        self.assertEqual(sources.audit_sources(continued)['status'], 'INVALID_ARCHIVE')
        self.assertTrue(sources.audit_sources(next_out)['valid'])
        self.assertFalse(self.base.exists())

    def test_unchanged_archive_rearchives_without_opening_missing_external_base(self):
        self.archive()
        result = sources.archive_sources(self.out, self.work / 'missing-base', self.work / 'another-archive')
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['reused_local_refs']), 3)

    def test_corrupt_local_record_is_rejected_instead_of_external_fallback(self):
        self.archive()
        manifest = p.read(self.out / sources.MANIFEST)
        path = self.out / manifest['records']['return-1.json']['path']
        with path.open('ab') as handle:
            handle.write(b' ')
        next_out = self.work / 'must-not-fall-back'
        with self.assertRaisesRegex(ValueError, 'historical record bytes changed'):
            sources.archive_sources(self.out, self.base, next_out)
        self.assertFalse(next_out.exists())

    def test_local_manifest_baseline_paths_formats_and_retained_uses_are_checked(self):
        self.archive()
        original = p.read(self.out / sources.MANIFEST)
        cases = ('baseline', 'traversal', 'format', 'foreign-use', 'duplicate-use')
        for case in cases:
            manifest = json.loads(json.dumps(original))
            record = manifest['records']['return-1.json']
            if case == 'baseline':
                manifest['source']['baseline_id'] = 'a-different-book'
            elif case == 'traversal':
                record['path'] = '../outside.json.raw'
            elif case == 'format':
                record['format'] = 'txt'
            elif case == 'foreign-use':
                record['uses'] = [{'event_id': 'not-a-current-event', 'field': 'source_ref'}]
            else:
                record['uses'] *= 2
            self.write_json(self.out / sources.MANIFEST, manifest)
            next_out = self.work / ('rejected-' + case)
            with self.subTest(case=case), self.assertRaises(ValueError):
                sources.archive_sources(self.out, self.base, next_out)
            self.assertFalse(next_out.exists())

    def test_only_required_local_records_are_opened(self):
        self.archive()
        manifest = p.read(self.out / sources.MANIFEST)
        manifest['records']['unselected.json'] = {'path': '../never-open-this', 'sha256': 'invalid',
                                                 'uses': [{'event_id': 'unselected', 'field': 'source_ref'}]}
        self.write_json(self.out / sources.MANIFEST, manifest)
        next_out = self.work / 'selected-only'
        result = sources.archive_sources(self.out, self.work / 'missing-base', next_out)
        self.assertTrue(result['valid'])
        self.assertNotIn('unselected.json', p.read(next_out / sources.MANIFEST)['records'])

    def test_linked_local_record_is_rejected(self):
        self.archive()
        manifest = p.read(self.out / sources.MANIFEST)
        path = self.out / manifest['records']['return-1.json']['path']
        outside = self.work / 'outside-return.json'
        outside.write_bytes(path.read_bytes())
        saved = self.work / 'saved-original-record.raw'
        for target in (path, saved):
            self.assertTrue(target.resolve().is_relative_to(self.work.resolve()))
        path.rename(saved)
        try:
            os.symlink(outside, path)
        except OSError:
            os.link(outside, path)
        next_out = self.work / 'linked-local-rejected'
        with self.assertRaisesRegex(ValueError, 'link|reparse'):
            sources.archive_sources(self.out, self.base, next_out)
        self.assertFalse(next_out.exists())

    def test_moved_archive_audits_with_original_base_offline_and_does_not_rewrite_history(self):
        before = (self.root / 'preprint.json').read_bytes()
        (self.base / 'unselected.pdf').write_bytes(b'Never select this original source.')
        self.write_json(self.base / 'pool.json', {'private': 'Never copy a private pool.'})
        self.write_json(self.base / 'input-1.json', p.actor_packet(self.root, 'jo'))
        result = self.archive()
        self.assertEqual(result['status'], 'VALID_WITH_INPUT_GAPS')
        self.assertEqual((self.root / 'preprint.json').read_bytes(), before)
        self.assertEqual((self.out / 'preprint.json').read_bytes(), before)
        manifest = p.read(self.out / sources.MANIFEST)
        self.assertEqual([x['event_id'] for x in manifest['missing_inputs']], [self.first['event_id']])
        self.assertEqual(result['native_return_text_checked'], [self.first['event_id'], self.second['event_id']])
        self.assertEqual(result['saved_packet_checked'], [self.second['event_id']])
        self.assertFalse(result['identity_authenticated'])
        self.assertEqual(len(list((self.out / 'records').iterdir())), 3)
        moved = self.work / 'moved-archive'
        offline = self.work / 'offline-evidence'
        for path in (self.base, self.out, moved, offline):
            self.assertTrue(path.resolve().is_relative_to(self.work.resolve()))
        self.base.rename(offline)
        self.out.rename(moved)
        audited = sources.audit_sources(moved)
        self.assertTrue(audited['valid'])
        self.assertEqual(audited['native_return_text_checked'], result['native_return_text_checked'])
        self.assertEqual(audited['saved_packet_checked'], result['saved_packet_checked'])
        self.assertEqual(audited['source']['source_file_sha256'], sha256(before).hexdigest())
        self.assertFalse(self.base.exists())

    def test_changed_archived_record_and_snapshot_are_detected(self):
        self.archive()
        manifest = p.read(self.out / sources.MANIFEST)
        name = next(iter(manifest['records'].values()))['path']
        target = self.out / name
        original = target.read_bytes()
        target.write_bytes(original + b' ')
        self.assertEqual(sources.audit_sources(self.out)['status'], 'INVALID_ARCHIVE')
        target.write_bytes(original)
        with (self.out / 'preprint.json').open('ab') as handle:
            handle.write(b'\n')
        self.assertIn('binding mismatch', sources.audit_sources(self.out)['errors'][0])

    def test_raw_envelopes_preserve_crlf_bom_and_explicit_record_formats(self):
        selected = {}
        for name in ('return-1.json', 'return-2.json', 'input-2.json'):
            original = p.read(self.base / name)
            data = (json.dumps(original, ensure_ascii=False, indent=2) + '\n').encode('utf-8').replace(b'\n', b'\r\n')
            if name == 'input-2.json':
                data = b'\xef\xbb\xbf' + data
            (self.base / name).write_bytes(data)
            selected[name] = data
        for name in ('note.txt', 'note.md'):
            data = b'Untouched raw note.\r\nSecond line.\r\n'
            (self.base / name).write_bytes(data)
            selected[name] = data
            p.append_event(self.root, {'kind': 'note', 'text': 'Constructed note reference.', 'source_ref': name},
                           expected_revision=p.load(self.root)['revision'], operation_id=name)
        result = self.archive()
        manifest = p.read(self.out / sources.MANIFEST)
        for ref, record in manifest['records'].items():
            name = Path(ref).name
            self.assertEqual(record['format'], Path(ref).suffix[1:])
            self.assertTrue(record['path'].endswith('.' + record['format'] + '.raw'))
            self.assertEqual((self.out / record['path']).read_bytes(), selected[name])
            self.assertEqual(record['sha256'], sha256(selected[name]).hexdigest())
            self.assertEqual((self.base / name).read_bytes(), selected[name])
        self.assertEqual(result['native_return_text_checked'], [self.first['event_id'], self.second['event_id']])
        self.assertEqual(result['saved_packet_checked'], [self.second['event_id']])

    def rewrite_archived_json(self, manifest, ref, update):
        record = manifest['records'][ref]
        old_path = self.out / record['path']
        value = json.loads(old_path.read_bytes().decode('utf-8-sig'))
        update(value)
        data = json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')
        digest = sha256(data).hexdigest()
        name = 'records/' + digest + '.json.raw'
        target = self.out / name
        for path in (old_path, target):
            self.assertTrue(path.resolve().is_relative_to(self.work.resolve()))
        old_path.rename(target)
        target.write_bytes(data)
        record.update(path=name, sha256=digest)
        self.write_json(self.out / sources.MANIFEST, manifest)

    def test_raw_native_text_comparison_still_runs_after_consistent_file_rehashing(self):
        self.archive()
        manifest = p.read(self.out / sources.MANIFEST)
        self.rewrite_archived_json(manifest, 'return-1.json',
                                   lambda value: value.update(actual_native_return='Different archived words.'))
        self.assertIn('text mismatch', sources.audit_sources(self.out)['errors'][0])

    def test_raw_input_packet_check_still_runs_after_consistent_file_rehashing(self):
        self.archive()
        manifest = p.read(self.out / sources.MANIFEST)
        self.rewrite_archived_json(manifest, 'input-2.json',
                                   lambda value: value['view'].update(scene='Different archived view.'))
        self.assertIn('packet digest mismatch', sources.audit_sources(self.out)['errors'][0])

    def test_record_format_cannot_be_relabelled_to_skip_json_checks(self):
        self.archive()
        manifest = p.read(self.out / sources.MANIFEST)
        record = manifest['records']['return-1.json']
        old_path = self.out / record['path']
        name = 'records/' + record['sha256'] + '.txt.raw'
        target = self.out / name
        for path in (old_path, target):
            self.assertTrue(path.resolve().is_relative_to(self.work.resolve()))
        old_path.rename(target)
        record.update(path=name, format='txt')
        self.write_json(self.out / sources.MANIFEST, manifest)
        self.assertIn('format differs from original reference', sources.audit_sources(self.out)['errors'][0])

    def test_legacy_schema_one_bare_extension_records_remain_readable(self):
        self.archive()
        manifest = p.read(self.out / sources.MANIFEST)
        renamed = set()
        for record in manifest['records'].values():
            current = record['path']
            legacy = current[:-4]
            if current not in renamed:
                source, target = self.out / current, self.out / legacy
                for path in (source, target):
                    self.assertTrue(path.resolve().is_relative_to(self.work.resolve()))
                source.rename(target)
                renamed.add(current)
            record['path'] = legacy
            record.pop('format')
        self.write_json(self.out / sources.MANIFEST, manifest)
        result = sources.audit_sources(self.out)
        self.assertEqual(result['status'], 'VALID_WITH_INPUT_GAPS')
        self.assertEqual(result['native_return_text_checked'], [self.first['event_id'], self.second['event_id']])
        self.assertEqual(result['saved_packet_checked'], [self.second['event_id']])

    def test_changed_native_return_is_not_archived_as_matching_evidence(self):
        path = self.base / 'return-1.json'
        document = p.read(path)
        document['actual_native_return'] = 'Different words.'
        self.write_json(path, document)
        before = (self.root / 'preprint.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'text mismatch'):
            self.archive()
        self.assertFalse(self.out.exists())
        self.assertEqual((self.root / 'preprint.json').read_bytes(), before)

    def test_saved_packet_mismatches_are_rejected(self):
        path = self.base / 'input-2.json'
        packet = p.read(path)
        packet['view']['scene'] = 'A different input.'
        self.write_json(path, packet)
        with self.assertRaisesRegex(ValueError, 'packet digest mismatch'):
            self.archive()
        packet['packet_sha256'] = p.digest(packet['view'])
        self.write_json(path, packet)
        with self.assertRaisesRegex(ValueError, 'differs from event packet'):
            self.archive()
        self.assertFalse(self.out.exists())

    def test_executor_is_checked_as_attribution_without_authenticating_identity(self):
        path = self.base / 'return-1.json'
        document = p.read(path)
        document['executor'] = 'a different attributed context'
        self.write_json(path, document)
        with self.assertRaisesRegex(ValueError, 'executor attribution mismatch'):
            self.archive()
        self.assertFalse(self.out.exists())

    def test_structured_world_source_is_preserved_without_claiming_a_native_text_match(self):
        proposal = {'proposal': 'A drop falls.', 'changes': {'floor': 'wet'},
                    'percepts': [{'to': ['public'], 'text': 'A drop reaches the floor.'}]}
        self.write_json(self.base / 'world.json', proposal)
        event = p.append_event(self.root, {'kind': 'world', 'decision': 'apply',
                                          'source_ref': 'world.json', 'reason': 'A constructed controller decision.',
                                          **proposal}, expected_revision=2, operation_id='world')
        result = self.archive()
        self.assertEqual(result['native_return_text_unchecked'], [event['event_id']])
        self.assertEqual(result['input_ref_uses'], 1)
        self.assertEqual(result['source_ref_uses'], 3)

    def test_paths_outside_base_directories_pdfs_and_pools_are_rejected_before_output(self):
        outside = self.work / 'outside.json'
        self.write_json(outside, {'actual_native_return': 'Fixture', 'executor': 'constructed-context'})
        (self.base / 'original.pdf').write_bytes(b'PDF source must not be copied')
        self.write_json(self.base / 'pool.json', {'private': 'pool'})
        for i, ref in enumerate(('../outside.json', outside.as_posix(), 'original.pdf', 'pool.json', '.', 'toolref:not-a-file')):
            with self.subTest(ref=ref):
                root = self.work / ('case-' + str(i))
                p.initialize(root, self.spec)
                self.native('Fixture', root=root, source_ref=ref)
                out = self.work / ('out-' + str(i))
                with self.assertRaises((ValueError, OSError)):
                    sources.archive_sources(root, self.base, out)
                self.assertFalse(out.exists())

    def test_source_links_are_rejected(self):
        outside = self.work / 'outside.json'
        self.write_json(outside, {'actual_native_return': 'Fixture', 'executor': 'constructed-context'})
        link = self.base / 'linked.json'
        try:
            os.symlink(outside, link)
        except OSError:
            # Hard links also cross provenance boundaries and must be rejected.
            os.link(outside, link)
        root = self.work / 'linked-book'
        p.initialize(root, self.spec)
        self.native('Fixture', root=root, source_ref='linked.json')
        with self.assertRaisesRegex(ValueError, 'link|reparse'):
            sources.archive_sources(root, self.base, self.out)
        self.assertFalse(self.out.exists())

    def test_manifest_cannot_omit_references_hide_gaps_or_escape_archive(self):
        self.archive()
        manifest_path = self.out / sources.MANIFEST
        manifest = p.read(manifest_path)
        original = json.loads(json.dumps(manifest))
        ref = next(iter(manifest['records']))
        manifest['records'][ref]['format'] = 'txt'
        self.write_json(manifest_path, manifest)
        self.assertIn('format differs', sources.audit_sources(self.out)['errors'][0])
        manifest = json.loads(json.dumps(original))
        manifest['missing_inputs'] = []
        self.write_json(manifest_path, manifest)
        self.assertIn('missing-input', sources.audit_sources(self.out)['errors'][0])
        manifest = json.loads(json.dumps(original))
        ref = next(iter(manifest['records']))
        manifest['records'][ref]['path'] = '../outside.json'
        self.write_json(manifest_path, manifest)
        self.assertIn('archive record path', sources.audit_sources(self.out)['errors'][0])
        manifest = json.loads(json.dumps(original))
        manifest['records'].pop(ref)
        self.write_json(manifest_path, manifest)
        self.assertIn('coverage', sources.audit_sources(self.out)['errors'][0])

    def test_existing_output_and_invalid_world_are_preserved(self):
        self.out.mkdir()
        marker = self.out / 'original.txt'
        marker.write_text('Preserve me.', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'refusing overwrite'):
            self.archive()
        self.assertEqual(marker.read_text(), 'Preserve me.')
        state = p.read(self.root / 'preprint.json')
        state['world']['unrecorded'] = True
        self.write_json(self.root / 'preprint.json', state)
        with self.assertRaisesRegex(ValueError, 'outside a recorded operation'):
            sources.archive_sources(self.root, self.base, self.work / 'new-output')
        self.assertFalse((self.work / 'new-output').exists())

    def test_shared_reference_is_copied_once_and_retains_both_event_uses(self):
        self.native('The door’s still open—come in.', source_ref='return-1.json')
        result = self.archive()
        manifest = p.read(self.out / sources.MANIFEST)
        self.assertEqual(len(manifest['records']['return-1.json']['uses']), 2)
        self.assertEqual(result['archived_files'], 3)


if __name__ == '__main__':
    unittest.main()
