# -*- coding: utf-8 -*-
"""
NÚCLEO DO GERADOR (roda dentro do Blender):
  blender -b -P nucleo_blender.py -- <projeto.json> <pasta_saida>

Usa o manequim da Giovanna como CORPO-BASE e o deforma para as medidas do projeto:
  - alturas: cada altura do corpo-base é levada para a altura correspondente da pessoa
    (gancho, quadril, pequeno quadril, cintura, busto, cava, jugular, ombro, 7ª cervical...);
  - larguras: proporção inicial pelos contornos e depois calibração automática até bater
    busto, cintura, pequeno quadril, quadril, pescoço, coxa, joelho, panturrilha, tornozelo,
    braço, cotovelo e pulso.
O corpo é um campo de distância com união suave (OpenVDB), sem degraus entre tronco e pernas.
Unidades: modelagem em cm reais; saída em mm na escala do projeto.
"""
import bpy, bmesh, math, os, sys, json, time
import numpy as np
from mathutils import Matrix, Vector

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PROJ = json.load(open(ARGV[0], encoding="utf-8"))
OUT = ARGV[1]
os.makedirs(OUT, exist_ok=True)

ESC = PROJ["esc_mm_por_cm"]      # cm real -> mm no modelo
VOX = 0.25
SMOOTH_IT = 50
NRING = 128
T0 = time.time()
ALVO = PROJ["alvos"]
LM = PROJ["landmarks"]
COM_BRACO = PROJ["com_braco"]

def log(*a):
    print("[%6.1fs]" % (time.time() - T0), *a, flush=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpo as _corpo
globals().update(_corpo.preparar(PROJ))

log("projeto", PROJ["nome"], "escala 1:%g" % PROJ["escala"], "razões Q %.3f C %.3f B %.3f N %.3f ombro %.3f"
    % (R_Q, R_C, R_B, R_N, R_SH))

# --------------------------------------------------------------------------
# utilidades numéricas
# --------------------------------------------------------------------------
def pchip(x, y, xq):
    x = np.asarray(x, float); y = np.asarray(y, float); xq = np.asarray(xq, float)
    h = np.diff(x); d = np.diff(y) / h; n = len(x); m = np.zeros(n)
    for k in range(1, n - 1):
        if d[k - 1] * d[k] > 0:
            w1 = 2 * h[k] + h[k - 1]; w2 = h[k] + 2 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / d[k - 1] + w2 / d[k])
    m[0] = d[0] if n > 2 and d[0] * d[1] > 0 else 0.0
    m[-1] = d[-1] if n > 2 and d[-1] * d[-2] > 0 else 0.0
    idx = np.clip(np.searchsorted(x, xq) - 1, 0, n - 2)
    t = (xq - x[idx]) / h[idx]; hh = h[idx]
    h00 = 2*t**3 - 3*t**2 + 1; h10 = t**3 - 2*t**2 + t; h01 = -2*t**3 + 3*t**2; h11 = t**3 - t**2
    return h00*y[idx] + h10*hh*m[idx] + h01*y[idx+1] + h11*hh*m[idx+1]

TH = np.linspace(0, 2*np.pi, NRING, endpoint=False)

def superelipse(a, bf, bb, n):
    c = np.cos(TH); s = np.sin(TH)
    x = a * np.sign(c) * np.abs(c) ** (2.0 / n)
    b = np.where(s > 0, bf, bb)
    y = b * np.sign(s) * np.abs(s) ** (2.0 / n)
    return x, y

def loft(rings):
    """rings: lista de arrays (N,3). Retorna (verts, faces) fechado com tampas."""
    R = len(rings); N = rings[0].shape[0]
    V = np.vstack(rings + [rings[0].mean(0, keepdims=True), rings[-1].mean(0, keepdims=True)])
    F = []
    for i in range(R - 1):
        for j in range(N):
            F.append((i*N + j, i*N + (j+1) % N, (i+1)*N + (j+1) % N, (i+1)*N + j))
    c0 = R*N; c1 = R*N + 1; base = (R-1)*N
    for j in range(N):
        F.append((c0, (j+1) % N, j))
        F.append((c1, base + j, base + (j+1) % N))
    return V, F

