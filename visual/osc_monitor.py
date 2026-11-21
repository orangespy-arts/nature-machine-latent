"""监听并统计画面工具发出的 OSC（不需要 Max），用于确认消息内容与频率。

  python visual/osc_monitor.py [--port 7400] [--seconds 20]

每秒打印一行：各地址的消息数与最新值。结束时汇总。
"""
import argparse
import threading
import time
from collections import Counter

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=7400)
    ap.add_argument('--seconds', type=float, default=20)
    args = ap.parse_args()

    counts, total, last = Counter(), Counter(), {}
    lock = threading.Lock()

    def on_any(address, *vals):
        with lock:
            counts[address] += 1
            total[address] += 1
            last[address] = vals

    d = Dispatcher()
    d.set_default_handler(on_any)
    server = ThreadingOSCUDPServer((args.host, args.port), d)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f'listening on {args.host}:{args.port} for {args.seconds:.0f} s', flush=True)
    t0 = time.time()
    while time.time() - t0 < args.seconds:
        time.sleep(1)
        with lock:
            line = '  '.join(f'{a.split("/")[-1]}={counts[a]}/s {last[a]}' for a in sorted(counts))
            counts.clear()
        print(f'{time.time() - t0:5.1f}s  {line or "(nothing)"}', flush=True)
    server.shutdown()
    print('total:', dict(total))


if __name__ == '__main__':
    main()
