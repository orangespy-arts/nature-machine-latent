"""生成 reveal-sound.maxpat：接收画面工具（visual/reveal.py）的 OSC，驱动 RAVE 潜在插值的声音。

  python instrument/max/reveal/make_reveal_sound_patch.py               # Mac 版：reveal-sound.maxpat（手动 open 两个源）
  python instrument/max/reveal/make_reveal_sound_patch.py --target 4070 # 4070 版：reveal-sound-4070.maxpat
  python instrument/max/reveal/make_reveal_sound_patch.py --target 5070 # 5070 拷贝包版：源用文件名（与 patch 同文件夹）
                                                                        # （自动载入两个源、自动开音频）
两版都把状态（CPU、输出电平、a、包络、采样率）以 OSC 发到 127.0.0.1:7401，
供 instrument/max/reveal/sound_status.py 在不看屏幕的情况下检查。

信号链（Mac，Max 9 + nn~ v1.6.0，最终模型 exp003-…-final-step1500000）：
  sfplay~ 自然源（循环） → nn~ encode ─┐
  sfplay~ 机械源（循环） → nn~ encode ─┤ 每维 z = z_自然 + a·(z_机械 − z_自然) → nn~ decode
                                       └ a 来自 OSC /reveal/mix（50 ms 平滑）
  → 出现包络（/reveal/present：1 → 400 ms 淡入，0 → 800 ms 淡出，与画面一致）
  → 等功率声像（/reveal/pos 的 x：左 cos(πx/2)、右 sin(πx/2)）→ 总音量 → ezdac~
  /reveal/seed（每次移动换种子）→ speedlim 1000 → 两个源各跳到随机位置（seek，0–8000 ms）
依据：nn~ 写法与 encode/decode 端口同 instrument/max/exp-003 测试 patch；sfplay~ seek、cos~、udpreceive 见 README。
用生成脚本而不是手改 JSON，便于复现与修改。
"""
import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--target', choices=['mac', '4070', '5070'], default='mac')
TARGET = ap.parse_args().target

MODEL = 'exp003-forest-s105ck01-final-step1500000_streaming'
PORT = 7400
PREFIX = '/reveal'
STATUS_PORT = 7401
# 4070 上的默认源（与插值试听文件配对一致）；Max 在 Windows 上接受 E:/… 形式的绝对路径
LISTEN_4070 = 'E:/nature-machine-latent-data/listening/exp-003/final-step1500000/level-matched'
AUTOLOAD = {
    '4070': (f'{LISTEN_4070}/nature/night_forest_a__orig.wav',
             f'{LISTEN_4070}/machine/torque_wrench_turning_constant__orig.wav'),
    # 5070 拷贝包：WAV 与 patch 放在同一文件夹，只写文件名（Max 先在已打开 patch 所在文件夹里找文件）
    '5070': ('night_forest_a__orig.wav', 'torque_wrench_turning_constant__orig.wav'),
}

boxes, lines = [], []
_n = [0]

SIG = 'signal'
# (numinlets, outlettypes) for objects we use
SPEC = {
    'udpreceive': (1, ['']),
    'route': (2, [''] * 6),
    'sel': (1, ['bang', 'bang', '']),
    'line~': (2, [SIG, 'bang']),
    'unpack': (1, ['float', 'float']),
    'prepend': (2, ['']),
    't': (1, ['bang', 'bang']),
    'random': (2, ['int']),
    'sfplay~': (2, [SIG, 'bang']),
    'loadmess': (1, ['']),
    'adstatus': (2, ['', 'int']),
    'metro': (2, ['bang']),
    'sig~': (1, [SIG]),
    'cos~': (1, [SIG]),
    'snapshot~': (2, ['float']),
    'speedlim': (2, ['']),
    'loadbang': (1, ['bang']),
    'delay': (2, ['bang']),
    'udpsend': (1, []),
    'peakamp~': (2, ['float']),
    'pack': (2, ['']),
}


