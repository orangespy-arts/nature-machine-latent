"""黑屏时的提示动画（无文字）：一只圆圆的、没有手指的大手伸进来，拿起桌上的手电筒，打开，照向桌面，再放回、离开。

约 13 秒一循环（亮着约 6 秒）：
  手电静置（镜头一点微光呼吸）→ 手臂从左上方伸入，手指张开 → 握住 → 沿弧线抬起并朝下倾斜
  → 拇指按下开关，像真手电一样闪两下点亮，暖光锥落到桌面
  → 光圈左右缓慢扫动：光圈里浮现细线图案（左半是弯曲的叶脉，右半是直线齿轮齿，对应“自然—机械”），
  光锥里有浮尘 → 拇指再按，熄灭 → 放回桌上 → 手指张开，手臂收回 → 停顿。
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

# 手（局部坐标同手电，单位 = 筒长）：没有手指的圆润大手（连指手套形），一团包住握把，
# 上方一个圆圆的拇指包压在开关上；手腕有袖口。轮廓从手腕下沿绕一圈到手腕上沿，前臂接着向外延伸。
_WRIST_TOP, _WRIST_BOT = (-0.50, -0.095), (-0.52, 0.075)
# (握住时的点, 张开时的偏移)
_MITTEN = [
    ((-0.52, 0.075), (0.00, 0.00)),     # 手腕下沿
    ((-0.41, 0.110), (0.00, 0.02)),     # 掌根
    ((-0.26, 0.150), (0.05, 0.08)),     # 下方圆肚（四指合在一起）
    ((-0.11, 0.158), (0.09, 0.12)),
    ((0.015, 0.130), (0.12, 0.12)),
    ((0.068, 0.068), (0.13, 0.08)),     # 前端圆头
    ((0.075, 0.000), (0.11, 0.03)),
    ((0.052, -0.062), (0.07, 0.00)),
    ((0.050, -0.088), (0.04, -0.04)),   # 拇指：从下侧伸向前，圆头，压在开关上
    ((0.105, -0.096), (0.04, -0.06)),
    ((0.122, -0.122), (0.04, -0.07)),
    ((0.095, -0.146), (0.03, -0.07)),
    ((0.000, -0.152), (0.02, -0.05)),
    ((-0.09, -0.146), (0.00, -0.02)),
    ((-0.22, -0.148), (0.00, 0.00)),    # 手背
    ((-0.35, -0.142), (0.00, 0.00)),
    ((-0.44, -0.122), (0.00, 0.00)),
    ((-0.50, -0.095), (0.00, 0.00)),    # 手腕上沿
]
_THUMB_IDX = (8, 9, 10, 11, 12)


def _catmull(pts, n=8):
    """开放 Catmull-Rom 样条：过所有控制点的平滑曲线。"""
    p = np.asarray(pts, np.float32)
    p = np.vstack([p[:1], p, p[-1:]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(p[-2])
    return np.array(out, np.float32)


def _hand_shape(g, press):
    """返回 (轮廓控制点, 装饰线列表)。g：0 张开 → 1 握住；press：拇指按下 0–1。"""
    pts = []
    for k, ((x, y), (ox, oy)) in enumerate(_MITTEN):
        x, y = x + ox * (1 - g), y + oy * (1 - g)
        if k in _THUMB_IDX:
            y += 0.025 * press
        pts.append((x, y))
    # 袖口：手腕处两条弧线；拇指与手掌的分界；手背一小段高光弧
    cuff = [[(-0.445, -0.138), (-0.462, -0.02), (-0.445, 0.112)],
            [(-0.485, -0.112), (-0.498, -0.01), (-0.485, 0.088)]]
    o = (1 - g)
    thumb = [(pts[8][0] - 0.005, pts[8][1]), (0.00 + 0.02 * o, -0.112 - 0.03 * o + 0.02 * press), (-0.07, -0.128 - 0.01 * o)]
    shine = [(-0.30, -0.115), (-0.23, -0.123), (-0.16, -0.118)]
    return pts, cuff + [thumb, shine]


class IdlePrompt:
    PERIOD = 13.0

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
        """当前时刻的场景状态（坐标为 1/2 分辨率像素）。"""
        hw, hh = self.hw, self.hh
        L = hh * self.cfg.get('torch_len', 0.30)
        table_y = hh * self.cfg.get('table_y', 0.74)
        rest = (hw * 0.5 + 0.10 * L, table_y - 0.125 * L - 2, math.radians(-4))
        up = (hw * 0.5 - 0.48 * L, table_y - 1.55 * L, math.radians(60))
        T = t % self.PERIOD
        lift = _ease(_seg(T, 2.3, 3.6)) - _ease(_seg(T, 10.3, 11.5))
        x = rest[0] + (up[0] - rest[0]) * lift
        y = rest[1] + (up[1] - rest[1]) * lift - math.sin(math.pi * lift) * 0.25 * L  # 弧线
        ang = rest[2] + (up[2] - rest[2]) * lift
        # 扫动（只在亮着时）
        sweep = _seg(T, 4.2, 4.9) * (1 - _seg(T, 9.4, 9.9))
        ang += sweep * math.radians(6) * math.sin(2 * math.pi * (T - 4.2) / 3.4)
        x += sweep * 0.10 * L * math.sin(2 * math.pi * (T - 4.2) / 3.4 + 0.6)
        # 开灯：拇指按下后两次闪烁再稳定；关灯：拇指再按，渐暗
        if T < 3.8:
            on = 0.0
        elif T < 4.2:
            on = [0.9, 0.15, 1.0, 0.45, 1.0][min(int((T - 3.8) / 0.4 * 5), 4)]
        else:
            on = 1.0 - _seg(T, 9.95, 10.35)
        press = max(math.sin(math.pi * _seg(T, 3.6, 3.85)), math.sin(math.pi * _seg(T, 9.75, 10.0)))
        # 手：伸入（reach 1→0 为离手电的远近）、握拢（grip 0 张开 → 1 握住）
        reach = 1 - _ease(_seg(T, 0.8, 1.9)) + _ease(_seg(T, 11.8, 12.7))
        grip = _ease(_seg(T, 1.9, 2.3)) - _ease(_seg(T, 11.5, 11.8))
        glint = (1 - lift) * (0.5 + 0.5 * math.sin(2 * math.pi * T / 1.6)) * (1 - on) * (1 - grip)
        return dict(x=x, y=y, ang=ang, on=on, glint=glint, L=L, ty=table_y, press=press, reach=reach, grip=grip, T=T)

    # ---------- 绘制 ----------
    def draw(self, canvas, t):
        if self.alpha <= 0:
            return
        if getattr(self, 't0', None) is None:
            self.t0 = t
        t = t - self.t0
        st = self._state(t)
        x, y, ang, on, glint, L, ty = (st[k] for k in ('x', 'y', 'ang', 'on', 'glint', 'L', 'ty'))
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
        self._hand(lines, st, R)

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

    def _hand(self, img, st, R):
        """手。layout.json prompt.hand_style：
        filled  ——填色的卡通连指手（暖肤色＋柔和明暗，深色描边），袖子是另一种颜色、向后渐隐；
        shadow  ——没有描边的深色剪影，只有朝向镜头光的边缘被照亮；
        outline ——只有线条（黑色填充）；
        none    ——不画手，手电自己被“拿起”。"""
        style = self.cfg.get('hand_style', 'filled')
        if st['reach'] >= 0.999 or style == 'none':
            return
        L = st['L']
        shoulder = np.array([-0.30 * self.hw, -0.45 * self.hh], np.float32)
        org = np.array([st['x'], st['y']], np.float32)
        wrist0 = np.array(_WRIST_TOP, np.float32) @ R.T * L + org
        away = shoulder - wrist0
        away /= np.linalg.norm(away) + 1e-6
        off = away * st['reach'] * 1.3 * self.hw
        a = st['reach'] * 0.5   # 伸入时手稍微转动，握住时与手电对齐
        Rh = R @ np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]], np.float32)

        def P(pts):
            return np.asarray(pts, np.float32) @ Rh.T * L + org + off

        ctrl, deco = _hand_shape(st['grip'], st['press'])
        curve = P(_catmull(ctrl))
        nrm = np.array([-away[1], away[0]], np.float32)
        up = (np.array([0.0, -1.0], np.float32) @ Rh.T)        # 手背方向（局部 -y）
        if style == 'outline':
            self._hand_outline(img, curve, deco, P, away, nrm, L)
            return
        # 袖子：从袖口沿肩部方向延伸，比手腕宽，向后渐隐
        c_top, c_bot = P([(-0.45, -0.150)])[0], P([(-0.47, 0.125)])[0]
        length, widen = 1.6 * L, 0.06 * L
        side = 1.0 if np.dot(c_top - c_bot, nrm) > 0 else -1.0
        sleeve = np.array([c_top, c_top + away * length + nrm * side * widen,
                           c_bot + away * length - nrm * side * widen, c_bot], np.float32)
        if style == 'filled':
            k = 0.78
            skin = np.array([160, 190, 232], np.float32) * k        # BGR
            cloth = np.array([150, 118, 96], np.float32) * 0.62
            ink = (52, 66, 92)
            self._fill(img, sleeve, cloth, up, fade=(c_top * 0.5 + c_bot * 0.5, away, length))
            for e0 in (c_top, c_bot):
                self._fade_line(img, e0, e0 + away * length + nrm * side * widen * (1 if e0 is c_top else -1),
                                ink, 2)
            self._fill(img, curve, skin, up)
            cv2.polylines(img, [curve.astype(np.int32)], False, ink, 2, cv2.LINE_AA)
            # 袖口：一条弧线；拇指分界、手背高光
            cuff = P(_catmull([(-0.45, -0.150), (-0.475, -0.01), (-0.47, 0.125)], 6)).astype(np.int32)
            cv2.polylines(img, [cuff], False, ink, 2, cv2.LINE_AA)
            thumb, shine = deco[2], deco[3]
            cv2.polylines(img, [P(_catmull(thumb, 6)).astype(np.int32)], False, tuple(int(v * 0.9) for v in ink), 2, cv2.LINE_AA)
            cv2.polylines(img, [P(_catmull(shine, 6)).astype(np.int32)], False,
                          tuple(int(min(255, v * 1.25)) for v in skin), 2, cv2.LINE_AA)
            return
        # shadow：深色剪影，边缘按朝向镜头的程度被照亮
        dark = np.array([24, 24, 27], np.float32)
        self._fill(img, sleeve, dark, up, fade=(c_top * 0.5 + c_bot * 0.5, away, length), shade=0.0)
        self._fill(img, curve, dark, up, shade=0.0)
        lens = np.array([0.5, 0.0], np.float32) @ R.T * L + org
        light = self.light_rgb[::-1]
        center = curve.mean(0)
        for p0, p1 in zip(curve[:-1], curve[1:]):
            mid = (p0 + p1) / 2
            tng = p1 - p0
            n_out = np.array([tng[1], -tng[0]], np.float32)
            if np.dot(n_out, mid - center) < 0:
                n_out = -n_out
            n_out /= np.linalg.norm(n_out) + 1e-6
            to_l = lens - mid
            dist = np.linalg.norm(to_l) + 1e-6
            facing = max(0.0, float(np.dot(n_out, to_l / dist)))
            b = 0.10 + 0.9 * st['on'] * facing * min(1.0, 0.9 * L / dist) + 0.25 * facing * (1 - st['on'])
            cv2.line(img, tuple(p0.astype(int)), tuple(p1.astype(int)), tuple(int(v * min(b, 1.0)) for v in light),
                     2, cv2.LINE_AA)

    def _fill(self, img, poly, bgr, up, fade=None, shade=0.22):
        """多边形填色（不透明，遮住后面的线），沿 up 方向上亮下暗；fade=(起点, 方向, 长度) 时向后渐隐成黑。"""
        H, W = img.shape[:2]
        x0, y0 = np.floor(poly.min(0)).astype(int) - 2
        x1, y1 = np.ceil(poly.max(0)).astype(int) + 2
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
        if x0 >= x1 or y0 >= y1:
            return
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.fillPoly(m, [(poly - [x0, y0]).astype(np.int32)], 255, cv2.LINE_AA)
        m = m.astype(np.float32)[..., None] / 255
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        c = poly.mean(0)
        size = float(np.ptp(poly, 0).max()) / 2 + 1e-3
        t = ((xx - c[0]) * up[0] + (yy - c[1]) * up[1]) / size
        col = np.ones_like(m) * np.asarray(bgr, np.float32) * (1 + shade * np.clip(t, -1, 1))[..., None]
        if fade is not None:
            o, d, ln = fade
            u = ((xx - o[0]) * d[0] + (yy - o[1]) * d[1]) / ln
            col *= (np.clip(1 - u, 0, 1) ** 1.4)[..., None]
        roi = img[y0:y1, x0:x1].astype(np.float32)
        img[y0:y1, x0:x1] = np.clip(roi * (1 - m) + col * m, 0, 255).astype(np.uint8)

    def _fade_line(self, img, a0, a1, bgr, th, steps=20):
        for i in range(steps):
            u0, u1 = i / steps, (i + 1) / steps
            c = tuple(int(v * (1 - u0) ** 1.6) for v in bgr)
            cv2.line(img, tuple((a0 + (a1 - a0) * u0).astype(int)), tuple((a0 + (a1 - a0) * u1).astype(int)),
                     c, th, cv2.LINE_AA)

    def _hand_outline(self, img, curve, deco, P, away, nrm, L):
        col = self.line_bgr
        wb, wt = curve[0], curve[-1]
        length, widen = 1.5 * L, 0.04 * L
        side_t = 1.0 if np.dot(wt - wb, nrm) > 0 else -1.0
        far_t = wt + away * length + nrm * side_t * widen
        far_b = wb + away * length - nrm * side_t * widen
        cv2.fillPoly(img, [np.vstack([curve, far_t[None], far_b[None]]).astype(np.int32)], (0, 0, 0), cv2.LINE_AA)
        cv2.polylines(img, [curve.astype(np.int32)], False, col, 3, cv2.LINE_AA)
        self._fade_line(img, wt, far_t, col, 2)
        self._fade_line(img, wb, far_b, col, 2)
        dim = tuple(int(v * 0.55) for v in col)
        for seg in deco:
            cv2.polylines(img, [P(_catmull(seg, 6)).astype(np.int32)], False, dim, 2, cv2.LINE_AA)

    def _table(self, ty, L):
        """长方形黑色桌子（略俯视的透视）：桌面梯形、前沿厚度、四条腿；手电和光圈落在桌面中部的 ty 处。
        桌面填很暗的灰（后暗前亮一点），与纯黑背景区分；线条为暗淡的线色。静态，只画一次。"""
        if getattr(self, '_table_img', None) is None:
            hw, hh = self.hw, self.hh
            img = np.zeros((hh, hw, 3), np.uint8)
            c = self.cfg
            yb, yf = ty - c.get('table_back', 0.11) * hh, ty + c.get('table_front', 0.08) * hh
            bx0, bx1 = hw * 0.25, hw * 0.75           # 后沿（远，短）
            fx0, fx1 = hw * 0.13, hw * 0.87           # 前沿（近，长）
            th = 0.028 * hh                           # 桌面厚度
            floor = min(hh - 4, yf + th + 0.21 * hh)  # 前腿落地
            top = np.array([(bx0, yb), (bx1, yb), (fx1, yf), (fx0, yf)], np.float32)
            # 桌面：后暗前亮的极暗灰
            m = np.zeros((hh, hw), np.uint8)
            cv2.fillPoly(m, [top.astype(np.int32)], 255, cv2.LINE_AA)
            g = np.clip((np.arange(hh, dtype=np.float32) - yb) / max(yf - yb, 1), 0, 1)[:, None]
            shade = (9 + 9 * g) * (m.astype(np.float32) / 255)
            img[:] = np.clip(shade[..., None] * np.array([1.0, 1.0, 1.1], np.float32), 0, 255).astype(np.uint8)
            edge = tuple(int(v * 0.50) for v in self.line_bgr)
            dim = tuple(int(v * 0.30) for v in self.line_bgr)
            # 前沿厚度（正面一条窄带）
            face = np.array([(fx0, yf), (fx1, yf), (fx1, yf + th), (fx0, yf + th)], np.float32)
            cv2.fillPoly(img, [face.astype(np.int32)], (6, 6, 7), cv2.LINE_AA)
            # 腿：前腿在前沿两端内侧，后腿在后沿两端下方、较短（更远）
            lw = 0.012 * hw
            legs = [((fx0 + 0.02 * hw, yf + th), floor, edge), ((fx1 - 0.02 * hw - lw, yf + th), floor, edge),
                    ((bx0 + 0.01 * hw, yf + th), floor - 0.08 * hh, dim), ((bx1 - 0.01 * hw - lw * 0.8, yf + th), floor - 0.08 * hh, dim)]
            for (lx, ly), lb, col in legs[2:] + legs[:2]:   # 先画后腿
                w = lw if col is edge else lw * 0.8
                cv2.rectangle(img, (int(lx), int(ly)), (int(lx + w), int(lb)), (5, 5, 6), -1)
                cv2.line(img, (int(lx), int(ly)), (int(lx), int(lb)), col, 1, cv2.LINE_AA)
                cv2.line(img, (int(lx + w), int(ly)), (int(lx + w), int(lb)), col, 1, cv2.LINE_AA)
            cv2.polylines(img, [face.astype(np.int32)], True, dim, 1, cv2.LINE_AA)
            cv2.polylines(img, [top.astype(np.int32)], True, edge, 1, cv2.LINE_AA)
            # 前沿上缘稍亮，像一点反光
            cv2.line(img, (int(fx0), int(yf)), (int(fx1), int(yf)), tuple(int(v * 0.65) for v in self.line_bgr), 1, cv2.LINE_AA)
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
        k = on * _seg(T, 4.1, 5.0) * 0.8
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
    for i in range(390):
        c = np.zeros((H, W, 3), np.uint8)
        t0 = time.perf_counter()
        p.draw(c, i / 30)
        ms.append(1000 * (time.perf_counter() - t0))
        vw.write(cv2.resize(c, (W // 2, H // 2), interpolation=cv2.INTER_AREA))
        if i in (15, 45, 63, 90, 112, 150, 200, 270, 300 - 1):
            cv2.imwrite(str(out / f'prompt_{i / 30:04.1f}s.png'), c)
    vw.release()
    print(f'saved previews to {out}; draw {np.median(ms):.1f} ms median, {max(ms):.1f} ms max')
