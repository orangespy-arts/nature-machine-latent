"""按声学特征从候选目录中挑选与参考素材最接近的文件，使总时长接近参考素材总时长。

这是基于信号特征的初筛代理，不是试听判断：
- 每个文件下混单声道、重采样到 44100 Hz 后，以 2048 点窗、1024 点跳步计算逐帧特征。
- 特征：活动帧比例、活动帧电平起伏、起音密度、谱质心、谱平坦度、四个频段能量占比。
- 所有特征以参考＋候选合并的均值／标准差标准化；每个候选文件取与参考集最近 k 个文件的平均欧氏距离为得分。
- 按得分从低到高累加，直到最接近目标时长（整文件，不剪辑）。

输出 CSV（全部候选及得分、是否入选）和 JSON 汇总；已存在的输出会被拒绝覆盖。
依赖：numpy、soundfile、soxr。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import soxr

SR = 44100
N_FFT = 2048
HOP = 1024
BANDS = [(0, 500), (500, 2000), (2000, 8000), (8000, SR / 2)]
FEATURES = [
    "active_ratio", "level_spread_db", "onset_rate_hz", "log_centroid",
    "flatness_db", "band_low", "band_mid", "band_high", "band_air",
]


def load_mono(path: Path) -> np.ndarray:
    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    m = x.mean(axis=1)
    return soxr.resample(m, sr, SR, quality="HQ") if sr != SR else m


def features(y: np.ndarray) -> dict:
    n = 1 + max(0, (len(y) - N_FFT) // HOP)
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n)[:, None]
    frames = y[idx] * np.hanning(N_FFT).astype(np.float32)
    spec = np.abs(np.fft.rfft(frames, axis=1)) ** 2 + 1e-12
    freqs = np.fft.rfftfreq(N_FFT, 1 / SR)

    energy = spec.sum(axis=1)
    edb = 10 * np.log10(energy)
    active = edb > edb.max() - 40  # 活动帧：距文件最响帧 40 dB 以内
    if active.sum() < 5:
        active = edb >= np.percentile(edb, 50)
    a = spec[active]

    centroid = (a * freqs).sum(axis=1) / a.sum(axis=1)
    flat = np.exp(np.log(a).mean(axis=1)) / a.mean(axis=1)
    band_e = np.array([a[:, (freqs >= lo) & (freqs < hi)].sum() for lo, hi in BANDS])
    band_e = band_e / band_e.sum()

    # 起音：对数谱通量的正向峰值（超过中位数 + 6 dB 的局部极大值）
    lspec = np.log10(spec)
    flux = np.maximum(lspec[1:] - lspec[:-1], 0).mean(axis=1)
    thr = np.median(flux) + 2.0 * (np.median(np.abs(flux - np.median(flux))) * 1.4826 + 1e-9)
    peaks = (flux[1:-1] > thr) & (flux[1:-1] >= flux[:-2]) & (flux[1:-1] > flux[2:])
    dur = len(y) / SR

    ea = edb[active]
    return {
        "active_ratio": float(active.mean()),
        "level_spread_db": float(np.percentile(ea, 90) - np.percentile(ea, 10)),
        "onset_rate_hz": float(peaks.sum() / dur),
        "log_centroid": float(np.log2(np.median(centroid))),
        "flatness_db": float(10 * np.log10(np.median(flat))),
        "band_low": float(band_e[0]),
        "band_mid": float(band_e[1]),
        "band_high": float(band_e[2]),
        "band_air": float(band_e[3]),
        "duration_seconds": dur,
    }


def scan(root: Path) -> list[tuple[str, dict]]:
    out = []
    for f in sorted(p for p in root.rglob("*") if p.suffix.lower() == ".wav"):
        out.append((f.relative_to(root).as_posix(), features(load_mono(f))))
        print(f"  {f.name}", file=sys.stderr)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--reference", required=True, type=Path, help="参考素材目录（目标声音风格）")
    p.add_argument("--candidates", required=True, type=Path, help="候选素材目录")
    p.add_argument("--output", required=True, type=Path, help="新的 CSV 路径")
    p.add_argument("--report", required=True, type=Path, help="新的 JSON 路径")
    p.add_argument("--k", type=int, default=3, help="最近参考文件数")
    p.add_argument("--target-seconds", type=float, help="目标总时长；默认等于参考素材总时长")
    args = p.parse_args()

    for path in (args.output, args.report):
        if path.exists():
            print(f"输出已存在，拒绝覆盖：{path}", file=sys.stderr)
            return 2

    print("扫描参考素材…", file=sys.stderr)
    ref = scan(args.reference)
    print("扫描候选素材…", file=sys.stderr)
    cand = scan(args.candidates)

    R = np.array([[f[k] for k in FEATURES] for _, f in ref])
    C = np.array([[f[k] for k in FEATURES] for _, f in cand])
    # 用参考+候选的合并统计量标准化，避免参考集内几乎不变的特征（如活动比例）独占权重
    pooled = np.vstack([R, C])
    mu, sd = pooled.mean(axis=0), pooled.std(axis=0) + 1e-9
    Rz, Cz = (R - mu) / sd, (C - mu) / sd
    dist = np.sqrt(((Cz[:, None, :] - Rz[None, :, :]) ** 2).sum(axis=2))
    order_ref = np.argsort(dist, axis=1)[:, : args.k]
    score = np.take_along_axis(dist, order_ref, axis=1).mean(axis=1)

    target = args.target_seconds or sum(f["duration_seconds"] for _, f in ref)
    ranking = np.argsort(score)
    durs = np.array([f["duration_seconds"] for _, f in cand])
    total, chosen = 0.0, []
    for i in ranking:
        if abs(total + durs[i] - target) < abs(total - target):
            chosen.append(i)
            total += durs[i]
        elif total + durs[i] > target:
            continue
    chosen_set = set(int(i) for i in chosen)

    with args.output.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "relative_path", "selected", "score", "nearest_reference", "duration_seconds", *FEATURES])
        for rank, i in enumerate(ranking, 1):
            path, f = cand[i]
            nearest = ";".join(ref[j][0].split("/")[-1] for j in order_ref[i])
            w.writerow([rank, path, int(i in chosen_set), f"{score[i]:.3f}", nearest,
                        f"{f['duration_seconds']:.3f}", *(f"{f[k]:.4f}" for k in FEATURES)])

    report = {
        "method": "kNN distance in pooled-standardized feature space; whole files, no trimming; signal proxy, not listening",
        "features": FEATURES,
        "k": args.k,
        "reference_root": str(args.reference.resolve()),
        "candidate_root": str(args.candidates.resolve()),
        "reference_files": len(ref),
        "reference_total_seconds": round(sum(f["duration_seconds"] for _, f in ref), 3),
        "candidate_files": len(cand),
        "candidate_total_seconds": round(float(durs.sum()), 3),
        "target_seconds": round(target, 3),
        "selected_files": len(chosen_set),
        "selected_total_seconds": round(total, 3),
        "selected_active_seconds_estimate": round(sum(cand[i][1]["duration_seconds"] * cand[i][1]["active_ratio"] for i in chosen_set), 1),
        "reference_feature_mean": dict(zip(FEATURES, map(float, R.mean(axis=0)))),
        "pooled_feature_std": dict(zip(FEATURES, map(float, sd))),
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"入选 {len(chosen_set)}/{len(cand)} 个文件，共 {total:.2f}s；目标 {target:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
