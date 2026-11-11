"""将 WAV 素材统一转换为指定采样率的单声道 WAV，输出到新目录，保留原件。

处理步骤：
1. 多声道取各声道平均值下混为单声道（RAVE preprocess 在 channels=1 时只取第 0 声道，
   这里事先下混，避免只用左声道）。
2. 使用 soxr VHQ 重采样到目标采样率（默认 44100 Hz，与 RAVE preprocess 默认一致）。
3. 不做响度归一化、降噪或剪辑；电平保持原样。仅当重采样后峰值超过 0.999 时，
   对该文件整体做最小衰减（不削波），并在报告中记录 gain_applied_db。
4. 写入 24-bit PCM，并生成 JSON 报告，记录源文件与输出文件 SHA-256。

依赖：numpy、soundfile、soxr（见项目 .venv）。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf
import soxr


PEAK_LIMIT = 0.999


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", required=True, type=Path, help="源素材根目录（递归查找 .wav）")
    p.add_argument("--output", required=True, type=Path, help="新的输出目录，必须不存在")
    p.add_argument("--report", required=True, type=Path, help="新的 JSON 报告路径，必须不存在")
    p.add_argument("--sample-rate", type=int, default=44100)
    p.add_argument("--subtype", default="PCM_24", help="soundfile 写入格式，默认 PCM_24")
    p.add_argument("--selection", type=Path,
                   help="可选：只处理 CSV 中 selected=1 的行；relative_path 相对 --root（如 select_matching_audio.py 的输出）")
    args = p.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"源目录不存在：{root}", file=sys.stderr)
        return 2
    if args.output.exists():
        print(f"输出目录已存在，拒绝覆盖：{args.output}", file=sys.stderr)
        return 2
    if args.report.exists():
        print(f"报告已存在，拒绝覆盖：{args.report}", file=sys.stderr)
        return 2
    if not args.report.parent.is_dir():
        print(f"报告父目录不存在：{args.report.parent}", file=sys.stderr)
        return 2

    files = sorted(f for f in root.rglob("*") if f.is_file() and f.suffix.lower() == ".wav")
    if args.selection:
        with args.selection.open(encoding="utf-8-sig", newline="") as fh:
            wanted = {r["relative_path"] for r in csv.DictReader(fh) if r.get("selected") == "1"}
        present = {f.relative_to(root).as_posix() for f in files}
        missing = sorted(wanted - present)
        if missing:
            print(f"选片清单中有 {len(missing)} 个文件不存在，例如：{missing[0]}", file=sys.stderr)
            return 2
        files = [f for f in files if f.relative_to(root).as_posix() in wanted]
    if not files:
        print("未找到 WAV 文件", file=sys.stderr)
        return 2

    args.output.mkdir(parents=True)
    entries = []
    total = 0.0
    for src in files:
        rel = src.relative_to(root)
        dst = args.output / rel
        dst.parent.mkdir(parents=True, exist_ok=True)

        info = sf.info(str(src))
        x, sr = sf.read(str(src), dtype="float64", always_2d=True)
        mono = x.mean(axis=1)
        y = soxr.resample(mono, sr, args.sample_rate, quality="VHQ") if sr != args.sample_rate else mono
        peak = float(np.abs(y).max()) if y.size else 0.0
        gain_db = 0.0
        if peak > PEAK_LIMIT:
            # 重采样产生的样本间峰值超过上限时，整体做最小衰减，不削波；衰减量写入报告
            g = PEAK_LIMIT / peak
            y = y * g
            gain_db = 20 * np.log10(g)
            print(f"  峰值 {peak:.4f} 超过 {PEAK_LIMIT}，整体衰减 {gain_db:.3f} dB：{rel}", file=sys.stderr)
            peak = PEAK_LIMIT
        sf.write(str(dst), y, args.sample_rate, subtype=args.subtype)

        dur = len(y) / args.sample_rate
        total += dur
        entries.append({
            "relative_path": rel.as_posix(),
            "source_sample_rate_hz": sr,
            "source_channels": x.shape[1],
            "source_subtype": info.subtype,
            "source_duration_seconds": round(x.shape[0] / sr, 4),
            "source_sha256": sha256(src),
            "output_sample_rate_hz": args.sample_rate,
            "output_channels": 1,
            "output_subtype": args.subtype,
            "output_duration_seconds": round(dur, 4),
            "gain_applied_db": round(gain_db, 4),
            "output_peak_dbfs": round(20 * np.log10(peak), 2) if peak > 0 else None,
            "output_sha256": sha256(dst),
        })
        print(f"{rel.as_posix():60s} {sr}Hz {x.shape[1]}ch -> {args.sample_rate}Hz 1ch  {dur:8.2f}s")

    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_root": str(root),
        "selection": str(args.selection.resolve()) if args.selection else None,
        "output_root": str(args.output.resolve()),
        "processing": {
            "downmix": "mean of all channels",
            "resampler": f"soxr {soxr.__version__} VHQ",
            "sample_rate_hz": args.sample_rate,
            "subtype": args.subtype,
            "normalization": "none",
            "trimming": "none",
            "peak_protection": f"files whose resampled peak exceeds {PEAK_LIMIT} are attenuated to {PEAK_LIMIT}; see gain_applied_db",
        },
        "file_count": len(entries),
        "total_duration_seconds": round(total, 2),
        "files": entries,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"共 {len(entries)} 个文件，{total:.2f}s（{total / 60:.2f} 分钟）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
