"""Read-only WAV inventory. Outputs a new manifest and report; never changes audio."""
import argparse
import csv
import hashlib
import json
import wave
from collections import Counter, defaultdict
from pathlib import Path

FIELDS = 'asset_id,relative_path,recording_group,category,sound_family,description,source,license,duration_seconds,sample_rate_hz,channels,sha256,split,notes'.split(',')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--prefix', required=True)
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error('Source directory does not exist')
    if args.output.exists() or args.report.exists():
        parser.error('Output exists; choose new paths to protect reviewed records')
    files = sorted((p for p in args.root.rglob('*') if p.is_file() and p.suffix.lower() == '.wav'), key=lambda p: p.relative_to(args.root).as_posix().casefold())
    rows, errors = [], []
    hashes = defaultdict(list)
    rates, channels, widths, folders = Counter(), Counter(), Counter(), Counter()
    total_bytes = 0
    total_duration = 0.0
    for index, path in enumerate(files, 1):
        relative = path.relative_to(args.root).as_posix()
        row = dict.fromkeys(FIELDS, '')
        row.update(asset_id=f'{args.prefix}-{index:04d}', relative_path=relative,
                   source=f'Local collection: {args.root.name}; original source unconfirmed',
                   license='unknown', split='unassigned', notes='review=pending; recording_group=unconfirmed')
        total_bytes += path.stat().st_size
        folders[str(path.relative_to(args.root).parent)] += 1
        try:
            with path.open('rb') as stream:
                row['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
            hashes[row['sha256']].append(row['asset_id'])
            with wave.open(str(path), 'rb') as audio:
                rate, count, frames = audio.getframerate(), audio.getnchannels(), audio.getnframes()
                width = audio.getsampwidth()
                duration = frames / rate
                row.update(duration_seconds=f'{duration:.6f}', sample_rate_hz=rate, channels=count)
                rates[rate] += 1
                channels[count] += 1
                widths[width * 8] += 1
                total_duration += duration
                # Read all PCM frames to detect truncated payloads, without changing files.
                expected = frames * count * width
                actual = 0
                while chunk := audio.readframes(65536):
                    actual += len(chunk)
                if actual != expected:
                    raise ValueError(f'Truncated PCM data: expected {expected}, read {actual}')
                row['notes'] += '; pcm_payload=readable; listening=not_done'
        except (OSError, EOFError, wave.Error, ValueError) as exc:
            errors.append({'asset_id': row['asset_id'], 'relative_path': relative, 'error': str(exc)})
            row['notes'] += f'; inspection_error={exc}'
        rows.append(row)
        if index % 100 == 0:
            print(f'Inspected {index}/{len(files)}', flush=True)
    duplicate_groups = [ids for ids in hashes.values() if len(ids) > 1]
    for row in rows:
        peers = hashes.get(row['sha256'], [])
        if len(peers) > 1:
            row['notes'] += '; identical_files=' + '|'.join(peers)
    report = dict(collection=args.root.name, files=len(rows), bytes=total_bytes,
                  duration_seconds=round(total_duration, 3), sample_rates=dict(rates),
                  channels=dict(channels), bit_depths=dict(widths), folders=dict(folders),
                  duplicate_groups=duplicate_groups, errors=errors,
                  limitations='PCM structural read and byte-identical duplicate check only. No listening, clipping/silence analysis, perceptual duplicate detection, or license verification.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
