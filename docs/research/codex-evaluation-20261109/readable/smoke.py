import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'smoke_http'
RUN.mkdir(exist_ok=True)
isolated = '--isolated' in sys.argv
cmd = [
    'codex', '--no-daemon', 'exec', '--ignore-user-config', '--ephemeral', '--json',
    '--skip-git-repo-check', '--color', 'never', '-C', str(RUN),
    '-s', 'read-only', '-m', 'gpt-6.1-sol',
    '-c', 'model_reasoning_effort="max"',
    '-c', 'project_doc_max_bytes=0',
    '-c', 'memories.use_memories=false',
    '-c', 'memories.generate_memories=false',
    '-c', 'web_search="disabled"',
    '-c', 'model_provider="study_http"',
    '-c', 'model_providers.study_http.name="Study HTTPS-only OpenAI"',
    '-c', 'model_providers.study_http.requires_openai_auth=true',
    '-c', 'model_providers.study_http.supports_websockets=false',
    '-c', 'model_providers.study_http.wire_api="responses"',
    '-c', 'model_providers.study_http.stream_max_retries=0',
    '--disable', 'apps', '--disable', 'plugins', '--disable', 'multi_agent',
    '-c', 'developer_instructions="This is a connectivity check. Do not use tools. Reply exactly READY."',
    '-',
]
child_env = os.environ.copy()
if isolated:
    child_env['CODEX_HOME'] = 'D:/CodexData/isolated-eval-home-20261109'
    child_env.pop('CODEX_SESSION_ID', None)
    child_env.pop('CODEX_THREAD_ID', None)
    cmd.remove('--ephemeral')
started = time.monotonic()
try:
    p = subprocess.run(cmd, input='Reply READY.', text=True, encoding='utf-8',
                       capture_output=True, timeout=60, cwd=RUN, env=child_env,
                       creationflags=subprocess.CREATE_NO_WINDOW)
except subprocess.TimeoutExpired as e:
    p = subprocess.CompletedProcess(cmd, 124,
        (e.stdout or b'').decode('utf-8', 'replace') if isinstance(e.stdout, bytes) else e.stdout or '',
        (e.stderr or b'').decode('utf-8', 'replace') if isinstance(e.stderr, bytes) else e.stderr or '')
events = []
for line in p.stdout.splitlines():
    try:
        event = json.loads(line)
    except ValueError:
        continue
    if event.get('item', {}).get('type') == 'reasoning':
        continue
    events.append(event)
result = dict(returncode=p.returncode, elapsed_seconds=time.monotonic()-started,
              command=cmd, events=events, stderr=p.stderr)
(RUN / ('isolated_result.json' if isolated else 'result.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
