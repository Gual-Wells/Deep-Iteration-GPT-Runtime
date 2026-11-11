"""Source-bound ESP cases and recorded semantic judgements.

This module checks references and explicit records, not linguistic usefulness,
reviewer independence, learner mastery or transfer. Old schema-1 books need no
learning contract and are never migrated by a read.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from runtime import codex_preprint as core


_DECISIONS = {'useful', 'revise', 'reject'}
_RELATIONS = {'exact-use', 'handling-function', 'contrastive-use'}
_NOT_CONTENT = {'learning_reviews', 'receipts', 'revision', 'integrity_sha256'}
_FORBIDDEN = {'learner_mastery', 'mastery_score', 'learner_evidence'}


def _object(value, label):
    core.need(isinstance(value, dict), label + ' must be an object')
    return value


def _fields(value, allowed, label):
    _object(value, label)
    core.need(not (set(value) - set(allowed)), label + ' has unsupported fields: ' +
              ', '.join(sorted(set(value) - set(allowed))))


def _no_mastery(value):
    if isinstance(value, dict):
        core.need(not (_FORBIDDEN & value.keys()),
                  'learning materials do not create learner mastery or learner evidence')
        for child in value.values():
            _no_mastery(child)
    elif isinstance(value, list):
        for child in value:
            _no_mastery(child)


def _key(value, label):
    core.need(isinstance(value, str) and core.KEY.fullmatch(value), 'invalid ' + label)
    return value


def validate_spec(spec):
    """Validate only the optional learning_contract; no domain effectiveness gate.

    Useful explicit domains include edge-ai-inference-interview,
    international-daily, mainland-foreign-company, ielts-listening-speaking and
    ielts-argument-writing. Other substantive domains remain possible.
    """
    _object(spec, 'spec')
    if 'learning_contract' not in spec:
        return
    item = spec['learning_contract']
    _no_mastery(item)
    _fields(item, {'schema_version', 'target_domain', 'why_relevant',
                   'difficulty_focus', 'intended_uses'}, 'learning contract')
    core.need(type(item.get('schema_version')) is int and item['schema_version'] == 1,
              'unsupported learning contract schema')
    for field in ('target_domain', 'why_relevant', 'difficulty_focus'):
        core.text(item.get(field), 'learning contract ' + field)
    uses = item.get('intended_uses')
    core.need(isinstance(uses, list) and uses, 'learning contract needs intended uses')
    for value in uses:
        core.text(value, 'intended use')


def content_digest(state):
    """Bind all current content, including future actor/perturbation fields.

    A review or receipt cannot stale itself. All other top-level fields are
    included deliberately; future content does not need a new allowlist.
    """
    return core.digest({k: v for k, v in state.items() if k not in _NOT_CONTENT})


def _public_events(state):
    # Use the publisher's exact public projection without an import-time cycle.
    from runtime import codex_preprint_export as publisher
    return publisher._public_events(state)


def _cases(state):
    items = state.get('learning_cases', [])
    core.need(isinstance(items, list), 'learning cases must be a list')
    return items


def _fragment(state, ids):
    core.need(isinstance(ids, list) and ids and all(isinstance(eid, str) for eid in ids)
              and len(set(ids)) == len(ids),
              'case needs unique ordered public event ids')
    public = _public_events(state)
    positions = {event['id']: n for n, event in enumerate(public)}
    core.need(all(isinstance(eid, str) and eid in positions for eid in ids),
              'case refers to a non-public or absent source event')
    start = positions[ids[0]]
    fragment = public[start:start + len(ids)]
    core.need([event['id'] for event in fragment] == ids,
              'case must retain a continuous public exchange in source order')
    core.need(sum(event['kind'] == 'speech' for event in fragment) >= 2,
              'case needs an exchange with at least two speech turns')
    return deepcopy(fragment)


def _usage(item, fragment):
    _no_mastery(item)
    _fields(item, {'event_id', 'surface', 'start', 'meaning', 'function', 'conditions',
                   'register', 'frequency_status', 'variants', 'public_sources'}, 'case usage')
    by_id = {event['id']: event for event in fragment if event['kind'] == 'speech'}
    event = by_id.get(item.get('event_id'))
    core.need(event is not None, 'usage must refer to speech inside its public exchange')
    surface = core.text(item.get('surface'), 'actual language span')
    start = item.get('start')
    if start is None:
        core.need(event['text'].count(surface) == 1,
                  'absent or ambiguous usage span; supply its exact start when repeated')
        start = event['text'].index(surface)
    core.need(type(start) is int and start >= 0 and
              event['text'][start:start + len(surface)] == surface,
              'usage span absent from the selected public utterance')
    result = {key: core.text(item.get(key), 'usage ' + key) for key in
              ('meaning', 'function', 'conditions', 'register', 'frequency_status')}
    result.update(event_id=event['id'], surface=surface, start=start,
                  end=start + len(surface), source_sha256=core.digest(event))
    variants = item.get('variants', [])
    core.need(isinstance(variants, list), 'usage variants must be a list')
    result['variants'] = []
    for variant in variants:
        _fields(variant, {'text', 'explanation'}, 'authored variant')
        result['variants'].append({key: core.text(variant.get(key), 'variant ' + key)
                                   for key in ('text', 'explanation')})
    sources = item.get('public_sources', [])
    core.need(isinstance(sources, list), 'public use sources must be a list')
    result['public_sources'] = []
    for source in sources:
        _fields(source, {'label', 'url'}, 'public use source')
        label = core.text(source.get('label'), 'public source label')
        url = core.text(source.get('url'), 'public source URL')
        parsed = urlsplit(url)
        core.need(parsed.scheme in {'https', 'http'} and parsed.netloc and
                  parsed.username is None and parsed.password is None,
                  'public source must be an HTTP(S) URL without credentials')
        result['public_sources'].append({'label': label, 'url': url})
    return result


def _case(state, item):
    _no_mastery(item)
    _fields(item, {'id', 'cue', 'intent', 'why_hard', 'what_changed', 'event_ids',
                   'usage'}, 'learning case')
    result = {'id': _key(item.get('id'), 'case id')}
    result.update({key: core.text(item.get(key), 'case ' + key) for key in
                   ('cue', 'intent', 'why_hard', 'what_changed')})
    fragment = _fragment(state, item.get('event_ids'))
    result['event_ids'] = [event['id'] for event in fragment]
    result['public_fragment'] = fragment
    result['fragment_sha256'] = core.digest(fragment)
    uses = item.get('usage')
    core.need(isinstance(uses, list) and uses, 'case needs source-bound usage explanations')
    result['usage'] = [_usage(use, fragment) for use in uses]
    return result


def _validate_case_binding(state, item):
    fragment = _fragment(state, item.get('event_ids'))
    core.need(fragment == item.get('public_fragment') and
              core.digest(fragment) == item.get('fragment_sha256'),
              'learning case source fragment changed; re-anchor the actual exchange')
    by_id = {event['id']: event for event in fragment if event['kind'] == 'speech'}
    for use in item['usage']:
        event = by_id.get(use['event_id'])
        core.need(event is not None and core.digest(event) == use['source_sha256'] and
                  event['text'][use['start']:use['end']] == use['surface'],
                  'learning usage source changed; re-anchor the actual span')


def _endpoint(state, case_id, surface=None, event_id=None):
    case = next((c for c in _cases(state) if c['id'] == case_id), None)
    core.need(case is not None, 'series relation refers to an absent learning case')
    _validate_case_binding(state, case)
    result = {'book_id': state['spec']['id'], 'book_title': state['spec']['title'],
              'case_id': case_id, 'case_sha256': core.digest(case),
              'fragment_sha256': case['fragment_sha256']}
    if surface is not None:
        matches = [use for use in case['usage'] if use['surface'] == surface and
                   (event_id is None or use['event_id'] == event_id)]
        core.need(len(matches) == 1,
                  'series relation needs one real use; specify its event id if ambiguous')
        use = matches[0]
        result.update(surface=surface, event_id=use['event_id'], start=use['start'],
                      end=use['end'], use_sha256=core.digest(use))
    else:
        core.need(event_id is None, 'series relation event id needs an actual surface')
    return result


def _relation(root, state, item):
    _no_mastery(item)
    _fields(item, {'id', 'kind', 'source_case_id', 'target_root', 'target_case_id',
                   'source_surface', 'target_surface', 'source_event_id', 'target_event_id',
                   'explanation', 'differences'},
            'series relation')
    kind = item.get('kind')
    core.need(kind in _RELATIONS, 'invalid series relation kind')
    target_root = Path(core.text(item.get('target_root'), 'actual target book root')).resolve()
    target = state if target_root == Path(root).resolve() else core.load(target_root)
    source_surface, target_surface = item.get('source_surface'), item.get('target_surface')
    if kind in {'exact-use', 'contrastive-use'}:
        core.text(source_surface, 'source surface for use relation')
        core.text(target_surface, 'target surface for use relation')
    if kind == 'exact-use':
        core.need(source_surface == target_surface,
                  'exact-use requires the same actual surface; other relations remain available')
    source = _endpoint(state, item.get('source_case_id'), source_surface, item.get('source_event_id'))
    target_binding = _endpoint(target, item.get('target_case_id'), target_surface, item.get('target_event_id'))
    if kind == 'exact-use':
        core.need(tuple(source.get(key) for key in ('book_id', 'event_id', 'start', 'end')) !=
                  tuple(target_binding.get(key) for key in ('book_id', 'event_id', 'start', 'end')),
                  'exact-use needs a different actual occurrence, not the same source span again')
    return {'id': _key(item.get('id'), 'relation id'), 'kind': kind,
            'source': source, 'target': target_binding,
            'target_root': target_root.as_posix(),
            'explanation': core.text(item.get('explanation'), 'relation explanation'),
            'differences': core.text(item.get('differences'), 'relation differences'),
            'semantic_certification': False}


def add_cases(root, payload, *, expected_revision, operation_id):
    """Save selected continuous public exchanges and explicitly authored review prose.

    Existing ids require replace=True. A relation's target_root is read only to
    bind a real case; it remains creator metadata and is not rendered publicly.
    Exact-use checks literal recurrence, never sameness of meaning. Inflected or
    otherwise different forms can be compared as another explicit relation.
    """
    _no_mastery(payload)
    _fields(payload, {'cases', 'series_relations', 'replace'}, 'learning case input')
    incoming, relations = payload.get('cases', []), payload.get('series_relations', [])
    core.need(isinstance(incoming, list) and isinstance(relations, list) and
              (incoming or relations), 'provide actual cases or series relations')
    replace = payload.get('replace', False)
    core.need(type(replace) is bool, 'replace must be boolean')

    def change(state):
        validate_spec(state['spec'])
        cases = [_case(state, item) for item in incoming]
        core.need(len({c['id'] for c in cases}) == len(cases), 'duplicate incoming case id')
        existing = {case['id']: case for case in _cases(state)}
        for case in cases:
            core.need(replace or case['id'] not in existing,
                      'case id exists; use replace=True for an explicit revision')
            existing[case['id']] = case
        state['learning_cases'] = list(existing.values())
        new_relations = [_relation(root, state, item) for item in relations]
        core.need(len({r['id'] for r in new_relations}) == len(new_relations),
                  'duplicate incoming relation id')
        old_relations = {r['id']: r for r in state.get('series_relations', [])}
        for relation in new_relations:
            core.need(replace or relation['id'] not in old_relations,
                      'relation id exists; use replace=True for an explicit revision')
            old_relations[relation['id']] = relation
        state['series_relations'] = list(old_relations.values())
        return {'case_ids': [case['id'] for case in cases],
                'relations_added': len(new_relations),
                'content_sha256': content_digest(state), 'learner_evidence_added': 0,
                'semantic_certification': False}
    return core._mutate(root, payload, expected_revision, operation_id, change)


def review(root, payload, *, expected_revision, operation_id):
    """Record a substantive operator judgement bound to the content they selected.

    reviewer is an attribution, not host authentication. useful is a recorded
    judgement, never a tool-generated statement about quality or learner gain.
    """
    _no_mastery(payload)
    _fields(payload, {'decision', 'reviewer', 'reason', 'case_findings',
                      'content_sha256'}, 'learning review input')

    def change(state):
        cases = _cases(state)
        for case in cases:
            _validate_case_binding(state, case)
        core.need(status(state)['bindings_current'],
                  'learning relation source changed; re-anchor the actual cases before reviewing')
        current = content_digest(state)
        core.need(payload.get('content_sha256') == current,
                  'learning review content changed; read the current material before reviewing')
        decision = payload.get('decision')
        core.need(decision in _DECISIONS, 'review decision must be useful, revise or reject')
        findings = payload.get('case_findings')
        core.need(isinstance(findings, list), 'review needs substantive case findings')
        ids = {case['id'] for case in cases}
        seen = set()
        for finding in findings:
            _fields(finding, {'case_id', 'judgment', 'reason'}, 'case finding')
            case_id = finding.get('case_id')
            core.need(case_id in ids and case_id not in seen,
                      'case finding must identify a distinct current public case')
            seen.add(case_id)
            core.need(finding.get('judgment') in _DECISIONS, 'invalid case judgement')
            core.text(finding.get('reason'), 'specific case finding')
        core.need(seen == ids, 'review must address every current learning case')
        if decision == 'useful':
            core.need(cases and all(f['judgment'] == 'useful' for f in findings),
                      'a useful judgement needs actual cases and consistent case findings')
        item = {'decision': decision, 'reviewer': core.text(payload.get('reviewer'), 'reviewer'),
                'reason': core.text(payload.get('reason'), 'substantive review reason'),
                'case_findings': deepcopy(findings), 'content_sha256': current,
                'recorded_at': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                'semantic_certification': False}
        state.setdefault('learning_reviews', []).append(item)
        return {'review_index': len(state['learning_reviews']) - 1,
                'decision': decision, 'content_sha256': current,
                'semantic_certification': False, 'learner_evidence_added': 0}
    return core._mutate(root, payload, expected_revision, operation_id, change)


def status(state, *, check_relation_targets=True):
    """Report record freshness, following only already-bound source references.

    Search can disable target reads to respect its explicit root list; it then
    reports linked_sources_current=None when relations have not been checked.
    """
    required = 'learning_contract' in state.get('spec', {})
    validate_spec(state['spec'])
    current = content_digest(state)
    cases = _cases(state)
    reviews = state.get('learning_reviews', [])
    latest = reviews[-1] if reviews else None
    matching = bool(latest and latest.get('content_sha256') == current)
    bindings_current = True
    try:
        for case in cases:
            _validate_case_binding(state, case)
    except (ValueError, KeyError, TypeError):
        bindings_current = False
    case_hashes = {case['id']: core.digest(case) for case in cases}
    relations_current = all(relation.get('source', {}).get('case_sha256') ==
                            case_hashes.get(relation.get('source', {}).get('case_id'))
                            for relation in state.get('series_relations', []))
    bindings_current = bindings_current and relations_current
    linked_current = None if state.get('series_relations') and not check_relation_targets else True
    if check_relation_targets:
        for relation in state.get('series_relations', []):
            try:
                target = core.load(relation['target_root'])
                case = next((c for c in _cases(target) if c['id'] == relation['target']['case_id']), None)
                core.need(case is not None, 'linked case is absent')
                _validate_case_binding(target, case)
                core.need(core.digest(case) == relation['target']['case_sha256'], 'linked case changed')
            except (OSError, ValueError, KeyError, TypeError):
                linked_current = False
    bindings_current = bindings_current and linked_current is not False
    decision = latest.get('decision') if matching else None
    label = ('NOT_REQUIRED' if not required and not cases else
             'NEEDS_CASES' if not cases else 'INVALID_CASE_SOURCE' if not bindings_current else
             'UNREVIEWED' if latest is None else 'STALE_REVIEW' if not matching else 'CURRENT_REVIEW')
    return {'required': required, 'status': label, 'content_sha256': current,
            'case_count': len(cases), 'bindings_current': bindings_current,
            'linked_sources_current': linked_current,
            'review_current': matching and bindings_current,
            'decision': decision if bindings_current else None,
            'needs_review': (required or bool(cases)) and (not matching or not bindings_current),
            'needs_revision': matching and decision in {'revise', 'reject'},
            'semantic_certification': False, 'learner_evidence_added': 0}


def _quote(value):
    return '\n'.join('> ' + line for line in value.split('\n'))


def _line(value):
    return ' '.join(value.split())


def review_markdown(state, public_events):
    """Render only explicit public projections and authored public-use prose."""
    core.need(public_events == _public_events(state),
              'review requires the exact current public event projection')
    core.need(status(state)['bindings_current'],
              'learning case or relation source changed; re-anchor before rendering')
    names = {actor['id']: actor['name'] for actor in state['spec']['actors']}
    parts = ['# ' + _line(state['spec']['title']) + ' · 处境与表达回看',
             '这些资料帮助回到真实原句和往返；它们不记录听者已经掌握了什么。']
    for case in _cases(state):
        _validate_case_binding(state, case)
        parts.extend(['## ' + _line(case['cue']), '此时要做的事：' + case['intent'],
                      '难处：' + case['why_hard'], '### 回到原来的往返'])
        for event in case['public_fragment']:
            who = '公开观察' if event['kind'] == 'observation' else names[event['actor']]
            if event['kind'] == 'action':
                who += ' · 动作'
            parts.extend(['**' + _line(who) + '**', _quote(event['text'])])
        parts.extend(['这段实际发生的变化：' + case['what_changed'], '### 措辞与使用条件'])
        for use in case['usage']:
            parts.extend(['**' + use['surface'] + '**', '这里的意思：' + use['meaning'],
                          '表达作用：' + use['function'], '使用条件：' + use['conditions'],
                          '语域：' + use['register'], '频率依据：' + use['frequency_status']])
            for variant in use['variants']:
                parts.extend(['回看作者的变式，非角色原句：' + variant['text'], variant['explanation']])
            for source in use['public_sources']:
                parts.append('用法来源：[' + source['label'] + '](' + source['url'] + ')')
        for relation in state.get('series_relations', []):
            if relation['source']['case_id'] == case['id']:
                label = {'exact-use': '相同原文措辞的用法比较',
                         'handling-function': '相近处境处理，不计作词块复现',
                         'contrastive-use': '用法对照，保留差别'}[relation['kind']]
                parts.extend([label + '：' + _line(relation['target']['book_title']),
                              relation['explanation'], '差别：' + relation['differences'],
                              '目标片段依据：' + relation['target']['book_id'] + ' / ' +
                              relation['target']['case_id'] + ' / ' + relation['target']['fragment_sha256']])
        parts.append('原句出处：' + state['spec']['id'] + ' / ' + case['id'] + ' / ' +
                     ', '.join(case['event_ids']) + '\n\n片段 SHA256：' + case['fragment_sha256'])
    return '\n\n'.join(parts) + '\n'


def find(roots, query, *, limit=20):
    """Search only explicitly supplied books, returning real current source spans.

    Relation semantics are attributed judgements. Targets are not followed or
    scanned implicitly; included target roots can establish current bindings.
    """
    core.text(query, 'situation, intent or expression query')
    core.need(type(limit) is int and limit > 0, 'search limit must be positive')
    if isinstance(roots, (str, Path)):
        roots = [roots]
    core.need(isinstance(roots, (list, tuple)) and roots, 'supply actual book roots')
    books = []
    for root in dict.fromkeys(str(Path(root).resolve()) for root in roots):
        state = core.load(root)
        books.append((root, state))
    target_cases = {(Path(root).as_posix().casefold(), case['id']): core.digest(case)
                    for root, state in books for case in _cases(state)}
    needle = query.casefold()
    results = []
    for root, state in books:
        for case in _cases(state):
            _validate_case_binding(state, case)
            searchable = [case[key] for key in ('cue', 'intent', 'why_hard', 'what_changed')]
            searchable += [use[key] for use in case['usage'] for key in
                           ('surface', 'meaning', 'function', 'conditions', 'register')]
            searchable += [event['text'] for event in case['public_fragment']]
            searchable += [variant[key] for use in case['usage'] for variant in use['variants']
                           for key in ('text', 'explanation')]
            if not any(needle in value.casefold() for value in searchable):
                continue
            relations = []
            for relation in state.get('series_relations', []):
                if relation['source']['case_id'] != case['id']:
                    continue
                public = {key: deepcopy(value) for key, value in relation.items() if key != 'target_root'}
                target = relation['target']
                target_key = Path(relation['target_root']).resolve().as_posix().casefold()
                actual = target_cases.get((target_key, target['case_id']))
                public['target_binding'] = ('NOT_INCLUDED' if actual is None else
                                             'CURRENT_CASE' if actual == target['case_sha256'] else 'CHANGED_CASE')
                relations.append(public)
            review_state = status(state, check_relation_targets=False)
            if relations:
                bindings = [r['target_binding'] for r in relations]
                review_state['linked_sources_current'] = (False if 'CHANGED_CASE' in bindings else
                    None if 'NOT_INCLUDED' in bindings else True)
                if review_state['linked_sources_current'] is False:
                    review_state.update(status='INVALID_CASE_SOURCE', bindings_current=False,
                                        review_current=False, decision=None, needs_review=True)
            results.append({'root': Path(root).as_posix(), 'book_id': state['spec']['id'],
                            'title': state['spec']['title'], 'content_sha256': content_digest(state),
                            'case': deepcopy(case), 'review': review_state, 'series_relations': relations})
            if len(results) >= limit:
                return {'query': query, 'results': results, 'semantic_certification': False}
    return {'query': query, 'results': results, 'semantic_certification': False}
