#!/usr/bin/env python3
"""Print raw evaluation inputs without reference answers or grading criteria."""
import argparse
import json
from build import ROOT, records

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ids', nargs='*')
    args = parser.parse_args()
    rows = records(ROOT / 'evaluation/cases.jsonl')
    if args.ids and not set(args.ids) <= {r['id'] for r in rows}:
        parser.error('unknown evaluation id')
    for row in rows:
        if not args.ids or row['id'] in args.ids:
            print(json.dumps({'id': row['id'], 'input': row['input']}, ensure_ascii=False))
