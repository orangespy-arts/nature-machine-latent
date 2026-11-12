"""Estimate model latency from a two-channel recording made in Max.

The exp-003 test patches (instrument/max/exp-003/) record the original signal on
the left channel and the nn~ output on the right. RAVE does not reproduce the
waveform sample by sample, so this compares amplitude envelopes (1 ms frames)
and reports the lag at which the right channel best matches the left.

What this measures: delay inside Max's signal graph (model + nn~ buffer).
It does NOT include the audio interface's input/output latency; read those
from Max's Audio Status and add them for a microphone-to-speaker figure.

Standard library only (no numpy), so it runs on a fresh Mac Python:

    python3 scripts/measure_max_latency.py rec.wav [--max-lag-ms 1000]
"""
import argparse
import struct
import sys
from array import array


def read_wav(path):
    """Return (sample_rate, left, right) as float lists. Supports PCM 16/24/32 and float32."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        sys.exit(f"{path}: not a WAV file (save the Max recording as .wav)")
    pos, fmt, raw = 12, None, None
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            tag, ch, sr = struct.unpack("<HHI", body[:8])
            bits = struct.unpack("<H", body[14:16])[0]
            if tag == 0xFFFE:  # WAVE_FORMAT_EXTENSIBLE: real tag in the sub-format GUID
                tag = struct.unpack("<H", body[24:26])[0]
            fmt = (tag, ch, sr, bits)
        elif cid == b"data":
            raw = body
        pos += 8 + size + (size & 1)
    if fmt is None or raw is None:
        sys.exit(f"{path}: missing fmt or data chunk")
    tag, ch, sr, bits = fmt
    if ch != 2:
        sys.exit(f"{path}: expected 2 channels, got {ch}")
    if tag == 3 and bits == 32:
        s = array("f")
        s.frombytes(raw[: len(raw) // 4 * 4])
        vals = list(s)
    elif tag == 1 and bits in (16, 24, 32):
        w = bits // 8
        full = float(1 << (bits - 1))
        n = len(raw) // w
        if bits == 24:
            vals = [int.from_bytes(raw[i * 3:i * 3 + 3], "little", signed=True) / full
                    for i in range(n)]
        else:
            s = array("h" if bits == 16 else "i")
            s.frombytes(raw[: n * w])
            vals = [v / full for v in s]
    else:
        sys.exit(f"{path}: unsupported format tag {tag}, {bits} bit")
    return sr, vals[0::2], vals[1::2]


def envelope(x, hop):
    return [sum(abs(v) for v in x[i:i + hop]) / hop for i in range(0, len(x) - hop + 1, hop)]


def normalise(e):
    m = sum(e) / len(e)
    d = [v - m for v in e]
    norm = sum(v * v for v in d) ** 0.5 or 1.0
    return [v / norm for v in d]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("wav")
    ap.add_argument("--max-lag-ms", type=int, default=1000)
    a = ap.parse_args()

    sr, left, right = read_wav(a.wav)
    hop = round(sr / 1000)  # 1 ms frames
    el, er = envelope(left, hop), envelope(right, hop)
    if len(el) < a.max_lag_ms * 2:
        sys.exit("recording too short: record at least twice --max-lag-ms of sound")
    span = len(el) - a.max_lag_ms
    ref = normalise(el[:span])
    best = (-2.0, 0)
    scores = []
    for lag in range(a.max_lag_ms + 1):
        seg = normalise(er[lag:lag + span])
        c = sum(p * q for p, q in zip(ref, seg))
        scores.append(c)
        best = max(best, (c, lag))
    c, lag = best
    runner = max((s, l) for l, s in enumerate(scores) if abs(l - lag) > 20)
    print(f"file            {a.wav}")
    print(f"sample rate     {sr} Hz, {len(left) / sr:.1f} s")
    print(f"best lag        {lag} ms  (envelope correlation {c:.3f}, 1 ms resolution)")
    print(f"next-best peak  {runner[1]} ms  (correlation {runner[0]:.3f}, >20 ms away)")
    if c < 0.5 or runner[0] > 0.9 * c:
        print("WARNING: weak or ambiguous match; use a file with clear, sparse attacks "
              "(e.g. typewriter) and record 10 s or more.")


if __name__ == "__main__":
    main()
