# 齿轮 → 甲虫 五件过渡（形态草图，尺寸为占位值，未做打印检查）
# 参照：用户的参考图（mechanical-gears / morph-02 / morph-03 / morph-04 / ground-beetle）。
# 原则：除了材质替换，还让结构互相渗透——鞘翅纹 ↔ 齿槽，鞘翅外缘 ↔ 齿轮圆弧。
# 以毫米建模，最后统一缩到米。
# 运行：blender -b --factory-startup --python morph_gear_beetle.py -- <输出目录>
import bpy, bmesh, math, random, sys, os
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.dirname(__file__)
os.makedirs(OUT, exist_ok=True)
random.seed(3)
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
coll = scn.collection

# ---------------- 材质 ----------------
def mat(name, rgb, metal=0.0, rough=0.5, aniso=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*rgb, 1)
    return m

M = {
    "steel": mat("steel", (0.62, 0.62, 0.62), 1.0, 0.32),
    "shell": mat("shell", (0.025, 0.025, 0.03), 0.25, 0.28),
    "limb": mat("limb", (0.04, 0.035, 0.035), 0.1, 0.4),
    "eye": mat("eye", (0.01, 0.01, 0.012), 0.0, 0.08),
    "floor": mat("floor", (0.055, 0.055, 0.058), 0.0, 0.85),
    "label": mat("label", (0.55, 0.55, 0.55), 0.0, 0.6),
}

PIECE = {}   # piece -> list of objects
CUR = [None]
def reg(o, m):
    if o.type == "MESH":
        o.data.materials.clear(); o.data.materials.append(M[m])
    else:
        o.data.materials.append(M[m])
    PIECE.setdefault(CUR[0], []).append(o)
    return o

def mesh_obj(name, bm, m, smooth=True):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return reg(o, m)

def extrude_poly(pts, z0, z1, m, name="poly"):
    """二维多边形（逆时针或顺时针均可）拉伸成实体。"""
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    top = [bm.verts.new((x, y, z1)) for x, y in pts]
    bm.faces.new(bot[::-1]); bm.faces.new(top)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    return mesh_obj(name, bm, m, smooth=False)

