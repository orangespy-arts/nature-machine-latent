# 落地装置原型 v3：许多小虫沿钢架逐渐耦合成机械（尺寸为占位值，待实测）
# 概念：底部散虫栖在花盆苔藓上 → 中段四条虫链逐渐咬合 → 顶部汇成一个机械体。
# 四种虫对应第一阶段模型的四个潜在维度（2026-11-12 单次试听，偏移约 +40，属外推）；
# 物种→维度的对应在 Max 里设定，重新训练后需要重新指定。
# 运行：blender -b --factory-startup --python proto_v3.py -- <输出目录>
import bpy, math, random, sys, os
from mathutils import Vector, Quaternion

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.dirname(__file__)
os.makedirs(OUT, exist_ok=True)
random.seed(11)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
coll = scn.collection

# ---------------- 材质 ----------------
def mat(name, rgb, metal=0.0, rough=0.5, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try: setattr(m, attr, val)
            except Exception: pass
    m.diffuse_color = (*rgb, alpha)
    return m

M = {
    "steel": mat("steel", (0.45, 0.45, 0.47), 0.9, 0.35),
    "dark": mat("dark", (0.12, 0.10, 0.09), 0.6, 0.4),
    "brass": mat("brass", (0.85, 0.62, 0.28), 1.0, 0.25),
    "copper": mat("copper", (0.80, 0.42, 0.25), 1.0, 0.3),
    "pla": mat("pla", (0.92, 0.87, 0.76), 0.0, 0.45),
    "wing": mat("wing", (0.97, 0.88, 0.70), 0.0, 0.2, alpha=0.40),
    "vein": mat("vein", (0.75, 0.42, 0.15), 0.6, 0.35),
    "bug_green": mat("bug_green", (0.26, 0.34, 0.20), 0.3, 0.45),
    "line": mat("line", (0.85, 0.88, 0.92), 0.0, 0.1, alpha=0.6),
    "cable": mat("cable", (0.80, 0.18, 0.12), 0.0, 0.5),
    "sensor": mat("sensor", (0.15, 0.45, 0.75), 0.0, 0.4),
    "floor": mat("floor", (0.30, 0.30, 0.29), 0.0, 0.8),
    "person": mat("person", (0.75, 0.75, 0.78), 0.0, 0.7),
    "speaker": mat("speaker", (0.10, 0.10, 0.10), 0.2, 0.5),
    "label": mat("label", (0.05, 0.05, 0.05), 0.0, 0.8),
    "terracotta": mat("terracotta", (0.62, 0.32, 0.20), 0.0, 0.8),
    "soil": mat("soil", (0.16, 0.11, 0.07), 0.0, 0.95),
    "moss": mat("moss", (0.20, 0.36, 0.10), 0.0, 0.9),
    "leaf": mat("leaf", (0.25, 0.46, 0.17), 0.0, 0.6),
    "petal": mat("petal", (0.90, 0.55, 0.62), 0.0, 0.5),
    "cricket": mat("cricket", (0.52, 0.34, 0.20), 0.2, 0.45),
}

GROUPS = {}
def put(o, m, group):
    o.data.materials.clear()
    o.data.materials.append(M[m])
    o.color = M[m].diffuse_color
    GROUPS.setdefault((group, m), []).append(o)
    return o

def rod(p1, p2, r, m, g, verts=16):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=max(d.length, 1e-4), vertices=verts, location=(p1 + p2) / 2)
    o = bpy.context.object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("Z", "Y")
    return put(o, m, g)