def box(maxclass, rect, text=None, inlets=None, outtypes=None, **extra):
    _n[0] += 1
    bid = f'obj-{_n[0]}'
    b = {'id': bid, 'maxclass': maxclass, 'patching_rect': rect}
    if text is not None:
        b['text'] = text
    if maxclass == 'newobj':
        name = text.split()[0]
        if name in SPEC:
            inl, outs = SPEC[name]
        elif name in ('*~', '+~', '-~', '!-~'):
            inl, outs = 2, [SIG]
        elif name == 'nn~':
            method = text.split()[2]
            inl, outs = (1, [SIG] * 4) if method == 'encode' else (4, [SIG])
        else:
            raise KeyError(name)
        b['numinlets'], b['numoutlets'], b['outlettype'] = inl, len(outs), outs
    elif maxclass == 'message':
        b.update(numinlets=2, numoutlets=1, outlettype=[''])
    elif maxclass in ('flonum', 'number'):
        b.update(numinlets=1, numoutlets=2, outlettype=['', 'bang'], parameter_enable=0)
    elif maxclass == 'toggle':
        b.update(numinlets=1, numoutlets=1, outlettype=['int'], parameter_enable=0)
    elif maxclass == 'ezdac~':
        b.update(numinlets=2, numoutlets=0)
    elif maxclass == 'comment':
        b.update(numinlets=1, numoutlets=0)
    if inlets is not None:
        b['numinlets'] = inlets
    if outtypes is not None:
        b['numoutlets'], b['outlettype'] = len(outtypes), outtypes
    b.update(extra)
    boxes.append({'box': b})
    return bid


def wire(src, dst, so=0, di=0):
    lines.append({'patchline': {'source': [src, so], 'destination': [dst, di]}})


def comment(rect, text):
    return box('comment', rect, text)


# ---- 标题
comment([20, 10, 760, 22], 'reveal-sound v1 · 画面工具 OSC → RAVE 潜在插值（exp-003 最终模型）')
comment([20, 34, 900, 50],
        f'OSC 端口 {PORT}，地址前缀 {PREFIX}。a（机械比例）= 画面各区域 a 值的反距离加权；present 控制淡入淡出；x 控制左右；\n'
        'seed 变化时两个源跳到随机位置。映射是人为设计的，模型不理解“自然／机械”。先各点一次 open 载入两个源（建议 heldout __orig.wav）。')

# ---- OSC 接收
udp = box('newobj', [20, 100, 110, 22], f'udpreceive {PORT}')
rt = box('newobj', [20, 135, 620, 22],
         f'route {PREFIX}/present {PREFIX}/pos {PREFIX}/mix {PREFIX}/region {PREFIX}/seed')
wire(udp, rt)
comment([650, 135, 300, 22], '← 若收不到，先看 Max Console 与防火墙')

# present
comment([20, 170, 130, 20], 'present（可点下方消息手动测试）')
pres_num = box('number', [20, 190, 50, 22])
wire(rt, pres_num, 0)
sel = box('newobj', [20, 225, 60, 22], 'sel 1 0')
wire(pres_num, sel)
m_in = box('message', [20, 260, 50, 22], '1 400')
m_out = box('message', [80, 260, 50, 22], '0 800')
wire(sel, m_in, 0)
wire(sel, m_out, 1)
env = box('newobj', [20, 295, 45, 22], 'line~')
wire(m_in, env)
wire(m_out, env)

# pos -> x
comment([160, 170, 80, 20], 'pos x  y')
unp = box('newobj', [160, 190, 75, 22], 'unpack f f')
wire(rt, unp, 1)
x_num = box('flonum', [160, 225, 55, 22])
y_num = box('flonum', [220, 225, 55, 22])
wire(unp, x_num, 0)
wire(unp, y_num, 1)
x_msg = box('message', [160, 260, 55, 22], '$1 50')
wire(x_num, x_msg)
x_sig = box('newobj', [160, 295, 45, 22], 'line~')
wire(x_msg, x_sig)
gl_scale = box('newobj', [160, 330, 60, 22], '*~ 0.25')
gl = box('newobj', [160, 365, 45, 22], 'cos~')
wire(x_sig, gl_scale)
wire(gl_scale, gl)
inv = box('newobj', [230, 330, 50, 22], '!-~ 1.')
gr_scale = box('newobj', [230, 365, 60, 22], '*~ 0.25')
gr = box('newobj', [230, 400, 45, 22], 'cos~')
wire(x_sig, inv)
wire(inv, gr_scale)
wire(gr_scale, gr)
comment([290, 365, 200, 34], '等功率：L = cos(πx/2)\nR = sin(πx/2) = cos(π(1−x)/2)')
x_init = box('newobj', [290, 225, 85, 22], 'loadmess 0.5')
wire(x_init, x_num)

