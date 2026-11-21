"""出一张对照图：行 = 区域，列 = t_index × 种子，用来挑加噪强度和检查提示词效果。

  python visual/sweep_strength.py --out <目录> [--t_index 5,10,15,20,25] [--seeds 0,1] [--regions insect_tl,hybrid_tl,machine]

t_index 每换一次要重建管线（约 2 秒）。输出 sweep.png 与每张单图。
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from sdgen import Generator, load_base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--layout', default=str(Path(__file__).with_name('layout.json')))
    ap.add_argument('--out', required=True)
    ap.add_argument('--t_index', default='5,10,15,20,25')
    ap.add_argument('--seeds', default='0,1')
    ap.add_argument('--regions', default='insect_tl,hybrid_tl,machine')
    ap.add_argument('--thumb', type=int, default=256)
    args = ap.parse_args()

    layout = json.loads(Path(args.layout).read_text(encoding='utf-8'))
    names = [r['name'] for r in layout['regions']]
    pick = [names.index(n) for n in args.regions.split(',')]
    seeds = [int(s) for s in args.seeds.split(',')]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    cols = {}
    for t in [int(v) for v in args.t_index.split(',')]:
        layout['generation']['t_index'] = t
        gen = Generator(layout, Path(args.layout).parent)
        for seed in seeds:
            gen.reseed(seed)
            col = []
            for i in pick:
                w = np.zeros(len(names))
                w[i] = 1
                img = gen.generate(w)
                cv2.imwrite(str(out / f'{names[i]}_t{t:02d}_s{seed}.png'), img[..., ::-1])
                col.append(cv2.resize(img, (args.thumb, args.thumb)))
            cols[(t, seed)] = np.concatenate(col, 0)
        del gen
    # 第一列放底图
    bases =np.concatenate([cv2.resize(load_base(layout['regions'][i], i, Path(args.layout).parent),
                                       (args.thumb, args.thumb)) for i in pick], 0)
    sheet = np.concatenate([bases] + [cols[k] for k in sorted(cols)], 1)
    labels = ['base'] + [f't{t} s{s}' for t, s in sorted(cols)]
    sheet = sheet[..., ::-1].copy()
    for j, lab in enumerate(labels):
        cv2.putText(sheet, lab, (j * args.thumb + 6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    for k, i in enumerate(pick):
        cv2.putText(sheet, names[i], (6, k * args.thumb + args.thumb - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(str(out / 'sweep.png'), sheet)
    print('saved', out / 'sweep.png')


if __name__ == '__main__':
    main()
