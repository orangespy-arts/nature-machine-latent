"""用导出的 RAVE 模型（.ts）重建一组音频，生成原声／重建对照试听文件。

输入目录下每个子文件夹（例如 machine/、nature/）里的 WAV 各自处理，输出：

  <out>/raw-level/<子文件夹>/<名称>__orig.wav   原声（原电平）
  <out>/raw-level/<子文件夹>/<名称>__recon.wav  重建（原电平）
  <out>/level-matched/<子文件夹>/<名称>__orig.wav / __recon.wav
        同一增益作用于原声和重建：原声 RMS 调到 --target_dbfs，且两者峰值不超过 --peak_dbfs
  <out>/level-matched/<子文件夹>/<名称>__ab.wav
        原声中 RMS 最大的 --ab_seconds 秒 → 1 秒静音 → 重建的同一段（已按估计延迟对齐）
  <out>/summary.csv

说明：
- 每个文件重新加载模型：streaming 模型的卷积缓存会跨调用保留，不重载会把上一文件的尾部带进下一文件开头。
- 输入末尾补静音到 2048 的整数倍再加 1 秒，避免 streaming 延迟截掉结尾；重建保存全长。
- 延迟用原声与重建前 60 秒对数 RMS 包络的互相关估计，只用于对齐 __ab.wav 和写入 summary，不改动 __recon.wav。
- 只做推理，CPU 运行（可用 CUDA_VISIBLE_DEVICES= 隐藏 GPU）。

示例：
  python scripts/render_listening.py --model <model.ts> --input <heldout 目录> --output <listening 目录>
"""
import argparse
import csv
import os
from pathlib import Path

import numpy as np
import soundfile as sf
import torch


def db(x):
    return 20 * np.log10(max(x, 1e-12))


def rms(x):
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) if len(x) else 0.0


def envelope(x, hop):
    n = len(x) // hop
    e = np.sqrt(np.mean(x[:n * hop].astype(np.float64).reshape(n, hop) ** 2, axis=1))
    e = np.log(e + 1e-6)
    return e - e.mean()


def estimate_delay(x, y, sr, max_delay_s=1.0, span_s=60.0, hop=64):
    """用对数 RMS 包络互相关估计重建相对原声的延迟（RAVE 不保留相位，波形互相关不可靠）。"""
    n = min(len(x), len(y), int(span_s * sr))
    a, b = envelope(x[:n], hop), envelope(y[:n], hop)
    m = int(max_delay_s * sr / hop)
    best, lag = -np.inf, 0
    for k in range(0, m + 1):  # 只考虑重建滞后于原声（因果 streaming）
        c = float(np.dot(a[:len(a) - k], b[k:]) /
                  (np.linalg.norm(a[:len(a) - k]) * np.linalg.norm(b[k:]) + 1e-12))
        if c > best:
            best, lag = c, k
    return lag * hop, best


def loudest_window(x, sr, seconds):
    w = int(seconds * sr)
    if len(x) <= w:
        return 0, len(x)
    hop = sr // 2
    best, best_start = -1.0, 0
    for s in range(0, len(x) - w + 1, hop):
        e = rms(x[s:s + w])
        if e > best:
            best, best_start = e, s
    return best_start, best_start + w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--input', required=True, help='含子文件夹（如 machine/、nature/）的目录')
    ap.add_argument('--output', required=True)
    ap.add_argument('--target_dbfs', type=float, default=-20.0)
    ap.add_argument('--peak_dbfs', type=float, default=-1.0)
    ap.add_argument('--ab_seconds', type=float, default=10.0)
    ap.add_argument('--threads', type=int, default=8)
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    inp, out = Path(args.input), Path(args.output)
    rows = []
    for wav in sorted(inp.glob('*/*.wav')):
        group = wav.parent.name
        x, sr = sf.read(str(wav), dtype='float32', always_2d=True)
        x = x[:, 0]
        model = torch.jit.load(args.model).eval()
        pad = (-len(x)) % 2048 + 2048 * int(np.ceil(sr / 2048))
        xp = np.concatenate([x, np.zeros(pad, np.float32)])
        with torch.no_grad():
            z = model.encode(torch.from_numpy(xp)[None, None])
            y = model.decode(z)[0, 0].numpy().astype(np.float32)
        lag, corr = estimate_delay(x, y, sr)

        g_rms = 10 ** (args.target_dbfs / 20) / max(rms(x), 1e-9)
        peak = max(np.abs(x).max(), np.abs(y).max(), 1e-9)
        g = min(g_rms, 10 ** (args.peak_dbfs / 20) / peak)

        stem = wav.stem
        raw_dir, lm_dir = out / 'raw-level' / group, out / 'level-matched' / group
        raw_dir.mkdir(parents=True, exist_ok=True)
        lm_dir.mkdir(parents=True, exist_ok=True)
        sf.write(raw_dir / f'{stem}__orig.wav', x, sr, subtype='PCM_24')
        sf.write(raw_dir / f'{stem}__recon.wav', np.clip(y, -1, 1), sr, subtype='PCM_24')
        sf.write(lm_dir / f'{stem}__orig.wav', x * g, sr, subtype='PCM_24')
        sf.write(lm_dir / f'{stem}__recon.wav', np.clip(y * g, -1, 1), sr, subtype='PCM_24')

        s, e = loudest_window(x, sr, args.ab_seconds)
        ys = y[s + lag:e + lag]
        ab = np.concatenate([x[s:e], np.zeros(sr, np.float32), ys]) * g
        sf.write(lm_dir / f'{stem}__ab.wav', np.clip(ab, -1, 1), sr, subtype='PCM_24')

        row = dict(
            group=group, file=wav.name, sr=sr, seconds=round(len(x) / sr, 2),
            latent_frames=z.shape[-1], latent_dims=z.shape[1],
            orig_rms_dbfs=round(db(rms(x)), 2), recon_rms_dbfs=round(db(rms(y[lag:lag + len(x)])), 2),
            orig_peak_dbfs=round(db(np.abs(x).max()), 2), recon_peak_dbfs=round(db(np.abs(y).max()), 2),
            recon_clipped_samples=int((np.abs(y) > 1).sum()),
            delay_samples=lag, delay_ms=round(1000 * lag / sr, 1), env_corr_at_delay=round(corr, 3),
            level_matched_gain_db=round(db(g), 2), ab_start_s=round(s / sr, 2), ab_end_s=round(e / sr, 2),
        )
        rows.append(row)
        print(f"{group}/{wav.name}: {row['seconds']} s, delay {row['delay_ms']} ms, "
              f"rms {row['orig_rms_dbfs']} -> {row['recon_rms_dbfs']} dBFS, gain {row['level_matched_gain_db']} dB",
              flush=True)

    out.mkdir(parents=True, exist_ok=True)
    with open(out / 'summary.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f'done: {len(rows)} files -> {out}')


if __name__ == '__main__':
    main()