def signed_volume(V, faces):
    vol = 0.0
    for f in faces:
        p0 = V[f[0]]
        for k in range(1, len(f) - 1):
            vol += np.dot(p0, np.cross(V[f[k]], V[f[k+1]]))
    return vol / 6.0

def orient(V, faces):
    if signed_volume(V, faces) < 0:
        faces = [tuple(reversed(f)) for f in faces]
    return V, faces

def combine(parts):
    Vs = []; Fs = []; off = 0
    for V, F in parts:
        Vs.append(V); Fs += [tuple(i + off for i in f) for f in F]; off += len(V)
    return np.vstack(Vs), Fs

def make_obj(name, V, F):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in V], [], [tuple(map(int, f)) for f in F])
    me.validate(); me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob

def delete(ob):
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if isinstance(me, bpy.types.Mesh) and me.users == 0:
        bpy.data.meshes.remove(me)

def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)

def remesh_smooth(ob, voxel=VOX, iters=SMOOTH_IT, factor=0.5):
    m = ob.modifiers.new("rm", "REMESH"); m.mode = "VOXEL"; m.voxel_size = voxel
    if iters > 0:
        s = ob.modifiers.new("sm", "SMOOTH"); s.factor = factor; s.iterations = iters
    apply_mods(ob)

def boolean(ob, cutter, op):
    for solver in ("MANIFOLD", "EXACT"):
        backup = ob.data.copy()
        m = ob.modifiers.new("b", "BOOLEAN"); m.operation = op; m.object = cutter; m.solver = solver
        apply_mods(ob)
        if len(ob.data.polygons) > 0:
            bpy.data.meshes.remove(backup)
            return
        log("  boolean %s vazio com %s, tentando de novo" % (op, solver))
        old = ob.data; ob.data = backup; bpy.data.meshes.remove(old)
    raise RuntimeError("boolean falhou")

def arrays(ob):
    me = ob.data
    V = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", V)
    E = np.empty(len(me.edges) * 2, dtype=np.int32); me.edges.foreach_get("vertices", E)
    return V.reshape(-1, 3), E.reshape(-1, 2)

def section(V, E, p, n):
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    d = (V - np.asarray(p, float)) @ n
    a = d[E[:, 0]]; b = d[E[:, 1]]
    m = (a * b) < 0
    t = a[m] / (a[m] - b[m])
    return V[E[m, 0]] + (V[E[m, 1]] - V[E[m, 0]]) * t[:, None]

def hull_perim(P2):
    pts = np.unique(np.round(P2, 6), axis=0)
    if len(pts) < 3:
        return 0.0
    pts = sorted(map(tuple, pts))
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo = []; up = []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    h = np.array(lo[:-1] + up[:-1])
    return float(np.sum(np.linalg.norm(np.roll(h, -1, 0) - h, axis=1)))



def caixa(xmin, xmax, ymin, ymax, zmin, zmax):
    V = np.array([[x, y, z] for z in (zmin, zmax) for y in (ymin, ymax) for x in (xmin, xmax)], float)
    F = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    return orient(V, F)

def prisma_cava(lado, zmin, zmax, xlong=80.0, recuo=0.0):
    s = -1 if lado == "D" else 1
    pts = [(xplano(zmin) + recuo, zmin), (-xlong, zmin), (-xlong, zmax), (xplano(zmax) + recuo, zmax)]
    V = []
    for y in (-40.0, 40.0):
        for x, z in pts:
            V.append([x if s < 0 else -x, y, z])
    V = np.array(V)
    F = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return orient(V, F)

def caixa_orientada(c, u, v, t, hu, hv, ht):
    V = np.array([c + su*hu*u + sv*hv*v + st*ht*t for st in (-1, 1) for sv in (-1, 1) for su in (-1, 1)])
    F = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    return orient(V, F)

