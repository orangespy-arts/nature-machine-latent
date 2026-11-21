# 落地装置原型 v2：鱼线悬吊、极繁风格（尺寸为占位值，待实测）
# 运行：blender -b --factory-startup --python proto_v2.py -- <输出目录>
import bpy, math, random, sys, os
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.dirname(__file__)
os.makedirs(OUT, exist_ok=True)
random.seed(7)

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
    "wing": mat("wing", (0.97, 0.88, 0.70), 0.0, 0.2, alpha=0.35),
    "vein": mat("vein", (0.75, 0.42, 0.15), 0.6, 0.35),
    "line": mat("line", (0.85, 0.88, 0.92), 0.0, 0.1, alpha=0.6),
    "cable": mat("cable", (0.80, 0.18, 0.12), 0.0, 0.5),
    "sensor": mat("sensor", (0.15, 0.45, 0.75), 0.0, 0.4),
    "floor": mat("floor", (0.30, 0.30, 0.29), 0.0, 0.8),
    "person": mat("person", (0.75, 0.75, 0.78), 0.0, 0.7),
    "speaker": mat("speaker", (0.10, 0.10, 0.10), 0.2, 0.5),
    "label": mat("label", (0.05, 0.05, 0.05), 0.0, 0.8),
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

def ball(loc, r, m, g, scale=(1, 1, 1), rot=(0, 0, 0), seg=16):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg, ring_count=seg // 2, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = scale
    bpy.ops.object.shade_smooth()
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
    """齿轮：轮缘＋齿＋轮毂＋辐条，axis 为轴向。"""
    center, axis = Vector(center), Vector(axis).normalized()
    q = axis.to_track_quat("Z", "Y")
    teeth = teeth or max(10, int(R * 260))
    torus(center, R * 0.86, R * 0.10, m, g, axis)
    rod(center - axis * th / 2, center + axis * th / 2, R * 0.22, m, g)
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        p = center + q @ Vector((R * math.cos(a), R * math.sin(a), 0))
        bpy.ops.mesh.primitive_cube_add(size=1, location=p)
        o = bpy.context.object
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = q @ Vector((0, 0, 1)).rotation_difference(Vector((0, 0, 1))) @ \
            __import__("mathutils").Quaternion((0, 0, 1), a)
        o.scale = (R * 0.16, R * 2 * math.pi / teeth * 0.5, th)
        put(o, m, g)
    for k in range(spokes):
        a = 2 * math.pi * k / spokes + 0.3
        rod(center, center + q @ Vector((R * 0.8 * math.cos(a), R * 0.8 * math.sin(a), 0)), R * 0.06, m, g, 8)

# ---------------- 钢架（占位：0.80 × 0.45 × 1.10 m，杆径 16 mm） ----------------
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
# 顶层加两根横杆，作为吊点
for x in (-0.18, 0.18):
    rod((x, -D / 2 - 0.03, H + 0.05), (x, D / 2 + 0.03, H + 0.05), R, "steel", "frame")
    for y in ys:
        rod((x - 0.022, y, H + 0.05), (x + 0.022, y, H + 0.05), 0.02, "dark", "frame")

bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
put(bpy.context.object, "floor", "floor")

TOP = H + 0.05
def hang(p, n=1, spread=0.0, g="lines"):
    """从顶层横杆垂直吊鱼线到点 p。"""
    p = Vector(p)
    for i in range(n):
        off = Vector(((i - (n - 1) / 2) * spread, 0, 0))
        q = p + off
        rod(q, (q.x, q.y, TOP), 0.0007, "line", g, 6)

def tie_down(p, to):
    """向下张紧的鱼线：抵消转动齿轮时的扭矩。"""
    rod(p, to, 0.0007, "line", "lines", 6)

