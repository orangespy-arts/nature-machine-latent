"""监听 reveal-sound patch 回报的状态（OSC 127.0.0.1:7401），不看屏幕也能确认 Max 端在工作。

  python instrument/max/reveal/sound_status.py [--seconds 20]

patch 每 250 ms 发：/snd/level（输出峰值，左声道）、/snd/a（平滑后的机械比例）、
/snd/env（出现包络 0–1）、/snd/cpu（Max DSP CPU %）、/snd/sr（采样率，若 adstatus 输出）。
每秒打印一行最新值；结束时打印各项的最小／最大值。需要 python-osc。
"""
import argparse
import threading
import time
from collections import defaultdict

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=7401)
    ap.add_argument('--seconds', type=float, default=20)
    args = ap.parse_args()

    last, lo, hi, n = {}, {}, {}, defaultdict(int)
    lock = threading.Lock()

    def on_any(address, *vals):
        if not vals or not isinstance(vals[0], (int, float)):
            return
        v = float(vals[0])
        with lock:
            last[address] = v
            lo[address] = min(lo.get(address, v), v)
            hi[address] = max(hi.get(address, v), v)
            n[address] += 1

    d = Dispatcher()
    d.set_default_handler(on_any)
    server = ThreadingOSCUDPServer(('127.0.0.1', args.port), d)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f'listening on 127.0.0.1:{args.port} for {args.seconds:.0f} s', flush=True)
    t0 = time.time()
    while time.time() - t0 < args.seconds:
        time.sleep(1)
        with lock:
            row = '  '.join(f'{k.split("/")[-1]}={v:.3f}' for k, v in sorted(last.items()))
        print(f'{time.time() - t0:5.0f}s  {row or "(nothing received)"}', flush=True)
    server.shutdown()
    print('summary:')
    for k in sorted(n):
        print(f'  {k}: n={n[k]}  min={lo[k]:.4f}  max={hi[k]:.4f}')


if __name__ == '__main__':
    main()
