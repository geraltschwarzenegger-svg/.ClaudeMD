#!/usr/bin/env python3
"""Validate actual source, generated exports and optional package; not style quality."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

from build import ROOT, INSTALLABLE_FILES, generated_texts, package_entries, records, release_archives


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node, deep=False):
    pairs = loader.construct_pairs(node, deep=deep)
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate YAML key: {key}')
        result[key] = value
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def anchors(text: str) -> set[str]:
    found, seen = set(), {}
    for heading in re.findall(r'^#{1,6}\s+(.+)$', text, re.M):
        slug = ''.join(c for c in heading.lower().strip() if c.isalnum() or c in ' -_').replace(' ', '-')
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        found.add(slug + (f'-{count}' if count else ''))
    return found


def validate(root: Path = ROOT, *, archive=False, source_only=False) -> list[str]:
    errors = []
    def issue(message):
        errors.append(message)
    required = ['VERSION', 'README.md', 'CHANGELOG.md', 'BENCHMARK.md', 'geralt-voice/SKILL.md', 'geralt-voice/agents/openai.yaml', 'evaluation/cases.jsonl', 'geralt-voice/references/examples.jsonl', 'geralt-voice/references/roles.json']
    for name in required:
        if not (root / name).is_file():
            issue('missing file: ' + name)
    if errors:
        return errors
    for p in (root / 'geralt-voice').rglob('*'):
        if p.is_symlink():
            issue('symlink in installable skill: ' + str(p))
        elif p.is_file() and '__pycache__' not in p.parts and p.relative_to(root / 'geralt-voice').as_posix() not in INSTALLABLE_FILES:
            issue('unexpected installable file: ' + str(p.relative_to(root)))
    version = (root / 'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-rc\.\d+)?', version):
        issue('invalid VERSION')
    skill = (root / 'geralt-voice/SKILL.md').read_text()
    m = re.match(r'\A---\n(.*?)\n---\n', skill, re.S)
    try:
        front = yaml.load(m.group(1), Loader=UniqueLoader) if m else None
        if not isinstance(front, dict) or set(front) != {'name', 'description'}:
            issue('frontmatter must contain exactly name and description')
        elif front['name'] != 'geralt-voice' or not isinstance(front['description'], str) or not 1 <= len(front['description']) <= 1024:
            issue('invalid skill metadata')
    except (yaml.YAMLError, ValueError, TypeError) as e:
        issue('invalid YAML: ' + str(e).splitlines()[0])
    if len(skill) > 18000:
        issue('core exceeds 18000 characters; review actual context size')
    try:
        ui = yaml.load((root / 'geralt-voice/agents/openai.yaml').read_text(), Loader=UniqueLoader)['interface']
        if not 25 <= len(ui['short_description']) <= 64 or '$geralt-voice' not in ui['default_prompt']:
            issue('invalid UI metadata')
    except (yaml.YAMLError, ValueError, KeyError, TypeError):
        issue('invalid agents/openai.yaml')
    try:
        demos = records(root / 'geralt-voice/references/examples.jsonl')
        cases = records(root / 'evaluation/cases.jsonl')
        roles = json.loads((root / 'geralt-voice/references/roles.json').read_text())
    except (json.JSONDecodeError, OSError) as e:
        return errors + ['invalid data: ' + str(e)]
    for label, rows, fields in [('examples', demos, {'id','category','provenance','user_accepted','input','output','principle','format'}), ('cases', cases, {'id','category','provenance','input','criteria'}), ('roles', roles, {'id','name','context','action'})]:
        if not isinstance(rows, list) or not rows:
            issue(label + ' must be a nonempty list')
            continue
        ids = []
        for n, row in enumerate(rows):
            if not isinstance(row, dict) or set(row) != fields:
                issue(f'{label} row {n}: invalid schema')
                continue
            ids.append(row['id'])
            if any(not isinstance(row[k], str) or not row[k].strip() for k in fields - {'user_accepted','criteria'}):
                issue(f'{label} row {n}: empty or nontext field')
            if label != 'roles' and row['provenance'] != 'synthetic':
                issue(f'{label} row {n}: unsupported provenance')
            if label == 'examples':
                if row['user_accepted'] is not False:
                    issue('synthetic example must not claim user acceptance')
                if row['format'] not in {'pc','standard'}:
                    issue('unknown format')
                if row['format'] == 'pc' and (row['output'] != row['output'].lower() or re.search(r'[.!?—–"«»]', row['output'])):
                    issue('pc format violation: ' + row['id'])
            if label == 'cases' and (not isinstance(row['criteria'], list) or not row['criteria'] or any(not isinstance(s, str) or not s.strip() for s in row['criteria'])):
                issue('invalid evaluation criteria')
        if len(ids) != len(set(ids)):
            issue(label + ' duplicate ids')
    demo_inputs = {r.get('input') for r in demos if isinstance(r, dict)}
    if any(isinstance(c, dict) and c.get('input') in demo_inputs for c in cases):
        issue('evaluation input leaked into examples')
    if len(demos) < 96 or len(cases) < 48 or len(roles) < 24:
        issue('release dataset coverage below contract')
    # A repeated long normative list item is meaningful; quotations/examples are excluded.
    seen = {}
    normative = [root / 'geralt-voice/SKILL.md', *sorted((root / 'geralt-voice/references').glob('*.md'))]
    for p in normative:
        if p.name in {'examples.md','roles.md'}:
            continue
        for n, line in enumerate(p.read_text().splitlines(),1):
            normalized = re.sub(r'^[\s*#\-\d.]+', '', line).strip()
            if len(normalized) >= 150 and not line.startswith(('|','>')):
                if normalized in seen:
                    issue(f'duplicate long rule: {p.name}:{n} and {seen[normalized]}')
                seen[normalized] = f'{p.name}:{n}'
    md = [root / n for n in ['README.md','CHANGELOG.md','BENCHMARK.md','AGENTS.md','CLAUDE.md'] if (root / n).exists()]
    md += list((root / 'docs').glob('*.md')) + list((root / 'geralt-voice').rglob('*.md'))
    for p in md:
        text = p.read_text()
        if text.count('```') % 2:
            issue('unbalanced fence: ' + str(p.relative_to(root)))
        targets = re.findall(r'!?\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)', text)
        targets += re.findall(r'(?:href|src)=[\'"]([^\'"]+)[\'"]', text)
        for target in targets:
            u = urlsplit(target)
            if u.scheme or u.netloc:
                continue
            dest = (p.parent / unquote(u.path)).resolve() if u.path else p.resolve()
            if not dest.is_relative_to(root.resolve()) or not dest.is_file():
                issue(f'broken link: {p.relative_to(root)} -> {target}')
            elif u.fragment and dest.suffix == '.md' and unquote(u.fragment) not in anchors(dest.read_text()):
                issue(f'broken anchor: {p.relative_to(root)} -> {target}')
        for name, number in re.findall(r'раздел\s+(\d+)\s+в\s+`([^`]+\.md)`', text):
            # Kept for legacy style references: first capture is the number.
            dest = p.parent / number
            if not dest.is_file() or not re.search(r'^##\s+' + re.escape(name) + r'\.', dest.read_text(), re.M):
                issue(f'broken numbered section: {p.name} -> {number}:{name}')
    if version not in (root / 'README.md').read_text() or f'## {version}' not in (root / 'CHANGELOG.md').read_text():
        issue('release version missing from README/CHANGELOG')
    if not source_only and not errors:
        for name, expected in generated_texts(root).items():
            p = root / name
            if not p.exists() or p.read_text() != expected:
                issue('generated file drift: ' + name)
        p = root / 'prompts/CLAUDE.md'
        try:
            ET.fromstring(p.read_text())
        except (ET.ParseError, OSError):
            issue('Claude export is not well-formed XML')
    if archive:
        expected_archives = release_archives(root)
        sums = []
        aliases = {
            f'geralt-voice-{version}.zip': 'Geralt Voice 3.0.0-rc.zip',
            f'geralt-voice-codex-{version}.zip': 'Geralt Voice Codex.zip',
            f'geralt-voice-claude-{version}.zip': 'Geralt Voice Claude.zip',
        }
        for filename, expected in expected_archives.items():
            target = root / 'dist' / filename
            if not target.is_file():
                issue('missing release ZIP: ' + filename)
                continue
            download = root / aliases[filename]
            if not download.is_file() or download.read_bytes() != target.read_bytes():
                issue('root download ZIP missing or differs from release ZIP: ' + filename)
            try:
                with zipfile.ZipFile(target) as z:
                    if len(z.namelist()) != len(set(z.namelist())) or set(z.namelist()) != set(expected):
                        issue('ZIP inventory mismatch: ' + filename)
                    for name, payload in expected.items():
                        if name not in z.namelist() or z.read(name) != payload:
                            issue('ZIP content mismatch: ' + filename + ': ' + name)
                    if z.testzip() is not None:
                        issue('ZIP CRC failure: ' + filename)
                sums.append(f'{hashlib.sha256(target.read_bytes()).hexdigest()}  {target.name}\n')
            except (zipfile.BadZipFile, OSError, KeyError) as e:
                issue('archive error: ' + str(e))
        if (root / 'dist/SHA256SUMS').read_text() != ''.join(sums):
            issue('checksum mismatch')
    return errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', action='store_true')
    parser.add_argument('--source-only', action='store_true')
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    errors = validate(args.root, archive=args.archive, source_only=args.source_only)
    for error in errors:
        print('ERROR:', error)
    print('PASS: structural validation only' if not errors else f'FAIL: {len(errors)} issue(s)')
    sys.exit(bool(errors))
