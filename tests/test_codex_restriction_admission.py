"""A proposed workflow gate needs authority; this never waives real boundaries."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from runtime.codex_foundation import _questions, BRIEF_FIELDS, propose_foundation
from runtime.codex_permissions import assess_operation, assess_restriction
from runtime.codex_session import create_session


ROOT = Path(__file__).resolve().parents[1]


def basis(**changes):
    return {**{'origin': 'user', 'source_ref': 'synthetic-current-user-source',
        'source_quote': 'Choose the destination before the irreversible operation.',
        'scope': 'the irreversible operation only', 'condition': 'destination remains undecided',
        'why_blocking': 'the destination cannot be selected without the actual user choice',
        'purpose': 'implementation', 'applies_now': True, 'necessary_now': True,
        'existing_authorization_checked': True, 'already_satisfied': False,
        'alternative_allows_progress': False, 'unaffected_work': ['continue read-only analysis']}, **changes}


class RestrictionAdmissionTests(unittest.TestCase):
    def test_model_and_collaborator_plans_cannot_create_authority(self):
        for origin in ('assistant', 'collaborator', 'old_plan'):
            self.assertFalse(assess_restriction(basis(origin=origin))['blocking_admitted'])

    def test_missing_or_obsolete_basis_is_advisory(self):
        for value in (None, {}, basis(applies_now=False), basis(necessary_now=False),
                      basis(existing_authorization_checked=False), basis(source_quote='')):
            self.assertEqual(assess_restriction(value)['next_action'], 'CONTINUE_WITHOUT_ADDED_GATE')

    def test_existing_satisfaction_or_safe_alternative_prevents_added_blocker(self):
        self.assertFalse(assess_restriction(basis(already_satisfied=True))['blocking_admitted'])
        self.assertFalse(assess_restriction(basis(alternative_allows_progress=True))['blocking_admitted'])

    def test_analysis_is_not_held_for_added_tests_or_future_feedback(self):
        for evidence in ('experiment', 'future_feedback', 'full_measurement'):
            self.assertFalse(assess_restriction(basis(origin='pinned_rule', purpose='analysis',
                evidence_kind=evidence))['blocking_admitted'])

    def test_an_explicit_empirical_commission_retains_its_actual_scope(self):
        value = assess_restriction(basis(purpose='analysis', evidence_kind='experiment',
            explicit_user_requirement=True))
        self.assertTrue(value['blocking_admitted'])
        self.assertFalse(value['authority_granted'])
        self.assertEqual(value['unaffected_work'], ['continue read-only analysis'])

    def test_restriction_advice_does_not_release_stop_or_unknown_api_budget(self):
        self.assertTrue(assess_restriction(basis())['blocking_admitted'])
        self.assertEqual(assess_operation({'scope':'fixture','authorized':True,'stopped':True},
            'write',within_task=True,capability='AVAILABLE')['next_action'], 'STOP')
        self.assertEqual(assess_operation({'scope':'fixture','authorized':True,
            'grants':{'paid_api':'actual prior grant'}},'paid_api',within_task=True,
            capability='AVAILABLE')['next_action'], 'VERIFY_COST_AND_BUDGET')

    def test_old_questions_keep_original_semantics(self):
        item = {'id':'q','question':'Synthetic choice','why':'Synthetic reason'}
        self.assertTrue(_questions([item])[0]['blocking'])
        self.assertFalse(_questions([item],restriction_admission=True)[0]['blocking'])

    def test_new_unadmitted_question_keeps_its_content_without_blocking(self):
        item = {'id':'q','question':'Do a larger evaluation?','why':'A model prefers it','blocking':True,
                'blocking_basis':basis(origin='assistant')}
        row = _questions([item],restriction_admission=True)[0]
        self.assertEqual(row['question'], item['question'])
        self.assertTrue(row['proposed_blocking'])
        self.assertFalse(row['blocking'])
        item['blocking_basis'] = basis()
        self.assertTrue(_questions([item],restriction_admission=True)[0]['blocking'])

    def test_real_proposal_and_existing_cli_use_the_same_admission(self):
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='restriction-', dir=cache) as td:
            base = Path(td)
            request = base / 'request.txt'
            request.write_text('DIGR: Execute this synthetic local fixture.',encoding='utf-8')
            root = base / 'session'
            create_session(root,request=request,p_run='0.18.0@'+'a'*40)
            proposal = {'brief':{k:'Synthetic '+k for k in BRIEF_FIELDS},
                'questions':[{'id':'q','question':'Run extra benchmarks?','why':'Model preference',
                              'blocking':True,'blocking_basis':basis(origin='assistant')}]}
            result = propose_foundation(root, proposal, reason='Synthetic actual proposal path')
            self.assertFalse(result['questions'][0]['blocking'])
            input_path = base / 'advice.json'
            input_path.write_text(json.dumps({'restriction':basis(origin='collaborator')}),encoding='utf-8')
            process = subprocess.run([sys.executable,'-I','-B',str(ROOT/'tools/codex.py'),
                'permissions','--input',str(input_path)],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(process.returncode,0,process.stderr)
            self.assertFalse(json.loads(process.stdout)['blocking_admitted'])
