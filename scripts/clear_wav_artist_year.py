"""Clear standard WAV artist/date tags, preserving PCM and other metadata.

Handles RIFF INFO, ID3v2.3/v2.4, iXML MediaArtist/date attributes and BEXT
origination date. Does not decode proprietary Soundminer SMED metadata.
Stores original metadata chunks for recovery before editing each file.
"""
import argparse
import base64
import csv
import hashlib
import json
import re
import struct
from collections import Counter
from pathlib import Path


def synchsafe(data):
    if any(x & 128 for x in data):
        raise ValueError('Invalid ID3 synchsafe size')
    return sum(x << (7 * (len(data) - i - 1)) for i, x in enumerate(data))


def clean_chunk(tag, data):
    removed = Counter()
    if tag == b'LIST' and data[:4] == b'INFO':
        kept, i = bytearray(b'INFO'), 4
        while i + 8 <= len(data):
            key, size = struct.unpack('<4sI', data[i:i + 8])
            end = i + 8 + size + size % 2
            if end > len(data):
                raise ValueError('Truncated INFO field')
            if key in (b'IART', b'ICRD'):
                removed['INFO:' + key.decode()] += 1
            else:
                kept.extend(data[i:end])
            i = end
        kept.extend(data[i:])
        gap = len(data) - len(kept)
        if gap:
            kept.extend(b'JUNK' + struct.pack('<I', gap - 8) + bytes(gap - 8))
        data = bytes(kept)
    elif tag.lower() == b'id3 ':
        if data[:3] != b'ID3' or data[3] not in (3, 4) or data[5] != 0:
            raise ValueError('Unsupported ID3 version or header flags')
        end = 10 + synchsafe(data[6:10])
        if end > len(data):
            raise ValueError('Truncated ID3 tag')
        i, frames = 10, bytearray()
        targets = {b'TPE1', b'TPE2', b'TPE3', b'TPE4', b'TOPE', b'TYER',
                   b'TORY', b'TDRC', b'TDOR', b'TDRL', b'TDEN', b'TDAT'}
        while i + 10 <= end and data[i]:
            key = data[i:i + 4]
            size_bytes = data[i + 4:i + 8]
            size = synchsafe(size_bytes) if data[3] == 4 else int.from_bytes(size_bytes, 'big')
            stop = i + 10 + size
            if stop > end:
                raise ValueError('Truncated ID3 frame')
            if key in targets:
                removed['ID3:' + key.decode()] += 1
            else:
                frames.extend(data[i:stop])
            i = stop
        if any(data[i:end]):
            raise ValueError('Unexpected ID3 padding')
        data = data[:10] + bytes(frames) + bytes(end - 10 - len(frames)) + data[end:]
    elif tag == b'iXML':
        def replace(match):
            attr = match.group()
            name = re.search(rb'<NAME>(.*?)</NAME>', attr, re.S)
            if name and name[1].lower() in (b'mediaartist', b'artist', b'albumartist', b'year', b'mediayear', b'date', b'mediadate'):
                removed['iXML:' + name[1].decode()] += 1
                return b''
            return attr
        cleaned = re.sub(rb'<ATTR>.*?</ATTR>', replace, data, flags=re.S)
        data = cleaned + bytes(len(data) - len(cleaned))
    elif tag == b'bext' and len(data) >= 330:
        if data[320:330].strip(b'\0 '):
            removed['BEXT:origination_date'] += 1
            data = data[:320] + bytes(10) + data[330:]
    return data, removed


def inspect(path):
    patches, removed = [], Counter()
    pcm = hashlib.sha256()
    with path.open('rb') as stream:
        head = stream.read(12)
        if head[:4] != b'RIFF' or head[8:] != b'WAVE':
            raise ValueError(f'Unsupported WAV: {path}')
        end = 8 + struct.unpack('<I', head[4:8])[0]
        if end != path.stat().st_size:
            raise ValueError(f'RIFF size mismatch: {path}')
        while stream.tell() < end:
            tag, size = struct.unpack('<4sI', stream.read(8))
            offset = stream.tell()
            if offset + size + size % 2 > end:
                raise ValueError('Chunk exceeds file')
            if tag == b'data':
                remaining = size
                while remaining:
                    chunk = stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError('Truncated PCM')
                    pcm.update(chunk)
                    remaining -= len(chunk)
            elif tag in (b'LIST', b'iXML', b'bext') or tag.lower() == b'id3 ':
                original = stream.read(size)
                cleaned, fields = clean_chunk(tag, original)
                if fields:
                    assert len(cleaned) == len(original)
                    patches.append((offset, original, cleaned))
                    removed.update(fields)
            else:
                stream.seek(size, 1)
            stream.seek(size % 2, 1)
    return patches, removed, pcm.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists() or args.backup.exists():
        parser.error('Choose new report and backup paths')
    root = args.root.resolve()
    with args.manifest.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    plans = []
    for row in rows:
        path = (root / row['relative_path']).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Path outside root')
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != row['sha256']:
            raise ValueError(f'Original hash mismatch: {path}')
        patches, removed, pcm = inspect(path)
        plans.append((row, path, patches, removed, pcm))
    args.backup.mkdir(parents=True)
    results = []
    for index, (row, path, patches, removed, pcm) in enumerate(plans, 1):
        backup = dict(asset_id=row['asset_id'], relative_path=row['relative_path'],
                      original_sha256=row['sha256'], pcm_sha256=pcm,
                      patches=[dict(offset=offset, original_base64=base64.b64encode(old).decode())
                               for offset, old, new in patches])
        with (args.backup / (row['asset_id'] + '.json')).open('x', encoding='utf-8') as stream:
            json.dump(backup, stream)
        try:
            with path.open('r+b') as stream:
                for offset, old, new in patches:
                    stream.seek(offset)
                    stream.write(new)
            remaining, _, actual_pcm = inspect(path)
            if remaining or actual_pcm != pcm:
                raise ValueError(f'Post-edit verification failed: {path}')
        except Exception:
            with path.open('r+b') as stream:
                for offset, old, new in patches:
                    stream.seek(offset)
                    stream.write(old)
            raise
        with path.open('rb') as stream:
            new_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
        results.append(dict(asset_id=row['asset_id'], relative_path=row['relative_path'],
                            original_sha256=row['sha256'], sha256=new_hash,
                            pcm_sha256=pcm, removed=dict(removed)))
        row['sha256'] = new_hash
        row['notes'] += '; standard_artist_year_tags=cleared; pcm=unchanged'
        if index % 100 == 0:
            print(f'Cleaned and verified {index}/{len(rows)}', flush=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(dict(files=len(results), results=results,
                       limitations='Standard RIFF INFO, ID3, iXML artist/date and BEXT date cleared. Proprietary SMED left unchanged; copyright and other provenance fields retained.'),
                  stream, ensure_ascii=False, indent=2)
    with args.manifest.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Finished: {len(rows)} files; PCM unchanged; manifest hashes updated.')


if __name__ == '__main__':
    main()
