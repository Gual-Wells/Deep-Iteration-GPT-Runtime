#!/usr/bin/env python3
"""Export the optional Voice companion. No network, model calls or installation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def instruction_text(root: Path, layer: str) -> str:
    manifest = json.loads((root / 'voice/manifest.json').read_text(encoding='utf-8'))
    if manifest['version'] != (root / 'voice/VERSION').read_text(encoding='utf-8').strip():
        raise ValueError('Voice manifest and VERSION disagree')
    resident = (root / manifest['resident']).read_text(encoding='utf-8').strip()
    if layer == 'resident':
        return resident + '\n'
    if layer != 'project':
        raise ValueError(f'unknown Voice layer: {layer}')
    skill = (root / manifest['skill'] / 'SKILL.md').read_text(encoding='utf-8')
    if not skill.startswith('---\n') or '\n---\n' not in skill[4:]:
        raise ValueError('Voice skill frontmatter is missing or unclosed')
    skill = skill[4:].split('\n---\n', 1)[1].strip()
    # References travel with the upload; do not require a local checkout in ChatGPT.
    for filename, title in (('professional', 'Practice material'),
                            ('examples', 'Exchanges to learn from'),
                            ('hosts', 'Host guidance')):
        skill = skill.replace(f'(references/{filename}.md)',
                              f'(#{title.lower().replace(" ", "-")})')
    parts = [
        f'# DIGR Voice Companion {manifest["version"]} — self-contained project material',
        'This file contains conversation guidance and optional examples/material. '
        'Its presence alone is not a command to begin rehearsal or proof that Voice read it. '
        'When requested or selected by the host, use the guidance below. '
        'Do not recite the installation notes during practice.',
        '## Resident guidance\n\n' + resident,
        skill,
    ]
    for key, anchor in (('examples', 'exchanges-to-learn-from'),
                        ('professional', 'practice-material'),
                        ('hosts', 'host-guidance')):
        path = (root / manifest[key]) if key in manifest else (
            root / manifest['skill'] / 'references' / f'{key}.md')
        parts.append(f'<a id="{anchor}"></a>\n\n' + path.read_text(encoding='utf-8').strip())
    return '\n\n---\n\n'.join(parts) + '\n'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for action in ('instructions', 'export'):
        command = sub.add_parser(action)
        command.add_argument('layer', choices=('resident', 'project'))
        if action == 'export':
            command.add_argument('--out', type=Path, required=True,
                                 help='create a new file; never overwrite or install')
    args = parser.parse_args(argv)
    try:
        content = instruction_text(ROOT, args.layer)
        if args.command == 'instructions':
            print(content, end='')
        else:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(content)
            print(json.dumps({'exported': args.out.resolve().as_posix(),
                              'layer': args.layer, 'version':
                              (ROOT / 'voice/VERSION').read_text(encoding='utf-8').strip(),
                              'global_install_performed': False,
                              'voice_behavior_observed': False}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f'Voice companion error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
