"""自然↔机械：潜在轨迹线性插值，与直接混合原声对照（exp-003 第 12 步）。

每一对（一段自然 + 一段机械，等长）输出到 <out>/<pair_id>/：

  latent_a000.wav … latent_a100.wav  z = (1-a)·z_自然 + a·z_机械，再 decode
  audio_a000.wav  … audio_a100.wav   x = (1-a)·x_自然 + a·x_机械（直接混合两段原声，对照组）
  latent_sweep.wav / audio_sweep.wav  a 在整段内从 0 线性变到 1
  latent_sequence.wav / audio_sequence.wav  各 a 依次拼接，中间 0.5 秒静音（便于连续试听）
  source_nature.wav / source_machine.wav   电平调整后的输入原段
<out>/summary.csv

做法与限制（依据 RAVE 2.3.1 scripts/export.py VariationalScriptedRAVE、rave/blocks.py VariationalEncoder）：
- 导出模型的 encode 对后验做随机采样（mean + std·randn），经 PCA 后只保留前 latent_size 维（本模型 4 维）；
  decode 把其余维度补随机噪声。所以插值只作用在这 4 维上，输出带随机性；用 --seed 固定，结果可复现。
- 两段输入先各自调到同一 RMS（--target_dbfs，峰值不超过 --peak_dbfs），使插值与原声混合起点相同。
- 编码时在段前多取 --preroll 秒、段后补静音，丢掉 streaming 卷积缓存的起始过渡；输出按
  a=0 重建与自然原段的包络互相关估计延迟后对齐裁切（与 render_listening.py 相同方法）。
- 每次 encode／decode 都重新加载模型，避免 streaming 缓存在调用之间残留。
- 这是外围程序对潜在向量的线性运算，不是模型自带的“自然—机械”控制；中间点听起来是什么，需要试听判断。

示例：
  python scripts/render_interpolation.py --model <model.ts> --input <heldout 目录> --output <listening 目录> \
    --pair night_forest_a.wav@3.5 torque_wrench_turning_constant.wav@0 --device cuda
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_listening import db, estimate_delay, rms  # noqa: E402


def load_segment(path, start, seconds, preroll):
    x, sr = sf.read(str(path), dtype='float32', always_2d=True)
    x = x[:, 0]
    s = int(round(start * sr))
    n = int(round(seconds * sr))
    p = min(int(round(preroll * sr)), s)
    if s + n > len(x):
        raise SystemExit(f'{path.name}: {start}+{seconds} 秒超出文件长度 {len(x) / sr:.2f} 秒')
    return x[s - p:s + n], p, sr


def run_model(model_path, device, seed, fn):
    torch.manual_seed(seed)
    model = torch.jit.load(model_path, map_location=device).eval()
    with torch.no_grad():
        return fn(model)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--input', required=True, help='含 nature/、machine/ 子文件夹的目录')
    ap.add_argument('--output', required=True)
    ap.add_argument('--pair', nargs=2, action='append', required=True,
                    metavar=('NATURE@START', 'MACHINE@START'),
                    help='nature/ 与 machine/ 下的文件名及起点秒数，可重复')
    ap.add_argument('--seconds', type=float, default=10.0)
    ap.add_argument('--preroll', type=float, default=2.0)
    ap.add_argument('--alphas', default='0,0.25,0.5,0.75,1')
    ap.add_argument('--target_dbfs', type=float, default=-20.0)
    ap.add_argument('--peak_dbfs', type=float, default=-1.0)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--device', default='cpu')
    ap.add_argument('--threads', type=int, default=8)
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    alphas = [float(a) for a in args.alphas.split(',')]
    inp, out = Path(args.input), Path(args.output)
    rows = []

    for nat_spec, mach_spec in args.pair:
        nat_name, nat_start = nat_spec.rsplit('@', 1)
        mach_name, mach_start = mach_spec.rsplit('@', 1)
        xn, pre_n, sr = load_segment(inp / 'nature' / nat_name, float(nat_start), args.seconds, args.preroll)
        xm, pre_m, sr_m = load_segment(inp / 'machine' / mach_name, float(mach_start), args.seconds, args.preroll)
        assert sr == sr_m
        # 两段对齐到相同预卷长度（取较短者）
        pre = min(pre_n, pre_m)
        xn, xm = xn[pre_n - pre:], xm[pre_m - pre:]
        n = len(xn) - pre

        # 统一电平：按段本体（不含预卷）的 RMS
        def norm(x):
            g = 10 ** (args.target_dbfs / 20) / max(rms(x[pre:]), 1e-9)
            g = min(g, 10 ** (args.peak_dbfs / 20) / max(np.abs(x).max(), 1e-9))
            return (x * g).astype(np.float32), g
        xn, gn = norm(xn)
        xm, gm = norm(xm)

        tail = 2048 * int(np.ceil(sr / 2048))
        pad = (-(len(xn) + tail)) % 2048 + tail

        def encode(x):
            xp = np.concatenate([x, np.zeros(pad, np.float32)])
            t = torch.from_numpy(xp)[None, None].to(args.device)
            return run_model(args.model, args.device, args.seed, lambda m: m.encode(t))

        def decode(z):
            return run_model(args.model, args.device, args.seed,
                             lambda m: m.decode(z)[0, 0].cpu().numpy().astype(np.float32))

        zn, zm = encode(xn), encode(xm)
        assert zn.shape == zm.shape
        ratio = (len(xn) + pad) // zn.shape[-1]

        # 用 a=0 的重建估计延迟（与自然原段比）
        y0 = decode(zn)
        lag, corr = estimate_delay(xn[pre:], y0[pre:], sr)

        def crop(y):
            return y[pre + lag:pre + lag + n]

        # 时变权重（sweep）：在 latent 帧上 0→1，段本体内线性，预卷保持 0，段后保持 1
        frames = zn.shape[-1]
        f0, f1 = pre // ratio, (pre + n) // ratio
        w = np.clip((np.arange(frames) - f0) / max(f1 - f0, 1), 0, 1).astype(np.float32)
        w_t = torch.from_numpy(w).to(zn.device)[None, None]

        pair_id = f'{Path(nat_name).stem}__{Path(mach_name).stem}'
        d = out / pair_id
        d.mkdir(parents=True, exist_ok=True)
        sf.write(d / 'source_nature.wav', xn[pre:], sr, subtype='PCM_24')
        sf.write(d / 'source_machine.wav', xm[pre:], sr, subtype='PCM_24')

        gap = np.zeros(sr // 2, np.float32)
        seq = {'latent': [], 'audio': []}

        def emit(kind, tag, y, a):
            clipped = int((np.abs(y) > 1).sum())
            sf.write(d / f'{kind}_{tag}.wav', np.clip(y, -1, 1), sr, subtype='PCM_24')
            rows.append(dict(
                pair=pair_id, nature=nat_name, nature_start_s=nat_start, machine=mach_name,
                machine_start_s=mach_start, seconds=args.seconds, kind=kind, alpha=a,
                rms_dbfs=round(db(rms(y)), 2), peak_dbfs=round(db(np.abs(y).max()), 2),
                clipped_samples=clipped, delay_ms=round(1000 * lag / sr, 1),
                env_corr_a0=round(corr, 3), nature_gain_db=round(db(gn), 2),
                machine_gain_db=round(db(gm), 2), seed=args.seed,
            ))
            if tag != 'sweep':
                seq[kind] += [y, gap]

        for a in alphas:
            tag = f'a{int(round(a * 100)):03d}'
            y = y0 if a == 0 else decode((1 - a) * zn + a * zm)
            emit('latent', tag, crop(y), a)
            emit('audio', tag, (1 - a) * xn[pre:] + a * xm[pre:], a)

        emit('latent', 'sweep', crop(decode((1 - w_t) * zn + w_t * zm)), 'sweep')
        ws = np.linspace(0, 1, n, dtype=np.float32)
        emit('audio', 'sweep', (1 - ws) * xn[pre:] + ws * xm[pre:], 'sweep')

        for kind in seq:
            sf.write(d / f'{kind}_sequence.wav', np.clip(np.concatenate(seq[kind][:-1]), -1, 1),
                     sr, subtype='PCM_24')
        print(f'{pair_id}: delay {1000 * lag / sr:.1f} ms (corr {corr:.3f}), '
              f'gain nature {db(gn):.1f} dB, machine {db(gm):.1f} dB', flush=True)

    out.mkdir(parents=True, exist_ok=True)
    with open(out / 'summary.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print(f'done: {len(args.pair)} pairs -> {out}')


if __name__ == '__main__':
    main()
