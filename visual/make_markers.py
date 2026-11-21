"""生成可打印的 ArUco 标记（A4，300 dpi）。

  python visual/make_markers.py [--out visual/markers] [--ids 0,1,2,3]

输出：
  aruco_4x4_sheet.png   一页 4 个（每个约 6.8 cm 见方），用于近距离／桌面
  aruco_4x4_id<N>.png   单个整页（约 15 cm 见方），用于较远距离
  aruco_4x4_all.pdf     以上全部（300 dpi，按实际大小打印）
打印时选“实际大小／100%”，不要缩放到页面；标记外的白边（静区）不要剪掉。
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

DPI = 300
A4 = (2480, 3508)  # 宽 × 高，像素 @300 dpi


def marker(dictionary, mid, side):
    img = cv2.aruco.generateImageMarker(dictionary, mid, side)
    q = side // 6  # 静区：约 1 个模块以上的白边
    return cv2.copyMakeBorder(img, q, q, q, q, cv2.BORDER_CONSTANT, value=255)


def label(img, text, y):
    cv2.putText(img, text, (60, y), cv2.FONT_HERSHEY_SIMPLEX, 1.6, 0, 3, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(Path(__file__).with_name('markers')))
    ap.add_argument('--ids', default='0,1,2,3')
    ap.add_argument('--dictionary', default='DICT_4X4_50')
    args = ap.parse_args()
    d = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, args.dictionary))
    ids = [int(i) for i in args.ids.split(',')]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # 一页 4 个，每个 800 px ≈ 6.8 cm（含白边约 9 cm）
    side = 800
    page = np.full((A4[1], A4[0]), 255, np.uint8)
    for k, mid in enumerate(ids[:4]):
        m = marker(d, mid, side)
        r, c = divmod(k, 2)
        y0 = 250 + r * (m.shape[0] + 300)
        x0 = 120 + c * (m.shape[1] + 120)
        page[y0:y0 + m.shape[0], x0:x0 + m.shape[1]] = m
        cv2.putText(page, f'ID {mid}', (x0 + 20, y0 + m.shape[0] + 80), cv2.FONT_HERSHEY_SIMPLEX, 2.2, 0, 4, cv2.LINE_AA)
    label(page, f'{args.dictionary}  marker {side / DPI * 2.54:.1f} cm  - print at 100%, keep white border', 120)
    pages = [page]
    Image.fromarray(page).save(out / 'aruco_4x4_sheet.png', dpi=(DPI, DPI))

    # 单个整页，1800 px ≈ 15.2 cm（含白边约 20 cm）
    side = 1800
    for mid in ids:
        page = np.full((A4[1], A4[0]), 255, np.uint8)
        m = marker(d, mid, side)
        y0, x0 = (A4[1] - m.shape[0]) // 2, (A4[0] - m.shape[1]) // 2
        page[y0:y0 + m.shape[0], x0:x0 + m.shape[1]] = m
        label(page, f'{args.dictionary}  ID {mid}  marker {side / DPI * 2.54:.1f} cm  - print at 100%', 160)
        pages.append(page)
        Image.fromarray(page).save(out / f'aruco_4x4_id{mid}.png', dpi=(DPI, DPI))
    ims = [Image.fromarray(p).convert('L') for p in pages]
    ims[0].save(out / 'aruco_4x4_all.pdf', save_all=True, append_images=ims[1:], resolution=DPI)
    print('saved to', out)


if __name__ == '__main__':
    main()
