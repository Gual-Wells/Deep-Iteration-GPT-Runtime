"""Final candidate connection; static screen checks are distinguished from executable retries."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import probe

ROOT = Path(__file__).resolve().parents[2]
packets = json.loads((ROOT / 'portfolio/task3_evidence/packets.json').read_text(encoding='utf-8'))['packets']
screen = json.loads((ROOT / 'portfolio/task3_evidence/output/screen.json').read_text(encoding='utf-8'))
roles = {r['job_id']: r for r in screen['roles']}
checks = []
def check(name, passed, observation):
    assert passed, name
    checks.append({'name': name, 'observation': observation})

for packet in packets:
    expected = probe.frontier(packet)
    actual = {key: roles[packet['job_id']][key] for key in expected}
    check('candidate-frontier-' + packet['job_id'], actual == expected, actual)

for packet in packets:
    reduced = copy.deepcopy(packet)
    reduced['sources'] = [s for s in reduced['sources'] if s['permission'] == 'allowed' and s['observed_on'] <= probe.AS_OF]
    check('unusable-source-deletion-' + packet['job_id'], all(roles[packet['job_id']][k] == v for k, v in probe.frontier(reduced).items()), 'Candidate baseline equals model after removing unusable sources. Static artifact; not a rerun of an unavailable generator.')

j01 = copy.deepcopy(next(p for p in packets if p['job_id'] == 'J01'))
j01['sources'].append({'source_id': 'COUNTERFACTUAL-HC', 'authority': 'official_public', 'permission': 'allowed', 'observed_on': probe.AS_OF, 'claims': {'remaining_hc': 0, 'hc_as_of': probe.AS_OF}})
changed = probe.frontier(j01)
check('isolated-HC-intervention', changed['hc'] == 'confirmed_zero' and all(changed[k] == roles['J01'][k] for k in ['status', 'status_evidence', 'recent_recruitment', 'recent_recruitment_evidence']), {'expected_change': {'hc': changed['hc'], 'hc_evidence': changed['hc_evidence']}, 'preserved': 'candidate J01 status and recent axes'})

spec = importlib.util.spec_from_file_location('candidate_queue', ROOT / 'portfolio/task4_retry/output/queue_payload.py')
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)
text = ' \t\r\n' + '\U0001f642' * 997 + 'e\u0301' + '\r\n  '
normalized = text.replace('\r\n', '\n').replace('\r', '\n')
snapshot = queue.prepare(b'\x00\xff\x01', text)
check('normalization-identity', snapshot['description']['text'] == normalized and snapshot['description']['sha256'] == hashlib.sha256(normalized.encode('utf-8')).hexdigest(), 'Whitespace, Unicode code points and normalized text hash agree.')
check('post-normalization-boundary', queue.prepare(b'', '\r\n' * 2000)['description']['text'] == '\n' * 2000, '4000 input code points normalize to 2000 and are accepted.')
check('codepoint-not-byte-boundary', queue.prepare(b'', '\U0001f642' * 2000)['description']['text'] == '\U0001f642' * 2000, '2000 high Unicode code points are accepted despite 8000 UTF-8 bytes.')
for origin, frozen in [('direct', snapshot), ('json-roundtrip', json.loads(json.dumps(snapshot)))]:
    baseline = copy.deepcopy(frozen)
    for live in ['changed', None, 'x' * 2001, object()]:
        returned = queue.retry(frozen, live)
        check('retry-value-' + origin, returned == baseline and frozen == baseline, 'Live form variation does not change any frozen field.')
        check('retry-identity-' + origin, returned is not frozen and returned['image'] is not frozen['image'] and returned['description'] is not frozen['description'], 'Independent outer, image and description dictionaries.')
        returned['schema'] = 99
        returned['image']['base64'] = 'changed-image'
        returned['image']['sha256'] = 'changed-image-hash'
        returned['description']['text'] = 'changed-text'
        returned['description']['sha256'] = 'changed-description-hash'
        check('nested-noninterference-' + origin, frozen == baseline, 'Mutation of every returned scalar at every mutable level leaves original unchanged.')

report = {'result': 'research and candidate confirmation; no D claim', 'checks': checks,
          'limitation': 'screen.json is static; counterfactual source behavior is established in the independent fact model and checked against candidate baseline, not attributed to an unseen generator.',
          'development': 'The two tasks impose different dependency boundaries: evidence conclusions depend on each authorized claim frontier; frozen retries depend solely on the submitted snapshot and are noninterfering with the current form.'}
Path(__file__).with_name('candidate_facts.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'result': report['result'], 'observations': len(checks), 'facts': str(Path(__file__).with_name('candidate_facts.json')), 'limitation': report['limitation']}, ensure_ascii=False))
