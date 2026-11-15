#!/usr/bin/env python3
"""Assemble a render_paper report into a lossless raster PDF and verify transport.

The CLI accepts local paths. It does not ship fonts, private asset locations or network URLs.
Optional PDFium previews are rendered from the written PDF, not copied from its source PNGs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_pages(expression: str | None, count: int) -> list[int]:
    if not expression:
        return list(range(1, count + 1))
    result: list[int] = []
    for piece in expression.split(','):
        ends = piece.strip().split('-')
        if len(ends) == 1:
            result.append(int(ends[0]))
        elif len(ends) == 2:
            start, stop = map(int, ends)
            result.extend(range(start, stop + 1))
        else:
            raise ValueError('Invalid --pages range')
    if not result or result != sorted(set(result)) or result[0] < 1 or result[-1] > count:
        raise ValueError('--pages must be an ascending, unique set within the report')
    return result


def assemble(args: argparse.Namespace) -> dict:
    from PIL import Image
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from pypdf import PdfReader

    report_path = Path(args.report).resolve()
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if report.get('status') != 'RENDERED' and not args.allow_diagnostic:
        raise ValueError('The render report is not RENDERED; review it or use --allow-diagnostic for internal comparison')
    pages = selected_pages(args.pages, report['layout']['pages'])
    shots = {item['page']: item for item in report['screenshots']}
    if any(p not in shots for p in pages):
        raise ValueError('The report has not captured every selected page')
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    title = args.title or report.get('title', output.stem)
    width = args.pdf_width
    writer = canvas.Canvas(str(output), pagesize=(width, width), pageCompression=1)
    writer.setTitle(title)
    writer.setAuthor(args.author or '')
    page_map = {p: i + 1 for i, p in enumerate(pages)}
    headings = [h for h in report['layout'].get('headings', []) if h['page'] in page_map]
    bookmarks = {h['id']: h for h in headings}
    dimensions: list[dict] = []
    outline_source_levels: list[int] = []
    for source_page in pages:
        shot = shots[source_page]
        image_path = Path(shot['file'])
        if sha256(image_path) != shot['sha256']:
            raise ValueError(f'Screenshot changed after rendering: page {source_page}')
        with Image.open(image_path) as original:
            image = original.convert('RGB')
            height = image.height / image.width * width
            writer.setPageSize((width, height))
            writer.drawImage(ImageReader(image), 0, 0, width=width, height=height)
            dimensions.append({'source_page': source_page, 'pdf_page': page_map[source_page],
                               'width': width, 'height': height, 'pixel_width': image.width,
                               'pixel_height': image.height})
        for heading in [h for h in headings if h['page'] == source_page]:
            writer.bookmarkPage(heading['id'])
            if heading['level'] <= args.outline_level:
                while outline_source_levels and outline_source_levels[-1] >= heading['level']:
                    outline_source_levels.pop()
                level = len(outline_source_levels)
                writer.addOutlineEntry(heading['text'], heading['id'], level=level, closed=False)
                outline_source_levels.append(heading['level'])
        for link in [item for item in report['layout'].get('links', []) if item['page'] == source_page]:
            rect = link['rect']
            factor = width / shot['css_width']
            bounds = (rect[0] * factor, height - rect[3] * factor,
                      rect[2] * factor, height - rect[1] * factor)
            href = link['href']
            if href.startswith(('https://', 'http://', 'mailto:')):
                writer.linkURL(href, bounds, relative=0, thickness=0)
            elif href.startswith('#') and href[1:] in bookmarks:
                writer.linkRect('', href[1:], bounds, relative=0, thickness=0)
        writer.showPage()
    writer.save()
    reader = PdfReader(str(output))
    if len(reader.pages) != len(pages):
        raise ValueError('Written PDF has an unexpected page count')
    pixel_matches = []
    for number, source_page in enumerate(pages):
        embedded = list(reader.pages[number].images)
        if len(embedded) != 1:
            raise ValueError(f'Expected one raster image on PDF page {number + 1}')
        with Image.open(shots[source_page]['file']) as original:
            expected = original.convert('RGB')
            actual = embedded[0].image.convert('RGB')
            match = expected.size == actual.size and expected.tobytes() == actual.tobytes()
        pixel_matches.append(match)
        if not match:
            raise ValueError(f'Raster pixels changed on PDF page {number + 1}')
        if abs(float(reader.pages[number].mediabox.width) - dimensions[number]['width']) > 0.01:
            raise ValueError('Unexpected PDF page width')
        if abs(float(reader.pages[number].mediabox.height) - dimensions[number]['height']) > 0.01:
            raise ValueError('Unexpected PDF page height')
    previews = []
    if args.preview_dir:
        import pypdfium2 as pdfium
        folder = Path(args.preview_dir).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        document = pdfium.PdfDocument(str(output))
        preview_numbers = selected_pages(args.preview_pages, len(pages))
        try:
            for number in preview_numbers:
                page = document[number - 1]
                bitmap = page.render(scale=args.preview_width / page.get_width())
                rendered = bitmap.to_pil()
                target = folder / f'pdf-page-{number:04d}.png'
                rendered.save(target)
                previews.append(str(target))
                bitmap.close()
                page.close()
        finally:
            document.close()
    result = {'schema_version': 1, 'pdf': str(output), 'sha256': sha256(output),
              'bytes': output.stat().st_size, 'pages': len(pages), 'source_pages': pages,
              'render_report': str(report_path), 'render_report_sha256': sha256(report_path),
              'render_status': report.get('status'), 'page_image_pixels_match': all(pixel_matches),
              'dimensions': dimensions, 'pdf_previews': previews,
              'assembler_sha256': sha256(Path(__file__)),
              'verification_kind': 'raster_transport_and_page_geometry'}
    target_report = Path(args.verification_report).resolve() if args.verification_report else output.with_suffix('.verification.json')
    target_report.parent.mkdir(parents=True, exist_ok=True)
    target_report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def main() -> None:
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--pages', help='Optional ascending ranges, e.g. 1-24,25-48')
    parser.add_argument('--title')
    parser.add_argument('--author')
    parser.add_argument('--pdf-width', type=float, default=390)
    parser.add_argument('--outline-level', type=int, default=3)
    parser.add_argument('--allow-diagnostic', action='store_true')
    parser.add_argument('--preview-dir')
    parser.add_argument('--preview-pages', help='PDF page ranges; defaults to all when previews are requested')
    parser.add_argument('--preview-width', type=int, default=390)
    parser.add_argument('--verification-report')
    args = parser.parse_args()
    if args.pdf_width <= 0 or args.preview_width <= 0:
        parser.error('PDF/preview widths must be positive')
    result = assemble(args)
    print(json.dumps({key: result[key] for key in ['pdf', 'pages', 'bytes', 'page_image_pixels_match', 'render_status']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
