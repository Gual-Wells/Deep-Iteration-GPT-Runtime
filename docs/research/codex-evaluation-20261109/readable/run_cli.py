"""Fixed-input native/light trial runner. No API keys or external API clients."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'support'))
import suite

COMMON = '''这是一个完整、自含的本地任务。请完成当前目录TASK.txt及四个子任务TASK.txt的实际交付。
本目录之外的项目、其他任务目录、评分器、support、用户记录、记忆、运行配置均不属于本任务输入，不得读取。
仅可读当前目录及其Git历史；只在TASK明确允许的output目录写入。没有网络、安装或外部服务需求。
本次只用你自己的执行循环，不启动独立代理，不调用其他模型或CLI。可自主使用shell和Python标准库。
Python调用加-B，避免为只读输入写__pycache__。当前任务无需保存隐藏思维链或另建工作平台。
分配的墙钟上限为480秒，可以完成后提前交付。不要为凑时间追加无用工作。
最终简要指出交付物和实际核对；未完成或影响使用的问题如实交代。
'''
PROMPT = '请完成当前目录 TASK.txt 中的全部四项任务，交付实际文件。'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def audit(thread_id, condition):
    candidates = list(Path('D:/CodexData/sessions/2026/11/09').glob('*' + thread_id + '*.jsonl'))
    light = (ROOT / 'pin/codex/AGENTS.light.md').read_text(encoding='utf-8').strip()
    result = {'thread_id': thread_id, 'matching_rollouts': [str(path) for path in candidates],
              'injected_original_AGENTS': False, 'injected_light_block': False,
              'expected_light': condition == 'light', 'message_summaries': [],
              'model': None, 'effort': None}
    for path in candidates:
        for line in path.open(encoding='utf-8'):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            payload = event.get('payload', {})
            if event.get('type') == 'turn_context':
                result['model'], result['effort'] = payload.get('model'), payload.get('effort')
            if event.get('type') != 'response_item' or payload.get('type') != 'message':
                continue
            if payload.get('role') not in ('user', 'developer'):
                continue
            text = ''.join(item.get('text', '') for item in payload.get('content', [])
                           if item.get('type') in ('input_text', 'output_text', 'text'))
            original = '每条用户消息只去开头空白' in text or '本机存储分工与 C 盘空间荒' in text
            has_light = light in text
            result['injected_original_AGENTS'] |= original
            result['injected_light_block'] |= has_light
            result['message_summaries'].append({'role': payload.get('role'), 'length': len(text),
                'sha256': digest(text.encode()), 'original_AGENTS_markers': original,
                'exact_light_block': has_light})
    result['audit_passed'] = (bool(candidates) and not result['injected_original_AGENTS']
                              and result['injected_light_block'] == result['expected_light'])
    return result


def run_one(record):
    label, condition = record['label'], record['condition']
    dest = ROOT / 'cli_subjects' / label
    dest.parent.mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'frozen_seed', dest)
    log = ROOT / 'cli_logs' / label
    log.mkdir(parents=True)
    instruction = COMMON
    if condition == 'light':
        instruction += '\n' + (ROOT / 'pin/codex/AGENTS.light.md').read_text(encoding='utf-8')
    (log / 'instructions.txt').write_text(instruction, encoding='utf-8')
    (log / 'prompt.txt').write_text(PROMPT, encoding='utf-8')
    cmd = ['codex', '--no-daemon', 'exec', '--ignore-user-config', '--json',
           '--skip-git-repo-check', '--color', 'never', '-C', str(dest),
           '-s', 'danger-full-access', '-m', 'gpt-6.1-sol',
           '-c', 'model_reasoning_effort="max"', '-c', 'project_doc_max_bytes=0',
           '-c', 'memories.use_memories=false', '-c', 'memories.generate_memories=false',
           '-c', 'web_search="disabled"', '-c', 'model_provider="study_http"',
           '-c', 'model_providers.study_http.name="Study HTTPS-only OpenAI"',
           '-c', 'model_providers.study_http.requires_openai_auth=true',
           '-c', 'model_providers.study_http.supports_websockets=false',
           '-c', 'model_providers.study_http.wire_api="responses"',
           '-c', 'model_providers.study_http.stream_max_retries=0',
           '--disable', 'apps', '--disable', 'plugins', '--disable', 'multi_agent',
           '-c', 'developer_instructions=' + json.dumps(instruction, ensure_ascii=False), '-']
    metadata = dict(record, workspace=str(dest), started_at_utc=datetime.now(timezone.utc).isoformat(),
                    instructions_sha256=digest(instruction.encode()), prompt_sha256=digest(PROMPT.encode()),
                    command=cmd, wall_ceiling_seconds=480, tool_calls=0, usage=None, timed_out=False)
    (log / 'start.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'event': 'trial_started', 'label': label, 'condition': condition}), flush=True)
    started = time.monotonic()
    events = []
    stderr_handle = (log / 'stderr.txt').open('w', encoding='utf-8')
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=stderr_handle, text=True, encoding='utf-8',
                               cwd=dest, creationflags=subprocess.CREATE_NO_WINDOW)
    process.stdin.write(PROMPT)
    process.stdin.close()
    def collect():
        with (log / 'events.jsonl').open('w', encoding='utf-8') as out:
            for line in process.stdout:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get('item', {}).get('type') == 'reasoning':
                    continue
                events.append(event)
                out.write(json.dumps(event, ensure_ascii=False) + '\n')
                out.flush()
    reader = threading.Thread(target=collect, daemon=True)
    reader.start()
    try:
        process.wait(timeout=480)
    except subprocess.TimeoutExpired:
        metadata['timed_out'] = True
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True,
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=20)
        process.wait(timeout=20)
    reader.join(timeout=5)
    stderr_handle.close()
    metadata['elapsed_seconds'] = time.monotonic() - started
    metadata['ended_at_utc'] = datetime.now(timezone.utc).isoformat()
    metadata['exit_code'] = process.returncode
    messages = []
    for event in events:
        if event.get('type') == 'thread.started':
            metadata['thread_id'] = event.get('thread_id')
        if event.get('type') == 'turn.completed':
            metadata['usage'] = event.get('usage')
        item = event.get('item', {})
        if event.get('type') == 'item.started' and item.get('type') in (
                'command_execution', 'mcp_tool_call', 'web_search'):
            metadata['tool_calls'] += 1
        if event.get('type') == 'item.completed' and item.get('type') == 'agent_message':
            messages.append(item.get('text', ''))
    metadata['input_audit'] = audit(metadata.get('thread_id', 'not-found'), condition)
    metadata['final_response'] = messages[-1] if messages else None
    usage = metadata['usage']
    if usage:
        metadata['uncached_input_plus_output'] = usage.get('input_tokens', 0) - usage.get('cached_input_tokens', 0) + usage.get('output_tokens', 0)
    truth = json.loads((ROOT / 'support/truth.json').read_text(encoding='utf-8'))
    metadata['grade'] = suite.grade(dest, truth)
    (log / 'result.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'event': 'trial_completed', 'label': label, 'elapsed_seconds': metadata['elapsed_seconds'],
                      'exit_code': metadata['exit_code'], 'input_audit_passed': metadata['input_audit']['audit_passed'],
                      'usage': usage}), flush=True)
    return metadata


if __name__ == '__main__':
    records = [{'condition': condition, 'repeat': repeat} for repeat in (1, 2) for condition in ('native', 'light')]
    random.Random(20261109).shuffle(records)
    for index, record in enumerate(records, 1):
        record['label'] = 'a' + str(index).zfill(2)
    (ROOT / 'cli_order.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    completed = []
    for record in records:
        result = run_one(record)
        completed.append(result)
        (ROOT / 'cli_results.json').write_text(json.dumps(completed, ensure_ascii=False, indent=2), encoding='utf-8')
        if not result['input_audit']['audit_passed']:
            print('INPUT_AUDIT_FAILED: stop before another efficacy run', flush=True)
            break
