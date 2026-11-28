"""Append-only local Paper Pool index with evidence-bound read snapshots."""
from __future__ import annotations

from contextlib import closing, contextmanager
from hashlib import sha256
import heapq
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from . import codex_paper_pool as evidence


INDEX_SCHEMA = 'digr.codex.paper-pool.index.v1'
INDEX_NAME = 'paper-pool.sqlite3'
APPLICATION_ID = 0x50504F4C
_SCHEMA = f"""
PRAGMA application_id = {APPLICATION_ID};
PRAGMA user_version = 1;
CREATE TABLE batches (
    revision INTEGER PRIMARY KEY,
    fingerprint TEXT NOT NULL UNIQUE,
    batch_digest TEXT NOT NULL UNIQUE,
    sources TEXT NOT NULL,
    papers INTEGER NOT NULL,
    parents INTEGER NOT NULL,
    extractions INTEGER NOT NULL
);
CREATE TABLE papers (
    rowid INTEGER PRIMARY KEY,
    id TEXT NOT NULL UNIQUE,
    publication_id TEXT NOT NULL UNIQUE,
    publication_url TEXT NOT NULL UNIQUE,
    abstract_hash TEXT NOT NULL UNIQUE,
    archive_record TEXT NOT NULL UNIQUE,
    revision INTEGER NOT NULL REFERENCES batches(revision),
    fields TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE VIRTUAL TABLE paper_fts USING fts5(
    terms, content='', tokenize='trigram case_sensitive 1'
);
"""


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _path(value: Path, *, missing_ok: bool = False) -> Path:
    path = evidence._absolute_local(value)
    evidence._check_file(path, 'Paper Pool index', missing_ok=missing_ok)
    for ending in ('-journal', '-wal', '-shm'):
        evidence._check_file(path.with_name(path.name + ending), 'Paper Pool index sidecar', missing_ok=True)
    return path


@contextmanager
def _open(value: Path, *, write: bool = False):
    path = _path(value)
    mode = 'rw' if write else 'ro'
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=' + mode, uri=True, timeout=30)) as db:
            db.row_factory = sqlite3.Row
            if (db.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID
                    or db.execute('PRAGMA user_version').fetchone()[0] != 1):
                raise evidence.PaperPoolCatalogError('unsupported Paper Pool index schema')
            if write:
                # Retain SQLite's local rollback journal and one atomic writer.
                db.execute('PRAGMA foreign_keys = ON')
                db.execute('BEGIN IMMEDIATE')
            with db:
                yield db
    except sqlite3.IntegrityError as exc:
        raise evidence.PaperPoolCatalogError(f'batch rejected for a duplicate or invalid identity: {exc}') from exc
    except sqlite3.Error as exc:
        raise evidence.PaperPoolCatalogError(f'Paper Pool index operation failed: {exc}') from exc


def _snapshot(db: sqlite3.Connection, fingerprint: str | None = None) -> sqlite3.Row:
    if fingerprint is None:
        selected = db.execute('SELECT * FROM batches ORDER BY revision DESC LIMIT 1').fetchone()
    else:
        selected = db.execute('SELECT * FROM batches WHERE fingerprint = ?', (fingerprint,)).fetchone()
    evidence._require(selected is not None, 'requested Paper Pool snapshot is unavailable in this index')
    return selected


def _summary(snapshot: sqlite3.Row) -> dict:
    return {
        'schema': INDEX_SCHEMA,
        'status': 'ready',
        'scope': 'author_abstract',
        'corpus_fingerprint': snapshot['fingerprint'],
        'batches': snapshot['revision'],
        'counts': {
            'papers': snapshot['papers'], 'abstracts': snapshot['papers'],
            'parents': snapshot['parents'], 'extractions': snapshot['extractions'],
        },
    }


def _pad(text: str) -> str:
    # The separator never occurs in normalized text. Padding also gives
    # one- and two-character phrases trigrams, including Chinese queries.
    return '|' + '|'.join(text) + '|'


