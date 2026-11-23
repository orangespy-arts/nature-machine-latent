"""定位输入：鼠标（无摄像头时代替标记）、演示路径，或摄像头追踪。

都输出画布归一化坐标 (x, y) 与是否存在。摄像头两种模式（layout.json camera.mode）：
- aruco：黑白 ArUco 方块标记（OpenCV 4.11 cv2.aruco），只看明暗对比，不受光线颜色影响，且能分辨标记 ID；
- color：HSV 阈值 → 最大连通块 → 最小外接圆圆心（受光线／白平衡影响大，见 README 实测）；
- light：黑幕布上的手电光斑。亮度（HSV 的 V，彩色手电也算）→ 相对背景的自适应阈值 → 最大亮块 → 质心。
都
用 4 点校准（投影区域四角：左上、右上、右下、左下）做透视变换，把摄像头坐标映射到画布。
"""
import json
import threading
import time
from pathlib import Path

import cv2
import numpy as np


class MouseInput:
    """按住左键 = 标记存在；坐标取鼠标在显示窗口中的位置。"""

    def __init__(self, window, canvas_w, canvas_h):
        self.cw, self.ch = canvas_w, canvas_h
        self.pos, self.down = (0.5, 0.5), False
        cv2.setMouseCallback(window, self._cb)

    def _cb(self, event, x, y, flags, param):
        self.pos = (x / self.cw, y / self.ch)
        if event == cv2.EVENT_LBUTTONDOWN:
            self.down = True
        elif event == cv2.EVENT_LBUTTONUP:
            self.down = False

    def read(self):
        return self.pos, self.down

    def close(self):
        pass


class DemoInput:
    """无人操作时的演示：标记沿李萨如曲线移动，出现 on_s 秒、消失 off_s 秒。"""

    def __init__(self, on_s=4.0, off_s=1.5):
        self.t0, self.on_s, self.off_s = time.time(), on_s, off_s

    def read(self):
        t = time.time() - self.t0
        x = 0.45 + 0.38 * np.sin(0.23 * t * 2 * np.pi)
        y = 0.45 + 0.36 * np.sin(0.31 * t * 2 * np.pi + 0.7)
        return (float(x), float(y)), (t % (self.on_s + self.off_s)) < self.on_s

    def close(self):
        pass


MARKER_KEYS = ('hsv_low', 'hsv_high', 'hsv_low2', 'hsv_high2')


def hsv_range_from_patch(frame, cx, cy, r=10, h_tol=7, s_margin=35, v_margin=50):
    """在 (cx, cy) 周围取样，按中位色相 ± h_tol、饱和度／亮度下限给出识别范围（处理色相 0/180 环绕）。"""
    hgt, wid = frame.shape[:2]
    x0, x1 = max(int(cx) - r, 0), min(int(cx) + r + 1, wid)
    y0, y1 = max(int(cy) - r, 0), min(int(cy) + r + 1, hgt)
    hsv = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(int)
    h = hsv[:, 0]
    # 以样本中位数为中心展开色相，避免 0/180 环绕
    ref = int(np.median(h))
    d = (h - ref + 90) % 180 - 90
    hc = (ref + int(np.median(d))) % 180
    s_lo = int(max(40, np.percentile(hsv[:, 1], 10) - s_margin))
    v_lo = int(max(40, np.percentile(hsv[:, 2], 10) - v_margin))
    lo, hi = hc - h_tol, hc + h_tol
    out = {'sampled_hsv': [int(hc), int(np.median(hsv[:, 1])), int(np.median(hsv[:, 2]))]}
    if lo < 0:
        out.update(hsv_low=[0, s_lo, v_lo], hsv_high=[hi, 255, 255], hsv_low2=[180 + lo, s_lo, v_lo], hsv_high2=[180, 255, 255])
    elif hi > 180:
        out.update(hsv_low=[lo, s_lo, v_lo], hsv_high=[180, 255, 255], hsv_low2=[0, s_lo, v_lo], hsv_high2=[hi - 180, 255, 255])
    else:  # 第二段设为空范围
        out.update(hsv_low=[lo, s_lo, v_lo], hsv_high=[hi, 255, 255], hsv_low2=[0, 255, 255], hsv_high2=[0, 255, 255])
    return out