# mix a
comment([520, 170, 160, 20], 'mix a（0 自然 → 1 机械）')
a_num = box('flonum', [520, 190, 60, 22])
wire(rt, a_num, 2)
comment([590, 190, 220, 20], '← 无 OSC 时可手动拖动测试')
a_msg = box('message', [520, 225, 55, 22], '$1 50')
wire(a_num, a_msg)
a_sig = box('newobj', [520, 260, 45, 22], 'line~')
wire(a_msg, a_sig)

# region (display)
comment([830, 170, 80, 20], 'region')
reg_pre = box('newobj', [830, 190, 75, 22], 'prepend set')
wire(rt, reg_pre, 3)
reg_msg = box('message', [830, 225, 140, 22], '-')
wire(reg_pre, reg_msg)

# seed -> random seek
comment([1000, 170, 80, 20], 'seed')
seed_num = box('number', [1000, 190, 110, 22])
wire(rt, seed_num, 4)
lim = box('newobj', [1000, 225, 85, 22], 'speedlim 1000')
wire(seed_num, lim)
comment([1090, 225, 260, 34], '最多每秒跳一次：画面 demo 中\nseed 可达每秒 11 次（2026-11-17 实测）')
tbb = box('newobj', [1000, 262, 40, 22], 't b b')
wire(lim, tbb)
rnd_n = box('newobj', [1000, 297, 85, 22], 'random 8000')
rnd_m = box('newobj', [1100, 297, 85, 22], 'random 8000')
wire(tbb, rnd_n, 1)
wire(tbb, rnd_m, 0)
seek_n = box('newobj', [1000, 332, 85, 22], 'prepend seek')
seek_m = box('newobj', [1100, 332, 85, 22], 'prepend seek')
wire(rnd_n, seek_n)
wire(rnd_m, seek_m)

# ---- 两个源
for k, (label, x0, seek) in enumerate([('自然源', 20, seek_n), ('机械源', 360, seek_m)]):
    comment([x0, 450, 200, 20], f'{label}：open → 自动循环播放')
    op = box('message', [x0, 475, 42, 22], 'open')
    play = box('message', [x0 + 50, 475, 30, 22], '1')
    stop = box('message', [x0 + 85, 475, 30, 22], '0')
    lp = box('newobj', [x0 + 120, 475, 70, 22], 'loadmess loop 1')
    sf = box('newobj', [x0, 515, 77, 22], 'sfplay~ 1')
    for m in (op, play, stop, lp, seek):
        wire(m, sf)
    enc = box('newobj', [x0, 555, 320, 22], f'nn~ {MODEL} encode 2048')
    wire(sf, enc)
    if k == 0:
        enc_n, sf_n, play_n = enc, sf, play
    else:
        enc_m, sf_m, play_m = enc, sf, play

# ---- 每维插值 z = zn + a (zm - zn)
comment([20, 600, 600, 20], '每维：z = z自然 + a · (z机械 − z自然)')
dec = box('newobj', [20, 760, 560, 22], f'nn~ {MODEL} decode 2048')
for i in range(4):
    x0 = 20 + i * 150
    comment([x0, 625, 40, 20], f'z{i + 1}')
    diff = box('newobj', [x0, 650, 40, 22], '-~')
    mul = box('newobj', [x0, 685, 40, 22], '*~')
    add = box('newobj', [x0, 720, 40, 22], '+~')
    wire(enc_m, diff, i, 0)
    wire(enc_n, diff, i, 1)
    wire(diff, mul, 0, 0)
    wire(a_sig, mul, 0, 1)
    wire(mul, add, 0, 0)
    wire(enc_n, add, i, 1)
    wire(add, dec, 0, i)