def cilindro(p0, p1, r, n=48):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    t = p1 - p0; t /= np.linalg.norm(t)
    a = np.array([1.0, 0, 0]) if abs(t[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(t, a); u /= np.linalg.norm(u); v = np.cross(t, u)
    th = np.linspace(0, 2*np.pi, n, endpoint=False)
    ring = np.outer(r*np.cos(th), u) + np.outer(r*np.sin(th), v)
    return orient(*loft([p0 + ring, p1 + ring]))

def cortar(ob, cutters, op="DIFFERENCE"):
    for i, (V, F) in enumerate(cutters):
        c = make_obj("cut%d" % i, V, F)
        boolean(ob, c, op)
        delete(c)

# --------------------------------------------------------------------------
# STL
# --------------------------------------------------------------------------
def write_stl(ob, path, chao=True):
    me = ob.data; me.calc_loop_triangles()
    V = np.empty(len(me.vertices)*3, np.float64); me.vertices.foreach_get("co", V); V = V.reshape(-1, 3)
    T = np.empty(len(me.loop_triangles)*3, np.int32); me.loop_triangles.foreach_get("vertices", T); T = T.reshape(-1, 3)
    if chao:
        V = V - np.array([0, 0, V[:, 2].min()])
    tri = V[T]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
    rec = np.zeros(len(T), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"] = n; rec["v"] = tri
    with open(path, "wb") as f:
        f.write(("Manequim " + PROJ["nome"]).encode("ascii", "ignore")[:70].ljust(80, b" "))
        f.write(np.uint32(len(T)).tobytes()); f.write(rec.tobytes())
    return len(T)

def checar(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    nm = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume(signed=True)
    bm.free()
    return nm, vol



# ==========================================================================
# CONSTRUÇÃO
# ==========================================================================
def braco_caminho(s):
    d1 = np.array([-math.sin(ABDUCAO), 0.0, -math.cos(ABDUCAO)])
    d2 = d1 * math.cos(FLEXAO) + np.array([0, 1.0, 0]) * math.sin(FLEXAO)
    w = np.clip((s - S_FLEX0) / (S_FLEX1 - S_FLEX0), 0, 1); w = w*w*(3 - 2*w)
    t = (1 - w)[:, None] * d1 + w[:, None] * d2
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    Pp = np.zeros((len(s), 3))
    for i in range(1, len(s)):
        Pp[i] = Pp[i-1] + 0.5 * (t[i] + t[i-1]) * (s[i] - s[i-1])
    i0 = np.argmin(np.abs(s))
    Pp += BRACO_P0 - Pp[i0]
    return Pp, t

def braco_frame(t):
    u = np.cross(t, [0, 1.0, 0]); u /= np.linalg.norm(u)
    v = np.cross(t, u); v /= np.linalg.norm(v)
    return u, v

def build_braco(Bq):
    ss = np.arange(Bq[0, 0], Bq[-1, 0] + 1e-6, 0.4)
    Pp, t = braco_caminho(ss)
    a = pchip(Bq[:, 0], Bq[:, 1], ss); b = pchip(Bq[:, 0], Bq[:, 2], ss)
    rings = []
    for i in range(len(ss)):
        u, v = braco_frame(t[i])
        rings.append(Pp[i] + np.outer(a[i]*np.cos(TH), u) + np.outer(b[i]*np.sin(TH), v))
    return orient(*loft(rings))

def braco_ponto(s):
    ss = np.arange(-3.0, float(B[-1, 0]) + 1e-6, 0.1)
    Pp, t = braco_caminho(ss)
    i = np.argmin(np.abs(ss - s))
    return Pp[i], t[i]

H_SDF = 0.2

def sdf_corpo(T, P, S, G):
    import openvdb as vdb
    arr, xs, ys, zs = _corpo.campo(globals(), T, P, S, G, H_SDF)
    g = vdb.FloatGrid(1e3)
    g.copyFromArray(arr)
    g.transform = vdb.createLinearTransform(voxelSize=H_SDF)
    pts, quads = g.convertToQuads(0.0)
    pts = np.asarray(pts, float) + np.array([xs[0], ys[0], zs[0]])
    return pts, np.asarray(quads)

def build_corpo(T, P, S, G):
    V, Q = sdf_corpo(T, P, S, G)
    ob = make_obj("corpo", V, [tuple(q) for q in Q])
    s = ob.modifiers.new("sm", "SMOOTH"); s.factor = 0.5; s.iterations = 20
    apply_mods(ob)
    return ob

# ==========================================================================
# MEDIÇÕES
# ==========================================================================
def gancho(V, E):
    Pt = section(V, E, (0, 0, 0), (1, 0, 0))
    Pt = Pt[(Pt[:, 2] <= Z_CINTURA) & (Pt[:, 2] >= Z_GANCHO - 2.0)]
    y = Pt[:, 1]; z = Pt[:, 2]
    cy, cz = -0.5, mz(97.0)
    ang = np.degrees(np.arctan2(z - cz, y - cy))
    ang = np.where(ang > 90, ang - 360, ang)
    r = np.hypot(y - cy, z - cz)
    bins = np.floor(ang).astype(int)
    pts = []
    for bnum in np.unique(bins):
        m = bins == bnum
        k = np.argmax(r[m])
        pts.append((ang[m][k], y[m][k], z[m][k]))
    pts.sort(key=lambda p: -p[0])
    pts = np.array([[p[1], p[2]] for p in pts])
    return float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))

MED_TRONCO = {"busto": Z_BUSTO, "cintura": Z_CINTURA, "peq_quadril": Z_PEQ_Q,
              "quadril": Z_QUADRIL, "pescoco": Z_PESCOCO}
_PN = {"coxa": 77.0, "meia_coxa": 60.0, "joelho": 46.8, "panturrilha": 34.0, "canela": 15.0, "tornozelo": 9.0}
MED_PERNA = {k: (mz(10.0 if k == "tornozelo" else tz), ALVO[k]) for k, tz in _PN.items()}
MED_PERNA_ANEL = {k: mz(tz) for k, tz in _PN.items()}
MED_BRACO = {"braco": (float(maps(15.0)), ALVO["braco"]), "cotovelo": (BRACO_S_COTOVELO, ALVO["cotovelo"]),
             "pulso": (BRACO_S_PULSO - 1.0, ALVO["pulso"])}

def medir_corpo(ob, esc=1.0):
    V, E = arrays(ob); V = V / esc
    r = {}
    for k, z in MED_TRONCO.items():
        Pq = section(V, E, (0, 0, z), (0, 0, 1))
        r[k] = hull_perim(Pq[:, :2])
    for k, (z, _) in MED_PERNA.items():
        Pq = section(V, E, (0, 0, z), (0, 0, 1))
        Pq = Pq[Pq[:, 0] < -0.2]
        r[k] = hull_perim(Pq[:, :2])
    r["gancho"] = gancho(V, E)
    return r

def medir_braco(ob, esc=1.0):
    V, E = arrays(ob); V = V / esc
    r = {}
    for k, (s, _) in MED_BRACO.items():
        p, t = braco_ponto(s)
        Pq = section(V, E, p, t)
        Pq = Pq[np.linalg.norm(Pq - p, axis=1) < 9.0 * max(1.0, R_B)]
        u, v = braco_frame(t)
        r[k] = hull_perim(np.column_stack([(Pq - p) @ u, (Pq - p) @ v]))
    return r

# ==========================================================================
# 1) CALIBRAÇÃO DO CORPO
# ==========================================================================
for ob in list(bpy.data.objects):
    delete(ob)

def idx(arr, z):
    return int(np.argmin(np.abs(arr[:, 0] - z)))

hist = []
N_IT = 12
Z_PESC_INI = mz(146.5)
for it in range(N_IT):
    corpo = build_corpo(T, P, S, G)
    m = medir_corpo(corpo)
    hist.append(m)
    log("iter %d corpo:" % it, {k: round(v, 1) for k, v in m.items()})
    if it == N_IT - 1:
        break
    delete(corpo)
    for k, z in MED_TRONCO.items():
        r = ALVO[k] / m[k]
        if MASC and k in ("busto", "quadril"):
            # masculino: tórax e quadril pela largura/profundidade do tronco (peitoral e glúteo fixos)
            w = np.exp(-0.5 * ((T[:, 0] - z) / 4.0) ** 2)
            T[:, 1:4] *= r ** w[:, None]
            if k == "quadril" and r < 1:
                topo_perna = P[:, 0] >= Z_GANCHO - 4.0
                P[topo_perna, 1] *= r ** 0.6
        elif k == "busto":
            S[1] = max(0.5, S[1] + (ALVO[k] - m[k]) * 0.4)
        elif k == "quadril":
            G[1] = max(0.5, G[1] + (ALVO[k] - m[k]) * 0.35)
            if G[1] <= 0.5 and r < 1:   # glúteo já no mínimo: reduz largura do quadril
                w = np.exp(-0.5 * ((T[:, 0] - z) / 4.0) ** 2)
                T[:, 1] *= r ** w
        else:
            w = np.exp(-0.5 * ((T[:, 0] - z) / 3.5) ** 2)
            if k == "pescoco":
                w = np.where(T[:, 0] >= Z_PESC_INI, 1.0, w * 0.3)
            T[:, 1:4] *= r ** w[:, None]
    for k, (z, alvo) in MED_PERNA.items():
        r = alvo / m[k]
        P[idx(P, MED_PERNA_ANEL[k]), 3:5] *= r
        if k == "tornozelo":
            P[idx(P, mz(5.0)), 3:5] *= r

# plano da cava refeito com a largura real do tronco já calibrado
def _a_em(z):
    return float(pchip(T[:, 0], T[:, 1], [z])[0])
_X1 = -(_a_em(_Z1) + 0.15)
_X2 = -_a_em(mz(142.0))
N_CAVA = np.array([-(_Z2 - _Z1), 0.0, (_X2 - _X1)]); N_CAVA /= np.linalg.norm(N_CAVA)
def xplano(z):
    return _X1 + (z - _Z1) * (_X2 - _X1) / (_Z2 - _Z1)
BRACO_P0[0] = _X2 + 0.8
log("plano da cava: x %.2f @ %.1f  /  x %.2f @ %.1f" % (_X1, _Z1, _X2, _Z2))

# ==========================================================================
# 2) CALIBRAÇÃO DO BRAÇO
# ==========================================================================
if COM_BRACO:
    for it in range(4):
        V, F = build_braco(B)
        br = make_obj("braco_tmp", V, F)
        remesh_smooth(br)
        mb = medir_braco(br)
        log("iter %d braco:" % it, {k: round(v, 1) for k, v in mb.items()})
        delete(br)
        if it == 3:
            break
        for k, (s, alvo) in MED_BRACO.items():
            r = alvo / mb[k]
            if k == "pulso":
                for ss in (float(maps(55.0)), float(maps(60.0))):
                    B[idx(B, ss), 1:3] *= r
            else:
                B[idx(B, s), 1:3] *= r

# ==========================================================================
# 3) PEÇAS
# ==========================================================================
log("cortando")
tronco = corpo; tronco.name = "tronco_perna"
braco = None
if COM_BRACO:
    corpo_copia = tronco.copy(); corpo_copia.data = tronco.data.copy()
    bpy.context.scene.collection.objects.link(corpo_copia)
    cortar(corpo_copia, [prisma_cava("D", Z_CAVA_MIN, LM["topo"] + 25, recuo=2.5)], "INTERSECT")
    Vc, Ec = arrays(corpo_copia)
    Fc = [tuple(p.vertices) for p in corpo_copia.data.polygons]
    delete(corpo_copia)
    Vb, Fb = build_braco(B)
    Vu, Fu = combine([(Vb, Fb), (Vc, Fc)])
    braco = make_obj("braco", Vu, Fu)
    remesh_smooth(braco, iters=SMOOTH_IT)
    pw, tw = braco_ponto(BRACO_S_PULSO)
    uw, vw = braco_frame(tw)
    cortar(braco, [prisma_cava("D", LM["gancho"] - 20, LM["topo"] + 30)], "INTERSECT")
    cortar(braco, [caixa_orientada(pw + tw * 10.0, uw, vw, tw, 10, 10, 10)])

cortar(tronco, [prisma_cava("D", Z_CAVA_MIN, LM["topo"] + 25),
                prisma_cava("E", Z_CAVA_MIN, LM["topo"] + 25),
                caixa(-60, 60, -60, 60, Z_TOPO, Z_TOPO + 60),
                caixa(0.0, 60, -60, 60, -10, Z_COTO),
                caixa(-60, 0.5, -60, 60, -10, Z_TORNOZELO)])

# ==========================================================================
# 4) ESCALA (mm) + FUROS
# ==========================================================================
SM = Matrix.Scale(ESC, 4)
tronco.data.transform(SM)
if braco:
    braco.data.transform(SM)
log("furos")
Pv = P[::-1]
cx_c = -pchip(Pv[:, 0], Pv[:, 1], [Z_COTO])[0]
cy_c = pchip(Pv[:, 0], Pv[:, 2], [Z_COTO])[0]
HX, HY = cx_c * ESC, cy_c * ESC
Z_COTO_MM = Z_COTO * ESC
# haste proporcional ao tamanho (10 mm em 1:5)
HASTE_D = round(max(6.0, min(16.0, 10.0 * ESC / 2.0)))
FOLGA = 0.4
PROF_HASTE = round(26.0 * ESC / 2.0)
cortar(tronco, [cilindro([HX, HY, Z_COTO_MM - 1], [HX, HY, Z_COTO_MM + PROF_HASTE], (HASTE_D + FOLGA) / 2)])

pinos = []
if braco:
    V, E = arrays(tronco)
    for zr in Z_PINOS:
        zmm = zr * ESC
        xmm = xplano(zr) * ESC
        Pq = section(V, E, (xmm + 0.4, 0, 0), (1, 0, 0))
        Pq = Pq[np.abs(Pq[:, 2] - zmm) < 1.5]
        ymm = 0.5 * (Pq[:, 1].min() + Pq[:, 1].max()) if len(Pq) else -2.0
        pinos.append(np.array([xmm, ymm, zmm]))
    PINO_D = 2.1; PINO_PROF = 6.5
    cortar(tronco, [cilindro(c + N_CAVA * 1.0, c - N_CAVA * PINO_PROF, PINO_D / 2) for c in pinos])
    cortar(braco, [cilindro(c - N_CAVA * 1.0, c + N_CAVA * PINO_PROF, PINO_D / 2) for c in pinos])

# ==========================================================================
# 5) BASE + HASTE (mm)
# ==========================================================================
LADO_BASE = round(110.0 * ESC / 2.0); ESP_BASE = 5.0
def placa(cx, cy, half, z0, z1, n=6.0):
    x, y = superelipse(half, half, half, n)
    r0 = np.column_stack([x + cx, y + cy, np.full(NRING, z0)])
    r1 = np.column_stack([x + cx, y + cy, np.full(NRING, z1)])
    return orient(*loft([r0, r1]))
base = make_obj("base", *placa(HX, HY, LADO_BASE / 2, 0, ESP_BASE))
R_BOSS = HASTE_D / 2 + 6.0; H_BOSS = 17.0
cortar(base, [cilindro([HX, HY, ESP_BASE - 1], [HX, HY, H_BOSS], R_BOSS)], "UNION")
Z_SOCKET = 3.0
cortar(base, [cilindro([HX, HY, Z_SOCKET], [HX, HY, 30.0], (HASTE_D + FOLGA) / 2)])
Z_HASTE_TOPO = Z_COTO_MM + PROF_HASTE - 1.0
haste = make_obj("haste", *cilindro([HX, HY, Z_SOCKET], [HX, HY, Z_HASTE_TOPO], HASTE_D / 2, 64))

# ==========================================================================
# 6) MEDIÇÃO FINAL, ESPELHO, EXPORTAÇÃO
# ==========================================================================
mf = medir_corpo(tronco, ESC)
mbf = medir_braco(braco, ESC) if braco else {}
pecas = [("tronco_perna", tronco), ("braco", braco), ("base", base), ("haste", haste)]
pecas = [(n, o) for n, o in pecas if o is not None]
if PROJ["lado"] == "D":   # modelado com perna/braço em x<0 (lado esquerdo); espelha para o direito
    ESP = Matrix.Scale(-1.0, 4, (1.0, 0.0, 0.0))
    for _, ob in pecas:
        ob.data.transform(ESP); ob.data.flip_normals(); ob.data.update()
rel = {"nome": PROJ["nome"], "corpo_cm_reais": mf, "braco_cm_reais": mbf}
for nome, ob in pecas:
    nm, vol = checar(ob)
    V, _ = arrays(ob)
    rel[nome] = {"arestas_nao_manifold": nm, "volume_mm3": round(vol, 0),
                 "bbox_mm": (V.min(0).round(1).tolist(), V.max(0).round(1).tolist())}
    rel[nome]["triangulos"] = write_stl(ob, os.path.join(OUT, "manequim_%s.stl" % nome))
    log(nome, rel[nome])
ALT_TOTAL_MM = Z_TOPO * ESC
rel["altura_montado_mm"] = round(ALT_TOTAL_MM, 1)
rel["haste"] = {"diametro_mm": HASTE_D, "comprimento_mm": round(Z_HASTE_TOPO - Z_SOCKET, 1)}
rel["base_lado_mm"] = LADO_BASE
rel["pinos_mm"] = [c.round(2).tolist() for c in pinos]
rel["parametros_finais"] = {"tronco": T.round(3).tolist(), "perna": P.round(3).tolist(),
                            "seio": S.round(3).tolist(), "gluteo": G.round(3).tolist(),
                            "braco": B.round(3).tolist()}
rel["historico_calibracao"] = hist

mont = make_obj("montagem", *combine([(arrays(o)[0], [tuple(p.vertices) for p in o.data.polygons])
                                      for _, o in pecas]))
write_stl(mont, os.path.join(OUT, "manequim_montagem_conferencia.stl"), chao=False)
delete(mont)

# ==========================================================================
# 7) IMAGENS
# ==========================================================================
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "OBJECT"
sc.display.shading.show_cavity = True
if sc.world is None:
    sc.world = bpy.data.worlds.new("w")
sc.world.color = (1, 1, 1)
RES_X, RES_Y = 1200, 1650
sc.render.resolution_x = RES_X; sc.render.resolution_y = RES_Y
sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"
for nome, ob in pecas:
    ob.color = (0.15, 0.15, 0.15, 1) if nome == "base" else (0.25, 0.25, 0.25, 1) if nome == "haste" \
        else (0.93, 0.80, 0.66, 1)
    for p in ob.data.polygons:
        p.use_smooth = True
ORTHO = ALT_TOTAL_MM * 1.11
ZC = ALT_TOTAL_MM / 2.0 + 6.0
cam_data = bpy.data.cameras.new("cam"); cam_data.type = "ORTHO"; cam_data.ortho_scale = ORTHO
cam_data.clip_start = 1.0; cam_data.clip_end = 20.0 * ALT_TOTAL_MM
cam = bpy.data.objects.new("cam", cam_data); sc.collection.objects.link(cam); sc.camera = cam
D = 4.0 * ALT_TOTAL_MM
sx = 1.0 if PROJ["lado"] == "D" else -1.0   # lado do braço/perna longa (x do corpo)
vistas = {   # vista lateral e 3/4 sempre do lado do braço
    "frente": ((0, D, ZC), (90, 0, 180)),
    "lado": ((sx * D, 0, ZC), (90, 0, 90 * sx)),
    "costas": ((0, -D, ZC), (90, 0, 0)),
    "tres_quartos": ((sx * D * 0.7071, D * 0.7071, ZC), (90, 0, 180 - 45 * sx)),
}
for nome, (loc, rot) in vistas.items():
    cam.location = loc
    cam.rotation_euler = tuple(math.radians(r) for r in rot)
    sc.render.filepath = os.path.join(OUT, "previa_%s.png" % nome)
    bpy.ops.render.render(write_still=True)
rel["render"] = {"ortho_mm": ORTHO, "zc_mm": ZC, "res": [RES_X, RES_Y], "esc": ESC}
with open(os.path.join(OUT, "relatorio_medidas.json"), "w", encoding="utf-8") as f:
    json.dump(rel, f, ensure_ascii=False, indent=1, default=float)
log("FIM")
