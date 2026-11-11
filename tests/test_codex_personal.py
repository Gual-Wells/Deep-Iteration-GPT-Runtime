from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile
from runtime import codex_personal as p
from runtime import codex_personal_sources as source

ROOT = Path(__file__).resolve().parents[1]


def epub(path, escape=False):
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('META-INF/container.xml', '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OPS/content.opf"/></rootfiles></container>')
        href = '../../outside.xhtml' if escape else 'one.xhtml'
        z.writestr('OPS/content.opf', '<package xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Constructed source book</dc:title></metadata><manifest>'
            '<item id="one" href="'+href+'" media-type="application/xhtml+xml"/><item id="two" href="two.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="one"/><itemref idref="two"/></spine></package>')
        z.writestr('OPS/one.xhtml', '<html xmlns="http://www.w3.org/1999/xhtml"><body><p id="p1">A Tensor handle is not an independent value snapshot.</p></body></html>')
        z.writestr('OPS/two.xhtml', '<html xmlns="http://www.w3.org/1999/xhtml"><body><p>Repeated output need not be correct output.</p></body></html>')


class PersonalTests(unittest.TestCase):
    def setUp(self):
        cache=ROOT/'.cache';cache.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=cache,prefix='personal-test-');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.root=self.base/'private';p.initialize(self.root)
        self.raw=self.root/'self.txt';self.raw.write_text('I have used a benchmark runner.\nI have not written a GPU kernel.\n',encoding='utf-8')
        self.n=0

    def op(self):
        self.n+=1
        return {'expected_revision':p.load(self.root)['revision'],'operation_id':'op-'+str(self.n)}

    def register(self, file=None, origin='user_message', **kwargs):
        return p.register_source(self.root,file or self.raw,origin=origin,**kwargs,**self.op())['source_id']

    def entry(self,sid=None,eid='runner',kind='self_report',**extra):
        return {'id':eid,'kind':kind,'statement':'I have used a benchmark runner.','scope':'one personal self-report, not all deployment knowledge',
                'as_of':'2026-11-11','source_id':sid,'unit_id':'line:1','quote':'used a benchmark runner','sharing':'actor',**extra}

    def test_selected_view_preserves_kind_and_excludes_other_private_entries(self):
        sid=self.register();p.admit(self.root,self.entry(sid),**self.op())
        p.admit(self.root,self.entry(sid,eid='private-thing',sharing='self'),**self.op())
        view=p.make_view(self.root,entry_ids=['runner'],purpose='fictional candidate boundary',audience='actor',book_id='fixture-book',role_id='candidate')
        self.assertEqual(view['view']['entries'][0]['kind'],'self_report')
        self.assertNotIn('private-thing',json.dumps(view));self.assertTrue(view['view']['requires_private_publication'])
        with self.assertRaisesRegex(ValueError,'not shared'):
            p.make_view(self.root,entry_ids=['private-thing'],purpose='opponent',audience='actor',book_id='fixture-book',role_id='candidate')
        with self.assertRaisesRegex(ValueError,'explicit unique'):
            p.make_view(self.root,entry_ids=[],purpose='everything')

    def test_a_book_or_simulation_cannot_become_personal_mastery(self):
        for origin in ('reference','simulation'):
            with self.subTest(origin=origin):
                f=self.root/(origin+'.txt');f.write_text('used a benchmark runner',encoding='utf-8')
                sid=self.register(f,origin=origin)
                with self.assertRaisesRegex(ValueError,'cannot become'):
                    p.admit(self.root,self.entry(sid,kind='knowledge_evidence',evidence_scope='fictional actor succeeded'),**self.op())
                p.admit(self.root,self.entry(sid,eid=origin,kind='resource'),**self.op())
                with self.assertRaisesRegex(ValueError,'not actor knowledge'):
                    p.make_view(self.root,entry_ids=[origin],purpose='role',audience='actor',book_id='fixture-book',role_id='candidate')
        self.assertEqual(p.inspect(self.root)['entries_by_kind']['knowledge_evidence'],0)

    def test_source_change_and_removal_do_not_reconstruct_removed_facts(self):
        sid=self.register();p.admit(self.root,self.entry(sid),**self.op())
        old=p.make_view(self.root,entry_ids=['runner'],purpose='role',audience='actor',book_id='fixture-book',role_id='candidate')
        self.raw.write_text('different current material',encoding='utf-8')
        self.assertEqual(p.check_view(self.root,old)['status'],'STALE_OR_UNAVAILABLE')
        self.assertEqual(p.make_view(self.root,entry_ids=['runner'],purpose='role',audience='actor',book_id='fixture-book',role_id='candidate')['view']['entries'],[])
        self.raw.unlink()
        new=p.make_view(self.root,entry_ids=['runner'],purpose='role',audience='actor',book_id='fixture-book',role_id='candidate')
        self.assertEqual(new['view']['unavailable'][0]['source_status'],'MISSING')

    def test_withdrawn_source_stays_excluded_from_new_views_without_erasing_history(self):
        sid=self.register();p.admit(self.root,self.entry(sid),**self.op())
        view=p.make_view(self.root,entry_ids=['runner'],purpose='role',audience='actor',book_id='fixture-book',role_id='candidate')
        p.withdraw_source(self.root,sid,reason='User excludes this version',**self.op())
        self.assertEqual(p.source_status(self.root,p.load(self.root)['sources'][sid])['status'],'WITHDRAWN')
        self.assertEqual(p.check_view(self.root,view)['status'],'STALE_OR_UNAVAILABLE')
        self.assertEqual(p.make_view(self.root,entry_ids=['runner'],purpose='research')['view']['entries'],[])
        self.assertIn('runner',p.load(self.root)['entries'])

    def test_corrections_preserve_history_and_unrelated_changes_do_not_stale_view(self):
        sid=self.register();p.admit(self.root,self.entry(sid),**self.op())
        before=p.make_view(self.root,entry_ids=['runner'],purpose='role',audience='actor',book_id='fixture-book',role_id='candidate')
        p.admit(self.root,self.entry(sid,eid='other'),**self.op())
        self.assertEqual(p.check_view(self.root,before)['status'],'CURRENT_SELECTED_ENTRIES')
        replacement=self.entry(sid,statement='Used a runner; no kernel implementation claim.',replaces_sha256=p.load(self.root)['entries']['runner']['entry_sha256'])
        p.admit(self.root,replacement,**self.op())
        self.assertEqual(len(p.load(self.root)['history']),1)
        self.assertEqual(p.check_view(self.root,before)['issues'][0]['status'],'ENTRY_CHANGED')
        self.assertEqual(before['view']['entries'][0]['statement'],'I have used a benchmark runner.')

    def test_relative_material_and_view_survive_a_clone(self):
        sid=self.register();p.admit(self.root,self.entry(sid),**self.op())
        view=p.make_view(self.root,entry_ids=['runner'],purpose='role',audience='actor',book_id='fixture-book',role_id='candidate')
        clone=self.base/'clone';shutil.copytree(self.root,clone);self.raw.unlink()
        self.assertEqual(p.check_view(clone,view)['status'],'CURRENT_SELECTED_ENTRIES')
        self.assertEqual(p.check_view(self.root,view)['status'],'STALE_OR_UNAVAILABLE')

    def test_quote_and_revision_failures_leave_data_unchanged(self):
        sid=self.register();before=(self.root/'profile.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'quote is absent'):
            p.admit(self.root,self.entry(sid,quote='wrote every kernel'),**self.op())
        self.assertEqual((self.root/'profile.json').read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'revision conflict'):
            p.admit(self.root,self.entry(sid),expected_revision=0,operation_id='stale')
        self.assertEqual((self.root/'profile.json').read_bytes(),before)

    def test_retry_is_idempotent_and_lock_is_not_silently_removed(self):
        args=self.op();first=p.register_source(self.root,self.raw,origin='user_message',**args)
        second=p.register_source(self.root,self.raw,origin='user_message',**args)
        self.assertTrue(second['retried']);self.assertEqual(first['revision'],second['revision'])
        lock=self.root/'.writer.lock';lock.write_text('{"pid":123,"token":"other"}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'writer lock'):
            p.admit(self.root,self.entry(first['source_id']),**self.op())
        self.assertTrue(lock.exists())

    def test_unknown_is_not_an_inability_assertion(self):
        value={'id':'unprovided-cv','kind':'unknown','statement':'No CV selected for this scene.',
               'scope':'this intake only, not the person','as_of':'2026-11-11','reason':'not supplied','sharing':'scene_author'}
        p.admit(self.root,value,**self.op())
        view=p.make_view(self.root,entry_ids=['unprovided-cv'],purpose='genesis')
        self.assertEqual(view['view']['entries'][0]['kind'],'unknown')

    def test_epub_metadata_and_selected_items_are_not_full_reading(self):
        f=self.root/'book.epub';epub(f)
        metadata=source.extract(f);self.assertEqual(metadata['read_scope']['mode'],'metadata_and_inventory')
        self.assertEqual(set(metadata['units']),{'package:title'})
        self.assertEqual(metadata['metadata']['spine_count'],2)
        sid=self.register(f,origin='reference',items=['one'])
        self.assertNotIn('two:block:1',p.load(self.root)['sources'][sid]['units'])
        self.register(f,origin='reference',items=['two'])
        indexed=p.load(self.root)['sources'][sid]
        self.assertEqual(indexed['representation_sha256'],source.representation_digest(indexed['units']))
        self.assertEqual(len(indexed['representations']),2)
        self.assertIn('one:block:1',indexed['units']);self.assertIn('two:block:1',indexed['units'])

    def test_epub_package_traversal_is_rejected(self):
        f=self.root/'bad.epub';epub(f,escape=True)
        with self.assertRaisesRegex(ValueError,'escapes'):
            source.extract(f,items=['one'])

    def test_selected_json_paths_do_not_capture_unselected_content(self):
        f=self.root/'profile-input.json';f.write_text(json.dumps({'goal':'inference interview','unselected':'OTHER-CONTEXT-CANARY'}),encoding='utf-8')
        indexed=source.extract(f,selectors=['goal'])
        self.assertEqual(set(indexed['units']),{'goal'})
        self.assertNotIn('OTHER-CONTEXT-CANARY',json.dumps(indexed))

    def test_historical_copy_cannot_hide_a_corrected_primary(self):
        sid=self.register();p.admit(self.root,self.entry(sid),**self.op())
        archive=self.root/'old-copy.txt';archive.write_bytes(self.raw.read_bytes())
        self.assertEqual(self.register(archive),sid)
        old=p.make_view(self.root,entry_ids=['runner'],purpose='role',audience='actor',book_id='b1',role_id='candidate')
        self.raw.write_text('Correction: I used a runner, not an authored implementation.',encoding='utf-8')
        status=p.source_status(self.root,p.load(self.root)['sources'][sid])
        self.assertEqual(status['status'],'CHANGED');self.assertTrue(status['historical_snapshot_available'])
        self.assertEqual(p.check_view(self.root,old)['status'],'STALE_OR_UNAVAILABLE')
        self.assertEqual(p.make_view(self.root,entry_ids=['runner'],purpose='new book',audience='actor',book_id='b2',role_id='candidate')['view']['entries'],[])

    def test_explicit_new_logical_version_supersedes_old_source_without_rewriting_it(self):
        sid=self.register(lineage='resume');p.admit(self.root,self.entry(sid),**self.op())
        old=p.make_view(self.root,entry_ids=['runner'],purpose='role',audience='actor',book_id='b1',role_id='candidate')
        newer=self.root/'cv-v2.txt';newer.write_text('Corrected contribution: benchmark runner only.',encoding='utf-8')
        self.register(newer,lineage='resume',make_current=True)
        self.assertEqual(p.source_status(self.root,p.load(self.root)['sources'][sid])['status'],'CURRENT')
        self.assertEqual(p.check_view(self.root,old)['issues'][0]['status'],'SUPERSEDED_SOURCE')
        self.assertEqual(p.load(self.root)['entries']['runner']['statement'],old['view']['entries'][0]['statement'])

    def test_role_capsule_binds_destination_and_read_scope(self):
        sid=self.register();p.admit(self.root,self.entry(sid),**self.op())
        view=p.make_view(self.root,entry_ids=['runner'],purpose='role',audience='actor',book_id='b1',role_id='candidate')
        binding=view['view']['entries'][0]['source_binding']
        self.assertEqual(binding['origin'],'user_message');self.assertEqual(binding['read_scopes'],[{'mode':'text_lines'}])
        self.assertNotIn('locators',binding)
        p.validate_role_view(view,book_id='b1',role_id='candidate')
        with self.assertRaisesRegex(ValueError,'another book'):
            p.validate_role_view(view,book_id='b1',role_id='interviewer')
        with self.assertRaisesRegex(ValueError,'another book'):
            p.check_view(self.root,view,book_id='b2')

    def test_explicit_relocation_needs_exact_snapshot_and_does_not_guess(self):
        sid=self.register();archive=self.root/'move.txt';archive.write_bytes(self.raw.read_bytes());self.raw.unlink()
        self.assertEqual(p.source_status(self.root,p.load(self.root)['sources'][sid])['status'],'MISSING')
        p.relocate_source(self.root,sid,archive,**self.op())
        self.assertEqual(p.source_status(self.root,p.load(self.root)['sources'][sid])['status'],'CURRENT')
        archive.write_text('different source version',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'identical source'):
            p.relocate_source(self.root,sid,archive,**self.op())


if __name__=='__main__':
    unittest.main()