# ---- 包络、声像、音量、输出
g_env = box('newobj', [20, 800, 40, 22], '*~')
wire(dec, g_env, 0, 0)
wire(env, g_env, 0, 1)
pl = box('newobj', [20, 840, 40, 22], '*~')
pr = box('newobj', [80, 840, 40, 22], '*~')
wire(g_env, pl, 0, 0)
wire(g_env, pr, 0, 0)
wire(gl, pl, 0, 1)
wire(gr, pr, 0, 1)
vol = box('flonum', [200, 840, 55, 22])
comment([260, 840, 140, 20], '总音量（初始 0.5）')
vol_init = box('newobj', [200, 805, 75, 22], 'loadmess 0.5')
wire(vol_init, vol)
vl = box('newobj', [20, 880, 40, 22], '*~')
vr = box('newobj', [80, 880, 40, 22], '*~')
wire(pl, vl, 0, 0)
wire(pr, vr, 0, 0)
wire(vol, vl, 0, 1)
wire(vol, vr, 0, 1)
dac = box('ezdac~', [20, 920, 45, 45])
wire(vl, dac, 0, 0)
wire(vr, dac, 0, 1)

# ---- CPU
cpu_l = box('newobj', [700, 450, 84, 22], 'loadmess 1')
met = box('newobj', [700, 480, 77, 22], 'metro 250')
ads = box('newobj', [700, 510, 98, 22], 'adstatus cpu')
cpu = box('flonum', [700, 540, 60, 22])
comment([765, 540, 220, 20], 'Max DSP CPU %（每 250 ms）')
wire(cpu_l, met)
wire(met, ads)
wire(ads, cpu)

# ---- 状态回报（OSC → 127.0.0.1:STATUS_PORT），用于不看屏幕的检查
comment([700, 590, 420, 20], f'状态回报 → udpsend 127.0.0.1 {STATUS_PORT}（sound_status.py 读取）')
us = box('newobj', [700, 760, 150, 22], f'udpsend 127.0.0.1 {STATUS_PORT}')
pk = box('newobj', [700, 615, 85, 22], 'peakamp~ 250')
wire(vl, pk)
pk_p = box('newobj', [700, 645, 110, 22], 'prepend /snd/level')
wire(pk, pk_p)
wire(pk_p, us)
sa = box('newobj', [820, 615, 90, 22], 'snapshot~ 250')
wire(a_sig, sa)
sa_p = box('newobj', [820, 645, 90, 22], 'prepend /snd/a')
wire(sa, sa_p)
wire(sa_p, us)
se = box('newobj', [920, 615, 90, 22], 'snapshot~ 250')
wire(env, se)
se_p = box('newobj', [920, 645, 100, 22], 'prepend /snd/env')
wire(se, se_p)
wire(se_p, us)
cpu_p = box('newobj', [700, 690, 100, 22], 'prepend /snd/cpu')
wire(ads, cpu_p)
wire(cpu_p, us)
sr = box('newobj', [820, 690, 85, 22], 'adstatus sr')
wire(met, sr)
sr_p = box('newobj', [820, 720, 90, 22], 'prepend /snd/sr')
wire(sr, sr_p, 1)
wire(sr_p, us)

# ---- 4070／5070 版：自动载入两个源并开音频
if TARGET in AUTOLOAD:
    nat, mech = AUTOLOAD[TARGET]
    comment([360, 400, 330, 34], '本机自动：载入后 1.5 s 打开两个源并播放，2 s 后开音频\n（换源：点上面的 open 选别的文件）')
    lb = box('newobj', [700, 400, 60, 22], 'loadbang')
    d1 = box('newobj', [700, 425, 80, 22], 'delay 1500')
    wire(lb, d1)
    o_n = box('message', [20, 420, 330, 22], f'open {nat}, 1')
    o_m = box('message', [360, 440, 330, 22], f'open {mech}, 1')
    wire(d1, o_n)
    wire(d1, o_m)
    wire(o_n, sf_n)
    wire(o_m, sf_m)
    d2 = box('newobj', [790, 425, 80, 22], 'delay 2000')
    wire(lb, d2)
    dsp = box('message', [880, 425, 90, 22], '; dsp start')
    wire(d2, dsp)

patch = {'patcher': {
    'fileversion': 1,
    'appversion': {'major': 9, 'minor': 0, 'revision': 9, 'architecture': 'x64', 'modernui': 1},
    'classnamespace': 'box',
    'rect': [60, 60, 1250, 1000],
    'boxes': boxes,
    'lines': lines,
}}
out = Path(__file__).with_name('reveal-sound.maxpat' if TARGET == 'mac' else f'reveal-sound-{TARGET}.maxpat')
out.write_text(json.dumps(patch, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'wrote {out} ({len(boxes)} boxes, {len(lines)} lines)')