def _batch(db: sqlite3.Connection, paths: dict, papers: dict, hashes: dict) -> dict:
    digest = evidence._fingerprint(hashes)
    before = db.execute('SELECT * FROM batches ORDER BY revision DESC LIMIT 1').fetchone()
    duplicate = db.execute('SELECT 1 FROM batches WHERE batch_digest = ?', (digest,)).fetchone()
    if duplicate:
        return {**_summary(before), 'appended': 0, 'already_present': True}

    # The first snapshot deliberately retains the legacy binding's identity.
    fingerprint = evidence._fingerprint({'previous': before['fingerprint'], 'batch': digest}) if before else digest
    sources = {role: {'path': str(path), 'sha256': hashes[role]} for role, path in paths.items()}
    totals = tuple((before[key] if before else 0) + (len(papers) if role in paths else 0)
                   for key, role in zip(('papers', 'parents', 'extractions'), evidence.SOURCES))
    revision = db.execute(
        'INSERT INTO batches(fingerprint, batch_digest, sources, papers, parents, extractions) '
        'VALUES (?, ?, ?, ?, ?, ?)', (fingerprint, digest, _json(sources), *totals)).lastrowid

    for identity, paper in papers.items():
        author = paper.author
        fields = evidence._search_fields(paper)
        normalized = {name: [evidence._normalize(value) for value in values] for name, values in fields.items()}
        keys = (identity, author['paper_id'], _json(evidence._source_url_key(author['source_url'], identity)),
                author['abstract_sha256'], _json((author['archive_path'], author['archive_row'])))
        rowid = db.execute(
            'INSERT INTO papers(id, publication_id, publication_url, abstract_hash, archive_record, '
            'revision, fields, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (*keys, revision, _json(normalized), _json((paper.line, author, paper.dimensions, paper.extraction)))
        ).lastrowid
        searchable = ' '.join(_pad(value) for values in normalized.values() for value in values if value)
        db.execute('INSERT INTO paper_fts(rowid, terms) VALUES (?, ?)', (rowid, searchable))
    return {**_summary(_snapshot(db)), 'appended': len(papers), 'already_present': False}


def migrate(index: Path, legacy_binding: Path) -> dict:
    """Build a verified index beside its destination and publish it once."""
    path = _path(index, missing_ok=True)
    source = evidence._absolute_local(legacy_binding)
    evidence._require(path != source and not evidence._check_file(path, 'Paper Pool index', missing_ok=True),
                      'select a new Paper Pool index path')
    paths, hashes = evidence._read_binding(source)
    paths = evidence._source_paths(path, paths)
    papers, actual = evidence._load_sources(paths, hashes)
    handle, temporary_name = tempfile.mkstemp(dir=path.parent, prefix='.paper-pool-')
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with closing(sqlite3.connect(temporary)) as db:
            db.row_factory = sqlite3.Row
            db.executescript(_SCHEMA)
            db.execute('PRAGMA foreign_keys = ON')
            with db:
                result = _batch(db, paths, papers, actual)
        # A same-directory hard link publishes the complete file without
        # replacing any index another process created in the meantime.
        os.link(temporary, path)
        return result
    except sqlite3.Error as exc:
        raise evidence.PaperPoolCatalogError(f'could not build the Paper Pool index: {exc}') from exc
    finally:
        temporary.unlink(missing_ok=True)


def append(index: Path, *, abstracts: Path, parents: Path | None = None, extractions: Path | None = None) -> dict:
    """Validate the supplied batch, then append it in a single transaction."""
    path = _path(index)
    selected = dict(abstracts=abstracts, parents=parents, extractions=extractions)
    paths = evidence._source_paths(path, {role: location for role, location in selected.items() if location is not None})
    papers, hashes = evidence._load_sources(paths)
    with _open(path, write=True) as db:
        return _batch(db, paths, papers, hashes)