def load_marker(cfg, path):
    """若本机有点选保存的标记颜色（visual/local/marker.json），覆盖 layout 中的 HSV 范围。"""
    p = Path(path)
    if p.exists():
        m = json.loads(p.read_text(encoding='utf-8'))
        cfg.update({k: m[k] for k in MARKER_KEYS if k in m})
        print(f'marker colour from {p.name}: sampled HSV {m.get("sampled_hsv")}', flush=True)
    return cfg


def save_marker(cfg, sample, path, min_saturation=60):
    if sample['sampled_hsv'][1] < min_saturation:
        # 2026-11-17 实测：点到灰色纸杯（S≈31），识别范围变成“几乎任何灰暗像素”，背景小斑点被当成标记
        print(f'colour too grey to track (sampled HSV {sample["sampled_hsv"]}, S < {min_saturation}); '
              'not saved — use a strongly coloured marker', flush=True)
        return False
    cfg.update({k: sample[k] for k in MARKER_KEYS})
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(sample, indent=2), encoding='utf-8')
    print(f'marker colour saved: sampled HSV {sample["sampled_hsv"]} -> {path}', flush=True)


def load_calibration(path):
    p = Path(path)
    if not p.exists():
        return None
    pts = np.array(json.loads(p.read_text(encoding='utf-8'))['camera_points'], np.float32)
    dst = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], np.float32)
    return cv2.getPerspectiveTransform(pts, dst)


_ARUCO = {}


def _aruco_detector(acfg):
    params = acfg.get('params', {})
    key = (acfg.get('dictionary', 'DICT_4X4_50'), tuple(sorted(params.items())))
    if key not in _ARUCO:
        d = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, key[0]))
        p = cv2.aruco.DetectorParameters()
        p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        for k, v in params.items():  # 例：polygonalApproxAccuracyRate（见 README 实测）
            setattr(p, k, v)
        _ARUCO[key] = cv2.aruco.ArucoDetector(d, p)
    return _ARUCO[key]