# ---------------- 胸：金属框笼＋齿轮堆（中心 z≈0.75） ----------------
cx, cz = -0.06, 0.76
L, Wc, Hc = 0.30, 0.18, 0.20
corners = [(cx + sx * L / 2, sy * Wc / 2, cz + sz * Hc / 2) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
for a in corners:
    for b in corners:
        diff = sum(1 for i in range(3) if abs(a[i] - b[i]) > 1e-6)
        if diff == 1 and a < b:
            rod(a, b, 0.006, "steel", "thorax")
for c in corners:
    ball(c, 0.012, "brass", "thorax", seg=12)
# 竖向立柱与轴
for sx in (-1, 0, 1):
    for sy in (-1, 1):
        rod((cx + sx * 0.08, sy * Wc / 2, cz - Hc / 2), (cx + sx * 0.08, sy * Wc / 2, cz + Hc / 2), 0.004, "steel", "thorax")
for i in range(5):
    x = cx - L / 2 + 0.03 + i * 0.06
    rod((x, -Wc / 2 - 0.02, cz + random.uniform(-0.06, 0.06)), (x, Wc / 2 + 0.02, cz + random.uniform(-0.06, 0.06)),
        0.004, "steel", "thorax")
# 齿轮堆：轴向 y
for i in range(16):
    gx = cx + random.uniform(-L / 2 + 0.03, L / 2 - 0.03)
    gz = cz + random.uniform(-Hc / 2 + 0.03, Hc / 2 - 0.03)
    gy = random.uniform(-Wc / 2 + 0.02, Wc / 2 - 0.02)
    gear((gx, gy, gz), (0, 1, 0), random.uniform(0.018, 0.045), 0.006, random.choice(["brass", "brass", "copper"]),
         "thorax")
# 前面的大齿轮＝可转控制（AS5600 在其轴后）
GC = Vector((cx + 0.04, -Wc / 2 - 0.035, cz - 0.01))
gear(GC, (0, 1, 0), 0.075, 0.012, "brass", "thorax", teeth=36, spokes=6)
rod(GC + Vector((0.05, -0.006, 0)), GC + Vector((0.05, -0.05, 0)), 0.008, "pla", "thorax")  # 摇柄
ball(GC + Vector((0.05, -0.055, 0)), 0.012, "pla", "thorax")
rod(GC + Vector((0, 0.01, 0)), GC + Vector((0, 0.04, 0)), 0.006, "steel", "thorax")
put_box = lambda loc, s, m, g: (bpy.ops.mesh.primitive_cube_add(size=1, location=loc), setattr(bpy.context.object, "scale", s), put(bpy.context.object, m, g))
put_box(GC + Vector((0, 0.045, 0)), (0.025, 0.006, 0.025), "sensor", "thorax")  # AS5600 示意
# 弹簧
for sx in (-1, 1):
    pts = []
    for k in range(60):
        a = k * 0.6
        pts.append((cx + sx * 0.10 + 0.012 * math.cos(a), Wc / 2 + 0.02 + 0.012 * math.sin(a), cz - 0.08 + k * 0.0025))
    curve(pts, 0.0015, "steel", "thorax", order=3)
# 悬吊＋向下张紧
for c in corners:
    if c[2] > cz:
        hang(c)
    else:
        tie_down(c, (c[0] + (0.05 if c[0] > cx else -0.05), c[1] * 2.3, ZL + 0.025))

# ---------------- 头：多孔外壳、复眼、上颚、触角 ----------------
HC = Vector((cx - L / 2 - 0.13, 0, cz + 0.05))
ball(HC, 1.0, "pla", "head", scale=(0.085, 0.075, 0.07), seg=32)
for i in range(70):  # 外壳上的孔（深色点）
    u = random.uniform(-1.1, 1.1); v = random.uniform(-0.9, 0.9)
    n = Vector((-math.cos(v) * math.cos(u) * 0.7 - 0.3, math.cos(v) * math.sin(u), math.sin(v))).normalized()
    p = HC + Vector((n.x * 0.085, n.y * 0.075, n.z * 0.07))
    ball(p, 0.006, "dark", "head", seg=8)
for s in (-1, 1):
    ball(HC + Vector((-0.04, s * 0.055, 0.02)), 0.032, "copper", "head", seg=20)  # 复眼
    curve([HC + Vector((-0.07, s * 0.03, -0.04)), HC + Vector((-0.12, s * 0.05, -0.07)),
           HC + Vector((-0.13, s * 0.01, -0.10))], 0.006, "pla", "head")  # 上颚
    pts = [HC + Vector((-0.03, s * 0.03, 0.06))]
    for k in range(1, 9):
        pts.append(pts[0] + Vector((-0.02 * k + 0.002 * k * k, s * 0.012 * k, 0.045 * k - 0.0025 * k * k)))
    curve(pts, 0.0025, "brass", "head")
    for p in pts[1::1]:
        ball(p, 0.005, "brass", "head", seg=8)
hang(HC + Vector((0, 0, 0.07)))
hang(HC + Vector((0.05, 0, 0.05)))
# 头与胸之间的颈：露出的轴和线
rod(HC + Vector((0.08, 0, 0)), Vector((cx - L / 2, 0, cz + 0.03)), 0.008, "steel", "head")
for k in range(3):
    torus(HC + Vector((0.10 + k * 0.025, 0, -0.012 + k * 0.012)), 0.018, 0.004, "brass", "head", (1, 0, 0.3))

# ---------------- 翅：两对，膜＋翅脉；翅根有压电片 ----------------
def wing(root, length, width, yaw, pitch, g="wing"):
    root = Vector(root)
    dirv = Vector((math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch)))
    side = dirv.cross(Vector((0, 0, 1))).normalized()
    if side.length < 0.1: side = Vector((0, 1, 0))
    up = side.cross(dirv).normalized()
    c = root + dirv * length / 2
    # 膜
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16, location=c)
    o = bpy.context.object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = dirv.to_track_quat("X", "Z") if abs(dirv.z) < 0.99 else o.rotation_quaternion
    o.scale = (length / 2, width / 2, 0.0015)
    put(o, "wing", g)
    # 翅脉：主脉＋分支
    wside = o.rotation_quaternion @ Vector((0, 1, 0))
    curve([root, root + dirv * length * 0.5 + wside * width * 0.25, root + dirv * length * 0.98], 0.0022, "vein", g)
    curve([root, root + dirv * length * 0.5 - wside * width * 0.30, root + dirv * length * 0.95 - wside * width * 0.1],
          0.0018, "vein", g)
    for k in range(9):
        t = 0.15 + k * 0.09
        b = root + dirv * length * t
        e = b + dirv * length * 0.12 + wside * width * random.uniform(-0.45, 0.45)
        curve([b, (b + e) / 2 + wside * 0.01, e], 0.0011, "vein", g, order=3)
    # 翅缘
    pts = []
    for k in range(25):
        a = 2 * math.pi * k / 24
        pts.append(c + dirv * math.cos(a) * length / 2 + wside * math.sin(a) * width / 2)
    curve(pts, 0.0015, "vein", g, order=3)
    put_box(root, (0.022, 0.022, 0.006), "sensor", g)  # 压电片示意
    hang(root + dirv * length * 0.85 + Vector((0, 0, 0.01)))
    return o

