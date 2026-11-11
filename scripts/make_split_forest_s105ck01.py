"""为 forest-s105ck01-v001 生成按录音组留出的训练／留出划分清单（2026-11-11，4070）。

分组规则只根据文件名推断，未经试听：
- 机械（S105）：同一台机器（品牌／型号）或同一动作的变体（快/慢、长/短等）为一组。
- 自然（forest-v001）：按原文件名的系列编号分组；同标题且编号连续的视为同一次录音。
整组进入 train 或 heldout，任何组不跨两边。留出组由 HELD_MACHINE / HELD_NATURE 指定，
选择目标是覆盖各类声音，并使两边训练块数（按 5.944 秒切块）大致相等。

用法（RAVE 环境的 Python，含 soundfile）：
    python scripts/make_split_forest_s105ck01.py <数据集目录，含 machine/ nature/> <输出 CSV>
不会修改或复制音频；输出 CSV 已存在时拒绝覆盖。
"""
import csv, hashlib, json, pathlib, re, sys, collections
import soundfile as sf

root = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2])
repo = pathlib.Path(__file__).resolve().parent.parent
if out.exists():
    sys.exit(f'输出已存在，拒绝覆盖：{out}')
scan = []
for p in sorted(root.rglob('*.wav')):
    i = sf.info(str(p))
    scan.append(dict(rel=p.relative_to(root).as_posix(), cat=p.parent.name, dur=i.duration,
                     sha=hashlib.sha256(p.read_bytes()).hexdigest()))
s105 = {pathlib.Path(r['relative_path']).name: r['asset_id'] for r in csv.DictReader(open(repo / 'datasets/manifests/s105-v001.csv', encoding='utf-8-sig'))}
fr = json.load(open(repo / 'datasets/manifests/forest-v001-renames.json', encoding='utf-8'))
fmap = {pathlib.Path(r['relative_path']).name: (r['asset_id'], pathlib.Path(r['original_relative_path']).stem) for r in fr}

BRANDS = ['the_oliver', 'adler', 'remington_noiseless', 'remington', 'valentine', 'mercedes_five', 'aeg_mignon', 'kanzler', 'ceta',
          'underwood', 'lambert', 'standard', 'calligraph', 'triumphator', 'brunsviga', 'hamann', 'felix', 'resulta', 'rogli', 'veb',
          'hd_seven', 'mech_accountant', 'badenia', 'victor_champion', 'mercedes', 'headman', 'chicago', 'safeguard', 'hermes_stollwerck',
          'bergmann_stollwerck', 'reicherts_hexenhaus', 'bajazzo', 'mum_hen', 'mum_stork']
FAMILIES = ['typewriter', 'calculating_machine', 'checkwriter', 'slot_machine']
VARIANT = r'(_(a|b|fast|slow|long|short|single|multiple|sequence|handling|light|resonant|squeaky|to|open|close|rolling|snap|big|small|medium|turns?|turning|constant|without|with|pedaling|loading|up|down))+$'

def machine_group(stem):
    fam = next((f for f in FAMILIES if f in stem), None)
    brand = next((b for b in BRANDS if re.search(r'(^|_)' + b + r'($|_)', stem)), None)
    if fam and brand:
        if brand == 'remington_noiseless': brand = 'remington_noiseless'
        return f'{fam}:{brand}'
    if 'checkwriter' in stem and 'unknown' in stem: return 'checkwriter:unknown'
    if stem.startswith('bicycle_wheels'): return 'bicycle_wheels'
    if stem.startswith('bicycle_gear_shift'): return 'bicycle_gear_shift'
    if stem.startswith('metal_on_spokes') or stem == 'bicycle_spokes': return 'bicycle_spokes'
    if stem.startswith('knife_grinder'): return 'knife_grinder'
    if 'air_gun' in stem: return 'toy_air_gun' if 'toy' in stem else 'air_gun'
    if stem.startswith('ratchet_wood') or stem.startswith('ratchet_medium_wooden'): return 'ratchet_wooden'
    if stem.startswith('metal_ratchet_small'): return 'metal_ratchet_small'
    if stem.startswith('ratchet_lever_loose'): return 'ratchet_lever_loose'
    if stem.startswith('ratchet_lever_snap'): return 'ratchet_lever_snap'
    if stem.startswith('ratchet_hoist_big'): return 'ratchet_hoist_big'
    if stem.startswith('ratchet_big'): return 'ratchet_big'
    if stem.startswith('nut_runner_small'): return 'nut_runner_small'
    if stem.startswith('nut_runner'): return 'nut_runner'
    if stem.startswith('dial_chunky_metal'): return 'dial_chunky_metal'
    if stem.startswith('dial_metal'): return 'dial_metal'
    if stem.startswith('pagination_stamp'): return 'pagination_stamp'
    if stem.startswith('metal_scissors_scrape'): return 'metal_scissors_scrape'
    if stem.startswith('stapler'): return 'stapler'
    return re.sub(VARIANT, '', stem)

def machine_family(stem):
    for k, f in [('typewriter', 'typewriter'), ('calculating_machine', 'calculating_machine'), ('checkwriter', 'checkwriter'),
                 ('slot_machine', 'slot_machine'), ('ratchet', 'ratchet'), ('bicycle', 'bicycle'), ('spokes', 'bicycle'),
                 ('bike', 'bicycle'), ('grinder', 'grinding'), ('nut_runner', 'tool_turning'), ('wrench', 'tool_turning'),
                 ('screwdriver', 'tool_turning'), ('vise', 'tool_turning'), ('dial', 'dial')]:
        if k in stem: return f
    return 'other'

def nature_group(name):
    aid, orig = fmap[name]
    m = re.search(r'_([A-Z0-9]+)\.(\d+)$', orig)
    title = orig.split('_')[0]
    if not m: return 'forest:pack-nocode', title
    series, num = m.group(1), int(m.group(2))
    rules = [('BW', 1757, 1761, 'BW.1757-1761'), ('BW', 60985, 60988, 'BW.60985-60988'), ('S08AM', 26, 32, 'S08AM.26-32'),
             ('S08AM', 33, 34, 'S08AM.33-34'), ('S08AM', 35, 39, 'S08AM.35-39'), ('SFXB', 69, 70, 'SFXB.69-70'), ('SFXB', 75, 76, 'SFXB.75-76')]
    for s, a, b, g in rules:
        if series == s and a <= num <= b: return 'forest:' + g, title
    return f'forest:{series}.{num}', title

HELD_MACHINE = {'typewriter:underwood', 'calculating_machine:hd_seven', 'ratchet_lever_snap', 'torque_wrench', 'slot_machine:mum_hen', 'rolling_chain'}
HELD_NATURE = {'forest:BW.1486', 'forest:SFXB.72', 'forest:SFXB.73', 'forest:SFXB.74', 'forest:pack-nocode', 'forest:SEU02.18'}

rows = []
for r in scan:
    p = pathlib.Path(r['rel']); stem = p.stem
    if r['cat'] == 'machine':
        g = 's105:' + machine_group(stem); fam = machine_family(stem); parent = s105[p.name]
        held = machine_group(stem) in HELD_MACHINE
    else:
        g0, fam = nature_group(p.name); g = g0; parent = fmap[p.name][0]
        held = g0 in HELD_NATURE
    rows.append(dict(relative_path=r['rel'], parent_asset_id=parent, category=r['cat'], family_hint=fam, recording_group=g,
                     proposed_split='heldout' if held else 'train', duration_seconds=f"{r['dur']:.3f}", usable_chunks=int(r['dur'] // 5.944),
                     sha256=r['sha']))
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

