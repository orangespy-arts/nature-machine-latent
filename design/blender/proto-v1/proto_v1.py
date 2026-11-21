# 落地装置原型 v1 体块草图（尺寸为占位值，待实测）
import bpy, math, random, sys, os
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
col_main = scn.collection

def mat(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = rgba
    return m

M = {
    "steel": mat("steel", (0.33, 0.33, 0.35, 1)),
    "clamp": mat("clamp", (0.22, 0.18, 0.16, 1)),
    "pla": mat("pla", (0.93, 0.89, 0.80, 1)),
    "brass": mat("brass", (0.80, 0.60, 0.25, 1)),
    "wing": mat("wing", (0.95, 0.80, 0.55, 1)),
    "pot": mat("pot", (0.70, 0.40, 0.28, 1)),
    "soil": mat("soil", (0.20, 0.14, 0.10, 1)),
    "leaf": mat("leaf", (0.30, 0.55, 0.25, 1)),
    "sensor": mat("sensor", (0.15, 0.45, 0.75, 1)),
    "elec": mat("elec", (0.10, 0.35, 0.30, 1)),
    "cable": mat("cable", (0.85, 0.15, 0.12, 1)),
    "speaker": mat("speaker", (0.12, 0.12, 0.12, 1)),
    "person": mat("person", (0.75, 0.75, 0.78, 1)),
    "floor": mat("floor", (0.62, 0.62, 0.60, 1)),
    "label": mat("label", (0.05, 0.05, 0.05, 1)),
}

def put(obj, m, name=None):
    obj.data.materials.clear()
    obj.data.materials.append(M[m])
    obj.color = M[m].diffuse_color
    if name: obj.name = name
    return obj

def rod(p1, p2, r, m, name=None):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, vertices=24, location=(p1 + p2) / 2)
    o = bpy.context.object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("Z", "Y")
    return put(o, m, name)

def box(loc, size, m, name=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = size
    return put(o, m, name)

def ellip(loc, size, m, name=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=24, ring_count=12, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = size
    bpy.ops.object.shade_smooth()
    return put(o, m, name)

def curve(points, r, m, name=None):
    cd = bpy.data.curves.new(name or "curve", "CURVE")
    cd.dimensions = "3D"
    cd.bevel_depth = r
    cd.bevel_resolution = 3
    sp = cd.splines.new("NURBS")
    sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        sp.points[i].co = (*p, 1)
    sp.use_endpoint_u = True
    sp.order_u = min(4, len(points))
    o = bpy.data.objects.new(name or "curve", cd)
    col_main.objects.link(o)
    cd.materials.append(M[m])
    o.color = M[m].diffuse_color
    return o

# ---------- 钢架（占位尺寸：宽 0.80 × 深 0.45 × 高 1.10 m，杆径 16 mm） ----------
W, D, H, ZL = 0.80, 0.45, 1.10, 0.40
R = 0.008
xs, ys = (-W / 2, W / 2), (-D / 2, D / 2)
for x in xs:
    for y in ys:
        rod((x, y, 0.0), (x, y, H + 0.04), R, "steel", "frame_leg")
for z in (ZL, H):
    for y in ys:
        rod((-W / 2 - 0.03, y, z), (W / 2 + 0.03, y, z), R, "steel", "frame_rail_x")
    for x in xs:
        rod((x, -D / 2 - 0.03, z + 0.025), (x, D / 2 + 0.03, z + 0.025), R, "steel", "frame_rail_y")
    for x in xs:
        for y in ys:
            rod((x - 0.022, y, z), (x + 0.022, y, z), 0.02, "clamp", "frame_clamp")
            rod((x, y - 0.022, z + 0.025), (x, y + 0.022, z + 0.025), 0.02, "clamp", "frame_clamp")

# ---------- 地面 ----------
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))
put(bpy.context.object, "floor", "floor")