WR = Vector((cx - 0.02, 0, cz + Hc / 2 + 0.02))
wing(WR + Vector((0, -0.03, 0)), 0.42, 0.13, math.radians(-25), math.radians(28))
wing(WR + Vector((0, 0.03, 0)), 0.42, 0.13, math.radians(25), math.radians(28))
wing(WR + Vector((0.06, -0.03, -0.01)), 0.30, 0.10, math.radians(-50), math.radians(15))
wing(WR + Vector((0.06, 0.03, -0.01)), 0.30, 0.10, math.radians(50), math.radians(15))
rod(WR + Vector((0, -0.05, 0)), WR + Vector((0, 0.05, 0)), 0.006, "brass", "wing")

# ---------------- 腹节：12 节，带孔，略拆开（爆炸图感），尾刺 ----------------
P0 = Vector((cx + L / 2 + 0.03, 0, cz))
ctrl = [P0, P0 + Vector((0.14, 0, 0.02)), P0 + Vector((0.30, 0, -0.06)), P0 + Vector((0.36, 0, -0.26))]
def bez(t):
    a, b, c, d = ctrl
    return a * (1 - t) ** 3 + b * 3 * t * (1 - t) ** 2 + c * 3 * t ** 2 * (1 - t) + d * t ** 3
N = 12
for i in range(N):
    t0, t1 = i / N + 0.012, (i + 1) / N - 0.012
    p, q = bez(t0), bez(t1)
    r = 0.055 - 0.035 * (i / N)
    rod(p, q, r, "pla", "abdomen", 32)
    torus(q, r * 0.98, 0.003, "brass", "abdomen", q - p)
    ax = (q - p).normalized()
    side = ax.cross(Vector((0, 1, 0))).normalized()
    for k in range(6):  # 孔
        a = math.pi * (0.2 + 0.6 * k / 5)
        n = side * math.cos(a) + Vector((0, -1, 0)) * math.sin(a)
        ball((p + q) / 2 + n * r, 0.0045, "dark", "abdomen", seg=8)
    if i % 3 == 0:
        hang((p + q) / 2 + Vector((0, 0, r)))
