"""Synthetic X task lifetime checks; no accounts, network or real transfers."""
import json
from pathlib import Path
import tempfile
import unittest

from runtime.codex_session import create_session, task_delivery_policy
from runtime.codex_lifecycle import ingest_message, handle_message


class XTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.registry = self.base / 'targets.json'
        self.targets = {'format':'digr-delivery-targets-1','targets':{
            'gmail':{'channel':'gmail','account':'self@example.test','recipient':'self@example.test',
                     'transport':'native-connector','target_kind':'self_mailbox'},
            'archive_2':{'channel':'gmail','account':'archive@example.test','recipient':'archive@example.test',
                         'transport':'native-connector','target_kind':'self_mailbox','aliases':['archive']}
        }}
        self.registry.write_text(json.dumps(self.targets),encoding='utf-8')

    def create(self, text, *, name='task', version='0.9.0', destinations=True):
        request = self.base / (name+'.txt')
        request.write_text(text,encoding='utf-8')
        root = self.base / name
        metadata = create_session(root,request=request,p_run=version+'@'+'a'*40,
            visits_path=self.base/'visits.jsonl',run_id=name,
            destinations=self.registry if destinations else None)
        return root, metadata

    def test_task_freezes_target_and_registry_changes_do_not_retarget(self):
        root, metadata = self.create('DIGR(X):create final file')
        first = task_delivery_policy(root)
        self.assertEqual((first['target'],first['account'],first['recipient']),
                         ('gmail','self@example.test','self@example.test'))
        self.targets['targets']['gmail']['account'] = 'different-account@example.test'
        self.registry.write_text(json.dumps(self.targets),encoding='utf-8')
        self.assertEqual(task_delivery_policy(root),first)
        self.assertEqual(metadata['delivery_contract'],'x-files-v1')

    def test_no_x_does_not_read_broken_registry_or_inherit_previous_task(self):
        self.create('DIGR(X=Gmail):first',name='first')
        self.registry.write_text('invalid JSON',encoding='utf-8')
        root, metadata = self.create('DIGR:second',name='second')
        self.assertEqual(task_delivery_policy(root)['mode'],'local')
        self.assertIsNone(metadata['delivery_registry_origin'])

    def test_unknown_target_fails_before_partial_session_creation(self):
        with self.assertRaises(ValueError):
            self.create('DIGR(X=unregistered):file')
        self.assertFalse((self.base/'task').exists())

    def test_registered_extension_alias_is_resolved_once(self):
        root, _ = self.create('DIGRP(N=16)(X=archive):complete paper')
        self.assertEqual(task_delivery_policy(root)['target'],'archive_2')

    def test_ordinary_and_routed_no_x_followups_keep_task_choice(self):
        root, _ = self.create('DIGR(X=Gmail):create file')
        policy = task_delivery_policy(root)
        for number, text in enumerate(['continue with a clearer title','DIGR:also fix layout'],1):
            reply = self.base/f'reply-{number}.txt'; reply.write_text(text,encoding='utf-8')
            value = ingest_message(root,source=reply,source_ref=f'actual-synthetic-{number}',
                route_pin='0.9.0@'+'a'*40 if text.startswith('DIGR') else None)
            handle_message(root,message_id=value['message_id'],action='ordinary',reason='Synthetic task supplement')
            self.assertEqual(task_delivery_policy(root),policy)

    def test_legacy_pin_is_not_silently_given_new_delivery_contract(self):
        root, metadata = self.create('DIGR:legacy file',version='0.8.5',destinations=False)
        self.assertNotIn('delivery_contract',metadata)
        self.assertIsNone(task_delivery_policy(root))


if __name__ == '__main__':
    unittest.main()
