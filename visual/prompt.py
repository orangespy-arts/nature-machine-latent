"""黑屏时的提示动画（无文字）：线描手电筒从桌上被拿起、打开、照向桌面，再放回。

约 10 秒一循环：
  静置（镜头上一点微光呼吸）→ 沿弧线抬起并朝下倾斜 → 像真手电一样闪两下点亮，暖光锥落到桌面
  → 光圈左右缓慢扫动：光圈里浮现细线图案（左半是弯曲的叶脉，右半是直线齿轮齿，对应“自然—机械”），
  光锥里有浮尘 → 熄灭 → 放回桌上 → 停顿。
一段时间没检测到光斑就淡入，检测到就淡出（update()）。

绘制：线条在 1/2 分辨率上用 OpenCV 抗锯齿画；光（光锥、光圈、镜头光晕）在 1/4 分辨率上填充后模糊，
再放大叠加到画布上，每帧几毫秒。参数在 layout.json 的 "prompt"；python visual/prompt.py <目录> 出预览。
"""
import math
from pathlib import Path

import cv2
import numpy as np


def _ease(x):  # easeInOutCubic
    x = min(max(x, 0.0), 1.0)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def _seg(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)


# 手电筒外形（局部坐标，单位 = 筒长；x 轴指向镜头）
_BODY = np.array([(-0.50, -0.070), (0.16, -0.070), (0.29, -0.125), (0.50, -0.125),
                  (0.50, 0.125), (0.29, 0.125), (0.16, 0.070), (-0.50, 0.070)], np.float32)
_RINGS = [-0.40, -0.35, -0.30]          # 握把上的环纹
_BUTTON = np.array([(-0.06, -0.070), (-0.06, -0.098), (0.06, -0.098), (0.06, -0.070)], np.float32)