# 中心穿线（内部弯曲传感器的位置示意）
curve([bez(t / 10) for t in range(11)], 0.003, "sensor", "abdomen")
tip = bez(1.0)
bpy.ops.mesh.primitive_cone_add(radius1=0.014, radius2=0.0, depth=0.07, location=tip + Vector((0.005, 0, -0.035)))
put(bpy.context.object, "pla", "abdomen")
rod(P0 - Vector((0.03, 0, 0)), P0 + Vector((0.01, 0, 0)), 0.012, "steel", "abdomen")

# ---------------- 腿：6 条，分节＋关节球，悬垂 ----------------
for j, lx in enumerate((-0.10, -0.02, 0.07)):
    for s in (-1, 1):
        a = Vector((cx + lx, s * Wc / 2, cz - Hc / 2 + 0.02))
        b = a + Vector((random.uniform(-0.05, 0.05), s * 0.13, 0.04))
        c = b + Vector((random.uniform(-0.04, 0.06), s * 0.06, -0.24))
        d = c + Vector((0.02 * (j - 1), s * 0.03, -0.07))
        for p, q, r in ((a, b, 0.008), (b, c, 0.0065), (c, d, 0.0045)):
            rod(p, q, r, "pla", "legs", 12)
        for p in (a, b, c):
            ball(p, 0.012, "brass", "legs", seg=12)
        bpy.ops.mesh.primitive_cone_add(radius1=0.006, radius2=0.0, depth=0.03, location=d + Vector((0, 0, -0.015)))
        put(bpy.context.object, "dark", "legs")
        hang(b + Vector((0, 0, 0.01)))

# ---------------- 漂浮的零件（拆开的齿轮、弹簧、节片），各自用鱼线吊着 ----------------
for i in range(14):
    p = Vector((random.uniform(-0.38, 0.38), random.uniform(-0.20, 0.20), random.uniform(0.50, 1.02)))
    if (p - Vector((cx, 0, cz))).length < 0.22:
        continue
    kind = random.random()
    if kind < 0.6:
        gear(p, (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.3, 0.3)), random.uniform(0.015, 0.035),
             0.005, random.choice(["brass", "copper"]), "floating")
    elif kind < 0.8:
        torus(p, random.uniform(0.015, 0.03), 0.003, "pla", "floating", (random.random(), random.random(), 0.3))
    else:
        rod(p, p + Vector((0.05, 0, 0.0)), 0.004, "steel", "floating")
    hang(p + Vector((0, 0, 0.02)))

