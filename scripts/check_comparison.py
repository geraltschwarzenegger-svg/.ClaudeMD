#!/usr/bin/env python3
"""Check paired author examples and chart provenance; never infer a winner."""
import hashlib
import json
import zipfile
from pathlib import Path
from probe_paths import recorded_source

ROOT = Path(__file__).resolve().parent.parent


def validate(root=ROOT):
    errors=[]
    meta=json.loads((root/'evaluation/probes/compare-metadata.json').read_text())
    for name,expected in meta['sha256'].items():
        p=recorded_source(root, name, meta['versions'][-1])
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
            errors.append('changed recorded file: '+name)
    with zipfile.ZipFile(root/'geraltvoice2.2.0.zip') as archive:
        for name,expected in meta['old_members_sha256'].items():
            if hashlib.sha256(archive.read('geralt-voice/'+name)).hexdigest()!=expected:
                errors.append('old instruction hash mismatch: '+name)
    rows=[json.loads(s) for s in (root/'evaluation/probes/compare-2.2-vs-3.0.jsonl').read_text().splitlines()]
    if len(rows)!=meta['pairs'] or len({r['id'] for r in rows})!=len(rows):
        errors.append('pair count or duplicate IDs')
    if meta['can_claim_win_rate'] is not False:
        errors.append('author examples do not establish a win rate')
    for row in rows:
        for field in ['input','criterion','output_2_2_0','output_3_0_0_rc_2','review']:
            if not isinstance(row[field],str) or not row[field].strip():
                errors.append('empty field: '+row['id']+':'+field)
        copied=row['copyable_2_2_0']
        if copied is not None and copied not in row['output_2_2_0']:
            errors.append('copyable text absent from full output: '+row['id'])
    return errors


if __name__=='__main__':
    errors=validate()
    for e in errors:print('ERROR:',e)
    print('FAIL: paired examples' if errors else 'PASS: 12 paired author examples and hashes; not a quality score')
    raise SystemExit(bool(errors))
