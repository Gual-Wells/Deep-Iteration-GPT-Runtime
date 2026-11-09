"""Apply the frozen independent behavior grader only to explicitly finished episodes."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'support'))
import suite

EXPECTED_SUITE_SHA = 'cfd363cabfe680242a91c70cbd0ff3611d22648bb2a40c1bb2c08c097cd448ba'


def score(labels):
    current_sha = hashlib.sha256((ROOT / 'support/suite.py').read_bytes()).hexdigest()
    if current_sha != EXPECTED_SUITE_SHA:
        raise RuntimeError('Frozen evaluator changed')
    truth = json.loads((ROOT / 'support/truth.json').read_text(encoding='utf-8'))
    records = []
    for label in labels:
        result = suite.grade(ROOT / 'native_subjects' / label / 'portfolio', truth)
        record = {'label': label, 'grade': result}
        records.append(record)
    result = {'suite_sha256': current_sha, 'finished_labels': labels, 'records': records}
    (ROOT / 'scores.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    result = score(sys.argv[1:])
    for record in result['records']:
        grade = record['grade']
        print(json.dumps({'label': record['label'], 'grade': grade}, ensure_ascii=False))
