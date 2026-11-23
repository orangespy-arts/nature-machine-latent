"""黑屏时的提示动画：提醒观众拿起桌上的手电筒照向桌面；检测到光斑后淡出，交给正常的揭示画面。

动画：一团柔和的暖白光（像手电光）在画面中缓慢游走，下方文字缓慢明暗呼吸。
文字用 Pillow 渲染（OpenCV putText 不支持中文），启动时渲染一次。
参数在 layout.json 的 "prompt"。
"""
from pathlib import Path

import numpy as np


def _render_text(lines, font_path, sizes, color, gap):
    """把多行文字渲染成 (BGR float32, alpha float32) 的小图。"""
    from PIL import Image, ImageDraw, ImageFont
    fonts = []
    for s in sizes:
        try:
            fonts.append(ImageFont.truetype(font_path, s))
        except OSError:
            print(f'prompt: font {font_path} not found, using default (no Chinese)', flush=True)
            fonts.append(ImageFont.load_default())
    boxes = [f.getbbox(t) for t, f in zip(lines, fonts)]
    w = max(b[2] - b[0] for b in boxes) + 20
    h = sum(b[3] - b[1] for b in boxes) + gap * (len(lines) - 1) + 20
    img = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(img)
    y = 10
    for t, f, b in zip(lines, fonts, boxes):
        tw = b[2] - b[0]
        d.text(((w - tw) / 2 - b[0], y - b[1]), t, font=f, fill=255)
        y += b[3] - b[1] + gap
    a = np.asarray(img, np.float32)[..., None] / 255.0
    col = np.ones((h, w, 3), np.float32) * np.array(color[::-1], np.float32)  # RGB → BGR
    return col, a


def _glow(size):
    yy, xx = np.mgrid[0:size, 0:size]
    r = np.hypot(xx - (size - 1) / 2, yy - (size - 1) / 2) / (size / 2)
    g = np.clip(1 - r, 0, 1) ** 1.6  # 中心亮、边缘渐隐，近似手电光斑
    return g[..., None].astype(np.float32)


class IdlePrompt:
    def __init__(self, cfg, W, H):
        self.cfg, self.W, self.H = cfg, W, H
        lines = list(cfg.get('lines', ['拿起桌上的手电筒', '照向桌面']))
        sizes = [cfg.get('font_px', 88)] * len(lines)
        if cfg.get('sub'):
            lines.append(cfg['sub'])
            sizes.append(cfg.get('sub_font_px', 40))
        self.text, self.text_a = _render_text(lines, cfg.get('font', 'C:/Windows/Fonts/msyh.ttc'), sizes,
                                              cfg.get('text_rgb', [235, 225, 205]), cfg.get('line_gap', 24))
        self.gs = int(cfg.get('glow_px', 520))
        self.glow = _glow(self.gs)
        self.glow_col = np.array(cfg.get('glow_rgb', [255, 236, 200])[::-1], np.float32)
        self.alpha = 0.0

    def update(self, idle_s, dt):
        """idle_s：已经多久没有检测到光斑（秒）。返回当前不透明度 0–1。"""
        c = self.cfg
        if idle_s >= c.get('idle_after_s', 2.0):
            self.alpha = min(1.0, self.alpha + dt / max(c.get('fade_in_s', 1.5), 1e-3))
        else:
            self.alpha = max(0.0, self.alpha - dt / max(c.get('fade_out_s', 0.3), 1e-3))
        return self.alpha

    def draw(self, canvas, t):
        if self.alpha <= 0:
            return
        c, W, H = self.cfg, self.W, self.H
        a = self.alpha
        # 光团：在画面上半部缓慢游走（李萨如曲线，周期约 9–13 秒），像有人拿手电在找
        gx = W * (0.5 + 0.28 * np.sin(2 * np.pi * t / 13.0))
        gy = H * (0.36 + 0.14 * np.sin(2 * np.pi * t / 9.0 + 0.8))
        k = c.get('glow_brightness', 0.28) * a * (0.85 + 0.15 * np.sin(2 * np.pi * t / 2.3))
        self._add(canvas, self.glow_col * 1.0, self.glow * k, gx - self.gs / 2, gy - self.gs / 2)
        # 文字：画面下部居中，亮度缓慢呼吸
        th, tw = self.text.shape[:2]
        k = c.get('text_brightness', 0.75) * a * (0.6 + 0.4 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 3.0)))
        self._add(canvas, self.text, self.text_a * k, (W - tw) / 2, H * c.get('text_y', 0.68) - th / 2)

    def _add(self, canvas, col, alpha, x0, y0):
        """在 canvas 上按 alpha 混合颜色（col 为整幅小图或单色）。"""
        H, W = canvas.shape[:2]
        h, w = alpha.shape[:2]
        x0, y0 = int(round(x0)), int(round(y0))
        xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
        if xa >= xb or ya >= yb:
            return
        m = alpha[ya - y0:yb - y0, xa - x0:xb - x0]
        src = col[ya - y0:yb - y0, xa - x0:xb - x0] if col.ndim == 3 else col
        roi = canvas[ya:yb, xa:xb].astype(np.float32)
        canvas[ya:yb, xa:xb] = (roi * (1 - m) + src * m).astype(np.uint8)


if __name__ == '__main__':  # 预览：python visual/prompt.py [输出目录]
    import json
    import sys
    import cv2
    here = Path(__file__).resolve().parent
    layout = json.loads((here / 'layout.json').read_text(encoding='utf-8'))
    W, H = layout['canvas']['width'], layout['canvas']['height']
    p = IdlePrompt(layout.get('prompt', {}), W, H)
    p.alpha = 1.0
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else here / 'local'
    out.mkdir(parents=True, exist_ok=True)
    for t in (0.0, 3.0, 6.0):
        c = np.zeros((H, W, 3), np.uint8)
        p.draw(c, t)
        cv2.imwrite(str(out / f'prompt_t{t:.0f}.png'), c)
    print('saved previews to', out)
