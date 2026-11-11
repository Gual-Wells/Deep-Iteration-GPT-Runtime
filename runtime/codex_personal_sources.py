"""Selected, source-bound text for private Personal Context; never a diagnosis."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return sha256(raw).hexdigest()


def representation_digest(units):
    return digest(json.dumps(units, ensure_ascii=False, sort_keys=True).encode('utf-8'))


def clean(value):
    return ' '.join(value.split())


def unit(location, value):
    value = clean(value)
    return {'location': location, 'text': value, 'text_sha256': digest(value.encode('utf-8'))}


def _member(z, name):
    need(name in z.namelist(), 'selected package item is missing: ' + name)
    info = z.getinfo(name)
    need(not info.is_dir() and info.file_size <= 8_000_000, 'selected text item is too large')
    need(not info.flag_bits & 1, 'encrypted package text is unsupported')
    return z.read(name)


def _join(base, href):
    parts = urlsplit(href)
    need(not parts.scheme and not parts.netloc, 'external package item is unsupported')
    name = posixpath.normpath(posixpath.join(posixpath.dirname(base), unquote(parts.path)))
    need(not name.startswith(('/', '../')) and '\\' not in name and ':' not in name,
         'package reference escapes its root')
    return name


def _epub(path, selected):
    ns = {'c': 'urn:oasis:names:tc:opendocument:xmlns:container',
          'o': 'http://www.idpf.org/2007/opf', 'd': 'http://purl.org/dc/elements/1.1/'}
    units = {}; metadata = {}; inventory = []
    with zipfile.ZipFile(path) as z:
        need(len(z.namelist()) == len(set(z.namelist())), 'duplicate package paths are ambiguous')
        container = ET.fromstring(_member(z, 'META-INF/container.xml'))
        files = container.findall('.//c:rootfile', ns)
        need(bool(files), 'EPUB package document is missing')
        opf_name = _join('', files[0].attrib['full-path'])
        opf = ET.fromstring(_member(z, opf_name))
        metadata['title'] = [e.text or '' for e in opf.findall('.//d:title', ns)]
        metadata['creator'] = [e.text or '' for e in opf.findall('.//d:creator', ns)]
        if metadata['title']:
            units['package:title'] = unit({'package': opf_name, 'metadata': 'title'}, ' / '.join(metadata['title']))
        items = {e.attrib['id']: e.attrib for e in opf.findall('./o:manifest/o:item', ns)}
        spine = [e.attrib['idref'] for e in opf.findall('./o:spine/o:itemref', ns)]
        for iid in spine:
            item = items[iid]
            inventory.append({'id': iid, 'href': _join(opf_name, item['href']),
                              'media_type': item.get('media-type')})
        metadata['spine_count'] = len(spine)
        metadata['inventory'] = inventory
        selected = selected or []
        need(len(selected) <= 12, 'select at most twelve EPUB items per intake')
        for iid in selected:
            need(iid in items, 'unknown EPUB item: ' + iid)
            item = items[iid]
            need(item.get('media-type') in {'application/xhtml+xml', 'text/html'}, 'selected item is not XHTML')
            name = _join(opf_name, item['href'])
            doc = ET.fromstring(_member(z, name))
            blocks = []
            for e in doc.iter():
                tag = e.tag.rsplit('}', 1)[-1]
                if tag in {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'pre', 'li', 'figcaption', 'td', 'th'}:
                    text = clean(''.join(e.itertext()))
                    if text:
                        blocks.append((e.attrib.get('id'), text))
            if not blocks:
                text = clean(' '.join(doc.itertext()))
                if text:
                    blocks = [(None, text)]
            for number, (anchor, text) in enumerate(blocks, 1):
                key = iid + ':block:' + str(number)
                units[key] = unit({'item_id': iid, 'href': name, 'element_id': anchor,
                                   'block': number}, text)
    return metadata, units, {'mode': 'selected_xhtml' if selected else 'metadata_and_inventory',
                             'selected_items': list(selected),
                             'limits': 'Text blocks only; images, formula layout, audio and Apple Books pagination were not interpreted.'}


def _json(path, selectors):
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    selectors = selectors or ['$']
    units = {}
    for selector in selectors:
        current = value
        if selector != '$':
            for part in selector.split('.'):
                current = current[int(part)] if isinstance(current, list) else current[part]
        text = json.dumps(current, ensure_ascii=False, sort_keys=True, allow_nan=False)
        units[selector] = unit({'json_path': selector}, text)
    return {}, units, {'mode': 'selected_json_paths', 'selectors': selectors}


def _pdf(path, pages):
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise ValueError('PDF extraction requires pypdf in the selected Python environment; source was not imported') from error
    reader = PdfReader(str(path))
    selected = pages or []
    need(len(selected) <= 30, 'select at most thirty PDF pages per intake')
    units = {}
    for number in selected:
        need(type(number) is int and 1 <= number <= len(reader.pages), 'invalid selected PDF page')
        text = reader.pages[number - 1].extract_text() or ''
        need(bool(text.strip()), 'selected PDF page has no extractable text; inspect the original instead')
        units['page:' + str(number)] = unit({'page': number}, text)
    return {'pages': len(reader.pages)}, units, {'mode': 'selected_pages' if selected else 'metadata_only',
                                               'selected_pages': selected, 'limits': 'Extracted text; not OCR or a visual/formula reading.'}


def _docx(path):
    with zipfile.ZipFile(path) as z:
        doc = ET.fromstring(_member(z, 'word/document.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    units = {}
    for number, p in enumerate(doc.findall('.//w:p', ns), 1):
        text = ''.join(e.text or '' for e in p.findall('.//w:t', ns))
        if text.strip():
            units['paragraph:' + str(number)] = unit({'paragraph': number}, text)
    return {}, units, {'mode': 'document_paragraphs', 'limits': 'No physical-page or rendered-layout claim.'}


def extract(path, *, selectors=None, pages=None, items=None):
    path = Path(path).resolve(strict=True)
    need(path.is_file(), 'selected source is not a file')
    before = path.stat()
    # Stream the identity; do not load a large illustrated EPUB into memory.
    h = sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    suffix = path.suffix.lower()
    if suffix == '.epub':
        metadata, units, scope = _epub(path, items)
    elif suffix == '.pdf':
        metadata, units, scope = _pdf(path, pages)
    elif suffix == '.docx':
        metadata, units, scope = _docx(path)
    elif suffix == '.json':
        metadata, units, scope = _json(path, selectors)
    else:
        need(suffix in {'.txt', '.md', '.py', '.cpp', '.cc', '.h', '.hpp', '.js', '.ts', '.yaml', '.yml'},
             'unsupported source format')
        need(before.st_size <= 4_000_000, 'select a smaller text source')
        lines = path.read_text(encoding='utf-8-sig').splitlines()
        units = {'line:' + str(i): unit({'line': i}, line) for i, line in enumerate(lines, 1) if line.strip()}
        metadata, scope = {}, {'mode': 'text_lines'}
    after = path.stat()
    need((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'source changed while indexing')
    need(sum(len(v['text']) for v in units.values()) <= 6_000_000, 'selected text exceeds intake limit')
    return {'sha256': h.hexdigest(), 'byte_length': before.st_size, 'format': suffix.lstrip('.'),
            'metadata': metadata, 'units': units, 'read_scope': scope,
            'representation_sha256': representation_digest(units)}