# ---------- 花盆与植物（花盆放地面，植物从框架中间长出） ----------
bpy.ops.mesh.primitive_cone_add(radius1=0.12, radius2=0.16, depth=0.28, vertices=48, location=(0, 0.02, 0.14))
put(bpy.context.object, "pot", "pot")
bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=0.01, vertices=48, location=(0, 0.02, 0.265))
put(bpy.context.object, "soil", "soil")
random.seed(3)
for i in range(7):
    a = random.uniform(0, 2 * math.pi)
    base = Vector((0.04 * math.cos(a), 0.02 + 0.04 * math.sin(a), 0.27))
    top = Vector((0.22 * math.cos(a), 0.02 + 0.15 * math.sin(a), random.uniform(0.85, 1.35)))
    mid = (base + top) / 2 + Vector((0, 0, 0.05))
    curve([base, mid, top], 0.005, "leaf", "plant_stem")
    for t in (0.45, 0.65, 0.85, 1.0):
        p = base.lerp(top, t)
        ellip(p, (0.06, 0.025, 0.006), "leaf", "plant_leaf",
              rot=(random.uniform(-0.5, 0.5), random.uniform(-0.6, 0.6), a + random.uniform(-0.8, 0.8)))

# ---------- 土壤湿度传感器 ----------
box((0.10, -0.05, 0.25), (0.022, 0.004, 0.10), "sensor", "soil_sensor")
box((0.10, -0.05, 0.31), (0.024, 0.012, 0.025), "sensor", "soil_sensor_head")

# ---------- 胸／齿轮（夹在前横杆上，可转） ----------
gx, gy = -0.12, -D / 2
rod((gx - 0.03, gy, H), (gx + 0.03, gy, H), 0.019, "pla", "thorax_clamp")
box((gx, gy - 0.02, H - 0.07), (0.10, 0.04, 0.12), "pla", "thorax_housing")
gear_c = Vector((gx, gy - 0.05, H - 0.08))
rod(gear_c - Vector((0, 0.006, 0)), gear_c + Vector((0, 0.006, 0)), 0.065, "brass", "gear")
for k in range(24):
    a = 2 * math.pi * k / 24
    box(gear_c + Vector((0.07 * math.cos(a), 0, 0.07 * math.sin(a))), (0.012, 0.012, 0.010), "brass", "gear_tooth",
        rot=(0, -a, 0))
rod(gear_c + Vector((0.045, -0.006, 0)), gear_c + Vector((0.045, -0.04, 0)), 0.007, "pla", "gear_handle")

# ---------- 头（前左角，外壳可放 Arduino；触角） ----------
hx, hy = -W / 2 - 0.02, -D / 2 - 0.06
ellip((hx, hy, H + 0.05), (0.08, 0.10, 0.07), "pla", "head", rot=(0.3, 0, 0.6))
for s in (-1, 1):
    curve([(hx, hy - 0.03, H + 0.10), (hx + 0.05 * s, hy - 0.10, H + 0.30), (hx + 0.12 * s, hy - 0.05, H + 0.45)],
          0.003, "brass", "antenna")

# ---------- 翅（夹在前横杆右段，压电片在翅根） ----------
wx = 0.22
rod((wx - 0.03, -D / 2, H), (wx + 0.03, -D / 2, H), 0.019, "pla", "wing_clamp")
box((wx, -D / 2 - 0.02, H + 0.03), (0.025, 0.012, 0.03), "sensor", "wing_piezo")
for s in (-1, 1):
    ellip((wx + 0.15 * s, -D / 2 - 0.03, H + 0.18), (0.20, 0.004, 0.07), "wing", "wing",
          rot=(0, s * -0.7, 0))

# ---------- 腹节（挂在右侧横杆，向下弯向植物；内部放弯曲传感器） ----------
pts = [Vector((W / 2, 0.0, H)), Vector((0.36, -0.05, 0.92)), Vector((0.28, -0.04, 0.75)), Vector((0.18, 0.0, 0.62))]
rod((W / 2, -0.03, H + 0.025), (W / 2, 0.03, H + 0.025), 0.019, "pla", "abdomen_clamp")
n = 10
def bez(t):
    a, b, c, d = pts
    return a * (1 - t) ** 3 + b * 3 * t * (1 - t) ** 2 + c * 3 * t ** 2 * (1 - t) + d * t ** 3
for i in range(n):
    t = (i + 0.5) / n
    p, q = bez(t - 0.03), bez(t + 0.03)
    r = 0.045 - 0.025 * t
    rod(p, q, r, "pla", "abdomen_segment")

# ---------- 电子盒（后横杆） ----------
box((0.0, D / 2 + 0.04, H - 0.05), (0.12, 0.05, 0.08), "elec", "arduino_box")