def ball(loc, r, m, g, scale=(1, 1, 1), quat=None, seg=16):
    """球／椭球。quat 给定时，scale 的 x 轴沿 quat 的前向。"""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg, ring_count=max(4, seg // 2), location=loc)
    o = bpy.context.object
    o.scale = scale
    if quat is not None:
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = quat
    bpy.ops.object.shade_smooth()
    return put(o, m, g)

def box(loc, s, m, g, quat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = s
    if quat is not None:
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = quat
    return put(o, m, g)

def torus(loc, R, r, m, g, axis=(0, 0, 1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=32, minor_segments=8, location=loc)
    o = bpy.context.object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector(axis).to_track_quat("Z", "Y")
    bpy.ops.object.shade_smooth()
    return put(o, m, g)

def curve(points, r, m, g, order=4):
    cd = bpy.data.curves.new("c", "CURVE")
    cd.dimensions = "3D"
    cd.bevel_depth = r
    cd.bevel_resolution = 2
    sp = cd.splines.new("NURBS")
    sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        sp.points[i].co = (*p, 1)
    sp.use_endpoint_u = True
    sp.order_u = min(order, len(points))
    o = bpy.data.objects.new("c", cd)
    coll.objects.link(o)
    cd.materials.append(M[m])
    o.color = M[m].diffuse_color
    return o

def gear(center, axis, R, th, m, g, teeth=None, spokes=5):
    center, axis = Vector(center), Vector(axis).normalized()
    q = axis.to_track_quat("Z", "Y")
    teeth = teeth or max(10, int(R * 260))
    torus(center, R * 0.86, R * 0.10, m, g, axis)
    rod(center - axis * th / 2, center + axis * th / 2, R * 0.22, m, g)
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        p = center + q @ Vector((R * math.cos(a), R * math.sin(a), 0))
        box(p, (R * 0.16, R * 2 * math.pi / teeth * 0.5, th), m, g, q @ Quaternion((0, 0, 1), a))
    for k in range(spokes):
        a = 2 * math.pi * k / spokes + 0.3
        rod(center, center + q @ Vector((R * 0.8 * math.cos(a), R * 0.8 * math.sin(a), 0)), R * 0.06, m, g, 8)

def bez(ctrl, t):
    a, b, c, d = [Vector(v) for v in ctrl]
    return a * (1 - t) ** 3 + b * 3 * t * (1 - t) ** 2 + c * 3 * t ** 2 * (1 - t) + d * t ** 3

def frame_of(fwd):
    """返回 (fwd, side, up) 正交基；up 尽量朝上。"""
    fwd = Vector(fwd).normalized()
    up0 = Vector((0, 0, 1)) if abs(fwd.z) < 0.95 else Vector((1, 0, 0))
    side = fwd.cross(up0).normalized()
    up = side.cross(fwd).normalized()
    return fwd, side, up

def quat_of(fwd, up):
    """把局部 x 轴对准 fwd、z 轴对准 up 的四元数。"""
    return fwd.to_track_quat("X", "Z") if abs(fwd.normalized().dot(up)) < 0.999 else Quaternion()

# ---------------- 钢架（与 v2 相同的占位尺寸：0.80 × 0.45 × 1.10 m） ----------------
W, D, H, ZL = 0.80, 0.45, 1.10, 0.40
R = 0.008
xs, ys = (-W / 2, W / 2), (-D / 2, D / 2)
for x in xs:
    for y in ys:
        rod((x, y, 0.0), (x, y, H + 0.04), R, "steel", "frame")
for z in (ZL, H):
    for y in ys:
        rod((-W / 2 - 0.03, y, z), (W / 2 + 0.03, y, z), R, "steel", "frame")
    for x in xs:
        rod((x, -D / 2 - 0.03, z + 0.025), (x, D / 2 + 0.03, z + 0.025), R, "steel", "frame")
    for x in xs:
        for y in ys:
            rod((x - 0.022, y, z), (x + 0.022, y, z), 0.02, "dark", "frame")
            rod((x, y - 0.022, z + 0.025), (x, y + 0.022, z + 0.025), 0.02, "dark", "frame")
for x in (-0.18, 0.18):
    rod((x, -D / 2 - 0.03, H + 0.05), (x, D / 2 + 0.03, H + 0.05), R, "steel", "frame")
    for y in ys:
        rod((x - 0.022, y, H + 0.05), (x + 0.022, y, H + 0.05), 0.02, "dark", "frame")

bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
put(bpy.context.object, "floor", "floor")

TOP = H + 0.05
def hang(p, g="lines"):
    p = Vector(p)
    rod(p, (p.x, p.y, TOP), 0.0007, "line", g, 6)

# ---------------- 花盆、土、苔藓、植物（真实植物的位置示意） ----------------
PC = Vector((0.06, 0.0, 0.0))     # 花盆中心（放在地面，钢架下层横杆从上方穿过）
PR, PH = 0.15, 0.24
bpy.ops.mesh.primitive_cone_add(radius1=PR * 0.80, radius2=PR, depth=PH, vertices=48, location=PC + Vector((0, 0, PH / 2)))
put(bpy.context.object, "terracotta", "pot")
torus(PC + Vector((0, 0, PH)), PR, 0.012, "terracotta", "pot")
SOIL_Z = PH - 0.025
bpy.ops.mesh.primitive_cylinder_add(radius=PR * 0.97, depth=0.01, vertices=48, location=PC + Vector((0, 0, SOIL_Z)))
put(bpy.context.object, "soil", "pot")
for i in range(30):   # 苔藓团
    a = random.uniform(0, 2 * math.pi); r = PR * 0.85 * math.sqrt(random.random())
    p = PC + Vector((r * math.cos(a), r * math.sin(a), SOIL_Z + 0.005))
    s = random.uniform(0.02, 0.04)
    ball(p, 1.0, "moss", "plant", scale=(s, s * random.uniform(0.8, 1.2), s * 0.45), seg=12)
for i in range(16):   # 溢出到地面的苔藓
    a = random.uniform(0, 2 * math.pi); r = PR + random.uniform(0.02, 0.18)
    p = PC + Vector((r * math.cos(a), r * math.sin(a), 0.0))
    s = random.uniform(0.02, 0.05)
    ball(p, 1.0, "moss", "plant", scale=(s, s * 0.8, s * 0.6), seg=12)
    ball(p + Vector((s * 0.7, s * 0.3, 0)), 1.0, "moss", "plant", scale=(s * 0.6, s * 0.6, s * 0.5), seg=10)

def leaf(p, d, size):
    fwd, side, up = frame_of(d)
    ball(p + fwd * size, 1.0, "leaf", "plant", scale=(size, size * 0.42, size * 0.06), quat=quat_of(fwd, up), seg=12)

STEMS = []
for i in range(7):
    a = 2 * math.pi * i / 7 + 0.3
    b = PC + Vector((0.06 * math.cos(a), 0.06 * math.sin(a), SOIL_Z))
    h = random.uniform(0.25, 0.55)
    top = b + Vector((0.10 * math.cos(a) + random.uniform(-0.05, 0.05), 0.08 * math.sin(a), h))
    pts = [b, b + Vector((0, 0, h * 0.4)), (b + top) / 2 + Vector((0.02, 0, 0.05)), top]
    curve(pts, 0.004, "leaf", "plant")
    STEMS.append(pts)
    for k in range(3, 9):
        t = k / 9
        p = bez(pts, t)
        dd = Vector((math.cos(a + k * 2.1), math.sin(a + k * 2.1), 0.5))
        leaf(p, dd, random.uniform(0.025, 0.045))
# 一枝高花茎：长喙虫的连杆最后伸向这朵花
FLOWER = Vector((0.16, 0.10, 0.80))
fb = PC + Vector((0.03, 0.03, SOIL_Z))
fstem = [fb, fb + Vector((0.0, 0.02, 0.25)), FLOWER + Vector((-0.04, 0.0, -0.22)), FLOWER]
curve(fstem, 0.005, "leaf", "plant")
for k in range(2, 8):
    leaf(bez(fstem, k / 10), Vector((math.cos(k * 2.4), math.sin(k * 2.4), 0.3)), 0.04)
for k in range(7):
    a = 2 * math.pi * k / 7
    d = Vector((math.cos(a), math.sin(a), 0.55))
    fwd, side, up = frame_of(d)
    ball(FLOWER + fwd * 0.03, 1.0, "petal", "plant", scale=(0.03, 0.014, 0.004), quat=quat_of(fwd, up), seg=12)
ball(FLOWER, 0.013, "brass", "plant", seg=12)
hang(FLOWER + Vector((0, 0, 0.02)))  # 实际做法待定：花茎可能需要支撑

# 土壤湿度传感器（插在土里）
MS = PC + Vector((-0.09, -0.06, SOIL_Z))
for dx in (-0.008, 0.008):
    box(MS + Vector((dx, 0, -0.03)), (0.006, 0.002, 0.07), "sensor", "sensor")
box(MS + Vector((0, 0, 0.012)), (0.025, 0.004, 0.02), "sensor", "sensor")

# ---------------- 虫：四个物种，一个耦合程度 t（0 = 自由的虫，1 = 机械部件） ----------------
SPECIES = {
    # 名称, 主体材质, 强调色
    "paper": ("pla", "pla"),        # z1：纸翅虫
    "cricket": ("cricket", "copper"),   # z2：蟋蟀型
    "beak": ("pla", "brass"),       # z3：长喙型
    "water": ("bug_green", "bug_green"),  # z4：水虫型
}

def insect(p, d, sp, t, sc=0.035, g="insects"):
    """在 p 处放一只朝向 d 的虫，t 为耦合程度。返回 (头端点, 尾端点)。"""
    p = Vector(p)
    fwd, side, up = frame_of(d)
    q = quat_of(fwd, up)
    body_m, acc = SPECIES[sp]
    mech = t > 0.65
    bm = "brass" if mech and sp != "water" else ("dark" if mech else body_m)
    slim = 0.75 if sp == "beak" else (1.25 if sp == "water" else 1.0)
    flat = 0.55 if sp == "water" else 1.0
    # 身体：t 越大越接近圆柱（拉长、变细、变规则）
    e = 1.0 + 0.6 * t
    ball(p + fwd * 0.95 * sc, 0.26 * sc, bm if t > 0.4 else body_m, g, seg=12)                    # 头
    ball(p, 1.0, body_m if t < 0.85 else bm, g, scale=(0.36 * sc * e, 0.30 * sc * slim, 0.28 * sc * flat), quat=q, seg=14)  # 胸
    ball(p - fwd * 1.05 * sc * e, 1.0, body_m, g,
         scale=(0.62 * sc * e, 0.32 * sc * slim * (1 - 0.3 * t), 0.30 * sc * flat * (1 - 0.3 * t)), quat=q, seg=14)  # 腹
    if t > 0.3:   # 腹节上出现金属环
        for k in range(int(1 + t * 4)):
            c = p - fwd * (0.6 + 0.25 * k) * sc * e
            torus(c, 0.30 * sc * slim * (1 - 0.3 * t), 0.03 * sc, "brass", g, fwd)
    # 腿：随 t 变短、变直，最后消失
    legs = 0 if t > 0.8 else 3
    for j in range(legs):
        for s in (-1, 1):
            a = p + fwd * (0.25 - 0.25 * j) * sc + side * s * 0.25 * sc
            L = sc * (0.8 - 0.85 * t) * (1.4 if (sp == "cricket" and j == 2) else 1.0)
            b = a + side * s * L * 0.7 + up * L * 0.35 - fwd * 0.2 * L * (j - 1)
            c = b + side * s * L * 0.3 - up * L * 0.9
            rod(a, b, 0.035 * sc, "dark", g, 6)
            rod(b, c, 0.03 * sc, "dark", g, 6)
            if sp == "water" and j == 2:   # 桨状后腿
                ball(c, 1.0, "bug_green", g, scale=(0.25 * sc, 0.08 * sc, 0.02 * sc), quat=quat_of(side * s, up), seg=8)
    # 物种特征
    if sp == "paper":   # 两对薄翅；耦合后翅变成径向叶片
        for s in (-1, 1):
            for k, (ln, ang) in enumerate(((1.4, 0.35), (1.1, 0.75))):
                wd = (fwd * -math.cos(ang) + side * s * math.sin(ang) + up * (0.5 - 0.4 * t)).normalized()
                ff, ss, uu = frame_of(wd)
                ball(p + up * 0.2 * sc + wd * ln * sc * 0.5, 1.0, "wing" if t < 0.6 else "pla", g,
                     scale=(ln * sc * 0.5, 0.32 * sc, 0.012 * sc), quat=quat_of(ff, up), seg=12)
    elif sp == "cricket":   # 翅平贴在背上，翅上一排齿纹（锉）
        for s in (-1, 1):
            c = p - fwd * 0.6 * sc * e + side * s * 0.12 * sc + up * 0.28 * sc
            ball(c, 1.0, "wing", g, scale=(0.9 * sc * e, 0.22 * sc, 0.02 * sc), quat=q, seg=12)
            for k in range(7):
                box(c + fwd * (k - 3) * 0.2 * sc + up * 0.02 * sc, (0.04 * sc, 0.18 * sc, 0.05 * sc), acc, g, q)
        for s in (-1, 1):   # 长触角
            curve([p + fwd * 1.1 * sc, p + fwd * 1.8 * sc + side * s * 0.5 * sc + up * 0.5 * sc,
                   p + fwd * 2.4 * sc + side * s * 1.2 * sc + up * 0.2 * sc], 0.02 * sc, acc, g)
    elif sp == "beak":   # 长喙；小而快的翅
        rod(p + fwd * 1.15 * sc, p + fwd * (2.4 + 0.8 * t) * sc - up * 0.15 * sc, 0.035 * sc, "brass", g, 8)
        for s in (-1, 1):
            wd = (side * s + up * 0.6).normalized()
            ball(p + wd * 0.5 * sc, 1.0, "wing", g, scale=(0.55 * sc, 0.2 * sc, 0.01 * sc), quat=quat_of(wd, fwd), seg=10)
    elif sp == "water":   # 背上的气泡（水虫携带气泡的联想），宽扁身体
        for k in range(3):
            ball(p - fwd * (0.4 + 0.45 * k) * sc + up * 0.3 * sc, 0.09 * sc, "line", g, seg=8)
    head = p + fwd * 1.2 * sc
    tail = p - fwd * (1.05 + 0.62) * sc * e
    if t > 0.45:   # 两端出现关节球：可以和下一只咬合
        ball(head, 0.12 * sc, "brass", g, seg=10)
        ball(tail, 0.12 * sc, "brass", g, seg=10)
    return head, tail

# ---------------- 顶部机械体（悬吊） ----------------
HUB = Vector((-0.02, 0.0, 0.93))
hs = 0.06
cs = [HUB + Vector((sx * hs, sy * hs, sz * hs)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
for a in cs:
    for b in cs:
        if sum(1 for i in range(3) if abs(a[i] - b[i]) > 1e-6) == 1 and tuple(a) < tuple(b):
            rod(a, b, 0.004, "steel", "machine")
for c in cs:
    ball(c, 0.009, "brass", "machine", seg=10)
    if c.z > HUB.z: hang(c)
for i in range(5):
    gear(HUB + Vector((random.uniform(-0.04, 0.04), random.uniform(-0.04, 0.04), random.uniform(-0.04, 0.04))),
         (random.uniform(-1, 1), 1, random.uniform(-0.3, 0.3)), random.uniform(0.015, 0.03), 0.004,
         random.choice(["brass", "copper"]), "machine")

ANCH = {}
# z1 纸翅虫 → 叶片齿轮（转：AS5600）
G1 = HUB + Vector((-0.20, -0.06, -0.02))
gear(G1, (0, 1, 0), 0.085, 0.010, "brass", "machine", teeth=32, spokes=6)
for k in range(14):   # 齿轮外圈：纸翅叶片
    a = 2 * math.pi * k / 14
    dvec = Vector((math.cos(a), 0, math.sin(a)))
    ball(G1 + dvec * 0.125, 1.0, "pla", "machine", scale=(0.045, 0.004, 0.018),
         quat=quat_of(dvec, Vector((0, 1, 0))), seg=10)
rod(G1, HUB + Vector((-hs, 0, -0.02)), 0.006, "steel", "machine")
box(G1 + Vector((0, 0.03, 0)), (0.025, 0.006, 0.025), "sensor", "sensor")       # AS5600 示意
rod(G1 + Vector((0.05, -0.01, 0)), G1 + Vector((0.05, -0.06, 0)), 0.007, "pla", "machine")  # 摇柄
ball(G1 + Vector((0.05, -0.065, 0)), 0.011, "pla", "machine")
hang(G1 + Vector((0, 0, 0.13)))
ANCH["paper"] = G1 + Vector((0.0, 0.0, -0.135))

# z2 蟋蟀型 → 棘轮翅排（拨：压电片在翅根）
B0 = HUB + Vector((hs, -0.02, 0.0)); B1 = HUB + Vector((0.30, -0.08, 0.04))
rod(B0, B1, 0.006, "steel", "machine")
bv = (B1 - B0)
for k in range(16):   # 锉齿
    c = B0 + bv * (k + 0.5) / 16
    box(c + Vector((0, 0, 0.008)), (0.004, 0.02, 0.012), "copper", "machine", bv.to_track_quat("X", "Z"))
for k in range(5):    # 叠在一起的翅（像瓦片），每片翅根一片压电片
    c = B0 + bv * (0.15 + 0.17 * k) + Vector((0, 0, 0.02))
    wd = (bv.normalized() * 0.4 + Vector((0, -0.6, 0.7))).normalized()
    ball(c + wd * 0.07, 1.0, "wing", "machine", scale=(0.08, 0.025, 0.002), quat=quat_of(wd, bv.normalized()), seg=12)
    box(c, (0.016, 0.016, 0.004), "sensor", "sensor")
hang(B1 + Vector((0, 0, 0.01))); hang(B0 + bv * 0.5)
ANCH["cricket"] = B1

# z3 长喙型 → 连杆，最后一节伸进花里（触角／连杆弯：弯曲传感器）
L0 = HUB + Vector((0.02, hs, -0.02))
pts = [L0, L0 + Vector((0.06, 0.06, -0.03)), L0 + Vector((0.10, 0.04, -0.09)), FLOWER + Vector((-0.03, -0.01, 0.05))]
for a, b in zip(pts, pts[1:]):
    rod(a, b, 0.005, "brass", "machine", 10)
for p in pts[:-1]:
    ball(p, 0.010, "brass", "machine", seg=10)
rod(pts[-1], FLOWER + Vector((0, 0, 0.008)), 0.0025, "brass", "machine", 8)     # 喙尖
box(pts[1] + Vector((0, 0, 0.012)), (0.03, 0.006, 0.004), "sensor", "sensor")   # 弯曲传感器示意
hang(pts[1]); hang(pts[2])
ANCH["beak"] = pts[1]

# z4 水虫型 → 分节管子，回到土里（弯：内部弯曲传感器）
T0 = HUB + Vector((0.0, -hs, -hs))
tctrl = [T0, T0 + Vector((0.05, -0.10, -0.15)), PC + Vector((-0.05, -0.12, SOIL_Z + 0.30)), PC + Vector((-0.04, -0.07, SOIL_Z - 0.02))]
N = 16
for i in range(N):
    t0, t1 = i / N + 0.01, (i + 1) / N - 0.01
    a, b = bez(tctrl, t0), bez(tctrl, t1)
    r = 0.016 - 0.006 * i / N
    rod(a, b, r, "bug_green" if i % 2 else "dark", "machine", 20)
    torus(b, r, 0.0025, "brass", "machine", b - a)
curve([bez(tctrl, k / 12) for k in range(13)], 0.002, "sensor", "sensor")
for k in (0.25, 0.5):
    hang(bez(tctrl, k) + Vector((0, 0, 0.02)))
ANCH["water"] = bez(tctrl, 0.35)

# ---------------- 四条虫链：从盆沿往上爬，越往上越密、越机械 ----------------
CHAIN = {"paper": 205, "cricket": 300, "beak": 70, "water": 150}   # 起点在盆沿的角度（度）
NCH = 13
for sp, deg in CHAIN.items():
    a = math.radians(deg)
    S = PC + Vector(((PR + 0.01) * math.cos(a), (PR + 0.01) * math.sin(a), PH + 0.01))
    A = ANCH[sp]
    out = Vector((math.cos(a), math.sin(a), 0))
    ctrl = [S, S + out * 0.10 + Vector((0, 0, 0.25)), A + out * 0.12 + Vector((0, 0, -0.25)), A]
    prev_head = None
    for k in range(NCH):
        u = k / (NCH - 1)
        s = 1 - (1 - u) ** 1.7          # 越往上越密
        t = u ** 1.2                    # 耦合程度
        p = bez(ctrl, s)
        d = bez(ctrl, min(1, s + 0.02)) - bez(ctrl, max(0, s - 0.02))
        sc = 0.034 - 0.006 * t
        head, tail = insect(p, d, sp, t, sc)
        if prev_head is not None and t > 0.35:   # 咬合：上一只的头连到这只的尾
            rod(prev_head, tail, 0.0015 + 0.004 * t, "steel" if t > 0.6 else "dark", "insects", 8)
            if t > 0.7:
                torus((prev_head + tail) / 2, 0.006, 0.0015, "brass", "insects", tail - prev_head)
        prev_head = head
        if t > 0.3 and k % 3 == 0:
            hang(p + Vector((0, 0, 0.015)))

# ---------------- 底部散虫：栖在苔藓、盆沿、地面和下层横杆上 ----------------
spl = list(SPECIES)
for i in range(26):
    sp = spl[i % 4]
    where = random.random()
    if where < 0.45:      # 苔藓上
        a = random.uniform(0, 2 * math.pi); r = PR * 0.75 * math.sqrt(random.random())
        p = PC + Vector((r * math.cos(a), r * math.sin(a), SOIL_Z + 0.025))
    elif where < 0.65:    # 盆沿
        a = random.uniform(0, 2 * math.pi)
        p = PC + Vector((PR * math.cos(a), PR * math.sin(a), PH + 0.02))
    elif where < 0.85:    # 地面
        a = random.uniform(0, 2 * math.pi); r = PR + random.uniform(0.05, 0.25)
        p = PC + Vector((r * math.cos(a), r * math.sin(a), 0.012))
    else:                 # 下层横杆
        y = random.choice(ys); x = random.uniform(-0.35, 0.35)
        p = Vector((x, y, ZL + 0.018))
    yaw = random.uniform(0, 2 * math.pi)
    insect(p, (math.cos(yaw), math.sin(yaw), random.uniform(-0.1, 0.15)), sp, random.uniform(0.0, 0.12), 0.030)

# ---------------- 线缆：传感器 → 顶部电子盒 ----------------
EB = Vector((0.0, D / 2 + 0.05, H + 0.02))
box(EB, (0.12, 0.05, 0.07), "dark", "elec")
for src in (G1 + Vector((0, 0.035, 0.02)), B0 + Vector((0, 0, 0.03)), pts[1] + Vector((0, 0, 0.02)),
            T0 + Vector((0, 0, 0.02)), MS + Vector((0, 0, 0.02))):
    curve([src, src + Vector((0, 0.03, 0.12)), Vector((src.x * 0.6, D / 2 - 0.02, H - 0.01)), EB], 0.0022, "cable", "cables")
curve([EB + Vector((0.06, 0.02, 0)), (0.5, 0.6, 0.8), (0.9, 1.2, 0.01)], 0.004, "cable", "cables")

# ---------------- 外部扬声器、比例参照 ----------------
for s in (-1, 1):
    rod((s * 1.25, -0.40, 0), (s * 1.25, -0.40, 1.0), 0.012, "steel", "env")
    box((s * 1.25, -0.40, 1.13), (0.18, 0.18, 0.28), "speaker", "env")
rod((-1.75, -0.2, 0), (-1.75, -0.2, 1.45), 0.13, "person", "person")
ball((-1.75, -0.2, 1.58), 0.11, "person", "person")

# ---------------- 合并对象 ----------------
for (g, m), objs in GROUPS.items():
    objs = [o for o in objs if o.name in bpy.data.objects]
    if len(objs) < 2: continue
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    bpy.context.object.name = f"{g}_{m}"

# ---------------- 标注 ----------------
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
coll.objects.link(cam)
scn.camera = cam
font = None
for fp in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
    try: font = bpy.data.fonts.load(fp); break
    except Exception: pass
LABELS = [
    ("z1 纸翅虫 → 叶片齿轮：转（AS5600）", G1 + Vector((-0.12, -0.20, 0.20))),
    ("z2 蟋蟀 → 锉齿翅排：拨（压电片）", B1 + Vector((0.12, -0.20, 0.14))),
    ("z3 长喙虫 → 连杆伸进花：弯（弯曲传感器）", FLOWER + Vector((0.32, -0.25, 0.0))),
    ("z4 水虫 → 分节管回到土里：弯", bez(tctrl, 0.6) + Vector((-0.38, -0.25, 0.0))),
    ("四条虫链：越往上越密、越机械", Vector((-0.30, -0.30, 0.62))),
    ("散虫：栖在苔藓、盆沿、地面", PC + Vector((0.30, -0.30, 0.10))),
    ("土壤湿度传感器", MS + Vector((-0.30, -0.25, 0.02))),
]
labels = []
for txt, loc in LABELS:
    cu = bpy.data.curves.new("lbl", "FONT")
    cu.body = txt; cu.size = 0.030; cu.align_x = "CENTER"
    if font: cu.font = font
    o = bpy.data.objects.new("label", cu); coll.objects.link(o)
    o.location = loc
    cu.materials.append(M["label"])
    c = o.constraints.new("TRACK_TO"); c.target = cam; c.track_axis = "TRACK_Z"; c.up_axis = "UP_Y"
    labels.append(o)

# ---------------- 灯光与渲染 ----------------
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: scn.render.engine = eng; break
    except TypeError: pass
print("engine", scn.render.engine)
world = bpy.data.worlds.new("w"); scn.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.80, 0.78, 0.74, 1); bg.inputs[1].default_value = 0.35
def light(loc, energy, size):
    ld = bpy.data.lights.new("l", "AREA"); ld.energy = energy; ld.size = size
    o = bpy.data.objects.new("l", ld); coll.objects.link(o); o.location = loc
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (Vector((0, 0, 0.6)) - Vector(loc)).to_track_quat("-Z", "Y")
light((-2.0, -2.5, 3.0), 220, 2.0)
light((2.5, -1.0, 2.0), 80, 1.5)
light((0.5, 2.5, 2.5), 90, 2.0)
scn.render.resolution_x, scn.render.resolution_y = 1400, 1000
try: scn.eevee.taa_render_samples = 32
except Exception: pass
vt = [i.identifier for i in scn.view_settings.bl_rna.properties["view_transform"].enum_items]
scn.view_settings.view_transform = "AgX" if "AgX" in vt else "Standard"

def shoot(name, loc, target, lens=35, show_labels=False, hide_env=False):
    cam.location = loc
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
    cam_data.lens = lens
    for o in labels: o.hide_render = not show_labels
    for o in bpy.data.objects:
        if o.name.startswith(("person", "env")): o.hide_render = hide_env
    bpy.context.view_layer.update()
    scn.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", scn.render.filepath)

shoot("v3_hero", (1.25, -1.65, 1.00), (0.0, 0, 0.60), 32, hide_env=True)
shoot("v3_labels", (1.5, -2.1, 1.15), (0, -0.1, 0.62), 30, show_labels=True, hide_env=True)
shoot("v3_scale", (2.1, -3.1, 1.5), (0, 0, 0.65), 28)
shoot("v3_side", (0.0, -2.3, 0.70), (0.0, 0, 0.58), 30, hide_env=True)
shoot("v3_detail", (0.55, -0.75, 0.55), (0.02, 0, 0.45), 40, hide_env=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "proto_v3.blend"))
print("saved")
