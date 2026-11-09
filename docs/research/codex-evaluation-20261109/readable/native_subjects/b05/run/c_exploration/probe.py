"""Public research probe: claim-local evidence frontiers and frozen transaction identity."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AS_OF = '2026-11-09'
START = '2026-11-03'
OFFICIAL = {'official_public', 'official_authorized_private'}


def frontier(packet):
    usable = [s for s in packet['sources'] if s['permission'] == 'allowed' and s['observed_on'] <= AS_OF]
    official = [s for s in usable if s['authority'] in OFFICIAL]
    def newest(sources):
        return max(sources, key=lambda s: s['observed_on'], default=None)
    status_source = newest([s for s in official if 'accepting_applications' in s['claims']])
    status = 'unknown'
    if status_source:
        c = status_source['claims']
        status = 'open' if c['accepting_applications'] and (c.get('deadline') is None or c['deadline'] >= AS_OF) else 'closed'
    recent_source = newest([s for s in official if s['claims'].get('current_recruiting_action') is True and START <= s['claims'].get('recruiting_action_on', '') <= AS_OF])
    recent = 'official_confirmed' if recent_source else 'none'
    if not recent_source:
        recent_source = newest([s for s in usable if s['authority'] == 'candidate_self_report' and s['claims'].get('interview_occurred') is True and START <= s['claims'].get('interview_on', '') <= AS_OF])
        if recent_source:
            recent = 'self_report_only'
    hc_source = newest([s for s in official if 'remaining_hc' in s['claims'] and 'hc_as_of' in s['claims'] and s['claims']['hc_as_of'] <= AS_OF])
    hc = 'unknown' if not hc_source else ('confirmed_available' if hc_source['claims']['remaining_hc'] > 0 else 'confirmed_zero')
    return {'status': status, 'status_evidence': status_source['source_id'] if status_source else None,
            'recent_recruitment': recent, 'recent_recruitment_evidence': recent_source['source_id'] if recent_source else None,
            'hc': hc, 'hc_evidence': hc_source['source_id'] if hc_source else None}


def main():
    packets = json.loads((ROOT / 'portfolio/task3_evidence/packets.json').read_text(encoding='utf-8'))['packets']
    by_id = {p['job_id']: p for p in packets}
    findings = {'domain': 'Claim-local evidence frontiers and intervention invariance', 'baseline': {k: frontier(by_id[k]) for k in ['J01', 'J03', 'J06', 'J09', 'J10']}}
    checks = []
    def check(name, condition, detail):
        assert condition, name
        checks.append({'name': name, 'observed': detail})
    for job, banned_id in [('J03', 'J03-O2'), ('J10', 'J10-X1')]:
        revised = copy.deepcopy(by_id[job])
        revised['sources'] = [s for s in revised['sources'] if s['source_id'] != banned_id]
        check('unusable-removal-' + job, frontier(revised) == frontier(by_id[job]), 'Removing future or ungranted evidence changes no output dimension.')
    j = copy.deepcopy(by_id['J01'])
    j['sources'].append({'source_id': 'COUNTERFACTUAL-HC', 'authority': 'official_public', 'permission': 'allowed', 'observed_on': AS_OF, 'claims': {'remaining_hc': 0, 'hc_as_of': AS_OF}})
    before, after = frontier(by_id['J01']), frontier(j)
    check('claim-local-newer-HC', after['status'] == before['status'] and after['status_evidence'] == before['status_evidence'] and after['recent_recruitment'] == before['recent_recruitment'] and after['hc'] == 'confirmed_zero', {'before': before, 'after': after})
    j = copy.deepcopy(by_id['J10'])
    next(s for s in j['sources'] if s['source_id'] == 'J10-X1')['permission'] = 'allowed'
    granted = frontier(j)
    check('permission-is-upstream', granted['status'] == 'closed' and granted['hc'] == 'confirmed_zero' and granted['recent_recruitment'] == 'official_confirmed', {'without_grant': frontier(by_id['J10']), 'counterfactual_grant': granted})
    spec = importlib.util.spec_from_file_location('starter_probe', ROOT / 'portfolio/task4_retry/starter/queue_payload.py')
    starter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(starter)
    original_text = '  A\r\nB\r\t\n  '
    seed = starter.prepare(b'\x00\xff', original_text)
    normalized = original_text.replace('\r\n', '\n').replace('\r', '\n')
    starter_findings = {'preserves_full_text': seed['description']['text'] == normalized, 'hash_matches_returned_text': seed['description']['sha256'] == hashlib.sha256(seed['description']['text'].encode('utf-8')).hexdigest()}
    before = copy.deepcopy(seed)
    repeated = starter.retry(seed, 'changed form')
    starter_findings.update({'retry_preserves_input': seed == before, 'retry_returns_frozen_values': repeated == before, 'retry_returns_independent_outer_object': repeated is not seed})
    findings.update({'checked_counterexamples': checks, 'starter_observations': starter_findings, 'next_question': 'When independent dimensions select different sources, does the final candidate preserve each frontier and its witness? For retries, does editing any returned nested field leave the submitted snapshot unchanged?'})
    path = Path(__file__).with_name('facts.json')
    path.write_text(json.dumps(findings, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'checks': len(checks), 'facts': str(path), 'starter_observations': starter_findings}, ensure_ascii=False))

if __name__ == '__main__':
    main()
