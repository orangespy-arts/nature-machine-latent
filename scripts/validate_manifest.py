"""Validate inventory metadata without changing manifests or audio (stdlib only)."""
import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path, PureWindowsPath

FIELDS = 'asset_id,relative_path,recording_group,category,sound_family,description,source,license,duration_seconds,sample_rate_hz,channels,sha256,split,notes'.split(',')
SPLITS = {'train', 'validation', 'test'}


def read_csv(path, required):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or not set(required) <= set(headers):
            raise ValueError(f'{path}: missing required or duplicate columns')
        rows = list(reader)
        if any(None in row or any(value is None for value in row.values()) for row in rows):
            raise ValueError(f'{path}: inconsistent CSV column count')
        return rows


def validate(rows, queue=None, root=None):
    errors, pending = [], Counter()
    assets, paths = {}, set()
    groups, hashes = defaultdict(set), defaultdict(set)
    for line, row in enumerate(rows, 2):
        asset = row['asset_id'].strip()
        label = f'row {line} ({asset})'
        if not asset or asset in assets:
            errors.append(f'{label}: empty or duplicate asset_id')
        assets[asset] = row
        path = PureWindowsPath(row['relative_path'])
        if not row['relative_path'].strip() or path.drive or path.root or '..' in path.parts or not path.parts:
            errors.append(f'{label}: unsafe relative_path')
        elif root is not None:
            target = root.joinpath(*path.parts).resolve()
            if not target.is_relative_to(root.resolve()) or not target.is_file():
                errors.append(f'{label}: file missing or outside root')
        key = path.as_posix().casefold()
        if key in paths:
            errors.append(f'{label}: duplicate relative_path')
        paths.add(key)
        for field in ('duration_seconds', 'sample_rate_hz', 'channels'):
            try:
                value = float(row[field])
                if not math.isfinite(value) or value <= 0 or (field != 'duration_seconds' and not value.is_integer()):
                    raise ValueError()
            except ValueError:
                errors.append(f'{label}: invalid {field}')
        digest = row['sha256'].strip().lower()
        if not re.fullmatch(r'[0-9a-f]{64}', digest):
            errors.append(f'{label}: invalid sha256')
        split = row['split'].strip()
        if split not in SPLITS | {'unassigned'}:
            errors.append(f'{label}: invalid split')
        if row['category'] not in ('', 'nature', 'machine'):
            errors.append(f'{label}: invalid category')
        for field in ('recording_group', 'category', 'sound_family', 'source', 'license'):
            if row[field].strip().lower() in ('', 'unknown', 'unconfirmed'):
                pending[field] += 1
                if split in SPLITS and field in ('recording_group', 'source', 'license'):
                    errors.append(f'{label}: assigned split without {field}')
        if split == 'unassigned':
            pending['split'] += 1
        if split in SPLITS:
            if row['recording_group'].strip():
                groups[row['recording_group'].strip()].add(split)
            if digest:
                hashes[digest].add(split)
    for name, mapping in (('recording_group', groups), ('sha256', hashes)):
        for key, splits in mapping.items():
            if len(splits) > 1:
                errors.append(f'{name} {key}: cross-split leakage ({", ".join(sorted(splits))})')
    reviews = Counter()
    if queue is not None:
        seen = set()
        for row in queue:
            asset = row['asset_id']
            if asset in seen:
                errors.append(f'queue {asset}: duplicate asset_id')
            seen.add(asset)
            if asset not in assets:
                errors.append(f'queue {asset}: unknown asset_id')
            else:
                for field in ('relative_path', 'duration_seconds'):
                    if row[field] != assets[asset][field]:
                        errors.append(f'queue {asset}: {field} differs from manifest')
            review = row['review']
            if review not in ('pending', 'keep', 'hold', 'exclude'):
                errors.append(f'queue {asset}: invalid review')
            reviews[review] += 1
    if not rows:
        errors.append('Manifest contains no assets')
    return dict(files=len(rows), errors=errors, pending_metadata=dict(pending),
                queue_reviews=dict(reviews), files_checked=root is not None,
                limitations='Metadata and optional file existence checks only. No audio decoding, hash recomputation, listening, license verification, or confirmation of recording groups. Nonempty metadata is not proof of training readiness.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--queue', type=Path)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.report and args.report.exists():
        parser.error('Report exists; choose a new output path')
    if args.root and not args.root.is_dir():
        parser.error('Source directory does not exist')
    try:
        rows = read_csv(args.manifest, FIELDS)
        queue = read_csv(args.queue, ['asset_id', 'relative_path', 'duration_seconds', 'review', 'listening_notes']) if args.queue else None
        report = validate(rows, queue, args.root)
        output = json.dumps(report, ensure_ascii=False, indent=2)
        if args.report:
            with args.report.open('x', encoding='utf-8') as stream:
                stream.write(output + '\n')
        print(output)
        return 1 if report['errors'] else 0
    except (OSError, ValueError, csv.Error) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    raise SystemExit(main())