def grid_solid(P, nu, nv, m, name="shell", zb=None):
    """P(u, v) -> (x, y, z) 为顶面；底面为同 xy、z = zb(u,v)（默认 0）。四周封闭成实体。"""
    bm = bmesh.new()
    T = [[None] * (nv + 1) for _ in range(nu + 1)]
    B = [[None] * (nv + 1) for _ in range(nu + 1)]
    for i in range(nu + 1):
        for j in range(nv + 1):
            u, v = i / nu, j / nv
            x, y, z = P(u, v)
            T[i][j] = bm.verts.new((x, y, z))
            B[i][j] = bm.verts.new((x, y, zb(u, v) if zb else 0.0))
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((T[i][j], T[i + 1][j], T[i + 1][j + 1], T[i][j + 1]))
            bm.faces.new((B[i][j + 1], B[i + 1][j + 1], B[i + 1][j], B[i][j]))
    for i in range(nu):
        bm.faces.new((T[i][0], B[i][0], B[i + 1][0], T[i + 1][0]))
        bm.faces.new((T[i + 1][nv], B[i + 1][nv], B[i][nv], T[i][nv]))
    for j in range(nv):
        bm.faces.new((T[0][j + 1], B[0][j + 1], B[0][j], T[0][j]))
        bm.faces.new((T[nu][j], B[nu][j], B[nu][j + 1], T[nu][j + 1]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    return mesh_obj(name, bm, m)

def ball(loc, r, m, scale=(1, 1, 1), rot=None, seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg, ring_count=seg // 2, location=loc)
    o = bpy.context.object; o.scale = scale
    if rot is not None:
        o.rotation_mode = "QUATERNION"; o.rotation_quaternion = rot
    bpy.ops.object.shade_smooth()
    return reg(o, m)

def rod(p1, p2, r, m, verts=12):
    p1, p2 = Vector(p1), Vector(p2); d = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=max(d.length, 1e-3), vertices=verts, location=(p1 + p2) / 2)
    o = bpy.context.object
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = d.to_track_quat("Z", "Y")
    bpy.ops.object.shade_smooth()
    return reg(o, m)

def tube(points, r, m):
    cd = bpy.data.curves.new("c", "CURVE"); cd.dimensions = "3D"
    cd.bevel_depth = r; cd.bevel_resolution = 3; cd.use_fill_caps = True
    sp = cd.splines.new("NURBS"); sp.points.add(len(points) - 1)
    for i, p in enumerate(points): sp.points[i].co = (*p, 1)
    sp.use_endpoint_u = True; sp.order_u = min(4, len(points))
    o = bpy.data.objects.new("c", cd); coll.objects.link(o)
    return reg(o, m)

# ---------------- 齿轮 ----------------
RG, RROOT, NT, TG = 60.0, 52.0, 22, 10.0     # 外径半径、齿根半径、齿数、厚度（mm）
RH, RHUB = 14.0, 24.0                         # 轴孔半径、轮毂半径

def tooth_r(a, R=RG, Rr=RROOT, n=NT):
    ph = (a / (2 * math.pi / n)) % 1.0
    d = abs(ph - 0.5)
    if d < 0.17: return R
    if d > 0.31: return Rr
    return R - (R - Rr) * (d - 0.17) / 0.14

def wavy(y):
    """齿轮与甲虫之间的波浪缝合线：x = wavy(y)。"""
    return 6.0 * math.sin(3.2 * math.pi * abs(y) / RG) - 2.0

def gear_sector(a0, a1, seam=False, steps_per_deg=2):
    """带齿的环形扇区（a0→a1 逆时针），内侧为轴孔弧。seam=True 时两条径向边改为波浪线（只用于 90°–270°）。"""
    pts = []
    n = int(abs(a1 - a0) * 180 / math.pi * steps_per_deg)
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        r = tooth_r(a)
        pts.append((r * math.cos(a), r * math.sin(a)))
    if seam:   # 从下方齿尖沿波浪线回到孔下缘
        for k in range(1, 20):
            y = -RG + (RG - RH) * k / 20
            pts.append((wavy(y), y))
    for k in range(41):   # 轴孔弧，反向
        a = a1 + (a0 - a1) * k / 40
        pts.append((RH * math.cos(a), RH * math.sin(a)))
    if seam:
        for k in range(1, 20):
            y = RH + (RG - RH) * k / 20
            pts.append((wavy(y), y))
    return pts

def hub_ring(a0, a1, z0, z1, m="steel"):
    pts = [(RHUB * math.cos(a0 + (a1 - a0) * k / 60), RHUB * math.sin(a0 + (a1 - a0) * k / 60)) for k in range(61)]
    pts += [(RH * math.cos(a1 + (a0 - a1) * k / 60), RH * math.sin(a1 + (a0 - a1) * k / 60)) for k in range(61)]
    extrude_poly(pts, z0, z1, m, "hub")

def full_gear(z0=0.0):
    extrude_poly(gear_sector(0, math.pi), z0, z0 + TG, "steel", "gear")
    extrude_poly(gear_sector(math.pi, 2 * math.pi), z0, z0 + TG, "steel", "gear")
    hub_ring(0, math.pi, z0 + TG, z0 + TG + 3); hub_ring(math.pi, 2 * math.pi, z0 + TG, z0 + TG + 3)

# ---------------- 甲虫部件 ----------------
GD = 0.9   # 纵纹深度（mm）——是否能在 0.2 mm 层高下保留，待打样

def elytron(x0, L, W, Hm, s, nstr=9):
    """一片鞘翅。x0 为肩部 x，向 -x 延伸 L；s = ±1 为左右。"""
    def P(u, v):
        w = W * (1 - u ** 2.4) ** 0.55 * (0.82 + 0.18 * min(1, u / 0.12))
        x = x0 - L * u
        y = s * (0.6 + v * (w - 0.6))
        crown = (1 - u ** 2.6) ** 0.45 * (0.25 + 0.75 * (1 - (u - 0.35) ** 2))
        z = 1.2 + Hm * crown * (1 - v ** 2.2) ** 0.6
        z -= GD * (0.5 - 0.5 * math.cos(2 * math.pi * v * nstr)) ** 2 * (1 - u ** 4)
        return (x, y, max(z, 0.8))
    return grid_solid(P, 70, 64, "shell", "elytron")

def pronotum(cx, a, b, h, z0=1.0):
    def P(u, v):   # u：半径，v：角度
        r = 0.02 + 0.98 * u; th = 2 * math.pi * v
        # 前缘略凹、后缘平直的盾形
        bb = b * (1 + 0.08 * math.cos(2 * th))
        x = cx + a * r * math.cos(th) * (0.92 if math.cos(th) > 0 else 1.0)
        y = bb * r * math.sin(th)
        z = z0 + h * (1 - r ** 2.2) ** 0.55 + 0.9 * math.exp(-((r - 0.9) / 0.06) ** 2)   # 边缘上卷
        return (x, y, z)
    return grid_solid(P, 30, 72, "shell", "pronotum")

def head(cx, s=1.0):
    ball((cx, 0, 4.5 * s), 1.0, "shell", scale=(8.5 * s, 7.5 * s, 4.8 * s))
    for k in (-1, 1):
        ball((cx + 3.5 * s, k * 6.3 * s, 5.0 * s), 2.6 * s, "eye")
        tube([(cx + 6 * s, k * 3 * s, 3 * s), (cx + 11 * s, k * 4.5 * s, 2.6 * s), (cx + 13 * s, k * 1.2 * s, 2.4 * s)],
             1.1 * s, "limb")   # 上颚
        # 触角：11 节，用小椭球串起来（直径 ≥ 1.6 mm，打印能否成型待测）
        p = Vector((cx + 5 * s, k * 5.5 * s, 6 * s))
        d = Vector((0.75, k * 0.66, 0.08)).normalized()
        for j in range(11):
            q = p + d * 4.2 * s
            ball((p + q) / 2, 1.0, "limb", scale=(2.2 * s, 0.85 * s, 0.85 * s), rot=d.to_track_quat("X", "Z"), seg=12)
            p = q
            d = (d + Vector((0.03, k * 0.07, -0.01))).normalized()

def legs(anchors, s=1.0):
    """anchors: [(x, 方向角偏移)]，每个 x 左右各一条腿：基节→腿节→胫节→跗节（落到 z≈0.8）。"""
    for x, sweep, ln in anchors:
        for k in (-1, 1):
            a = Vector((x, k * 6.0 * s, 3.0 * s))
            b = a + Vector((sweep * 6 * s, k * 13 * s * ln, 4.0 * s))
            c = b + Vector((sweep * 12 * s, k * 12 * s * ln, -5.5 * s))
            d = c + Vector((sweep * 10 * s, k * 5 * s * ln, -0.8 * s))
            rod(a, b, 1.9 * s, "limb"); rod(b, c, 1.5 * s, "limb"); rod(c, d, 1.1 * s, "limb")
            for p in (b, c): ball(p, 2.0 * s if p is b else 1.6 * s, "limb", seg=12)
            # 跗节小球 + 爪
            for j in range(4):
                ball(d + Vector((sweep * 2.2, k * 0.9, 0)) * j * s, 1.0 * s, "limb", seg=10)
            # 胫节上的刺（加粗处理，原型可省略）
            for j in range(3):
                t = 0.3 + 0.25 * j
                p = b + (c - b) * t
                rod(p, p + Vector((sweep * 1.5, k * 1.6, 1.2)) * s, 0.45 * s, "limb", 6)

def beetle(x_shoulder=0.0, L=68.0, W=22.0, Hm=15.0, with_tip_gear=False):
    for s in (-1, 1):
        elytron(x_shoulder, L, W, Hm, s)
    rod((x_shoulder, 0, 1.2), (x_shoulder - L * 0.97, 0, 1.2), 0.6, "shell", 8)   # 鞘翅缝
    pronotum(x_shoulder + 12.0, 13.0, 15.0, 9.0)
    rod((x_shoulder + 1, 0, 3), (x_shoulder + 3, 0, 3), 6, "shell")               # 胸腰
    head(x_shoulder + 31.0)
    legs([(x_shoulder + 18, 1.0, 1.0), (x_shoulder + 6, 0.2, 1.05), (x_shoulder - 8, -0.8, 1.15)])
    if with_tip_gear:   # 鞘翅末端长出一段齿轮弧
        tip = x_shoulder - L
        C = Vector((tip + 18.0, 0))
        R, Rr, n = 21.5, 18.5, 26
        pts = [(C.x, C.y)]
        a0, a1 = math.pi - 0.62, math.pi + 0.62
        for k in range(121):
            a = a0 + (a1 - a0) * k / 120
            r = tooth_r(a, R, Rr, n)
            pts.append((C.x + r * math.cos(a), C.y + r * math.sin(a)))
        extrude_poly(pts, 0.0, 5.5, "steel", "tipgear")

# ---------------- 五件 ----------------
def piece_0():   # 纯齿轮
    full_gear()

def piece_1():   # 齿轮上嵌一块甲壳：扇区内的纹沿齿轮圆周走
    full_gear()
    a0, a1, r0, r1 = math.radians(18), math.radians(72), 30.0, 49.0
    def P(u, v):
        r = r0 + (r1 - r0) * u; a = a0 + (a1 - a0) * v
        dome = math.sin(math.pi * u) ** 0.5 * math.sin(math.pi * v) ** 0.5
        z = TG + 0.4 + 1.6 * dome - GD * 0.8 * (0.5 - 0.5 * math.cos(2 * math.pi * u * 7)) ** 2
        return (r * math.cos(a), r * math.sin(a), z)
    grid_solid(P, 56, 40, "shell", "inlay", zb=lambda u, v: TG - 1.5)

def piece_2():   # 半齿轮半甲虫：鞘翅从前胸呈扇形放射，外缘贴着齿轮的波浪缝
    extrude_poly(gear_sector(math.pi / 2, 3 * math.pi / 2, seam=True), 0, TG, "steel", "halfgear")
    hub_ring(math.pi / 2, 3 * math.pi / 2, TG, TG + 3)
    apex = Vector((58.0, 0.0))
    span = math.radians(44)
    def seam_dist(phi):
        d = 50.0
        for _ in range(6):
            y = d * math.sin(phi)
            d = (apex.x - wavy(y)) / -math.cos(phi)
        return d
    for side in (-1, 1):   # 两片“鞘翅”扇面，中缝在 phi = π
        def P(u, v, side=side):
            phi = math.pi + side * span * v
            d = seam_dist(phi) - 0.6
            r = 6.0 + (d - 6.0) * u
            x, y = apex.x + r * math.cos(phi), apex.y + r * math.sin(phi)
            z = 1.0 + (TG + 6.5) * (0.35 + 0.65 * math.sin(math.pi * (0.15 + 0.7 * u))) * (1 - v ** 3) ** 0.5
            z -= GD * (0.5 - 0.5 * math.cos(2 * math.pi * v * 10)) ** 2 * min(1, u * 4)
            return (x, y, max(z, TG * 0.9 if u > 0.97 else 1.0))
        grid_solid(P, 60, 60, "shell", "fan")
    pronotum(apex.x + 8.0, 12.0, 14.0, 8.5, z0=2.0)
    head(apex.x + 27.0)
    legs([(apex.x + 14, 1.0, 1.0), (apex.x + 4, 0.3, 1.05), (apex.x - 8, -0.6, 1.1)])

def piece_3():   # 甲虫，鞘翅末端露出齿
    beetle(x_shoulder=22.0, with_tip_gear=True)

def piece_4():   # 纯甲虫
    beetle(x_shoulder=22.0)

STEPS = [("0", piece_0), ("1", piece_1), ("2", piece_2), ("3", piece_3), ("4", piece_4)]
GAP = 175.0
for i, (name, fn) in enumerate(STEPS):
    CUR[0] = name
    fn()
    for o in PIECE[name]:
        o.location.x += (i - 2) * GAP

# 缩到米，按件合并（每件两种材料各一个对象，便于以后分色打印）
for o in [o for objs in PIECE.values() for o in objs]:
    o.location *= 0.001; o.scale *= 0.001
bpy.context.view_layer.update()
for name, objs in PIECE.items():
    by_m = {}
    for o in objs:
        if o.type == "CURVE":
            bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.convert(target="MESH")
            o = bpy.context.object
        by_m.setdefault(o.data.materials[0].name, []).append(o)
    for mname, os_ in by_m.items():
        bpy.ops.object.select_all(action="DESELECT")
        for o in os_: o.select_set(True)
        bpy.context.view_layer.objects.active = os_[0]
        bpy.ops.object.join()
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        bpy.context.object.name = f"step{name}_{mname}"

bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))
p = bpy.context.object; p.data.materials.append(M["floor"])