class IdlePrompt:
    PERIOD = 10.0

    def __init__(self, cfg, W, H):
        self.cfg, self.W, self.H = cfg, W, H
        self.hw, self.hh = W // 2, H // 2            # 线条层
        self.qw, self.qh = W // 4, H // 4            # 光层
        self.alpha = 0.0
        self.light_rgb = np.array(cfg.get('light_rgb', [255, 214, 150]), np.float32)
        self.line_bgr = tuple(int(v) for v in cfg.get('line_rgb', [214, 204, 186])[::-1])
        rng = np.random.default_rng(7)
        self.dust = rng.random((cfg.get('dust', 46), 4)).astype(np.float32)  # u, v, 相位, 速度

    # ---------- 淡入淡出 ----------
    def update(self, idle_s, dt):
        c = self.cfg
        if idle_s >= c.get('idle_after_s', 2.0):
            if self.alpha == 0.0:
                self.t0 = None  # 每次重新出现都从“静置”开始
            self.alpha = min(1.0, self.alpha + dt / max(c.get('fade_in_s', 1.5), 1e-3))
        else:
            self.alpha = max(0.0, self.alpha - dt / max(c.get('fade_out_s', 0.3), 1e-3))
        return self.alpha

    # ---------- 场景状态 ----------
    def _state(self, t):
        """返回 (筒中心 x,y, 角度 rad, 光强 0–1, 微光 0–1)，坐标为 1/2 分辨率像素。"""
        hw, hh = self.hw, self.hh
        L = hh * self.cfg.get('torch_len', 0.30)
        table_y = hh * self.cfg.get('table_y', 0.74)
        rest = (hw * 0.5 + 0.10 * L, table_y - 0.125 * L - 2, math.radians(-4))
        up = (hw * 0.5 - 0.48 * L, table_y - 1.55 * L, math.radians(60))
        T = t % self.PERIOD
        lift = _ease(_seg(T, 1.2, 2.7)) - _ease(_seg(T, 7.5, 8.9))
        x = rest[0] + (up[0] - rest[0]) * lift
        y = rest[1] + (up[1] - rest[1]) * lift - math.sin(math.pi * lift) * 0.25 * L  # 弧线
        ang = rest[2] + (up[2] - rest[2]) * lift
        # 扫动（只在亮着时）
        sweep = _seg(T, 2.9, 3.6) * (1 - _seg(T, 6.8, 7.3))
        ang += sweep * math.radians(6) * math.sin(2 * math.pi * (T - 2.9) / 3.6)
        x += sweep * 0.10 * L * math.sin(2 * math.pi * (T - 2.9) / 3.6 + 0.6)
        # 开灯：两次闪烁后稳定；关灯：渐暗
        if T < 2.75:
            on = 0.0
        elif T < 3.15:
            k = (T - 2.75) / 0.4
            on = [0.9, 0.15, 1.0, 0.45, 1.0][min(int(k * 5), 4)]
        else:
            on = 1.0 - _seg(T, 7.0, 7.45)
        glint = (1 - lift) * (0.5 + 0.5 * math.sin(2 * math.pi * T / 1.6)) * (1 - on)
        return x, y, ang, on, glint, L, table_y

    # ---------- 绘制 ----------
    def draw(self, canvas, t):
        if self.alpha <= 0:
            return
        if getattr(self, 't0', None) is None:
            self.t0 = t
        t = t - self.t0
        x, y, ang, on, glint, L, ty = self._state(t)
        ca, sa = math.cos(ang), math.sin(ang)
        R = np.array([[ca, -sa], [sa, ca]], np.float32)

        def to_px(pts):
            return pts @ R.T * L + np.array([x, y], np.float32)

        lens_c = to_px(np.array([[0.50, 0.0]], np.float32))[0]
        lens_a, lens_b = to_px(np.array([[0.50, -0.10], [0.50, 0.10]], np.float32))
        lines = self._table(ty, L).copy()
        light = np.zeros((self.qh, self.qw), np.float32)
        q = 0.5  # 1/2 分辨率 → 1/4 分辨率

        # 光圈：沿镜头轴与张角边缘求与桌面交点
        pool = None
        if on > 0 and sa > 0.2:
            spread = math.radians(self.cfg.get('beam_deg', 15))
            hits = []
            for d in (-spread, spread):
                a2 = ang + d
                s2 = max(math.sin(a2), 0.15)
                hits.append(lens_c[0] + (ty - lens_c[1]) / s2 * math.cos(a2))
            cx = (hits[0] + hits[1]) / 2
            ax = min(abs(hits[1] - hits[0]) / 2, 0.75 * L)
            by = ax * 0.30
            pool = (cx, ty, ax, by)
            # 光圈里不画桌面线（光落在桌面上，线会把光圈切成两半）
            cv2.ellipse(lines, (int(cx), int(ty)), (int(ax * 1.05), int(by * 1.6)), 0, 0, 360, (0, 0, 0), -1, cv2.LINE_AA)
            # 光锥（1/4 分辨率）：镜头两端 → 光圈左右两端，亮度随距离衰减
            cone = np.zeros((self.qh, self.qw), np.uint8)
            poly = np.array([lens_a, lens_b, (cx + ax, ty), (cx, ty + by), (cx - ax, ty)], np.float32) * q
            cv2.fillPoly(cone, [poly.astype(np.int32)], 255)
            ys, xs = np.nonzero(cone)  # 只算光锥内的像素
            d = np.hypot(xs - lens_c[0] * q, ys - lens_c[1] * q)
            fall = np.clip(1.15 - d / (np.hypot(cx - lens_c[0], ty - lens_c[1]) * q + 1e-3), 0.35, 1.0)
            light[ys, xs] += fall * 0.30 * on
            ell = np.zeros((self.qh, self.qw), np.uint8)
            cv2.ellipse(ell, (int(cx * q), int(ty * q)), (int(ax * q), int(by * q)), 0, 0, 360, 255, -1, cv2.LINE_AA)
            light += ell.astype(np.float32) / 255 * 0.85 * on
            self._pool_pattern(lines, pool, t, on)
            self._dust(lines, lens_c, pool, t, on)

        # 镜头光晕：开灯时亮，静置时一点微光呼吸
        g = on * 1.6 + glint * 0.55
        if g > 0:
            cv2.circle(light, (int(lens_c[0] * q), int(lens_c[1] * q)), max(int(0.07 * L * q), 2), float(g), -1, cv2.LINE_AA)

        # 投影：亮着时在光圈后方，静置时在筒下方
        sh_x = x + 0.1 * L
        sh_w = 0.55 * L * (1 - 0.35 * min((ty - y) / (1.6 * L), 1))
        sh_a = 0.25 if pool is None else 0.12
        cv2.ellipse(lines, (int(sh_x), int(ty + 2)), (int(sh_w), max(int(sh_w * 0.08), 1)), 0, 0, 360,
                    tuple(int(c * sh_a) for c in self.line_bgr), 1, cv2.LINE_AA)

        # 手电筒（线描）
        col = self.line_bgr
        cv2.polylines(lines, [to_px(_BODY).astype(np.int32)], True, col, 2, cv2.LINE_AA)
        cv2.polylines(lines, [to_px(_BUTTON).astype(np.int32)], False, col, 2, cv2.LINE_AA)
        for rx in _RINGS:
            p = to_px(np.array([[rx, -0.07], [rx, 0.07]], np.float32)).astype(np.int32)
            cv2.line(lines, tuple(p[0]), tuple(p[1]), tuple(int(c * 0.6) for c in col), 1, cv2.LINE_AA)
        lens_col = tuple(int(min(255, c * (0.8 + 0.5 * on))) for c in col)
        cv2.line(lines, tuple(lens_a.astype(int)), tuple(lens_b.astype(int)), lens_col, 3, cv2.LINE_AA)

        # 合成：光层模糊（柔光＋大范围光晕）后放大
        soft = cv2.GaussianBlur(light, (0, 0), 2.2)
        small = cv2.resize(light, (self.qw // 2, self.qh // 2), interpolation=cv2.INTER_AREA)
        halo = cv2.resize(cv2.GaussianBlur(small, (0, 0), 7), (self.qw, self.qh), interpolation=cv2.INTER_LINEAR)
        lum = np.clip(soft + 0.55 * halo, 0, 1.2) * self.cfg.get('light_brightness', 0.55)
        lq = np.clip(lum[..., None] * self.light_rgb[::-1], 0, 255).astype(np.uint8)
        k = self.alpha
        half = cv2.add(cv2.resize(lq, (self.hw, self.hh), interpolation=cv2.INTER_LINEAR), lines)
        layer = cv2.resize(half, (self.W, self.H), interpolation=cv2.INTER_LINEAR)
        if k < 1:
            layer = cv2.convertScaleAbs(layer, alpha=k)
        cv2.add(canvas, layer, dst=canvas)

    def _table(self, ty, L):
        """桌面：一条细线，两端渐隐；下面一条更淡的线表示桌面厚度（静态，只画一次）。"""
        if getattr(self, '_table_img', None) is None:
            img = np.zeros((self.hh, self.hw, 3), np.uint8)
            x0, x1 = int(self.hw * 0.16), int(self.hw * 0.84)
            for xs in range(x0, x1, 6):
                f = math.sin(math.pi * (xs - x0) / (x1 - x0)) ** 0.7
                col = tuple(int(c * 0.55 * f) for c in self.line_bgr)
                cv2.line(img, (xs, int(ty)), (min(xs + 6, x1), int(ty)), col, 1, cv2.LINE_AA)
                col2 = tuple(int(c * 0.18 * f) for c in self.line_bgr)
                cv2.line(img, (xs, int(ty + 0.06 * L)), (min(xs + 6, x1), int(ty + 0.06 * L)), col2, 1, cv2.LINE_AA)
            self._table_img = img
        return self._table_img

    def _pool_pattern(self, lines, pool, t, on):
        """光圈里的细线：左半弯曲叶脉，右半齿轮齿，缓慢旋转；只在光圈里出现。"""
        cx, cy, ax, by = pool
        rot = t * 0.25
        layer = np.zeros_like(lines)
        col = tuple(int(c * 0.9) for c in self.line_bgr)
        n = 28
        for i in range(n):
            th = rot + 2 * math.pi * i / n
            right = math.cos(th) > 0
            pts = []
            for r in np.linspace(0.18, 0.82, 12):
                bend = 0.0 if right else 0.35 * math.sin(r * 3.2) * (r - 0.18)
                a2 = th + bend
                pts.append((cx + ax * r * math.cos(a2), cy + by * r * math.sin(a2)))
            cv2.polylines(layer, [np.array(pts, np.int32)], False, col, 1, cv2.LINE_AA)
            if right:  # 齿轮齿：外圈一个小方齿
                a0, a1 = th - 0.06, th + 0.06
                tooth = [(cx + ax * 0.82 * math.cos(a0), cy + by * 0.82 * math.sin(a0)),
                         (cx + ax * 0.92 * math.cos(a0), cy + by * 0.92 * math.sin(a0)),
                         (cx + ax * 0.92 * math.cos(a1), cy + by * 0.92 * math.sin(a1)),
                         (cx + ax * 0.82 * math.cos(a1), cy + by * 0.82 * math.sin(a1))]
                cv2.polylines(layer, [np.array(tooth, np.int32)], False, col, 1, cv2.LINE_AA)
        for r in (0.18, 0.5, 0.82):
            cv2.ellipse(layer, (int(cx), int(cy)), (max(int(ax * r), 1), max(int(by * r), 1)), 0, 0, 360,
                        tuple(int(c * 0.5) for c in col), 1, cv2.LINE_AA)
        # 只在光圈内，边缘渐隐；图案在开灯后约 0.8 秒才浮现
        T = t % self.PERIOD
        k = on * _seg(T, 3.1, 4.0) * 0.8
        x0, x1 = max(int(cx - ax) - 20, 0), min(int(cx + ax) + 20, lines.shape[1])
        y0, y1 = max(int(cy - by) - 20, 0), min(int(cy + by) + 20, lines.shape[0])
        if x0 < x1 and y0 < y1 and k > 0:
            m = np.zeros((y1 - y0, x1 - x0), np.float32)
            cv2.ellipse(m, (int(cx) - x0, int(cy) - y0), (int(ax * 0.95), int(by * 0.95)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
            m = cv2.GaussianBlur(m, (0, 0), 6)
            sub = layer[y0:y1, x0:x1].astype(np.float32) * (m[..., None] * k)
            lines[y0:y1, x0:x1] = np.clip(lines[y0:y1, x0:x1].astype(np.float32) + sub, 0, 255).astype(np.uint8)

    def _dust(self, lines, lens, pool, t, on):
        """光锥里缓慢飘动、闪烁的浮尘。"""
        cx, cy, ax, _ = pool
        for u0, v0, ph, sp in self.dust:
            u = (u0 + t * 0.03 * (0.5 + sp)) % 1.0
            v = (v0 * 2 - 1) * 0.85 + 0.08 * math.sin(t * 0.7 + ph * 6.28)
            px = lens[0] + (cx + v * ax - lens[0]) * u
            py = lens[1] + (cy - lens[1]) * u
            tw = 0.5 + 0.5 * math.sin(t * (1.5 + 2 * sp) + ph * 6.28)
            b = on * tw * (0.35 + 0.65 * u) * math.sin(math.pi * u)
            if b > 0.05:
                c = tuple(int(255 * b * w) for w in (0.70, 0.86, 1.0))
                cv2.circle(lines, (int(px), int(py)), 1, c, -1, cv2.LINE_AA)


if __name__ == '__main__':  # 预览：python visual/prompt.py [输出目录]：存 3 张关键帧＋一段 10 秒 mp4（1/2 尺寸）
    import json
    import sys
    import time
    here = Path(__file__).resolve().parent
    layout = json.loads((here / 'layout.json').read_text(encoding='utf-8'))
    W, H = layout['canvas']['width'], layout['canvas']['height']
    p = IdlePrompt(layout.get('prompt', {}), W, H)
    p.alpha, p.t0 = 1.0, 0.0
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else here / 'local'
    out.mkdir(parents=True, exist_ok=True)
    vw = cv2.VideoWriter(str(out / 'prompt_preview.mp4'), cv2.VideoWriter_fourcc(*'mp4v'), 30, (W // 2, H // 2))
    ms = []
    for i in range(300):
        c = np.zeros((H, W, 3), np.uint8)
        t0 = time.perf_counter()
        p.draw(c, i / 30)
        ms.append(1000 * (time.perf_counter() - t0))
        vw.write(cv2.resize(c, (W // 2, H // 2), interpolation=cv2.INTER_AREA))
        if i in (15, 60, 120, 165, 200):
            cv2.imwrite(str(out / f'prompt_{i / 30:04.1f}s.png'), c)
    vw.release()
    print(f'saved previews to {out}; draw {np.median(ms):.1f} ms median, {max(ms):.1f} ms max')
