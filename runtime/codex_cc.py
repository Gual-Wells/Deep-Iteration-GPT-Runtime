"""Community Cry's pinned evidence pool and task-specific finding interface."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import urlsplit

from .validation import require_nonempty_text

POOL_PATH = 'codex/COMMUNITY_CRY.json'
_SOURCE_KINDS = {'community', 'digr_research', 'community_method', 'calibration'}
_CODE = re.compile(r'[a-z][a-z0-9-]{0,79}')


def enabled(p_run: str) -> bool:
    version = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)@[0-9a-f]{40}', p_run)
    return bool(version and tuple(map(int, version.groups())) >= (2, 2, 0))


def _index(rows: list[dict], label: str) -> dict[str, dict]:
    if not isinstance(rows, list) or not rows:
        raise ValueError(f'CC requires actual {label}')
    result = {}
    for row in rows:
        identifier = require_nonempty_text(f'CC {label} id', row['id'])
        if not _CODE.fullmatch(identifier) or identifier in result:
            raise ValueError(f'Invalid or duplicate CC {label} id: {identifier}')
        result[identifier] = row
    return result


def _category_ids(value: Any, categories: Mapping) -> list[str]:
    if (not isinstance(value, list) or not value
            or any(not isinstance(item, str) or item not in categories for item in value)
            or len(set(value)) != len(value)):
        raise ValueError('CC requires unique category IDs from the pinned pool')
    return list(value)


def load_pool(path: Path | None = None) -> dict:
    source = path if path is not None else Path(__file__).resolve().parents[1] / POOL_PATH
    raw = source.read_bytes()
    value = json.loads(raw)
    if value.get('schema_version') != 1:
        raise ValueError('Unsupported CC pool schema')
    require_nonempty_text('CC pool revision', value['revision'])
    for key in ('collected_on', 'method', 'coverage'):
        require_nonempty_text(f'CC pool scope {key}', value['scope'][key])
    categories = _index(value['categories'], 'categories')
    sources = _index(value['sources'], 'sources')
    for row in categories.values():
        for key in ('title', 'signal', 'legitimate', 'repair'):
            require_nonempty_text(f'CC category {key}', row[key])
    urls, community_categories = set(), set()
    for row in sources.values():
        for key in ('venue', 'title', 'observation'):
            require_nonempty_text(f'CC source {key}', row[key])
        url = urlsplit(require_nonempty_text('CC source URL', row['url']))
        if url.scheme != 'https' or not url.hostname or url.username or row['url'] in urls:
            raise ValueError('CC evidence needs distinct public HTTPS source links')
        urls.add(row['url'])
        ids = _category_ids(row['categories'], categories)
        if row['kind'] not in _SOURCE_KINDS:
            raise ValueError(f"Unknown CC evidence kind: {row['kind']}")
        if row['kind'] == 'community':
            if row.get('attribution') not in {'reported', 'unresolved'}:
                raise ValueError('CC community reports must preserve attribution uncertainty')
            community_categories.update(ids)
    if community_categories != categories.keys():
        raise ValueError('Each CC category requires a traceable community report')
    return {**value, 'sha256': sha256(raw).hexdigest()}


def search_pool(pool: Mapping, *, category: str | None = None, query: str | None = None,
                kind: str | None = None) -> dict:
    categories = _index(pool['categories'], 'categories')
    if category:
        _category_ids([category], categories)
    if kind and kind not in _SOURCE_KINDS:
        raise ValueError('Unknown CC evidence kind')
    terms = (query or '').casefold().split()
    results = []
    for row in pool['sources']:
        if (category and category not in row['categories']) or (kind and row['kind'] != kind):
            continue
        searchable = ' '.join([row['id'], row['venue'], row['title'], row['observation'],
                               *(categories[item]['title'] for item in row['categories'])]).casefold()
        if all(term in searchable for term in terms):
            results.append(row)
    return {'revision': pool['revision'], 'sha256': pool['sha256'], 'count': len(results),
            'categories': [categories[category]] if category else list(categories.values()),
            'sources': results}


def assess(pool: Mapping, supplied: Mapping) -> dict:
    """Normalize a public, host-authored finding. The host reasons about applicability."""
    categories = _index(pool['categories'], 'categories')
    ids = _category_ids(supplied.get('categories'), categories)
    fields = ('excerpt', 'requirement', 'impact', 'repair', 'boundary_check')
    finding = {key: require_nonempty_text(f'CC {key}', supplied.get(key)) for key in fields}
    protected = supplied.get('protected_basis')
    if protected is not None:
        protected = require_nonempty_text('CC applicable protected basis', protected)
    return {**finding, 'categories': ids, 'protected_basis': protected,
            'disposition': 'PROTECTED' if protected else 'ACTIONABLE',
            'pool_revision': pool['revision'], 'pool_sha256': pool['sha256'],
            'semantic_basis': 'HOST_ASSERTED',
            'criteria': [categories[item] for item in ids]}
