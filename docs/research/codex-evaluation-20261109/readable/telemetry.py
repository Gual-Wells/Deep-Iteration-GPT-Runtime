"""Read only exact current-study thread metadata and numeric usage, never reasoning text."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

STUDY = Path(__file__).resolve().parent
SESSION_DAY = Path('D:/CodexData/sessions/2026/11/09')
PARENT = '01a1bf03-197e-78e0-8ad1-08021e30ab92'
EXPERIMENT_PREFIX = '/root/trial_'


def get_meta(path):
    with path.open(encoding='utf-8') as stream:
        line = stream.readline()
    try:
        data = json.loads(line)
    except ValueError:
        return None
    if data.get('type') != 'session_meta':
        return None
    data = data['payload']
    spawn = data.get('source', {})
    spawn = spawn.get('subagent', {}).get('thread_spawn', {}) if isinstance(spawn, dict) else {}
    return {'id': data['id'], 'parent': spawn.get('parent_thread_id'),
            'agent_path': spawn.get('agent_path'), 'timestamp': data.get('timestamp'),
            'file': str(path)}


def scan():
    # Restrict inventory to this date, and metadata to the first line only.
    metas = [get_meta(path) for path in SESSION_DAY.glob('*.jsonl')]
    metas = [meta for meta in metas if meta]
    subjects = [meta for meta in metas if meta['parent'] == PARENT
                and (meta['agent_path'] or '').startswith(EXPERIMENT_PREFIX)]
    study_ids = {meta['id'] for meta in subjects}
    while True:
        new_ids = {meta['id'] for meta in metas if meta['parent'] in study_ids}
        if new_ids <= study_ids:
            break
        study_ids |= new_ids
    selected = [meta for meta in metas if meta['id'] in study_ids]
    records = []
    for meta in selected:
        record = dict(meta, model=None, effort=None, last_usage=None,
                      usage_source='event_msg.token_count.info.total_token_usage',
                      tool_calls=0, tools={}, visible_messages=0, final_response=None,
                      first_event=None, last_event=None, task_completions=[],
                      inherited_AGENTS_sha256=None, global_listing_calls=0,
                      global_thread_listing_calls=0, turn_ids=[])
        for line in Path(meta['file']).open(encoding='utf-8'):
            try:
                data = json.loads(line)
            except ValueError:
                continue
            kind, payload = data.get('type'), data.get('payload', {})
            stamp = data.get('timestamp')
            if stamp:
                record['first_event'] = record['first_event'] or stamp
                record['last_event'] = stamp
            if kind == 'turn_context':
                record['model'] = payload.get('model')
                record['effort'] = payload.get('effort')
                turn_id = payload.get('turn_id')
                if turn_id and turn_id not in record['turn_ids']:
                    record['turn_ids'].append(turn_id)
            elif kind == 'event_msg' and payload.get('type') == 'token_count':
                info = payload.get('info') or {}
                if info.get('total_token_usage'):
                    record['last_usage'] = info['total_token_usage']
            elif kind == 'event_msg' and payload.get('type') == 'task_complete':
                record['task_completions'].append(stamp)
                if payload.get('last_agent_message'):
                    record['final_response'] = payload['last_agent_message']
            elif kind == 'response_item' and payload.get('type') in ('function_call', 'custom_tool_call'):
                name = payload.get('name', 'unknown')
                record['tools'][name] = record['tools'].get(name, 0) + 1
                record['tool_calls'] += 1
                if name.endswith('list_agents'):
                    record['global_listing_calls'] += 1
                if name.endswith('list_threads') or name.endswith('read_thread'):
                    record['global_thread_listing_calls'] += 1
            elif kind == 'response_item' and payload.get('type') == 'message' and payload.get('role') == 'assistant':
                record['visible_messages'] += 1
                if payload.get('phase') == 'final_answer':
                    text = ''.join(part.get('text', '') for part in payload.get('content', [])
                                   if part.get('type') == 'output_text')
                    record['final_response'] = text
            elif kind == 'response_item' and payload.get('type') == 'message' and payload.get('role') == 'user':
                text = ''.join(part.get('text', '') for part in payload.get('content', [])
                               if part.get('type') in ('input_text', 'text'))
                if text.startswith('# AGENTS.md instructions'):
                    import hashlib
                    record['inherited_AGENTS_sha256'] = hashlib.sha256(text.encode()).hexdigest()
        usage = record['last_usage']
        if usage:
            # reasoning_output_tokens is a SUBSET of output_tokens; never add twice.
            record['uncached_input_plus_output'] = (
                usage.get('input_tokens', 0) - usage.get('cached_input_tokens', 0)
                + usage.get('output_tokens', 0))
        if record['first_event'] and record['last_event']:
            record['observed_span_seconds'] = (
                datetime.fromisoformat(record['last_event'].replace('Z', '+00:00'))
                - datetime.fromisoformat(record['first_event'].replace('Z', '+00:00'))).total_seconds()
        records.append(record)
    groups = []
    for subject in subjects:
        ids = {subject['id']}
        while True:
            new = {record['id'] for record in records if record['parent'] in ids}
            if new <= ids:
                break
            ids |= new
        members = [record for record in records if record['id'] in ids]
        sums = {}
        for member in members:
            for key, value in (member['last_usage'] or {}).items():
                sums[key] = sums.get(key, 0) + value
        groups.append({'agent_path': subject['agent_path'], 'main_id': subject['id'],
                       'member_ids': sorted(ids), 'numeric_usage_sum': sums,
                       'tool_calls_sum': sum(member['tool_calls'] for member in members),
                       'uncached_input_plus_output': sum(member.get('uncached_input_plus_output', 0) for member in members),
                       'model_effort_pairs': sorted({(member['model'], member['effort']) for member in members}),
                       'main_observed_span_seconds': next(member.get('observed_span_seconds') for member in members if member['id'] == subject['id'])})
    result = {'read_at_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'Only current study subject roots and recursively linked descendants',
              'usage_caveat': 'Native cumulative token counters, summed once per thread; may include repeated context and cache. Not dollars, physical compute, active-work time, or protocol quality.',
              'records': records, 'groups': groups}
    (STUDY / 'telemetry.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    result = scan()
    print(json.dumps(result['groups'], ensure_ascii=False, indent=2))