def detect_aruco(frame, cfg):
    """ArUco 黑白方块标记：只看明暗对比，不依赖颜色。返回最大（最近）的允许 ID 标记：(cx, cy, r, id)。

    mask 为调试图：检测用的灰度图上叠加检测到的标记轮廓。"""
    acfg = cfg.get('aruco', {})
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = _aruco_detector(acfg).detectMarkers(gray)
    dbg = gray.copy()
    if ids is None:
        return None, dbg
    allowed = acfg.get('ids')
    best = None
    for c, i in zip(corners, ids.flatten()):
        if allowed and int(i) not in allowed:
            continue
        pts = c.reshape(4, 2)
        side = float(np.mean(np.linalg.norm(pts - np.roll(pts, 1, 0), axis=1)))
        cv2.polylines(dbg, [pts.astype(np.int32)], True, 255, 3)
        cv2.putText(dbg, f'id {int(i)}', tuple(pts[0].astype(int)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 255, 2)
        if side * side < cfg['min_area_px']:
            continue
        if best is None or side > best[2] * 2 / 1.414:
            cx, cy = pts.mean(0)
            best = (float(cx), float(cy), side * 1.414 / 2, int(i))
    return best, dbg


def detect_light(frame, cfg):
    """黑幕布上的手电光斑：返回最大亮块 (cx, cy, r, None)，r 为等面积圆半径。

    光线强弱未定，所以阈值随画面自适应：thr = max(min_v, 背景 + min_contrast, 背景 + (峰值 − 背景) × rel)。
    背景取模糊后亮度的中位数（黑幕布占画面大部分时即幕布亮度）。峰值与背景差不到 min_contrast 视为没有光斑。
    mask 为调试图：阈值后的二值图。"""
    lc = cfg.get('light', {})
    v = frame.max(axis=2)  # = HSV 的 V；彩色手电（偏黄／偏蓝）也按亮度算
    hgt, wid = v.shape
    k = max(3, int(round(wid * lc.get('blur', 0.012))) | 1)
    v = cv2.GaussianBlur(v, (k, k), 0)
    bg = float(np.median(v[::4, ::4]))
    peak = float(v.max())
    if peak - bg < lc.get('min_contrast', 40):
        return None, np.zeros_like(v)
    thr = max(lc.get('min_v', 60), bg + lc.get('min_contrast', 40), bg + (peak - bg) * lc.get('rel', 0.5))
    mask = (v >= thr).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, mask
    min_area = lc.get('min_area_frac', 0.002) * hgt * wid
    best = None
    for c in sorted(cnts, key=cv2.contourArea, reverse=True):
        area = cv2.contourArea(c)
        if area < min_area:
            break
        # 光斑是实心亮块；空心轮廓、细线（如屏幕图标、物体边缘反光）亮像素占比低。2026-11-23 摄像头被系统禁用时
        # 画面是灰底白线锁形图标，无此检查会被当成光斑。
        x, y, w, h = cv2.boundingRect(c)
        fill = cv2.countNonZero(mask[y:y + h, x:x + w]) / max(area, 1)
        if fill >= lc.get('min_fill', 0.6):
            best = c
            break
    if best is None:
        return None, mask
    c, area = best, cv2.contourArea(best)
    m = cv2.moments(c)
    return (m['m10'] / m['m00'], m['m01'] / m['m00'], float(np.sqrt(area / np.pi)), None), mask


def detect(frame, cfg):
    mode = cfg.get('mode', 'color')
    if mode == 'aruco':
        return detect_aruco(frame, cfg)
    if mode == 'light':
        return detect_light(frame, cfg)
    return detect_color(frame, cfg)


def detect_color(frame, cfg):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(cfg['hsv_low']), np.array(cfg['hsv_high']))
    if 'hsv_low2' in cfg:
        mask |= cv2.inRange(hsv, np.array(cfg['hsv_low2']), np.array(cfg['hsv_high2']))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, mask
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < cfg['min_area_px']:
        return None, mask
    (cx, cy), r = cv2.minEnclosingCircle(c)
    return (cx, cy, r, None), mask


def open_camera(cfg):
    """DirectShow 打开；设 MJPG（本机 CAMERA - UAC 在 1280×720 下 MJPG 约 27 fps，默认格式约 11 fps）。"""
    cap = cv2.VideoCapture(cfg['index'], cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise SystemExit(f"打不开摄像头 index={cfg['index']}；用 --list_cameras 查看，或重插 USB")
    if cfg.get('fourcc'):
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*cfg['fourcc']))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg['width'])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg['height'])
    # 手动曝光（可选）：自动曝光在黑幕布上会把增益拉高，光斑出现时又整体压暗，阈值会跟着跳。
    # DirectShow：AUTO_EXPOSURE 0.25 = 手动；exposure 为 log2 秒（如 -6 ≈ 1/64 s），具体可用范围取决于摄像头驱动。
    exp = cfg.get('light', {}).get('exposure') if cfg.get('mode') == 'light' else cfg.get('exposure')
    if exp is not None:
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, float(exp))
    return cap


