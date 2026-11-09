"""Narrow post-run checks. These checks do not score protocol semantics or taste."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
LABELS=('b01','b05','b03','b04')

def verify():
    plan=json.loads((ROOT/'native_plan.json').read_text(encoding='utf-8'))
    truth=json.loads((ROOT/'support/truth.json').read_text(encoding='utf-8'))
    telemetry=json.loads((ROOT/'telemetry.json').read_text(encoding='utf-8'))
    records=telemetry['records']; results=[]; agents_hashes=[]
    for label in LABELS:
        row=next(row for row in plan['records'] if row['label']==label)
        group=next(g for g in telemetry['groups'] if g['agent_path']=='/root/trial_'+label)
        members=[r for r in records if r['id'] in group['member_ids']]
        main=next(r for r in members if r['id']==group['main_id'])
        helpers=[r for r in members if r['id']!=main['id']]
        protected=all((ROOT/'native_subjects'/label/'portfolio'/rel).is_file() and
            hashlib.sha256((ROOT/'native_subjects'/label/'portfolio'/rel).read_bytes()).hexdigest()==sha
            for rel,sha in truth['protected_input_sha256'].items())
        agents_hashes.append(main['inherited_AGENTS_sha256'])
        checks={'protected_inputs_match':protected,
                'canonical_requested_prompt_file_matches':hashlib.sha256(Path(row['prompt_file']).read_text(encoding='utf-8').encode()).hexdigest()==row['prompt_sha256'],
                'main_completed':bool(main['task_completions']),
                'all_model_effort_tags_match':all(r['model']=='gpt-6.1-sol' and r['effort']=='max' for r in members),
                'no_global_listing_in_accepted_episode':all(r['global_listing_calls']==0 and r['global_thread_listing_calls']==0 for r in members),
                'helper_identity_limit':len(helpers)<= (0 if label in ('b01','b04') else 3),
                'helper_completed_turn_limit':sum(len(r['task_completions']) for r in helpers)<=6,
                'main_wall_cap_observed':group['main_observed_span_seconds']<=row['cap']+2}
        results.append({'label':label,'checks':checks,'passed':all(checks.values()),
                        'helper_identities':len(helpers),
                        'helper_terminal_events':sum(len(r['task_completions']) for r in helpers),
                        'helper_unique_context_turns':sum(len(r['turn_ids']) for r in helpers)})
    expected_sha='cfd363cabfe680242a91c70cbd0ff3611d22648bb2a40c1bb2c08c097cd448ba'
    overall={'evaluator_unchanged':hashlib.sha256((ROOT/'support/suite.py').read_bytes()).hexdigest()==expected_sha,
             'all_inherited_AGENTS_exactly_same':len(set(agents_hashes))==1 and agents_hashes[0] is not None}
    result={'scope':'Measured execution and input boundaries only; semantic N/R/D/V review is separate. Requested-prompt hashes use canonical LF text; Windows on-disk files contain CRLF. Native transport message fields are encrypted in saved logs, so plaintext task-message readback is unavailable; do not interpret the requested-prompt check as full prompt attestation.',
            'overall':overall,'episodes':results,'passed':all(overall.values()) and all(row['passed'] for row in results)}
    (ROOT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False,indent=2))
