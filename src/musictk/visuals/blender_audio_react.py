# Run inside Blender:  blender -b scene.blend -P blender_audio_react.py -- audio.pcm out.blend
# 音に反応する Blender の見本: 曲を 1 コマずつ分析（全体の音量・低音・高音）して、明かりや物の大きさにキーを打つ
import bpy, sys, numpy as np
pcm, out = sys.argv[-2], sys.argv[-1]
FPS, SR = 30, 48000
x = np.fromfile(pcm, dtype=np.int16).astype(np.float32) / 32768
hop = SR // FPS; n = len(x) // hop
win = np.hanning(2048)
def band(spec, f0, f1): fr = np.fft.rfftfreq(2048, 1 / SR); return spec[(fr >= f0) & (fr < f1)].mean()
feat = []
for i in range(n):
    seg = x[i * hop: i * hop + 2048]
    if len(seg) < 2048: seg = np.pad(seg, (0, 2048 - len(seg)))
    sp = np.abs(np.fft.rfft(seg * win))
    feat.append((np.sqrt((seg ** 2).mean()), band(sp, 30, 150), band(sp, 4000, 12000)))
f = np.array(feat); f = f / (f.max(axis=0) + 1e-9)
# 少しなめらかに（立ち上がりは速く、消えるのはゆっくり）
for j in range(3):
    for i in range(1, n): f[i, j] = max(f[i, j], f[i - 1, j] * 0.82)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE'; sc.render.fps = FPS; sc.frame_start, sc.frame_end = 1, n
sc.render.resolution_x, sc.render.resolution_y = 540, 960
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.01, 0.012, 0.02, 1)
def emis(name, col):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*col, 1); nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs[0]); return m, e
# 床
bpy.ops.mesh.primitive_plane_add(size=20); fl = bpy.context.object
fm = bpy.data.materials.new("floor"); fm.use_nodes = True; b = fm.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.05, 0.05, 0.06, 1); b.inputs["Roughness"].default_value = 0.15; fl.data.materials.append(fm)
# スピーカーのコーン（低音で前後に動く）・画面（音量で明るさ）・LED の棒（高音で伸びる）
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.6, depth=0.2, location=(-1.2, 0, 1.2), rotation=(1.5708, 0, 0)); cone = bpy.context.object
cm, ce = emis("cone", (1.0, 0.35, 0.15)); cone.data.materials.append(cm)
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.0, 0, 1.4)); scr = bpy.context.object; scr.scale = (1.2, 0.1, 0.9)
sm, se = emis("screen", (0.25, 0.6, 1.0)); scr.data.materials.append(sm)
bars = []
for k in range(8):
    bpy.ops.mesh.primitive_cube_add(size=0.12, location=(-0.55 + k * 0.16, 0, 0.3)); bb = bpy.context.object
    bm, be = emis(f"bar{k}", (0.3, 1.0, 0.5)); bb.data.materials.append(bm); bars.append((bb, be, k))
bpy.ops.object.light_add(type='POINT', location=(0, -1.5, 2.5)); L = bpy.context.object; L.data.color = (1, 0.6, 0.4)
bpy.ops.object.camera_add(location=(0, -6.5, 1.6), rotation=(1.47, 0, 0)); sc.camera = bpy.context.object
rng = np.random.default_rng(3)
for i in range(n):
    fr = i + 1; vol, lo, hi = f[i]
    cone.scale = (1, 1, 1 + lo * 2.5); cone.keyframe_insert("scale", frame=fr)
    ce.inputs[1].default_value = 0.5 + lo * 12; ce.inputs[1].keyframe_insert("default_value", frame=fr)
    se.inputs[1].default_value = 0.4 + vol * 6; se.inputs[1].keyframe_insert("default_value", frame=fr)
    L.data.energy = 50 + lo * 900; L.data.keyframe_insert("energy", frame=fr)
    for bb, be, k in bars:
        h = max(0.05, hi * (1.2 + 0.6 * np.sin(k * 1.7 + i * 0.4)) * 2.0)
        bb.scale = (1, 1, h * 8); bb.location.z = 0.06 * h * 8 + 0.02
        bb.keyframe_insert("scale", frame=fr); bb.keyframe_insert("location", frame=fr)
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = out + '/f_####'  # 連番の画像に書いて、あとで ffmpeg で動画にする
bpy.ops.render.render(animation=True)
print("FRAMES", n)
