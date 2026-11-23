"""定位揭示：黑屏上只在标记所在处实时生成画面（v0）。

  python visual/reveal.py                    鼠标代替标记（按住左键 = 标记存在），全屏
  python visual/reveal.py --windowed         窗口模式
  python visual/reveal.py --input demo       标记自动沿曲线移动、出现／消失（无摄像头时演示）
  python visual/reveal.py --input camera     摄像头颜色追踪（先 --calibrate 校准）
  python visual/reveal.py --input light      摄像头看黑幕布，手电光斑的位置代替标记（同 camera，camera.mode 改为 light）
  python visual/reveal.py --list_cameras     列出可用摄像头
  python visual/reveal.py --calibrate        摄像头画面中点投影区域四角，存 visual/local/calibration.json

按键：q/Esc 退出，f 全屏切换，d 调试信息，g 显示区域位置，m 对照窗（左摄像头原画面／右输出），
c 摄像头调试窗（camera 模式）

流程：位置 → 各区域反距离权重 → 混合提示词 embedding 与底图 → StreamDiffusion img2img（独立线程）
→ 黑色画布上以标记为中心贴柔边圆形画面。移动超过 reseed_distance 或标记重新出现时换种子，
所以每次移动画面不同。OSC 发送 <prefix>/present、/pos、/mix（机械比例 a）、/region、/seed，供 Mac 上 Max 使用。
"""
import argparse
import json
import os
import random
import threading
import time
from pathlib import Path

# 限制 CPU 线程池（须在导入 numpy／cv2／torch 之前设）。2026-11-21 在 5070 上实测：不限制时生成画面占约 20／24 核，
# 与 Max nn~（CPU 推理）抢 CPU，按住时声音卡顿。VISUAL_CPU_THREADS 可改，默认 4。
CPU_THREADS = os.environ.get('VISUAL_CPU_THREADS', '4')
for _k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(_k, CPU_THREADS)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

cv2.setNumThreads(int(CPU_THREADS))

HERE = Path(__file__).resolve().parent


def list_monitors():
    """Windows：返回 [(名称, x, y, 宽, 高, 是否主屏)]，坐标为物理像素（进程设为 DPI 感知）。其他系统返回空表。"""
    if os.name != 'nt':
        return []
    import ctypes
    from ctypes import wintypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # 每显示器 DPI 感知：坐标与全屏尺寸按物理像素
    except (OSError, AttributeError):
        pass

    class MONITORINFOEXW(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT), ('rcWork', wintypes.RECT),
                    ('dwFlags', wintypes.DWORD), ('szDevice', wintypes.WCHAR * 32)]
    mons = []

    def cb(h, hdc, rect, data):
        mi = MONITORINFOEXW()
        mi.cbSize = ctypes.sizeof(mi)
        ctypes.windll.user32.GetMonitorInfoW(h, ctypes.byref(mi))
        r = mi.rcMonitor
        mons.append((mi.szDevice, r.left, r.top, r.right - r.left, r.bottom - r.top, bool(mi.dwFlags & 1)))
        return True
    proto = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    ctypes.windll.user32.EnumDisplayMonitors(None, None, proto(cb), 0)
    return sorted(mons, key=lambda m: (not m[5], m[1], m[2]))  # 主屏排第一


def pick_monitor(mons, display):
    """display：auto（有外接显示器就用第一个外接的，否则主屏）或编号（0 = 主屏，1、2… = 其他）。"""
    if not mons:
        return None
    if display == 'auto':
        return mons[1] if len(mons) > 1 else mons[0]
    i = int(display)
    return mons[i] if 0 <= i < len(mons) else mons[0]


class Worker(threading.Thread):
    def __init__(self, layout):
        super().__init__(daemon=True)
        from sdgen import Generator
        self.gen = Generator(layout, HERE)
        self.lock = threading.Lock()
        self.target, self.active, self.want_seed = None, False, None
        self.image, self.fps, self.ms = None, 0.0, 0.0
        self.running = True

    def set_target(self, weights, active, seed=None):
        with self.lock:
            self.target, self.active = weights, active
            if seed is not None:
                self.want_seed = seed

    def run(self):
        n, t0 = 0, time.time()
        while self.running:
            with self.lock:
                w, active, seed = self.target, self.active, self.want_seed
                self.want_seed = None
            if seed is not None:
                self.gen.reseed(seed)
            if not active or w is None:
                time.sleep(0.01)
                continue
            t = time.time()
            img = self.gen.generate(w)
            self.ms = 1000 * (time.time() - t)
            self.image = img
            n += 1
            if time.time() - t0 >= 1:
                self.fps, n, t0 = n / (time.time() - t0), 0, time.time()