# 标签
font = None
for fp in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
    try: font = bpy.data.fonts.load(fp); break
    except Exception: pass
labels = []
for i, txt in enumerate(["0  齿轮", "1  嵌入甲壳", "2  半齿半虫", "3  鞘翅长齿", "4  甲虫"]):
    cu = bpy.data.curves.new("lbl", "FONT"); cu.body = txt; cu.size = 0.013; cu.align_x = "CENTER"
    if font: cu.font = font
    o = bpy.data.objects.new("label", cu); coll.objects.link(o)
    o.location = ((i - 2) * GAP * 0.001, -0.095, 0.0003)
    cu.materials.append(M["label"]); labels.append(o)

# ---------------- 灯光与渲染 ----------------
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: scn.render.engine = eng; break
    except TypeError: pass
world = bpy.data.worlds.new("w"); scn.world = world; world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.5, 0.5, 0.52, 1); bg.inputs[1].default_value = 0.08
def light(loc, energy, size, target=(0, 0, 0)):
    ld = bpy.data.lights.new("l", "AREA"); ld.energy = energy; ld.size = size
    o = bpy.data.objects.new("l", ld); coll.objects.link(o); o.location = loc
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
light((-0.6, -0.5, 0.9), 14, 0.8)
light((0.7, 0.3, 0.5), 5, 0.6)
light((0.0, 0.8, 0.6), 7, 1.0)
scn.render.resolution_x, scn.render.resolution_y = 1800, 700
try: scn.eevee.taa_render_samples = 48
except Exception: pass
vt = [i.identifier for i in scn.view_settings.bl_rna.properties["view_transform"].enum_items]
scn.view_settings.view_transform = "AgX" if "AgX" in vt else "Standard"

cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data)
coll.objects.link(cam); scn.camera = cam
def shoot(name, loc, target, lens, res=None):
    if res: scn.render.resolution_x, scn.render.resolution_y = res
    cam.location = loc; cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y"); cam_data.lens = lens
    bpy.context.view_layer.update()
    scn.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True); print("rendered", scn.render.filepath)

shoot("morph_row", (0.0, -0.95, 0.65), (0.0, -0.01, 0.0), 34)
shoot("morph_top", (0.0, -0.02, 1.05), (0.0, -0.01, 0.0), 40)
for o in labels: o.hide_render = True
for i in range(5):
    x = (i - 2) * GAP * 0.001
    shoot(f"morph_step{i}", (x + 0.13, -0.17, 0.17), (x, 0, 0.006), 50, res=(1000, 1000))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "morph_gear_beetle.blend"))
print("saved")