# ---------- 线缆（示意） ----------
eb = Vector((0.0, D / 2 + 0.02, H - 0.05))
curve([(0.10, -0.05, 0.33), (0.10, 0.10, 0.6), eb], 0.003, "cable", "cable_soil")
curve([gear_c + Vector((0, 0.06, 0.04)), (gx, 0.0, H + 0.02), eb], 0.003, "cable", "cable_gear")
curve([(wx, -D / 2, H + 0.02), (wx, 0.0, H + 0.03), eb], 0.003, "cable", "cable_wing")
curve([(W / 2, 0.0, H - 0.02), (0.3, 0.15, H - 0.04), eb], 0.003, "cable", "cable_abdomen")
curve([eb + Vector((0, 0.03, -0.04)), (0.1, 0.5, 0.3), (0.6, 0.9, 0.01)], 0.004, "cable", "cable_to_mac")

# ---------- 外部扬声器（示意，立在地上） ----------
for s in (-1, 1):
    rod((s * 1.05, -0.35, 0), (s * 1.05, -0.35, 1.0), 0.012, "steel", "speaker_stand")
    box((s * 1.05, -0.35, 1.13), (0.18, 0.18, 0.28), "speaker", "speaker", rot=(0, 0, -s * 0.35))

# ---------- 人形比例参照（1.70 m） ----------
rod((-1.35, -0.3, 0), (-1.35, -0.3, 1.45), 0.13, "person", "person_body")
ellip((-1.35, -0.3, 1.58), (0.1, 0.1, 0.12), "person", "person_head")

# ---------- 标注 ----------
font = None
for fp in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
    try:
        font = bpy.data.fonts.load(fp); break
    except Exception as e:
        print("font fail", fp, e)

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
col_main.objects.link(cam)
scn.camera = cam

LABELS = [
    ("齿轮：转（AS5600）", gear_c + Vector((-0.10, -0.12, -0.12))),
    ("翅：拨／敲（压电片）", Vector((wx + 0.05, -D / 2 - 0.1, H + 0.33))),
    ("腹节：弯（弯曲传感器）", Vector((0.55, -0.15, 0.70))),
    ("头：外壳／触角", Vector((hx - 0.05, hy - 0.1, H + 0.55))),
    ("土壤湿度传感器", Vector((0.18, -0.30, 0.38))),
    ("花盆（地面）", Vector((-0.30, -0.30, 0.10))),
    ("电子盒→Mac", Vector((0.0, D / 2 + 0.1, H + 0.15))),
    ("外部扬声器", Vector((1.05, -0.45, 1.40))),
    ("1.70 m 参照", Vector((-1.35, -0.3, 1.80))),
]
for txt, loc in LABELS:
    cu = bpy.data.curves.new("lbl", "FONT")
    cu.body = txt
    cu.size = 0.045
    cu.align_x = "CENTER"
    if font: cu.font = font
    o = bpy.data.objects.new("label_" + txt, cu)
    col_main.objects.link(o)
    o.location = loc
    cu.materials.append(M["label"])
    o.color = M["label"].diffuse_color
    c = o.constraints.new("TRACK_TO")
    c.target = cam
    c.track_axis = "TRACK_Z"
    c.up_axis = "UP_Y"

# ---------- 渲染设置 ----------
scn.render.engine = "BLENDER_WORKBENCH"
sh = scn.display.shading
sh.light = "STUDIO"
sh.color_type = "OBJECT"
sh.show_shadows = False
sh.show_cavity = True
sh.show_object_outline = True
scn.render.resolution_x, scn.render.resolution_y = 1400, 1000
scn.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w"); scn.world = world
world.color = (0.96, 0.95, 0.93)

def shoot(name, loc, target, lens=35, hide_people=False):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = d.to_track_quat("-Z", "Y")
    cam_data.lens = lens
    for o in bpy.data.objects:
        if o.name.startswith("person"):
            o.hide_render = hide_people
    bpy.context.view_layer.update()
    scn.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", scn.render.filepath)

shoot("v1_front34", (1.9, -2.9, 1.7), (0.1, -0.1, 0.75), 30)
shoot("v1_front", (0, -3.4, 1.1), (0, 0, 0.75), 32)
shoot("v1_side", (3.2, 0.2, 1.15), (0, 0, 0.75), 32)
shoot("v1_detail", (0.9, -1.35, 1.55), (0.05, -0.1, 1.0), 35, hide_people=True)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "proto_v1.blend"))
print("saved")