def feather_mask(size, feather):
    yy, xx = np.mgrid[0:size, 0:size]
    r = np.hypot(xx - (size - 1) / 2, yy - (size - 1) / 2) / (size / 2)
    m = np.clip((1 - r) / max(feather, 1e-3), 0, 1)
    m = m * m * (3 - 2 * m)
    return m[..., None].astype(np.float32)


def paste(canvas, patch, mask, cx, cy, alpha):
    H, W = canvas.shape[:2]
    s = patch.shape[0]
    x0, y0 = int(round(cx - s / 2)), int(round(cy - s / 2))
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + s, W), min(y0 + s, H)
    if xa >= xb or ya >= yb:
        return
    p = patch[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    m = mask[ya - y0:yb - y0, xa - x0:xb - x0] * alpha
    roi = canvas[ya:yb, xa:xb].astype(np.float32)
    canvas[ya:yb, xa:xb] = (roi * (1 - m) + p * m).astype(np.uint8)


def monitor_view(frame, hit, canvas, present, x, y, h=450, pick_hint=False):
    """对照画面：左 摄像头原画面（绿圈 = 识别到的标记），右 输出画面（黄十字 = 映射后的位置）。"""
    ch, cw = canvas.shape[:2]
    right = cv2.resize(canvas, (int(cw * h / ch), h))
    if frame is not None:
        left = cv2.resize(frame, (int(frame.shape[1] * h / frame.shape[0]), h))
        if hit:
            s = h / frame.shape[0]
            cv2.circle(left, (int(hit[0] * s), int(hit[1] * s)), max(int(hit[2] * s), 4), (0, 255, 0), 2)
        label = 'camera: ' + (('FOUND' + (f' (id {hit[3]})' if len(hit) > 3 and hit[3] is not None else '')) if hit else 'no marker')
    else:
        left = np.zeros((h, int(h * 16 / 9), 3), np.uint8)
        label = 'camera: no frame (not connected / mouse / demo input)'
    cv2.putText(left, label, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0) if hit else (0, 200, 255), 2)
    if frame is not None and pick_hint:
        cv2.putText(left, 'click the marker here to set its colour', (12, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (255, 255, 255), 1)
    px, py = int(x * right.shape[1]), int(y * right.shape[0])
    if present:
        cv2.drawMarker(right, (px, py), (0, 255, 255), cv2.MARKER_CROSS, 24, 2)
    cv2.putText(right, 'output', (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    gap = np.full((h, 8, 3), 60, np.uint8)
    return np.concatenate([left, gap, right], 1)


def camera_test(cfg, seconds, snapshot_dir=None, marker_path=None):
    import tracker
    if marker_path:
        tracker.load_marker(cfg, marker_path)
    last = {'frame': None}
    win = 'camera test: left = camera, right = colour mask | q quit'
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, 1280, 360)
    t0, n, hits, last_snap, radii = time.time(), 0, 0, 0.0, []
    hint = '(click marker to set colour)' if marker_path else ''
    cap, fails, events = None, 0, []

    def on_click(event, mx, my, flags, param):
        f = last['frame']
        if event == cv2.EVENT_LBUTTONDOWN and f is not None and mx < f.shape[1] and marker_path:
            tracker.save_marker(cfg, tracker.hsv_range_from_patch(f, mx, my), marker_path)
    cv2.setMouseCallback(win, on_click)
    if snapshot_dir:
        Path(snapshot_dir).mkdir(parents=True, exist_ok=True)
    while time.time() - t0 < seconds:
        el = time.time() - t0
        if cap is None:
            try:
                cap = tracker.open_camera(cfg)
                events.append(f'{el:6.1f}s camera opened')
                print(events[-1], flush=True)
                fails = 0
            except SystemExit:
                wait = np.zeros((360, 1280, 3), np.uint8)
                cv2.putText(wait, f'waiting for camera ... plug it in   {seconds - el:.0f} s left', (30, 190),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 200, 255), 2)
                cv2.imshow(win, wait)
                if cv2.waitKey(1500) & 0xFF in (27, ord('q')):
                    break
                continue
        ok, f = cap.read()
        if not ok:
            fails += 1
            if fails > 30:
                events.append(f'{el:6.1f}s camera lost (read failed)')
                print(events[-1], flush=True)
                cap.release()
                cap = None
            else:
                time.sleep(0.03)
            continue
        fails = 0
        raw = f.copy()
        hit, mask = tracker.detect(f, cfg)
        n += 1
        if hit:
            hits += 1
            radii.append(hit[2])
            cv2.circle(f, (int(hit[0]), int(hit[1])), int(hit[2]), (0, 255, 0), 3)
        msg = f'{"FOUND" if hit else "no marker"}   {seconds - el:.0f} s left   {hint}'
        cv2.putText(f, msg, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0) if hit else (0, 255, 255), 3)
        view = np.concatenate([f, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)], 1)
        cv2.imshow(win, view)
        last['frame'] = raw
        if snapshot_dir and el - last_snap >= 2:
            cv2.imwrite(str(Path(snapshot_dir) / f'cam_{el:05.1f}s_{"hit" if hit else "miss"}.jpg'),
                        cv2.resize(view, (1280, 360)))
            last_snap = el
        if cv2.waitKey(1) & 0xFF in (27, ord('q')):
            break
    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()
    el = time.time() - t0
    print('events:', *events, sep='\n  ')
    print(f'camera test: {n} frames in {el:.1f} s, marker found in {hits} '
          f'({100 * hits / max(n, 1):.0f}%), median radius {np.median(radii) if radii else 0:.0f} px')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--layout', default=str(HERE / 'layout.json'))
    ap.add_argument('--input', choices=['mouse', 'demo', 'camera', 'light'], default='mouse')
    ap.add_argument('--calibration', default=str(HERE / 'local' / 'calibration.json'))
    ap.add_argument('--marker', default=str(HERE / 'local' / 'marker.json'), help='点选保存的标记颜色')
    ap.add_argument('--windowed', action='store_true')
    ap.add_argument('--display', default='auto',
                    help='全屏放在哪个显示器：auto（默认：有外接显示器就用外接的）、0 = 主屏、1 = 第二个……；--list_displays 查看')
    ap.add_argument('--list_displays', action='store_true', help='列出显示器')
    ap.add_argument('--no_osc', action='store_true')
    ap.add_argument('--no_prompt', action='store_true', help='不显示黑屏时的提示动画（layout.json prompt）')
    ap.add_argument('--debug', action='store_true', help='启动时即显示调试信息（左上角绿字）')
    ap.add_argument('--guide', action='store_true', help='启动时即显示区域位置标签（灰点＋名称）')
    ap.add_argument('--monitor', action='store_true', help='另开对照窗：左 摄像头原画面，右 输出画面（m 键切换）')
    ap.add_argument('--camera_index', type=int, default=None, help='覆盖 layout.json 的 camera.index')
    ap.add_argument('--calibrate', action='store_true')
    ap.add_argument('--list_cameras', action='store_true')
    ap.add_argument('--camera_test', action='store_true', help='只看摄像头与颜色识别（左：画面，右：掩膜），q 退出')
    ap.add_argument('--max_seconds', type=float, default=0, help='运行指定秒数后自动退出（测试用）')
    ap.add_argument('--snapshot_dir', default=None, help='每秒存一张画布截图（测试用）')
    args = ap.parse_args()

    layout = json.loads(Path(args.layout).read_text(encoding='utf-8'))
    import tracker
    if args.input == 'light':  # 手电光斑：其余与 camera 完全相同（同一画面、声音、OSC）
        layout['camera']['mode'] = 'light'
    if args.camera_index is not None:
        layout['camera']['index'] = args.camera_index
    if args.list_displays:
        for i, m in enumerate(list_monitors()):
            print(f'{i}: {m[0]}  {m[3]}x{m[4]} at ({m[1]},{m[2]}){"  primary" if m[5] else ""}')
        return
    if args.list_cameras:
        cams = tracker.list_cameras()
        print('cameras:', cams if cams else 'none found')
        return
    if args.calibrate:
        tracker.calibrate(layout['camera'], args.calibration)
        return
    if args.camera_test:
        camera_test(layout['camera'], args.max_seconds or 90, args.snapshot_dir,
                    args.marker if layout['camera'].get('mode') == 'color' else None)
        return

    W, H = layout['canvas']['width'], layout['canvas']['height']
    g, disp = layout['generation'], layout['display']
    regions = layout['regions']
    aspect = W / H

    osc = None
    if layout['osc']['enabled'] and not args.no_osc:
        from pythonosc.udp_client import SimpleUDPClient
        osc = SimpleUDPClient(layout['osc']['host'], layout['osc']['port'])
    pre = layout['osc'].get('prefix', '/reveal')

    print('loading StreamDiffusion ...', flush=True)
    worker = Worker(layout)
    worker.start()

    win = 'reveal'
    mons = list_monitors()
    mon = pick_monitor(mons, args.display)
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    fullscreen = not args.windowed
    if mon is not None:
        # 先把窗口移到目标显示器，再设全屏：OpenCV 的全屏铺满窗口当前所在的显示器（无标题栏）
        cv2.moveWindow(win, mon[1] + 40, mon[2] + 40)
        print(f'display: {mon[0]} {mon[3]}x{mon[4]}' + (f' (of {len(mons)})' if len(mons) > 1 else ''), flush=True)
    cv2.setWindowProperty(win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL)
    if not fullscreen:
        cv2.resizeWindow(win, W // 2, H // 2)
    hide_cursor = fullscreen and args.input != 'mouse' and os.name == 'nt'
    if hide_cursor:
        import ctypes
        while ctypes.windll.user32.ShowCursor(False) >= 0:
            pass
    if args.input == 'mouse':
        src = tracker.MouseInput(win, W, H)
    elif args.input == 'demo':
        src = tracker.DemoInput()
    else:
        if layout['camera'].get('mode') == 'color':
            tracker.load_marker(layout['camera'], args.marker)
        src = tracker.CameraTracker(layout['camera'], args.calibration)
    t_start, last_snap, stats = time.time(), 0.0, []
    if args.snapshot_dir:
        Path(args.snapshot_dir).mkdir(parents=True, exist_ok=True)

    mask = feather_mask(disp['patch_px'], disp['feather'])
    idle = None
    if layout.get('prompt', {}).get('enabled', False) and not args.no_prompt:
        from prompt import IdlePrompt
        idle = IdlePrompt(layout['prompt'], W, H)
    alpha, last_seen, was_present = 0.0, 0.0, False
    anchor, seed_t, seed = None, time.time(), 0
    show_debug, show_guide, show_cam = args.debug, args.guide, False
    show_monitor, last_mon = args.monitor, 0.0
    pick_hint = layout['camera'].get('mode', 'color') == 'color'
    if show_monitor:
        cv2.namedWindow('monitor', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('monitor', 1600, 470)
        if mons and mon is not None and mon != mons[0]:
            cv2.moveWindow('monitor', mons[0][1] + 20, mons[0][2] + 60)  # 对照窗留在主屏（笔记本）上

        def on_monitor_click(event, mx, my, flags, param):
            f = getattr(src, 'frame', None)
            if event != cv2.EVENT_LBUTTONDOWN or f is None:
                return
            s = 450 / f.shape[0]
            if mx < f.shape[1] * s and pick_hint:  # 颜色模式下点在左边摄像头画面上
                tracker.save_marker(src.cfg, tracker.hsv_range_from_patch(f, mx / s, my / s), args.marker)
        cv2.setMouseCallback('monitor', on_monitor_click)
    n, t0, dfps = 0, time.time(), 0.0
    last_osc, last_region = 0.0, None
    seed_on = layout['osc'].get('seed_on', 'move')
    sound_seed, was_visible = None, False
    t_prev = time.time()

    while True:
        now = time.time()
        dt, t_prev = now - t_prev, now
        (x, y), present = src.read()
        if present:
            last_seen = now
        visible = present or (now - last_seen) < disp['lost_after_s']

        w = worker.gen.weights(x, y)
        new_seed = None
        if present and (not was_present or anchor is None
                        or np.hypot((x - anchor[0]) * aspect, y - anchor[1]) > g['reseed_distance']
                        or (g['reseed_interval_s'] and now - seed_t > g['reseed_interval_s'])):
            seed = random.randrange(2 ** 31)
            new_seed, anchor, seed_t = seed, (x, y), now
        worker.set_target(w, visible, new_seed)
        # 声音跳位（/seed）：seed_on = "appear" 时只在标记出现（visible 由 0 变 1）时发，
        # 按住移动时声音连续播放；"move" 为旧行为，画面每换种子就发（Max 端限每秒一次）。
        if new_seed is not None and (seed_on == 'move' or (visible and not was_visible)):
            sound_seed = new_seed
        was_present, was_visible = present, visible

        rate = dt / max(disp['fade_in_s'] if visible else disp['fade_out_s'], 1e-3)
        alpha = min(1.0, alpha + rate) if visible else max(0.0, alpha - rate)

        canvas = np.zeros((H, W, 3), np.uint8)
        if show_guide:
            for r in regions:
                p = (int(r['x'] * W), int(r['y'] * H))
                cv2.circle(canvas, p, 6, (80, 80, 80), -1)
                cv2.putText(canvas, r['name'], (p[0] + 10, p[1] + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 80, 80), 1)
        if idle is not None:  # 黑屏提示：一段时间没检测到光斑就淡入，检测到就淡出
            idle.update(now - last_seen, dt)
            idle.draw(canvas, now - t_start)
        if worker.image is not None and alpha > 0:
            patch = cv2.resize(worker.image[..., ::-1], (disp['patch_px'], disp['patch_px']))
            paste(canvas, patch, mask, x * W, y * H, alpha)

        # 声音的机械比例单独用更大的反距离指数，靠近区域中心时 a 更快趋近该区域的值（画面混合仍用 blend_power）
        mix_power = layout['osc'].get('mix_power', g['blend_power'])
        w_mix = w if mix_power == g['blend_power'] else worker.gen.weights(x, y, mix_power)
        mix_a = float(np.dot(w_mix, [r['a'] for r in regions]))
        region = regions[int(np.argmax(w))]['name']
        if osc and now - last_osc > 1 / 30:
            osc.send_message(f'{pre}/present', int(visible))
            osc.send_message(f'{pre}/pos', [float(x), float(y)])
            osc.send_message(f'{pre}/mix', mix_a)
            if region != last_region:
                osc.send_message(f'{pre}/region', region)
                last_region = region
            if sound_seed is not None:
                osc.send_message(f'{pre}/seed', int(sound_seed))
                sound_seed = None
            last_osc = now

        n += 1
        if now - t0 >= 1:
            dfps, n, t0 = n / (now - t0), 0, now
            stats.append((dfps, worker.fps, worker.ms))
        if args.max_seconds and now - t_start > args.max_seconds:
            break
        if show_debug:
            cam = f' cam {src.fps:.0f} fps' if hasattr(src, 'fps') else ''
            lines = [f'display {dfps:.0f} fps  gen {worker.fps:.1f} fps ({worker.ms:.0f} ms){cam}',
                     f'pos {x:.3f},{y:.3f}  present {int(present)}  region {region}  mix a {mix_a:.2f}  seed {seed}',
                     f't_index {g["t_index"]}  input {args.input}  osc {"on" if osc else "off"}']
            for i, s in enumerate(lines):
                cv2.putText(canvas, s, (20, 40 + 32 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow(win, canvas)

        mon = None
        if show_monitor and now - last_mon >= 1 / 30:
            mon = monitor_view(getattr(src, 'frame', None), getattr(src, 'hit', None), canvas, present, x, y, pick_hint=pick_hint)
            cv2.imshow('monitor', mon)
            last_mon = now
        if args.snapshot_dir and now - last_snap >= 1 and now - t_start > 3:
            shot = mon if mon is not None else monitor_view(getattr(src, 'frame', None), getattr(src, 'hit', None),
                                                           canvas, present, x, y, pick_hint=pick_hint)
            cv2.imwrite(str(Path(args.snapshot_dir) / f'snap_{now - t_start:05.1f}s.jpg'), shot)
            last_snap = now

        if show_cam and args.input in ('camera', 'light') and src.frame is not None:
            f = src.frame.copy()
            if src.hit:
                cv2.circle(f, (int(src.hit[0]), int(src.hit[1])), int(src.hit[2]), (0, 255, 0), 2)
            cv2.imshow('camera', np.concatenate([f, cv2.cvtColor(src.mask, cv2.COLOR_GRAY2BGR)], 1))

        k = cv2.waitKey(1) & 0xFF
        if k in (27, ord('q')):
            break
        if k == ord('f'):
            fullscreen = not fullscreen
            cv2.setWindowProperty(win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL)
        if k == ord('d'):
            show_debug = not show_debug
        if k == ord('g'):
            show_guide = not show_guide
        if k == ord('m'):
            show_monitor = not show_monitor
            if not show_monitor:
                cv2.destroyWindow('monitor')
        if k == ord('c') and args.input in ('camera', 'light'):
            show_cam = not show_cam
            if not show_cam:
                cv2.destroyWindow('camera')
        if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
            break

    worker.running = False
    if hide_cursor:
        import ctypes
        while ctypes.windll.user32.ShowCursor(True) < 0:
            pass
    src.close()
    cv2.destroyAllWindows()
    if len(stats) > 3:
        a = np.array(stats[3:])
        busy = a[a[:, 1] > 0]
        print(f'display fps median {np.median(a[:, 0]):.1f}; '
              f'gen fps median {np.median(busy[:, 1]) if len(busy) else 0:.1f} '
              f'({np.median(busy[:, 2]) if len(busy) else 0:.0f} ms/frame, while marker visible)')


if __name__ == '__main__':
    main()
