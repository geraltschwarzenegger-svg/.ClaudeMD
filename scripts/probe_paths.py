"""Resolve historical source files without altering recorded metadata or raw outputs."""
from pathlib import Path


def recorded_source(root: Path, name: str, version: str) -> Path:
    # Only instruction/data sources may come from a snapshot. Raw outputs always
    # resolve to their original files so later tampering remains detectable.
    source = name == 'VERSION' or name.startswith('geralt-voice/') or name == 'evaluation/cases.jsonl'
    if source and (root/'VERSION').read_text().strip() != version:
        return root/'evaluation/snapshots'/version/name
    return root/name
