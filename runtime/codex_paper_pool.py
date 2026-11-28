"""Read-only local search over author abstracts and source-bound Paper Pool notes."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import unicodedata
from urllib.parse import urlsplit

from . import codex_io


CATALOG_SCHEMA = 'digr.codex.paper-pool.catalog.v1'
SOURCES = ('abstracts', 'parents', 'extractions')
DIMENSIONS = ('modeling', 'method', 'idea', 'perspective', 'focus', 'design',
              'mathematics', 'historical_work', 'delta_or_variable')
EXTRACTION_FIELDS = ('type_description', 'original_relation', 'scope_or_limit',
                     'transfer_or_specific_disposition')
JOINED_FIELDS = ('paper_id', 'title', 'source_url', 'publication_date', 'topic',
                 'archive_path', 'archive_row')
PAPER_ID = re.compile(r'P[0-9]{4,}')
SHA256 = re.compile(r'[0-9a-f]{64}')
WORD_SEPARATOR = re.compile(r'[\W_]+')
ASCII_WORD = re.compile(r'[a-z0-9]')
BILINGUAL_TERMS = (
    ('车联网', 'internet of vehicles', 'internet of vehicle', 'vehicular network',
     'vehicular networks', 'vehicle networking', 'vanet', 'vanets'),
    ('车载边缘计算', 'vehicular edge computing'),
    ('任务卸载', '计算卸载', 'task offloading', 'task offload',
     'computation offloading', 'computational offloading'),
    ('边缘计算', 'edge computing'),
    ('李雅普诺夫', '李亚普诺夫', 'lyapunov'),
    ('时延', '延迟', 'latency', 'latencies', 'delay', 'delays'),
    ('联邦学习', 'federated learning'),
    ('模型分割', '模型切分', 'model partitioning', 'model splitting'),
    ('拆分推理', '切分推理', 'split inference'),
    ('语义通信', 'semantic communication', 'semantic communications'),
    ('资源分配', 'resource allocation'),
    ('卡尔曼滤波', 'kalman filter', 'kalman filters', 'kalman filtering'),
    ('粒子滤波', 'particle filter', 'particle filters', 'particle filtering'),
    ('队列', 'queue', 'queues'),
    ('排队', 'queueing', 'queuing'),
)
VARIANTS = {term: group for group in BILINGUAL_TERMS for term in group}


class PaperPoolCatalogError(ValueError):
    """The local catalog request or evidence snapshot could not be verified."""


@dataclass(frozen=True)
class _Paper:
    line: int
    author: dict
    dimensions: dict
    extraction: dict


@dataclass(frozen=True)
class _Term:
    text: str
    needle: str
    alternatives: tuple[tuple[str, re.Pattern | None], ...]


def _require(condition, message: str) -> None:
    if not condition:
        raise PaperPoolCatalogError(message)


def _text(row: dict, key: str, where: str) -> str:
    value = row.get(key)
    _require(isinstance(value, str) and value.strip(), f'{where}: missing or invalid {key}')
    return value


def _absolute_local(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    if os.name == 'nt':
        _require(re.fullmatch(r'[A-Za-z]:', path.drive), 'Paper Pool requires a local absolute path')
        _require(all(':' not in part for part in path.parts[1:]),
                 'Paper Pool paths cannot address alternate data streams')
    return path


def _check_file(path: Path, role: str, *, missing_ok: bool = False) -> bool:
    # Check before following any path component, including Windows junctions.
    for component in (*reversed(path.parents), path):
        try:
            details = component.lstat()
        except FileNotFoundError as error:
            if component == path and missing_ok:
                return False
            raise PaperPoolCatalogError(f'{role}: local path is missing') from error
        except OSError as error:
            raise PaperPoolCatalogError(f'{role}: cannot inspect local path') from error
        is_reparse = getattr(details, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        _require(not is_reparse and not stat.S_ISLNK(details.st_mode),
                 f'{role}: linked or reparse paths are unsupported')
        valid_kind = stat.S_ISREG if component == path else stat.S_ISDIR
        _require(valid_kind(details.st_mode), f'{role}: expected a local regular file')
    return True


def _source_paths(binding: Path, sources: dict[str, Path]) -> dict[str, Path]:
    _require('abstracts' in sources and set(sources) <= set(SOURCES), 'invalid Paper Pool source roles')
    paths = {role: _absolute_local(source) for role, source in sources.items()}
    if os.name == 'nt':
        _require(all(path.drive.casefold() == binding.drive.casefold() for path in paths.values()),
                 'Paper Pool sources and binding must use the same local Windows volume')
    identities = {os.path.normcase(str(path)) for path in (binding, *paths.values())}
    _require(len(identities) == len(paths) + 1, 'Paper Pool paths must be distinct')
    return paths


def _object(pairs: list[tuple[str, object]]) -> dict:
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError('duplicate JSON object field')
    return obj


def _read_file(path: Path, role: str) -> bytes:
    _check_file(path, role)
    try:
        return codex_io.read_bytes(path)
    except OSError as error:
        raise PaperPoolCatalogError(f'{role}: cannot read local file') from error


def _read_rows(path: Path, role: str, expected_sha: str | None) -> tuple[dict, str]:
    data = _read_file(path, role)
    actual = sha256(data).hexdigest()
    _require(expected_sha is None or actual == expected_sha,
             f'{role}: contents differ from the bound snapshot')
    rows = {}
    for line, raw in enumerate(io.BytesIO(data), 1):
        where = f'{role} line {line}'
        try:
            row = json.loads(raw.decode('utf-8-sig' if line == 1 else 'utf-8'),
                             object_pairs_hook=_object)
        except ValueError as error:
            raise PaperPoolCatalogError(f'{where}: invalid JSON') from error
        _require(isinstance(row, dict), f'{where}: expected a record')
        identity = _text(row, 'id', where)
        _require(PAPER_ID.fullmatch(identity) and identity[1:].strip('0'),
                 f'{where}: invalid Paper Pool ID')
        _require(identity not in rows, f'{where}: duplicate Paper Pool ID {identity}')
        rows[identity] = (line, row)
    _require(rows, f'{role}: catalog source is empty')
    return rows, actual


def _source_url_key(value: str, where: str) -> tuple:
    try:
        url = urlsplit(value)
        _require(url.scheme in ('https', 'http') and url.hostname and url.username is None,
                 f'{where}: invalid publication URL')
        return (url.scheme, url.netloc.casefold(), url.path, url.query)
    except ValueError as error:
        raise PaperPoolCatalogError(f'{where}: invalid publication URL') from error


def _is_offset(value: object) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(type(n) is int for n in value)


def _source_chunks(row: dict, where: str) -> dict:
    contents = row['abstract']
    chunks = row.get('chunks')
    _require(isinstance(chunks, list) and chunks, f'{where}: author chunks are missing')
    by_number = {}
    cursor = 0
    for chunk in chunks:
        _require(isinstance(chunk, dict), f'{where}: invalid author chunk')
        number, offsets = chunk.get('n'), chunk.get('offset')
        _require(type(number) is int and number > 0 and number not in by_number,
                 f'{where}: invalid or duplicate author sentence ID')
        _require(_is_offset(offsets), f'{where}: invalid author chunk offsets')
        start, end = offsets
        _require(cursor <= start < end <= len(contents) and not contents[cursor:start].strip()
                 and contents[start:end] == chunk.get('text'),
                 f'{where}: author chunk differs from the abstract at its offsets')
        by_number[number] = chunk
        cursor = end
    _require(not contents[cursor:].strip(), f'{where}: author chunks omit abstract text')
    return by_number


def _check_dimensions(genotype: object, chunks: dict, where: str) -> None:
    _require(isinstance(genotype, dict) and set(genotype) == set(DIMENSIONS),
             f'{where}: expected the nine dimensions')
    for name in DIMENSIONS:
        dimension = genotype[name]
        location = f'{where} dimension {name}'
        _require(isinstance(dimension, dict), f'{location}: invalid dimension')
        components = dimension.get('components')
        _require(isinstance(components, list)
                 and dimension.get('status') == ('populated' if components else 'evidence_missing'),
                 f'{location}: inconsistent status and components')
        if not components:
            _text(dimension, 'reason', location)
        for component in components:
            _require(isinstance(component, dict), f'{location}: invalid component')
            _text(component, 'statement', location)
            _require(component.get('provenance') in ('author_abstract', 'analyst_inference'),
                     f'{location}: invalid component provenance')
            numbers, offsets = component.get('author_sentence_ids'), component.get('offsets')
            _require(isinstance(numbers, list) and isinstance(offsets, list) and numbers
                     and len(numbers) == len(offsets)
                     and all(type(n) is int and n in chunks for n in numbers)
                     and len(numbers) == len(set(numbers))
                     and all(_is_offset(offset) and chunks[n]['offset'] == offset
                             for n, offset in zip(numbers, offsets)),
                     f'{location}: component anchors disagree with the author chunks')


def _check_extraction(extraction: dict, chunks: dict, where: str) -> None:
    _require(extraction.get('source_level') == 'author_abstract',
             f'{where}: expected an author-abstract extraction')
    for key in ('type', *EXTRACTION_FIELDS):
        _text(extraction, key, where)
    anchors = extraction.get('anchors')
    _require(isinstance(anchors, list) and anchors, f'{where}: extraction anchors are missing')
    seen = set()
    for anchor in anchors:
        number = anchor.get('n') if isinstance(anchor, dict) else None
        _require(type(number) is int and number in chunks and number not in seen
                 and _is_offset(anchor.get('offset'))
                 and all(anchor.get(key) == chunks[number][key] for key in ('offset', 'text')),
                 f'{where}: extraction anchor disagrees with its author chunk')
        seen.add(number)


def _join(rows: dict) -> dict[str, _Paper]:
    primary = rows['abstracts']
    for role in ('parents', 'extractions'):
        if role not in rows:
            continue
        missing = sorted(primary.keys() - rows[role].keys())
        extra = sorted(rows[role].keys() - primary.keys())
        _require(not missing and not extra,
                 f'{role}: Paper Pool ID inventory differs '
                 f'(missing {len(missing)}: {missing[:3]}, extra {len(extra)}: {extra[:3]})')

    indexes = {key: {} for key in ('publication ID', 'publication URL', 'abstract SHA-256',
                                   'archive record')}
    papers = {}
    for identity, (line, row) in primary.items():
        where = f'{identity} at abstracts line {line}'
        for key in JOINED_FIELDS[:-1]:
            _text(row, key, where)
        _require(type(row.get('archive_row')) is int and row['archive_row'] >= 0,
                 f'{where}: invalid archive row')
        try:
            source_sha = sha256(_text(row, 'abstract', where).encode('utf-8')).hexdigest()
        except UnicodeError as error:
            raise PaperPoolCatalogError(f'{where}: invalid Unicode in the author abstract') from error
        _require(row.get('abstract_sha256') == source_sha, f'{where}: abstract SHA-256 mismatch')
        unique = {'publication ID': row['paper_id'],
                  'publication URL': _source_url_key(row['source_url'], where),
                  'abstract SHA-256': source_sha,
                  'archive record': (row['archive_path'], row['archive_row'])}
        for label, key in unique.items():
            existing = indexes[label].get(key)
            _require(existing is None, f'{where}: duplicate {label} shared with {existing}')
            indexes[label][key] = identity

        parent_line, parent = rows.get('parents', {}).get(identity, (None, None))
        extraction_line, extraction = rows.get('extractions', {}).get(identity, (None, None))
        for role, record_line, record, hash_field in (
            ('parents', parent_line, parent, 'author_abstract_sha256'),
            ('extractions', extraction_line, extraction, 'abstract_sha256'),
        ):
            if record is None:
                continue
            mismatches = [key for key in JOINED_FIELDS
                          if type(record.get(key)) is not type(row[key]) or record[key] != row[key]]
            if record.get(hash_field) != source_sha:
                mismatches.append(hash_field)
            _require(not mismatches,
                     f'{identity} at {role} line {record_line}: disagrees on {", ".join(mismatches)}')

        chunks = _source_chunks(row, where)
        if parent is not None:
            _check_dimensions(parent.get('genotype'), chunks, f'{identity} at parents line {parent_line}')
        if extraction is not None:
            _check_extraction(extraction, chunks, f'{identity} at extractions line {extraction_line}')
        papers[identity] = _Paper(line, row, parent['genotype'] if parent else {}, extraction or {})
    return papers


def _load_sources(paths: dict[str, Path], hashes: dict | None = None) -> tuple[dict[str, _Paper], dict]:
    rows, actual = {}, {}
    for role, path in paths.items():
        rows[role], actual[role] = _read_rows(path, role, hashes[role] if hashes is not None else None)
    return _join(rows), actual


def _fingerprint(hashes: dict) -> str:
    canonical = json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode('ascii')
    return sha256(canonical).hexdigest()


def _read_binding(path: Path) -> tuple[dict[str, Path], dict]:
    raw = _read_file(path, 'binding')
    try:
        binding = json.loads(raw.decode('utf-8'), object_pairs_hook=_object)
    except ValueError as error:
        raise PaperPoolCatalogError('binding: invalid JSON') from error
    _require(isinstance(binding, dict) and binding.get('schema') == CATALOG_SCHEMA,
             'binding: unsupported catalog schema')
    sources = binding.get('sources')
    _require(isinstance(sources, dict) and set(sources) == set(SOURCES),
             'binding: invalid catalog sources')
    paths, hashes = {}, {}
    for role in SOURCES:
        item = sources[role]
        _require(isinstance(item, dict), f'binding: invalid {role} source')
        location = Path(_text(item, 'path', f'binding {role}'))
        _require(location.is_absolute(), f'binding: {role} path must be absolute')
        digest = _text(item, 'sha256', f'binding {role}')
        _require(SHA256.fullmatch(digest), f'binding: invalid {role} SHA-256')
        paths[role] = location
        hashes[role] = digest
    _require(binding.get('corpus_fingerprint') == _fingerprint(hashes),
             'binding: corpus fingerprint disagrees with source hashes')
    return _source_paths(path, paths), hashes


def _write_binding(path: Path, document: dict) -> None:
    staging = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.paper-pool-', delete=False) as temp:
            staging = Path(temp.name)
            payload = json.dumps(document, ensure_ascii=False, indent=2) + '\n'
            temp.write(payload.encode('utf-8'))
            temp.flush()
            os.fsync(temp.fileno())
        codex_io.replace(staging, path)
    except OSError as error:
        raise PaperPoolCatalogError('binding: could not publish the verified snapshot') from error
    finally:
        if staging is not None:
            staging.unlink(missing_ok=True)


def _summary(papers: dict, hashes: dict) -> dict:
    return {
        'schema': CATALOG_SCHEMA,
        'status': 'ready',
        'scope': 'author_abstract',
        'corpus_fingerprint': _fingerprint(hashes),
        'counts': {'papers': len(papers), **dict.fromkeys(SOURCES, len(papers))},
        'source_sha256': hashes,
    }


def bind_catalog(binding: Path, abstracts: Path, parents: Path, extractions: Path) -> dict:
    """Check all three files and atomically store a path-and-hash binding."""
    path = _absolute_local(binding)
    paths = _source_paths(path, dict(zip(SOURCES, (abstracts, parents, extractions))))
    if _check_file(path, 'binding', missing_ok=True):
        _read_binding(path)
    papers, hashes = _load_sources(paths)
    result = _summary(papers, hashes)
    _write_binding(path, {
        'schema': CATALOG_SCHEMA,
        'corpus_fingerprint': result['corpus_fingerprint'],
        'sources': {role: {'path': str(source), 'sha256': hashes[role]}
                    for role, source in paths.items()},
    })
    return result


def _open_catalog(binding: Path) -> tuple[dict[str, _Paper], dict]:
    paths, expected = _read_binding(_absolute_local(binding))
    return _load_sources(paths, expected)


def check_catalog(binding: Path) -> dict:
    """Recheck the exact bound input bytes, joins and author-abstract anchors."""
    papers, hashes = _open_catalog(binding)
    return _summary(papers, hashes)


def _normalize(text: str) -> str:
    return WORD_SEPARATOR.sub(' ', unicodedata.normalize('NFKC', text).casefold()).strip()


def _terms(terms: list[str]) -> list[_Term]:
    _require(isinstance(terms, list) and terms, 'Paper Pool search requires at least one term')
    queries, seen = [], set()
    for term in terms:
        _require(isinstance(term, str) and term.strip(), 'Paper Pool search term is empty')
        normalized = _normalize(term)
        _require(normalized, 'Paper Pool search term has no searchable characters')
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates = []
        for phrase in VARIANTS.get(normalized, (normalized,)):
            prefix = r'(?<![a-z0-9])' if ASCII_WORD.fullmatch(phrase[0]) else ''
            suffix = r'(?![a-z0-9])' if ASCII_WORD.fullmatch(phrase[-1]) else ''
            boundary = re.compile(prefix + re.escape(phrase) + suffix) if prefix or suffix else None
            candidates.append((phrase, boundary))
        queries.append(_Term(term.strip(), normalized, tuple(candidates)))
    return queries


def _matches(text: str, queries: list[_Term]) -> dict[str, set[str]]:
    normalized = _normalize(text)
    matches = {}
    for query in queries:
        found = {phrase for phrase, pattern in query.alternatives
                 if phrase in normalized and (pattern is None or pattern.search(normalized))}
        if found:
            matches[query.text] = found
    return matches


def _search_fields(paper: _Paper) -> dict[str, list[str]]:
    fields = {
        'title': [paper.author['title']],
        'author_abstract': [paper.author['abstract']],
        'topic': [paper.author['topic']],
        **{f'extraction.{key}': [paper.extraction[key]] for key in EXTRACTION_FIELDS if key in paper.extraction},
    }
    for name in DIMENSIONS:
        statements = [component['statement'] for component in paper.dimensions.get(name, {}).get('components', ())]
        if statements:
            # A query phrase must occur in a real component, not across two independently derived notes.
            fields[f'nine_dimensions.{name}'] = statements
    return fields


def _match_fields(fields: dict[str, list[str]], queries: list[_Term]) -> dict[str, dict[str, set[str]]]:
    matched = {query.text: {} for query in queries}
    for field, values in fields.items():
        for value in values:
            for term, phrases in _matches(value, queries).items():
                matched[term].setdefault(field, set()).update(phrases)
    return matched


def _ranking(fields: dict[str, dict[str, set[str]]]) -> tuple[int, int]:
    source_terms = sum('title' in match or 'author_abstract' in match for match in fields.values())
    score = sum(8 * ('title' in match) + 4 * ('author_abstract' in match) + ('topic' in match)
                + any(field.startswith('nine_dimensions.') for field in match)
                + any(field.startswith('extraction.') for field in match)
                for match in fields.values())
    return source_terms, score


def _entry(identity: str, paper: _Paper) -> dict:
    author = paper.author
    return {
        'paper_id': identity,
        'publication_id': author['paper_id'],
        'title': author['title'],
        'publication_date': author['publication_date'],
        'source_url': author['source_url'],
        'evidence': {
            'level': 'author_abstract',
            'locator': {
                'source': 'abstracts',
                'line': paper.line,
                'abstract_sha256': author['abstract_sha256'],
                'offset_unit': 'unicode_code_points',
                'offset_interval': 'half_open',
            },
        },
    }


def _quoted(chunk: dict) -> dict:
    return {key: chunk[key] for key in ('n', 'offset', 'text')}


def _previews(paper: _Paper, queries: list[_Term], anchored: set[int], extracted: set[int]) -> list[dict]:
    remaining = [(chunk, _matches(chunk['text'], queries)) for chunk in paper.author['chunks']]
    uncovered = {query.text for query in queries}
    excerpts = []

    def priority(choice):
        chunk, terms = choice
        return (-len(uncovered.intersection(terms)), -len(terms),
                chunk['n'] not in anchored, chunk['n'] not in extracted, chunk['offset'][0])

    while remaining and len(excerpts) < 3:
        best = min(remaining, key=priority)
        remaining.remove(best)
        chunk, terms = best
        excerpt = {**_quoted(chunk), 'matched_terms': list(terms)}
        aliases = {query.text: sorted(terms[query.text] - {query.needle}) for query in queries
                   if query.text in terms and terms[query.text] - {query.needle}}
        if aliases:
            excerpt['matched_variants'] = aliases
        excerpts.append(excerpt)
        uncovered.difference_update(terms)
    return excerpts


def _search_result(identity: str, paper: _Paper, queries: list[_Term],
                   matched: dict[str, dict[str, set[str]]], score: int) -> dict:
    result = _entry(identity, paper)
    result['score'] = score
    result['matches'] = []
    for query in queries:
        by_field = matched[query.text]
        match = {'term': query.text, 'fields': list(by_field)}
        aliases = {field: sorted(phrases - {query.needle}) for field, phrases in by_field.items()
                   if phrases - {query.needle}}
        if aliases:
            match['matched_variants'] = aliases
        result['matches'].append(match)
    fields = {field for matches in matched.values() for field in matches}
    components = []
    anchored_sentences = set()
    for name in DIMENSIONS:
        if f'nine_dimensions.{name}' in fields:
            for component in paper.dimensions[name]['components']:
                terms = _matches(component['statement'], queries)
                if terms:
                    anchored_sentences.update(component['author_sentence_ids'])
                    item = {key: component[key] for key in ('statement', 'provenance',
                                                            'author_sentence_ids', 'offsets')}
                    components.append({'dimension': name, 'matched_terms': list(terms), **item})
    extraction = {key: paper.extraction[key] for key in EXTRACTION_FIELDS if f'extraction.{key}' in fields}
    extracted_sentences = {anchor['n'] for anchor in paper.extraction.get('anchors', ())}
    if extraction:
        extraction['anchor_sentence_ids'] = sorted(extracted_sentences)
        anchored_sentences.update(extracted_sentences)
    result['derived'] = {
        'topic': paper.author['topic'],
        'nine_dimensions': components[:3],
        'extraction': extraction,
    }

    result['evidence']['excerpts'] = _previews(paper, queries, anchored_sentences, extracted_sentences)
    return result


def search_catalog(binding: Path, terms: list[str], limit: int = 12) -> dict:
    """Find records matching every term or a listed bilingual variant of that term."""
    queries = _terms(terms)
    _require(type(limit) is int and limit > 0, 'Paper Pool search limit must be a positive integer')
    papers, hashes = _open_catalog(binding)
    ranked = []
    for identity, paper in papers.items():
        matched = _match_fields(_search_fields(paper), queries)
        if all(matched.values()):
            source_terms, score = _ranking(matched)
            ranked.append((-source_terms, -score, identity, matched))
    ranked.sort()
    results = [_search_result(identity, papers[identity], queries, matched, -negative_score)
               for _, negative_score, identity, matched in ranked[:limit]]
    return {
        **_summary(papers, hashes),
        'query': [query.text for query in queries],
        'limit': limit,
        'returned': len(results),
        'total_matches': len(ranked),
        'results': results,
    }


def show_paper(binding: Path, paper_id: str) -> dict:
    """Expose the exact author abstract, local locator and independently labelled notes."""
    _require(isinstance(paper_id, str) and PAPER_ID.fullmatch(paper_id.strip().upper()),
             'Paper Pool lookup requires a P-number, such as P0001')
    identity = paper_id.strip().upper()
    papers, hashes = _open_catalog(binding)
    _require(identity in papers, f'Paper Pool contains no record for {identity}')
    return {**_summary(papers, hashes), 'paper': _paper_details(identity, papers[identity])}


def _paper_details(identity: str, paper: _Paper) -> dict:
    result = _entry(identity, paper)
    result['evidence'].update(
        abstract=paper.author['abstract'],
        chunks=[_quoted(chunk) for chunk in paper.author['chunks']],
        excerpts=[_quoted(anchor) for anchor in paper.extraction.get('anchors', ())],
    )
    result['derived'] = {
        'topic': paper.author['topic'],
        'nine_dimensions': paper.dimensions,
        'extraction': {key: paper.extraction[key] for key in ('type', *EXTRACTION_FIELDS)
                       if key in paper.extraction},
    }
    if paper.extraction:
        result['derived']['extraction']['anchor_sentence_ids'] = [
            anchor['n'] for anchor in paper.extraction['anchors']
        ]
    return result
