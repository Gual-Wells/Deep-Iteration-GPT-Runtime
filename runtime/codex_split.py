"""Bind native Codex task splitting to one actual Consult submission.

Codex researches and performs the split. This standard-library helper reads its
public decision and checks request/input/evidence identity; it does not run an
LLM, invent research, truncate sources, or certify the allocation's quality.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

CONTRACT = 'digr-native-split-1'


def required(p_run: str) -> bool:
    version = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)@[0-9a-f]{40}', p_run)
    return bool(version and tuple(map(int, version.groups())) >= (0, 13, 0))


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Split ' + name + ' must be nonempty public text')
    return value


def request_profile(request: Mapping[str, Any]) -> dict:
    """Describe the entire transmitted context; bytes are not token savings."""
    messages = request['messages']
    text_bytes, images = 0, 0
    for message in messages:
        content = message.get('content')
        if isinstance(content, str):
            text_bytes += len(content.encode('utf-8'))
        elif isinstance(content, list):
            for part in content:
                if part.get('type') == 'text':
                    text_bytes += len(part.get('text', '').encode('utf-8'))
                elif part.get('type') == 'image_url':
                    images += 1
    return {'message_count': len(messages), 'utf8_text_bytes': text_bytes,
            'image_count': images, 'token_savings': None,
            'scope': 'all prepared public messages and images, including replayed history; not a token estimate'}


def brief(*, p_run: str, exchange_id: str, request_sha256: str,
          prepared_input: Mapping[str, Any], current_input: Mapping[str, Any],
          authoring_scope: Mapping[str, Any] | None, request: Mapping[str, Any]) -> dict:
    if prepared_input != current_input:
        raise ValueError('Split needs the current user input; prepare a current exchange')
    binding = {'P_run': p_run, 'exchange_id': exchange_id, 'request_sha256': request_sha256,
               'input_ref': dict(current_input), 'authoring_scope': authoring_scope}
    return {'format': CONTRACT, 'required': required(p_run), 'binding': binding,
            'request_profile': request_profile(request),
            'native_work': 'Research this task, perform useful local work, and prepare the smallest sufficient Claude assignment while preserving its content judgment.',
            'plan_fields': ['format', 'binding', 'decision', 'local_work', 'claude_value', 'context_decision'],
            'scope': 'local binding aid; no model invocation, semantic approval or native responsibility credit'}


def _decision(plan: Mapping[str, Any], base: Path) -> dict:
    decision = {key: _text(key, plan.get(key)) for key in ('decision', 'claude_value', 'context_decision')}
    local = plan.get('local_work')
    if not isinstance(local, list):
        raise ValueError('Split local_work must describe actual completed local work')
    if not local:
        decision['local_work_reason'] = _text('local_work_reason', plan.get('local_work_reason'))
    checked_work = []
    for item in local:
        if not isinstance(item, Mapping):
            raise ValueError('Split local_work items must be objects')
        work = {key: _text('local_work.' + key, item.get(key)) for key in ('task', 'result')}
        evidence = item.get('evidence', [])
        if not isinstance(evidence, list):
            raise ValueError('Split evidence must be a list of selected actual files')
        work['evidence'] = []
        for entry in evidence:
            if not isinstance(entry, Mapping):
                raise ValueError('Split evidence must name a path and its observed SHA256')
            filename = Path(_text('evidence.path', entry.get('path')))
            filename = (base / filename).resolve() if not filename.is_absolute() else filename.resolve()
            evidence_raw = filename.read_bytes()
            digest = sha256(evidence_raw).hexdigest()
            if entry.get('sha256') != digest:
                raise ValueError('Split local evidence changed; update the affected work and split')
            work['evidence'].append({'path': filename.as_posix(), 'sha256': digest,
                                     'byte_length': len(evidence_raw)})
        checked_work.append(work)
    return {**decision, 'local_work': checked_work}


def bind_decision(input_path: Path, *, current_brief: Mapping[str, Any]) -> dict:
    """Copy opaque binding fields, never generate the native research text."""
    path = Path(input_path).resolve()
    decision = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(decision, dict) or 'binding' in decision or 'format' in decision:
        raise ValueError('Supply the current unbound native decision, not an old bound Split plan')
    # Resolve evidence relative to its author's note, independent of output dir.
    return {'format': CONTRACT, 'binding': dict(current_brief['binding']),
            **_decision(decision, path.parent)}


def Split(plan_path: Path | None, *, current_brief: Mapping[str, Any]) -> dict:
    """Run once locally before a generation, consuming real native split work.

    The plan is private host work, not another instruction payload for Claude.
    Its exact binding prevents reuse across tasks, corrections, paper scopes,
    models, output limits, public histories, or prepared source selections.
    """
    if plan_path is None:
        raise ValueError('Run native Codex Split for this exchange, then supply --split-plan before calling Claude')
    path = Path(plan_path).resolve()
    raw = path.read_bytes()
    plan = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(plan, dict) or plan.get('format') != CONTRACT:
        raise ValueError('Split plan needs format ' + CONTRACT)
    if plan.get('binding') != current_brief['binding']:
        raise ValueError('Split plan is stale or belongs to another prepared request/input/paper; redo the affected split')
    return {'format': CONTRACT, 'at': datetime.now(timezone.utc).isoformat(),
            'binding': dict(current_brief['binding']), 'plan_sha256': sha256(raw).hexdigest(),
            **_decision(plan, path.parent),
            'request_profile': dict(current_brief['request_profile']),
            'external_model_calls': 0, 'semantic_approval': False,
            'scope': 'native public allocation recorded and byte identity checked; not proof of research quality or token savings'}