class CameraTracker:
    """后台线程读摄像头并追踪；read() 返回最近一次结果。"""

    def __init__(self, cfg, calibration_path):
        self.cfg = cfg
        try:
            self.cap = open_camera(cfg)
        except SystemExit:
            print('camera not available yet, waiting ...', flush=True)
            self.cap = None
        self.H = load_calibration(calibration_path)
        self.pos, self.present, self.t_seen = (0.5, 0.5), False, 0.0
        self.frame, self.mask, self.hit = None, None, None
        self.fps = 0.0
        self.running = True
        self.th = threading.Thread(target=self._loop, daemon=True)
        self.th.start()

    def _to_canvas(self, cx, cy, w, h):
        if self.H is not None:
            p = cv2.perspectiveTransform(np.array([[[cx, cy]]], np.float32), self.H)[0, 0]
            return float(p[0]), float(p[1])
        return cx / w, cy / h

    def _loop(self):
        n, t0, fails = 0, time.time(), 0
        self.reconnects = 0
        while self.running:
            ok, frame = self.cap.read() if self.cap is not None else (False, None)
            if not ok:
                # 摄像头掉线（本机 USB 摄像头 2026-11-17 多次掉线）：连续失败约 1 秒后释放并每 2 秒重开
                self.present = False
                fails += 1
                if fails > 30:
                    if self.cap is not None:
                        print(f'camera lost at {time.strftime("%H:%M:%S")}, reconnecting ...', flush=True)
                        self.cap.release()
                        self.cap = None
                    time.sleep(2)
                    try:
                        self.cap = open_camera(self.cfg)
                        self.reconnects += 1
                        fails = 0
                        print('camera reconnected', flush=True)
                    except SystemExit:
                        pass
                else:
                    time.sleep(0.03)
                continue
            fails = 0
            if self.cfg.get('mirror'):
                frame = cv2.flip(frame, 1)
            hit, mask = detect(frame, self.cfg)
            if hit:
                x, y = self._to_canvas(hit[0], hit[1], frame.shape[1], frame.shape[0])
                a = self.cfg.get('smoothing', 0.0)
                if self.present:
                    x, y = a * self.pos[0] + (1 - a) * x, a * self.pos[1] + (1 - a) * y
                self.pos, self.present, self.t_seen = (x, y), True, time.time()
            else:
                self.present = False
            self.frame, self.mask, self.hit = frame, mask, hit
            n += 1
            if time.time() - t0 >= 1:
                self.fps, n, t0 = n / (time.time() - t0), 0, time.time()

    def read(self):
        return self.pos, self.present

    def close(self):
        self.running = False
        self.th.join(timeout=1)
        if self.cap is not None:
            self.cap.release()


def list_cameras(max_index=6):
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ok, f = cap.read()
            found.append((i, f.shape[1] if ok else None, f.shape[0] if ok else None))
        cap.release()
    return found


def calibrate(cfg, out_path):
    """摄像头画面中依次点击投影区域四角：左上、右上、右下、左下。按 r 重来，Enter 保存，Esc 取消。"""
    cap = open_camera(cfg)
    pts = []
    win = 'calibrate: click TL, TR, BR, BL | r reset | Enter save | Esc cancel'
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, lambda e, x, y, f, p: pts.append((x, y)) if e == cv2.EVENT_LBUTTONDOWN and len(pts) < 4 else None)
    saved = False
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        hit, _ = detect(frame, cfg)
        if hit:
            cv2.circle(frame, (int(hit[0]), int(hit[1])), int(hit[2]), (0, 255, 0), 2)
        for i, p in enumerate(pts):
            cv2.circle(frame, p, 6, (0, 255, 255), -1)
            cv2.putText(frame, 'TL TR BR BL'.split()[i], (p[0] + 8, p[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        if len(pts) == 4:
            cv2.polylines(frame, [np.array(pts, np.int32)], True, (0, 255, 255), 1)
        cv2.imshow(win, frame)
        k = cv2.waitKey(1) & 0xFF
        if k == 27:
            break
        if k == ord('r'):
            pts.clear()
        if k == 13 and len(pts) == 4:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_text(json.dumps({'camera_points': pts, 'camera_index': cfg['index'],
                                                  'camera_size': [frame.shape[1], frame.shape[0]]}, indent=2),
                                      encoding='utf-8')
            saved = True
            break
    cap.release()
    cv2.destroyWindow(win)
    print('saved ' + str(out_path) if saved else 'calibration cancelled')
