#!/usr/bin/env python3
"""Check current and historical probe provenance, coverage and input integrity."""
import hashlib
import json
from pathlib import Path
from probe_paths import recorded_source

ROOT = Path(__file__).resolve().parent.parent


def validate(root=ROOT, metadata="rc2-metadata.json"):
    errors = []
    meta = json.loads((root / 'evaluation/probes' / metadata).read_text())
    for name, expected in meta['sha256'].items():
        path = recorded_source(root, name, meta['version'])
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append('changed or missing recorded file: ' + name)
    cases = {row['id']: row for row in map(json.loads, recorded_source(root, 'evaluation/cases.jsonl', meta['version']).read_text().splitlines())}
    outputs = list(map(json.loads, (root / meta.get('outputs_file', 'evaluation/probes/rc2-author.jsonl')).read_text().splitlines()))
    ids = [row['id'] for row in outputs]
    if len(ids) != len(set(ids)) or len(ids) != meta['outputs']:
        errors.append('duplicate IDs or wrong output count')
    if set(ids) != set(meta['case_ids']):
        errors.append('recorded case inventory mismatch')
    if len(cases) != meta['total_cases']:
        errors.append('case bank count changed')
    for row in outputs:
        if row['id'] not in cases or row['input'] != cases[row['id']]['input']:
            errors.append('input mismatch: ' + row['id'])
        if not isinstance(row['output'], str) or not row['output'].strip():
            errors.append('empty output: ' + row['id'])
        if row.get('provenance') != 'synthetic' or row.get('generation_mode') != 'authored_in_current_codex_session':
            errors.append('incorrect provenance: ' + row['id'])
    return errors


if __name__ == '__main__':
    errors = validate() + validate(metadata="rc3-metadata.json")
    for error in errors:
        print('ERROR:', error)
    print('FAIL: recorded probes' if errors else 'PASS: 24 historical rc.2 and 12 rc.3 outputs, matching inputs and hashes; not a quality score')
    raise SystemExit(bool(errors))