# ---------------- 线缆：沿鱼线上去，汇到顶部电子盒 ----------------
EB = Vector((0.0, D / 2 + 0.05, H + 0.02))
put_box(EB, (0.12, 0.05, 0.07), "dark", "elec")
for src in (GC + Vector((0, 0.05, 0.03)), WR, P0 + Vector((0.1, 0, 0.05)), HC + Vector((0.03, 0, 0.06))):
    curve([src, src + Vector((0, 0.02, 0.15)), Vector((src.x * 0.6, D / 2 - 0.02, H - 0.01)), EB], 0.0025, "cable",
          "cables")
curve([EB + Vector((0.06, 0.02, 0)), (0.5, 0.6, 0.8), (0.9, 1.2, 0.01)], 0.004, "cable", "cables")

# ---------------- 外部扬声器、比例参照 ----------------
for s in (-1, 1):
    rod((s * 1.25, -0.40, 0), (s * 1.25, -0.40, 1.0), 0.012, "steel", "env")
    put_box((s * 1.25, -0.40, 1.13), (0.18, 0.18, 0.28), "speaker", "env")
rod((-1.75, -0.2, 0), (-1.75, -0.2, 1.45), 0.13, "person", "person")
ball((-1.75, -0.2, 1.58), 0.11, "person", "person")

# ---------------- 合并对象，减少数量 ----------------
for (g, m), objs in GROUPS.items():
    objs = [o for o in objs if o.name in bpy.data.objects]
    if len(objs) < 2: continue
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    bpy.context.object.name = f"{g}_{m}"

# ---------------- 标注（可选） ----------------
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
coll.objects.link(cam)
scn.camera = cam
font = None
for fp in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
    try: font = bpy.data.fonts.load(fp); break
    except Exception: pass
LABELS = [
    ("大齿轮：转（AS5600）", GC + Vector((0.0, -0.15, -0.16))),
    ("翅：拨（压电片在翅根）", WR + Vector((-0.05, -0.15, 0.38))),
    ("腹节：弯（弯曲传感器）", bez(0.8) + Vector((0.12, -0.15, -0.05))),
    ("头：多孔外壳", HC + Vector((-0.1, -0.15, 0.16))),
    ("鱼线吊点：顶层横杆", Vector((0.18, -0.30, H + 0.12))),
    ("向下张紧的鱼线", Vector((-0.30, -0.35, 0.50))),
    ("外部扬声器", Vector((1.25, -0.5, 1.42))),
    ("1.70 m 参照", Vector((-1.75, -0.2, 1.85))),
]
labels = []
for txt, loc in LABELS:
    cu = bpy.data.curves.new("lbl", "FONT")
    cu.body = txt; cu.size = 0.035; cu.align_x = "CENTER"
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
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (Vector((0, 0, 0.8)) - Vector(loc)).to_track_quat("-Z", "Y")
light((-2.0, -2.5, 3.0), 220, 2.0)
light((2.5, -1.0, 2.0), 80, 1.5)
light((0.5, 2.5, 2.5), 90, 2.0)
scn.render.resolution_x, scn.render.resolution_y = 1400, 1000
try: scn.eevee.taa_render_samples = 32
except Exception: pass
scn.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in scn.view_settings.bl_rna.properties["view_transform"].enum_items] else "Standard"

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

shoot("v2_hero", (1.15, -1.55, 1.05), (-0.05, 0, 0.78), 38, hide_env=True)
shoot("v2_labels", (2.0, -3.0, 1.6), (0, 0, 0.7), 30, show_labels=True)
shoot("v2_side", (0.0, -2.2, 0.85), (-0.02, 0, 0.75), 35, hide_env=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "proto_v2.blend"))
print("saved")
