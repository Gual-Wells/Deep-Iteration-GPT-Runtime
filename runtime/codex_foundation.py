"""Model-authored task briefs, real dialogue and explicit execution decisions.

This utility does not infer intent, generate questions, or authenticate a user.
It keeps the original request separate from a revisable interpretation and
checks the managed execution entry against the recorded current decision.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import time
from typing import Any, Mapping

from .validation import require_nonempty_text

FORMAT = 'digr-codex-foundation-1'
BRIEF_FIELDS = {
    'goal': '目标与用途', 'results': '用户拿到什么',
    'scope': '本次范围与完整任务的关系', 'granularity': '处理粒度与理由',
    'basis': '已有材料、实物与可复用程度', 'dependencies': '依赖与未知',
    'approach': '候选路线、取舍与最早整体结果',
    'resources': '前置与正式投入、成本依据及结束条件',
    'completion': '何时完成，什么仍只是中间产物',
}
# Source observations and presentation notes may be maintained without changing
# the accepted execution decision. A different outcome/scope/resource decision
# must not be smuggled through the caller's `non_material` label.
DECISION_FIELDS = frozenset(BRIEF_FIELDS) - {'basis'}


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             allow_nan=False).encode('utf-8')).hexdigest()


def _reply_text(value: str) -> str:
    require_nonempty_text('actual user reply', value)
    return value  # Preserve the selected original, including BOM-decoded CRLF.


def _present(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return '\n\n'.join('- ' + _present(item).replace('\n', '\n  ') for item in value)
    if isinstance(value, Mapping):
        labels = {'item': '材料', 'observed': '已观察', 'reuse': '如何复用', 'relation': '依赖关系',
                  'foundation': '前置投入', 'execution': '正式投入', 'cost_basis': '费用依据'}
        return '\n'.join(f"{labels.get(key, key)}：{_present(item)}" for key, item in value.items())
    return str(value)


def _context(root: Path) -> tuple[Path, dict[str, Any]]:
    from .codex_session import _session
    return _session(root)


def load_foundation(root: Path) -> dict[str, Any]:
    from .codex_session import _read_json
    root, session = _context(root)
    value = _read_json(root / 'foundation.json')
    if value.get('format') != FORMAT or value.get('request_sha256') != session['request_sha256']:
        raise ValueError('task brief is not bound to this original request')
    if value.get('brief_sha256') != _digest(value['brief']):
        raise ValueError('task brief changed outside the revision command')
    return value


def _questions(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        raise ValueError('questions must be a list; an empty list still needs explicit overall confirmation')
    result, seen = [], set()
    for supplied in items:
        if not isinstance(supplied, Mapping):
            raise ValueError('each question must be an object')
        item = {key: require_nonempty_text(key, supplied.get(key)) for key in ('id', 'question', 'why')}
        if item['id'] in seen:
            raise ValueError('question IDs must be unique')
        seen.add(item['id'])
        item['blocking'] = supplied.get('blocking', True)
        if type(item['blocking']) is not bool:
            raise ValueError('question blocking must be a boolean')
        options = supplied.get('options', [])
        if not isinstance(options, list) or any(not isinstance(o, str) or not o.strip() for o in options):
            raise ValueError('options must be nonempty strings; free text is always allowed')
        item['options'] = options
        result.append(item)
    return result


def propose_foundation(root: Path, proposal: Mapping[str, Any], *, reason: str,
                       change_kind: str = 'material') -> dict[str, Any]:
    from .codex_session import _write_json
    from .codex_lifecycle import require_open_decision
    root, session = _context(root)
    require_open_decision(root)
    reason = require_nonempty_text('change reason', reason)
    if change_kind not in {'material', 'non_material'}:
        raise ValueError('change_kind must be material or non_material')
    brief = proposal.get('brief')
    if not isinstance(brief, Mapping) or any(not brief.get(key) for key in BRIEF_FIELDS):
        raise ValueError('brief needs goal/results/scope/granularity/basis/dependencies/approach/resources/completion; use explicit unknowns')
    brief = json.loads(json.dumps(brief, ensure_ascii=False, allow_nan=False))
    questions = _questions(proposal.get('questions', []))
    previous = load_foundation(root) if (root / 'foundation.json').exists() else None
    if previous and change_kind == 'non_material':
        changed = [key for key in DECISION_FIELDS if previous['brief'].get(key) != brief.get(key)]
        if changed:
            raise ValueError('decision fields changed; use material revision: ' + ', '.join(sorted(changed)))
    revision = previous['revision'] + 1 if previous else 1
    # Answers survive only an unchanged decision question, not a recycled ID.
    old_questions = {q['id']: q for q in previous['questions']} if previous else {}
    for question in questions:
        old = old_questions.get(question['id'])
        if old and {k: v for k, v in old.items() if k != 'answer'} == question and old.get('answer'):
            question['answer'] = deepcopy(old['answer'])
    confirmation = None
    accepted = deepcopy(previous.get('accepted')) if previous else None
    unaffected = proposal.get('unaffected_lines', {})
    if not isinstance(unaffected, Mapping) or any(not isinstance(k, str) or not isinstance(v, str) or not v.strip()
                                                  for k, v in unaffected.items()):
        raise ValueError('unaffected_lines must explicitly map prepared line IDs to unchanged scope reasons')
    if unaffected and not accepted:
        raise ValueError('unchanged work needs an actual earlier accepted task brief')
    if unaffected and previous and previous['status'] == 'REVOKED':
        raise ValueError('revoked authority cannot be carried as unchanged scope')
    if unaffected:
        from .codex_session import _line_dir, _read_json
        for line_id in unaffected:
            _read_json(_line_dir(root, line_id) / 'line.json')
    history = list(previous['history']) if previous else []
    if previous:
        history.append({'revision': previous['revision'], 'brief_sha256': previous['brief_sha256'],
                        'confirmation': previous['confirmation'], 'change_to_next': reason,
                        'change_kind': change_kind})
        if change_kind == 'non_material' and previous['status'] == 'CONFIRMED':
            if any(q['blocking'] and not q.get('answer') for q in questions):
                raise ValueError('new unresolved decisions cannot carry an earlier confirmation')
            confirmation = deepcopy(previous['confirmation'])
            confirmation['applies_to_revision'] = revision
            confirmation['applies_to_brief_sha256'] = _digest(brief)
            confirmation.setdefault('carry_reasons', []).append(reason)
    value = {'format': FORMAT, 'request_sha256': session['request_sha256'],
             'revision': revision, 'brief': brief, 'brief_sha256': _digest(brief),
             'questions': questions, 'confirmation': confirmation, 'history': history,
             'accepted': accepted, 'unaffected_lines': dict(unaffected),
             'latest_change': {'kind': change_kind, 'reason': reason},
             'status': 'CONFIRMED' if confirmation else 'AWAITING_USER',
             'updated_wall_ns': time.time_ns(),
             'record_basis': 'model-authored interpretation; user replies recorded by operator, not authenticated by helper'}
    _write_json(root / 'foundation.json', value)
    return value


def answer_foundation(root: Path, question_id: str, *, revision: int, user_text: str,
                      source: str, effect: str, change_kind: str = 'material') -> dict[str, Any]:
    from .codex_session import _write_json
    from .codex_lifecycle import require_open_decision, consume_decision_message
    root, _ = _context(root)
    decision_context = require_open_decision(root, user_text=user_text, source=source)
    value = load_foundation(root)
    if type(revision) is not int or revision != value['revision']:
        raise ValueError('answer must identify the revision containing the actual question answered')
    if change_kind not in {'material', 'non_material'}:
        raise ValueError('answer change_kind must be material or non_material')
    question = next((q for q in value['questions'] if q['id'] == question_id), None)
    if question is None:
        raise ValueError('unknown current decision question')
    question['answer'] = {'user_text': _reply_text(user_text),
                          'source': require_nonempty_text('reply source', source),
                          'effect': require_nonempty_text('actual consequence', effect),
                          'recorded_at_revision': value['revision']}
    # A substantive correction takes effect before any subsequent proposal is
    # written. Merely recording an effect must not leave old execution open.
    if change_kind == 'material':
        value['confirmation'] = None
        value['unaffected_lines'] = {}
        value['status'] = 'REVISION_REQUIRED'
    elif not value['confirmation'] and value['status'] != 'REVISION_REQUIRED':
        value['status'] = 'AWAITING_USER'
    value['latest_change'] = {'kind': change_kind, 'reason': effect}
    value['updated_wall_ns'] = time.time_ns()
    _write_json(root / 'foundation.json', value)
    if decision_context.get('managed') is not False:
        consume_decision_message(root, message_id=decision_context['current_message']['id'],
            user_text=user_text, source=source, kind='answer', reason=effect)
    return value


def confirm_foundation(root: Path, *, revision: int, user_text: str,
                       source: str) -> dict[str, Any]:
    from .codex_session import _write_json
    from .codex_lifecycle import require_open_decision, consume_decision_message
    root, _ = _context(root)
    decision_context = require_open_decision(root, user_text=user_text, source=source)
    value = load_foundation(root)
    if type(revision) is not int or revision != value['revision']:
        raise ValueError('confirmation must identify the current presented revision')
    if value['status'] in {'REVISION_REQUIRED', 'REVOKED'}:
        raise ValueError('apply the user correction to the task brief with propose before confirming it')
    pending = [q['id'] for q in value['questions'] if q['blocking'] and not q.get('answer')]
    if pending:
        raise ValueError('unresolved user decisions: ' + ', '.join(pending))
    value['confirmation'] = {
        'user_confirmed_revision': revision, 'applies_to_revision': revision,
        'brief_sha256': value['brief_sha256'],
        'applies_to_brief_sha256': value['brief_sha256'],
        'user_text': _reply_text(user_text),
        'source': require_nonempty_text('decision source', source),
        'basis': 'operator-recorded explicit user decision; not semantic approval by helper',
    }
    value['status'] = 'CONFIRMED'
    value['accepted'] = {'revision': revision, 'brief': deepcopy(value['brief']),
                         'brief_sha256': value['brief_sha256'],
                         'confirmation': deepcopy(value['confirmation'])}
    value['unaffected_lines'] = {}
    value['updated_wall_ns'] = time.time_ns()
    _write_json(root / 'foundation.json', value)
    if decision_context.get('managed') is not False:
        consume_decision_message(root, message_id=decision_context['current_message']['id'],
            user_text=user_text, source=source, kind='confirm', reason='recorded explicit decision on the presented task')
    return value


def revoke_foundation(root: Path, *, user_text: str, source: str, reason: str) -> dict[str, Any]:
    """Invalidate managed execution now; keep the original decision as history.

    The supplied message is an operator-recorded source, not authenticated
    consent. A STOP or correction cannot be neutralized by an old JSON flag.
    """
    from .codex_session import _write_json
    root, _ = _context(root)
    value = load_foundation(root)
    notice = {'user_text': _reply_text(user_text),
              'source': require_nonempty_text('revocation source', source),
              'reason': require_nonempty_text('revocation reason', reason),
              'revision': value['revision'], 'recorded_wall_ns': time.time_ns()}
    value.setdefault('revocations', []).append(notice)
    value['confirmation'] = None
    value['unaffected_lines'] = {}
    value['status'] = 'REVOKED'
    value['latest_change'] = {'kind': 'material', 'reason': notice['reason']}
    value['updated_wall_ns'] = notice['recorded_wall_ns']
    _write_json(root / 'foundation.json', value)
    return value


def require_foundation_ready(root: Path, *, owner: str | None = None) -> dict[str, Any]:
    value = load_foundation(root)
    confirmation = value.get('confirmation')
    if value['status'] == 'REVOKED':
        raise ValueError('task decision was revoked; old accepted scope cannot restart execution')
    if confirmation and confirmation.get('applies_to_brief_sha256') != value['brief_sha256']:
        raise ValueError('confirmation is not bound to the current brief; use its pinned toolchain or establish a current decision')
    if value['status'] != 'CONFIRMED' or not confirmation or confirmation.get('applies_to_revision') != value['revision']:
        accepted = value.get('accepted')
        reason = value.get('unaffected_lines', {}).get(owner)
        if reason and accepted:
            return {'status': 'CONFIRMED_UNCHANGED_SCOPE', 'accepted': accepted,
                    'continuation_reason': reason, 'pending_revision': value['revision']}
        raise ValueError('task brief awaits explicit user confirmation; continue foundation research, not full execution')
    if any(q['blocking'] and not q.get('answer') for q in value['questions']):
        raise ValueError('task brief has unresolved user decisions')
    return value


def foundation_packet(root: Path) -> str:
    """One readable current entry; also usable as the execution prompt source."""
    root, _ = _context(root)
    value = load_foundation(root)
    parts = [f"# 任务说明 v{value['revision']} · {value['status']}",
             '用户原话保存在REQUEST.txt。以下是可修订解释；事实、推断、提议和已确认决定须按原身份理解。']
    accepted = value.get('accepted')
    if accepted and value['status'] == 'CONFIRMED' and accepted['brief'].get('basis') != value['brief'].get('basis'):
        parts += [f"## 已接受的基础（v{accepted['revision']}）", _present(accepted['brief']['basis']),
                  '以下基础栏是当前观察维护，不扩大原执行决定；改变依赖、用途或投入须实质修订。']
    if accepted and value['status'] != 'CONFIRMED':
        parts += [f"## 沿用与待决变化（上次接受 v{accepted['revision']}）",
                  value['latest_change']['reason']]
        for key, title in BRIEF_FIELDS.items():
            old, new = accepted['brief'][key], value['brief'][key]
            if old != new:
                before = _present(old)
                parts += ['### ' + title + ' · 原已接受内容', before]
        if value.get('unaffected_lines'):
            parts += ['仍在原确认范围内的工作（作者明确划定，不包含待决变更）：',
                      _present(value['unaffected_lines'])]
    for key, title in BRIEF_FIELDS.items():
        item = value['brief'][key]
        body = _present(item)
        parts += ['## ' + title, body]
    parts.append('## 需要用户决定')
    for q in value['questions']:
        parts += [f"### {q['id']} · {q['question']}", q['why']]
        parts += [f'{i}. {option}' for i, option in enumerate(q['options'], 1)]
        if q.get('answer'):
            answer = q['answer']
            parts += ['用户答复：' + answer['user_text'], '实际处理：' + answer['effect'], '来源：' + answer['source']]
        else:
            parts.append('待答；可直接用自己的话纠正。')
    if not value['questions']:
        parts.append('沿用已有明确决定；没有重要变化时直接续做。' if value['status'] == 'CONFIRMED'
                     else '暂无逐项待决分歧；当前整体说明仍待明确执行决定。')
    confirmation = value['confirmation']
    if confirmation:
        decision = (f"用户明确决定（原接受 v{confirmation['user_confirmed_revision']}，"
                    f"当前适用 v{confirmation['applies_to_revision']}）：\n{confirmation['user_text']}\n"
                    f"来源：{confirmation['source']}")
        if confirmation.get('carry_reasons'):
            decision += '\n非实质维护：' + '；'.join(confirmation['carry_reasons'])
    else:
        decision = '尚未获得对当前变化/完整说明的明确执行决定；先处理问答，不全面执行待决范围。'
    parts += ['## 当前决定', decision,
              '按这份说明执行时，以完整可用结果组织工作。中间文件、代理结束和参数次数不替代约定成品。'
              '已确认续做只研究相关变化；重要目标、路线或成本变化须先讨论。'
              '脚本记录与可执行入口检查不等于意图正确、用户身份认证或宿主全局拦截。']
    return '\n\n'.join(parts).rstrip() + '\n'