def check(index: Path, fingerprint: str | None = None) -> dict:
    with _open(index) as db:
        return _summary(_snapshot(db, fingerprint))


def audit(index: Path) -> dict:
    """Check the index and rehash the archived sources without loading them into memory."""
    path = _path(index)
    with _open(path) as db:
        snapshot = _snapshot(db)
        check_rows = db.execute('PRAGMA quick_check').fetchall()
        evidence._require(check_rows and all(row[0] == 'ok' for row in check_rows),
                          'Paper Pool index integrity check failed')
        for row in db.execute('SELECT sources FROM batches WHERE revision <= ?', (snapshot['revision'],)):
            sources = json.loads(row['sources'])
            paths = evidence._source_paths(path, {role: Path(item['path']) for role, item in sources.items()})
            for role, source in paths.items():
                evidence._check_file(source, role)
                with source.open('rb') as stream:
                    digest = sha256()
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(block)
                evidence._require(digest.hexdigest() == sources[role]['sha256'],
                                  f'{role}: contents differ from the indexed snapshot')
        return {**_summary(snapshot), 'source_hashes_verified': True}


def _match_expression(queries: list[evidence._Term]) -> str:
    groups = ['(' + ' OR '.join('"' + _pad(phrase) + '"' for phrase, _ in query.alternatives) + ')'
              for query in queries]
    return ' AND '.join(groups)


def _paper(db: sqlite3.Connection, identity: str, revision: int) -> tuple[evidence._Paper, dict]:
    row = db.execute('SELECT papers.payload, papers.revision, batches.sources FROM papers '
                     'JOIN batches USING (revision) WHERE id = ? AND papers.revision <= ?',
                     (identity, revision)).fetchone()
    evidence._require(row is not None, f'Paper Pool contains no record for {identity} in the selected snapshot')
    locator = {'batch': row['revision'], 'abstract_file_sha256': json.loads(row['sources'])['abstracts']['sha256']}
    return evidence._Paper(*json.loads(row['payload'])), locator


def search(index: Path, terms: list[str], limit: int = 12, fingerprint: str | None = None) -> dict:
    queries = evidence._terms(terms)
    evidence._require(type(limit) is int and limit > 0, 'Paper Pool search limit must be a positive integer')
    with _open(index) as db:
        snapshot = _snapshot(db, fingerprint)
        revision = snapshot['revision']
        candidates = db.execute('SELECT p.id, p.fields FROM paper_fts JOIN papers AS p ON p.rowid = paper_fts.rowid '
                                'WHERE paper_fts MATCH ? AND p.revision <= ?',
                                (_match_expression(queries), revision))
        count = 0

        def matching():
            nonlocal count
            for row in candidates:
                matched = evidence._match_fields(json.loads(row['fields']), queries)
                if all(matched.values()):
                    count += 1
                    source_terms, score = evidence._ranking(matched)
                    yield -source_terms, -score, row['id'], matched

        results = []
        for _, score, identity, matched in heapq.nsmallest(limit, matching(), key=lambda hit: hit[:3]):
            paper, locator = _paper(db, identity, revision)
            result = evidence._search_result(identity, paper, queries, matched, -score)
            result['evidence']['locator'].update(locator)
            results.append(result)
        return {**_summary(snapshot), 'query': [query.text for query in queries], 'limit': limit,
                'returned': len(results), 'total_matches': count, 'results': results}


def show(index: Path, paper_id: str, fingerprint: str | None = None) -> dict:
    evidence._require(isinstance(paper_id, str) and evidence.PAPER_ID.fullmatch(paper_id.strip().upper()),
                      'Paper Pool lookup requires a P-number, such as P0001')
    identity = paper_id.strip().upper()
    with _open(index) as db:
        snapshot = _snapshot(db, fingerprint)
        paper, locator = _paper(db, identity, snapshot['revision'])
        result = evidence._paper_details(identity, paper)
        result['evidence']['locator'].update(locator)
        return {**_summary(snapshot), 'paper': result}
