# -*- coding: utf-8 -*-
"""
Manequim de moulage "perna longa" com 1 braço removível - escala 1:5.
Medidas da Giovanna (tabela da cliente). Rodar com:
  blender -b -P gerar_manequim.py -- <pasta_saida>

Todo o corpo é modelado em CENTÍMETROS REAIS e no fim convertido para mm
na escala 1:5 (1 cm real = 2 mm no modelo).

Eixos de trabalho: y = frente (+), z = altura. Modela-se com perna/braço em x<0
e no fim tudo é espelhado em x, ficando perna longa e braço do lado DIREITO do corpo.
"""
import bpy, bmesh, math, os, sys, json, time
import numpy as np
from mathutils import Matrix, Vector

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGV[0] if ARGV else os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)

ESC = 2.0          # cm real -> mm no modelo (1:5)
VOX = 0.25         # voxel do remesh (cm reais) = 0.5 mm no modelo
SMOOTH_IT = 50     # suavização após união (arredonda virilha, seios, axila)
NRING = 128
T0 = time.time()

def log(*a):
    print("[%6.1fs]" % (time.time() - T0), *a, flush=True)

# --------------------------------------------------------------------------
# MEDIDAS-ALVO (cm reais) - tabela da Giovanna
# --------------------------------------------------------------------------
ALVO = {
    "busto": 90.0, "cintura": 78.0, "quadril": 108.0, "peq_quadril": 86.5,
    "pescoco": 43.0, "braco": 31.0, "cotovelo": 26.0, "pulso": 15.5,
    "joelho": 37.5, "gancho": 74.5,
}
# Estimadas por proporção (não constam na tabela)
ALVO_PROP = {"coxa": 61.0, "meia_coxa": 48.0, "panturrilha": 37.0,
             "canela": 22.5, "tornozelo": 21.5}

# Alturas verticais adotadas (cm reais, a partir do chão)
Z_GANCHO = 80.5              # entrepernas
Z_CINTURA = 80.5 + 30.0      # entrepernas + cintura ao gancho
Z_QUADRIL = 88.0             # cintura->quadril 24 lateral (x0,936)
Z_PEQ_Q = 98.3               # cintura->peq. quadril 13 lateral (x0,936)
Z_JOELHO = 46.8
Z_BUSTO = 122.0              # jugular 137,5 - altura do busto (20 em diagonal)
Z_PESCOCO = 150.0
Z_TOPO = 153.0               # corte do pescoço
Z_COTO = 66.0                # corte da perna curta
Z_TORNOZELO = 9.0            # fim da perna longa
BRACO_S_COTOVELO = 33.0
BRACO_S_PULSO = 57.5

# --------------------------------------------------------------------------
# PARÂMETROS DE FORMA
# --------------------------------------------------------------------------
# tronco: z, meia-largura a, prof. frente bf, prof. costas bb, centro y, expoente
TRONCO = np.array([
    [ 80.5,  7.0,  3.5,  4.5, -1.0, 2.0],
    [ 82.0, 12.5,  5.5,  8.0, -1.0, 2.1],
    [ 84.0, 16.0,  8.5, 10.0, -1.0, 2.2],
    [ 86.0, 17.4, 10.0, 11.0, -1.0, 2.3],
    [ 88.0, 17.9, 11.0, 11.2, -1.0, 2.4],
    [ 91.0, 18.1, 11.3, 11.2, -0.8, 2.4],
    [ 95.0, 17.8, 11.5, 11.1, -0.3, 2.3],
    [ 98.3, 16.6, 11.5, 10.7,  0.0, 2.3],
    [104.0, 15.0, 10.5, 10.0,  0.0, 2.2],
    [110.5, 14.0,  9.8,  9.3,  0.0, 2.2],
    [116.0, 14.4,  9.6,  9.8,  0.0, 2.2],
    [122.0, 14.8,  9.5, 10.3,  0.0, 2.2],
    [126.0, 15.2,  9.6, 10.5, -0.3, 2.3],
    [130.0, 16.8,  9.6, 10.3, -0.6, 2.3],
    [134.0, 17.8,  9.4,  9.8, -1.0, 2.3],
    [137.5, 18.3,  9.2,  9.2, -1.4, 2.3],
    [140.0, 18.4,  8.0,  8.6, -1.8, 2.3],
    [142.0, 17.8,  7.0,  8.0, -2.0, 2.2],
    [143.5, 14.0,  6.4,  7.6, -2.2, 2.3],
    [145.0, 10.0,  6.0,  7.0, -2.3, 2.2],
    [146.5,  7.4,  6.2,  6.7, -2.4, 2.1],
    [148.0,  6.9,  6.2,  6.6, -2.4, 2.0],
    [150.0,  6.9,  6.2,  6.6, -2.4, 2.0],
    [156.0,  6.8,  6.1,  6.5, -2.4, 2.0],
])
# seios (relevo somado à frente do tronco): x do mamilo, projeção A, z, sigma_x, sigma_z acima, sigma_z abaixo
SEIO = np.array([10.5, 4.0, Z_BUSTO, 5.0, 5.5, 4.0])
# glúteos (relevo somado às costas): x do centro da nádega, projeção, z do ponto mais saliente,
# sigma_x, sigma_z acima (sobe suave até a lombar), sigma_z abaixo (dobra redonda)
GLUTEO = np.array([8.5, 4.5, 86.0, 5.0, 9.0, 6.0])

# perna direita: z, cx, cy, a (lateral), b (frente-trás)
PERNA = np.array([
    [97.0, -7.5, -1.0, 4.5,  5.5],
    [92.0, -9.0, -1.0, 8.0,  9.5],
    [86.0, -9.5, -2.0, 9.2, 11.8],
    [82.0, -9.6, -1.8, 9.2, 11.4],
    [77.0, -9.6, -1.0, 9.0, 10.6],
    [70.0, -9.0, -0.3, 8.6,  8.8],
    [60.0, -8.2,  0.0, 7.8,  7.5],
    [50.0, -7.8,  0.2, 6.5,  6.1],
    [46.8, -7.6,  0.4, 6.1,  5.8],
    [42.0, -7.5,  0.0, 5.6,  5.4],
    [34.0, -7.3, -1.0, 5.6,  6.1],
    [25.0, -7.2, -0.6, 4.6,  4.9],
    [15.0, -7.0, -0.2, 3.5,  3.6],
    [ 9.0, -7.0,  0.0, 3.4,  3.4],
    [ 5.0, -7.0,  0.0, 3.4,  3.4],
])

# braço: s (cm a partir do acrômio, ao longo do eixo), a (lateral), b (frente-trás)
BRACO = np.array([
    [-1.8, 2.5, 2.5],
    [-0.5, 4.6, 4.4],
    [ 1.5, 5.8, 5.3],
    [ 5.0, 5.9, 5.4],
    [10.0, 5.3, 5.1],
    [15.0, 5.0, 4.9],
    [24.0, 4.5, 4.4],
    [33.0, 4.2, 4.1],
    [38.0, 4.1, 3.9],
    [46.0, 3.2, 3.5],
    [55.0, 2.25, 2.8],
    [60.0, 2.2, 2.75],
])
BRACO_P0 = np.array([-17.0, -1.0, 138.8])
ABDUCAO = math.radians(15.0)     # braço "abertinho"
FLEXAO = math.radians(12.0)      # antebraço levemente à frente

# plano da cava (lado direito): x = xplano(z); espelhado no lado esquerdo
def xplano(z):
    return -15.8 - (z - 127.0) * (2.0 / 16.0)
N_CAVA = np.array([-16.0, 0.0, -2.0]); N_CAVA /= np.linalg.norm(N_CAVA)  # normal p/ fora (dir.)
Z_CAVA_MIN = 121.0

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

# --------------------------------------------------------------------------
# construção das partes
# --------------------------------------------------------------------------
def build_tronco(T, S):
    zs = np.arange(T[0, 0], T[-1, 0] + 1e-6, 0.4)
    cols = [pchip(T[:, 0], T[:, k], zs) for k in range(1, 6)]
    xb, A, zb, sx, szu, szd = S
    rings = []
    for i, z in enumerate(zs):
        a, bf, bb, yc, n = (c[i] for c in cols)
        x, y = superelipse(a, bf, bb, n)
        sz = szu if z > zb else szd
        g = A * math.exp(-0.5 * ((z - zb) / sz) ** 2)
        if g > 1e-3:
            frente = np.clip(np.sin(TH), 0, 1)
            y = y + g * frente * np.exp(-0.5 * ((np.abs(x) - xb) / sx) ** 2)
        rings.append(np.column_stack([x, y + yc, np.full(NRING, z)]))
    return orient(*loft(rings))

def build_perna(P, lado=-1, zmin=None):
    P = P[::-1]  # z crescente
    z0 = P[0, 0] if zmin is None else zmin
    zs = np.arange(z0, P[-1, 0] + 1e-6, 0.4)
    cols = [pchip(P[:, 0], P[:, k], zs) for k in range(1, 5)]
    rings = []
    for i, z in enumerate(zs):
        cx, cy, a, b = (c[i] for c in cols)
        x, y = superelipse(a, b, b, 2.0)
        rings.append(np.column_stack([x + (cx if lado < 0 else -cx), y + cy, np.full(NRING, z)]))
    return orient(*loft(rings))

def build_elipsoide(c, r, n=64):
    phis = np.linspace(np.pi - 0.08, 0.08, 40)
    rings = []
    for ph in phis:
        rings.append(np.column_stack([c[0] + r[0]*np.sin(ph)*np.cos(TH),
                                      c[1] + r[1]*np.sin(ph)*np.sin(TH),
                                      np.full(NRING, c[2] + r[2]*np.cos(ph))]))
    return orient(*loft(rings))

def braco_caminho(s):
    d1 = np.array([-math.sin(ABDUCAO), 0.0, -math.cos(ABDUCAO)])
    d2 = d1 * math.cos(FLEXAO) + np.array([0, 1.0, 0]) * math.sin(FLEXAO)
    w = np.clip((s - 29.0) / 8.0, 0, 1); w = w*w*(3 - 2*w)
    t = (1 - w)[:, None] * d1 + w[:, None] * d2
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    P = np.zeros((len(s), 3))
    for i in range(1, len(s)):
        P[i] = P[i-1] + 0.5 * (t[i] + t[i-1]) * (s[i] - s[i-1])
    i0 = np.argmin(np.abs(s))
    P += BRACO_P0 - P[i0]
    return P, t

def braco_frame(t):
    u = np.cross(t, [0, 1.0, 0]); u /= np.linalg.norm(u)
    v = np.cross(t, u); v /= np.linalg.norm(v)
    return u, v

def build_braco(B):
    ss = np.arange(B[0, 0], B[-1, 0] + 1e-6, 0.4)
    P, t = braco_caminho(ss)
    a = pchip(B[:, 0], B[:, 1], ss); b = pchip(B[:, 0], B[:, 2], ss)
    rings = []
    for i in range(len(ss)):
        u, v = braco_frame(t[i])
        rings.append(P[i] + np.outer(a[i]*np.cos(TH), u) + np.outer(b[i]*np.sin(TH), v))
    return orient(*loft(rings))

def braco_ponto(s):
    ss = np.arange(-3.0, 60.0 + 1e-6, 0.1)
    P, t = braco_caminho(ss)
    i = np.argmin(np.abs(ss - s))
    return P[i], t[i]

# ---- corpo como campo de distância com união suave (sem degraus) ----
H_SDF = 0.2      # voxel do campo (cm reais) = 0.4 mm no modelo
K_UNIAO = 4.5    # raio da concordância tronco/pernas (cm reais)
Z_PERNA_TOPO = 97.0
Z_PERNA_E_MIN = 63.0

def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)

def dist_radial(X, Y, a, bpos, bneg, n):
    bsel = np.where(Y > 0, bpos, bneg)
    r = ((np.abs(X) / a) ** n + (np.abs(Y) / bsel) ** n) ** (1.0 / n)
    rho = np.sqrt(X * X + Y * Y)
    return np.where(r > 1e-6, rho * (1.0 - 1.0 / np.maximum(r, 1e-6)), -np.minimum(a, bsel))

def sdf_corpo(T, P, S, G=None):
    import openvdb as vdb
    h = H_SDF
    xs = np.arange(-25.0, 25.0 + h / 2, h); ys = np.arange(-22.0, 20.0 + h / 2, h)
    zs = np.arange(3.0, 158.0 + h / 2, h)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    arr = np.empty((len(xs), len(ys), len(zs)), np.float32)
    zt = np.clip(zs, T[0, 0], T[-1, 0])
    tp = [pchip(T[:, 0], T[:, k], zt) for k in range(1, 6)]
    Pv = P[::-1]
    zl = np.clip(zs, Pv[0, 0], Z_PERNA_TOPO)
    lp = [pchip(Pv[:, 0], Pv[:, k], zl) for k in range(1, 5)]
    xb, A, zb, sx, szu, szd = S
    G = GLUTEO if G is None else G
    gx = np.exp(-0.5 * ((np.sqrt(X * X + 2.0) - G[0]) / G[3]) ** 2)
    bx = np.exp(-0.5 * ((np.sqrt(X * X + 2.0) - xb) / sx) ** 2)   # sem quina no meio
    for iz, z in enumerate(zs):
        if z >= T[0, 0] - 6.0:
            a, bf, bb, yc, n = (c[iz] for c in tp)
            sz = szu if z > zb else szd
            bfe = bf + A * math.exp(-0.5 * ((z - zb) / sz) ** 2) * bx
            szg = G[4] if z > G[2] else G[5]
            bbe = bb + G[1] * math.exp(-0.5 * ((z - G[2]) / szg) ** 2) * gx
            dT = np.maximum(dist_radial(X, Y - yc, a, bfe, bbe, n), T[0, 0] - z)
        else:
            dT = np.full(X.shape, 1e3)
        cx, cy, la, lb = (c[iz] for c in lp)
        cap = max(z - Z_PERNA_TOPO, Pv[0, 0] - z)
        dR = np.maximum(dist_radial(X - cx, Y - cy, la, lb, lb, 2.0), cap)
        capE = max(z - Z_PERNA_TOPO, Z_PERNA_E_MIN - z)
        dE = np.maximum(dist_radial(X + cx, Y - cy, la, lb, lb, 2.0), capE)
        d = np.minimum(smin(dT, dR, K_UNIAO), smin(dT, dE, K_UNIAO))   # pernas não se fundem entre si
        arr[:, :, iz] = d
    g = vdb.FloatGrid(1e3)
    g.copyFromArray(arr)
    g.transform = vdb.createLinearTransform(voxelSize=h)
    pts, quads = g.convertToQuads(0.0)
    pts = np.asarray(pts, float) + np.array([xs[0], ys[0], zs[0]])
    return pts, np.asarray(quads)

def build_corpo(T, P, S, G=None):
    V, Q = sdf_corpo(T, P, S, G)
    ob = make_obj("corpo", V, [tuple(q) for q in Q])
    s = ob.modifiers.new("sm", "SMOOTH"); s.factor = 0.5; s.iterations = 20
    apply_mods(ob)
    return ob

# perna esquerda: build_perna com lado=+1 espelha cx
def _perna_fix():
    pass

# --------------------------------------------------------------------------
# medições
# --------------------------------------------------------------------------
def gancho(V, E):
    Pt = section(V, E, (0, 0, 0), (1, 0, 0))
    Pt = Pt[(Pt[:, 2] <= Z_CINTURA) & (Pt[:, 2] >= Z_GANCHO - 2.0)]
    y = Pt[:, 1]; z = Pt[:, 2]
    cy, cz = -0.5, 97.0
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
MED_PERNA = {"coxa": (77.0, 61.0), "meia_coxa": (60.0, 48.0), "joelho": (Z_JOELHO, 37.5),
             "panturrilha": (34.0, 37.0), "canela": (15.0, 22.5), "tornozelo": (10.0, 21.5)}
MED_PERNA_ANEL = {"coxa": 77.0, "meia_coxa": 60.0, "joelho": 46.8, "panturrilha": 34.0,
                  "canela": 15.0, "tornozelo": 9.0}
MED_BRACO = {"braco": (15.0, 31.0), "cotovelo": (33.0, 26.0), "pulso": (56.5, 15.5)}

def medir_corpo(ob, esc=1.0):
    V, E = arrays(ob); V = V / esc
    r = {}
    for k, z in MED_TRONCO.items():
        P = section(V, E, (0, 0, z), (0, 0, 1))
        r[k] = hull_perim(P[:, :2])
    for k, (z, _) in MED_PERNA.items():
        P = section(V, E, (0, 0, z), (0, 0, 1))
        P = P[P[:, 0] < -0.2]
        r[k] = hull_perim(P[:, :2])
    r["gancho"] = gancho(V, E)
    return r

def medir_braco(ob, esc=1.0):
    V, E = arrays(ob); V = V / esc
    r = {}
    for k, (s, _) in MED_BRACO.items():
        p, t = braco_ponto(s)
        P = section(V, E, p, t)
        P = P[np.linalg.norm(P - p, axis=1) < 9.0]
        u, v = braco_frame(t)
        r[k] = hull_perim(np.column_stack([(P - p) @ u, (P - p) @ v]))
    return r

# --------------------------------------------------------------------------
# cortadores
# --------------------------------------------------------------------------
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
        f.write(b"Manequim Giovanna 1:5".ljust(80, b" "))
        f.write(np.uint32(len(T)).tobytes()); f.write(rec.tobytes())
    return len(T)

def checar(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    nm = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume(signed=True)
    bm.free()
    return nm, vol

# ==========================================================================
# 1) CALIBRAÇÃO DO CORPO (tronco + pernas + seios)
# ==========================================================================
for ob in list(bpy.data.objects):
    delete(ob)

T = TRONCO.copy(); P = PERNA.copy(); S = SEIO.copy(); B = BRACO.copy(); G = GLUTEO.copy()

def idx(arr, z):
    return int(np.argmin(np.abs(arr[:, 0] - z)))

hist = []
for it in range(12):
    corpo = build_corpo(T, P, S, G)
    m = medir_corpo(corpo)
    hist.append(m)
    log("iter %d corpo:" % it, {k: round(v, 1) for k, v in m.items()})
    if it == 11:
        break
    delete(corpo)
    # ajustes
    for k, z in MED_TRONCO.items():
        r = ALVO[k] / m[k]
        i = idx(T, z)
        if k == "busto":
            S[1] = max(1.0, S[1] + (ALVO[k] - m[k]) * 0.4)   # projeção dos seios
        else:
            # ajuste espalhado suavemente nas alturas vizinhas (evita calombos)
            w = np.exp(-0.5 * ((T[:, 0] - z) / 3.5) ** 2)
            if k == "pescoco":
                w = np.where(T[:, 0] >= 146.5, 1.0, w * 0.3)
            if k == "quadril":
                # quadril: só profundidade (largura fica casada com o topo das coxas)
                G[1] = max(1.0, G[1] + (ALVO[k] - m[k]) * 0.35)   # volume dos glúteos
            else:
                T[:, 1:4] *= r ** w[:, None]
    for k, (z, alvo) in MED_PERNA.items():
        r = alvo / m[k]
        i = idx(P, MED_PERNA_ANEL[k])
        P[i, 3:5] *= r
        if k == "tornozelo":
            P[idx(P, 5.0), 3:5] *= r

# ==========================================================================
# 2) CALIBRAÇÃO DO BRAÇO
# ==========================================================================
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
            for ss in (55.0, 60.0):
                B[idx(B, ss), 1:3] *= r
        else:
            B[idx(B, s), 1:3] *= r

# ==========================================================================
# 3) PEÇAS: TRONCO+PERNA e BRAÇO
# ==========================================================================
log("cortando tronco")
tronco = corpo; tronco.name = "tronco_perna"

# braço = braço + (corpo ∩ região da cava direita)
corpo_copia = tronco.copy(); corpo_copia.data = tronco.data.copy()
bpy.context.scene.collection.objects.link(corpo_copia)
# ombro do braço tirado 2,5 cm para dentro, para a suavização não encolher a face de encaixe
cortar(corpo_copia, [prisma_cava("D", Z_CAVA_MIN, 175.0, recuo=2.5)], "INTERSECT")
Vc, Ec = arrays(corpo_copia)
Fc = [tuple(p.vertices) for p in corpo_copia.data.polygons]
delete(corpo_copia)
Vb, Fb = build_braco(B)
Vu, Fu = combine([(Vb, Fb), (Vc, Fc)])
braco = make_obj("braco", Vu, Fu)
remesh_smooth(braco, iters=SMOOTH_IT)
pw, tw = braco_ponto(BRACO_S_PULSO)
uw, vw = braco_frame(tw)
cortar(braco, [prisma_cava("D", 60.0, 180.0)], "INTERSECT")
cortar(braco, [caixa_orientada(pw + tw * 10.0, uw, vw, tw, 10, 10, 10)])

cortar(tronco, [prisma_cava("D", Z_CAVA_MIN, 175.0),
                prisma_cava("E", Z_CAVA_MIN, 175.0),
                caixa(-50, 50, -50, 50, Z_TOPO, 200),
                caixa(0.0, 50, -50, 50, -10, Z_COTO),
                caixa(-50, 0.5, -50, 50, -10, Z_TORNOZELO)])

# ==========================================================================
# 4) ESCALA 1:5 (mm) + FUROS
# ==========================================================================
S5 = Matrix.Scale(ESC, 4)
tronco.data.transform(S5); braco.data.transform(S5)
log("furos")

# haste: centro da perna curta no corte
Pv = PERNA[::-1]
cx_c = -pchip(Pv[:, 0], Pv[:, 1], [Z_COTO])[0]   # espelhado (+x)
cy_c = pchip(Pv[:, 0], Pv[:, 2], [Z_COTO])[0]
HX, HY = cx_c * ESC, cy_c * ESC
Z_COTO_MM = Z_COTO * ESC
HASTE_D = 10.0; FOLGA = 0.4; PROF_HASTE = 26.0
cortar(tronco, [cilindro([HX, HY, Z_COTO_MM - 1], [HX, HY, Z_COTO_MM + PROF_HASTE], (HASTE_D + FOLGA) / 2)])

# pinos braço<->tronco (filamento 1,75 mm ou pino de 2 mm)
V, E = arrays(tronco)
nmm = N_CAVA
pinos = []
for zr in (130.5, 138.0):
    zmm = zr * ESC
    xmm = xplano(zr) * ESC
    P = section(V, E, (xmm + 0.4, 0, 0), (1, 0, 0))
    P = P[np.abs(P[:, 2] - zmm) < 1.5]
    ymm = 0.5 * (P[:, 1].min() + P[:, 1].max()) if len(P) else -2.0
    pinos.append(np.array([xmm, ymm, zmm]))
PINO_D = 2.1; PINO_PROF = 6.5
cortar(tronco, [cilindro(c + nmm * 1.0, c - nmm * PINO_PROF, PINO_D / 2) for c in pinos])
cortar(braco, [cilindro(c - nmm * 1.0, c + nmm * PINO_PROF, PINO_D / 2) for c in pinos])

# ==========================================================================
# 5) BASE + HASTE (mm)
# ==========================================================================
LADO_BASE = 110.0; ESP_BASE = 5.0
def placa(cx, cy, half, z0, z1, n=6.0):
    x, y = superelipse(half, half, half, n)
    r0 = np.column_stack([x + cx, y + cy, np.full(NRING, z0)])
    r1 = np.column_stack([x + cx, y + cy, np.full(NRING, z1)])
    return orient(*loft([r0, r1]))
Vb_, Fb_ = combine([placa(HX, HY, LADO_BASE / 2, 0, ESP_BASE)])
base = make_obj("base", Vb_, Fb_)
cortar(base, [cilindro([HX, HY, ESP_BASE - 1], [HX, HY, 17.0], 11.0)], "UNION")
Z_SOCKET = 3.0
cortar(base, [cilindro([HX, HY, Z_SOCKET], [HX, HY, 30.0], (HASTE_D + FOLGA) / 2)])
Z_HASTE_TOPO = Z_COTO_MM + PROF_HASTE - 1.0
haste = make_obj("haste", *cilindro([HX, HY, Z_SOCKET], [HX, HY, Z_HASTE_TOPO], HASTE_D / 2, 64))

# ==========================================================================
# 6) MEDIÇÃO FINAL, CHECAGEM E EXPORTAÇÃO
# ==========================================================================
mf = medir_corpo(tronco, ESC)
mbf = medir_braco(braco, ESC)
# espelha tudo em x: perna longa e braço passam para o lado DIREITO do corpo
ESP = Matrix.Scale(-1.0, 4, (1.0, 0.0, 0.0))
for ob in (tronco, braco, base, haste):
    ob.data.transform(ESP)
    ob.data.flip_normals()
    ob.data.update()
rel = {"corpo_cm_reais": mf, "braco_cm_reais": mbf}
for nome, ob in (("tronco_perna", tronco), ("braco", braco), ("base", base), ("haste", haste)):
    nm, vol = checar(ob)
    V, _ = arrays(ob)
    bb = (V.min(0).round(1).tolist(), V.max(0).round(1).tolist())
    rel[nome] = {"arestas_nao_manifold": nm, "volume_mm3": round(vol, 0),
                 "bbox_mm": bb, "triangulos": None}
    rel[nome]["triangulos"] = write_stl(ob, os.path.join(OUT, "manequim_%s.stl" % nome))
    log(nome, rel[nome])

rel["haste_comprimento_mm"] = round(Z_HASTE_TOPO - Z_SOCKET, 1)
rel["pinos_mm"] = [c.round(2).tolist() for c in pinos]
rel["parametros_finais"] = {"tronco": T.round(3).tolist(), "perna": P.round(3).tolist(),
                            "seio": S.round(3).tolist(), "gluteo": G.round(3).tolist(), "braco": B.round(3).tolist()}
rel["historico_calibracao"] = hist
with open(os.path.join(OUT, "relatorio_medidas.json"), "w", encoding="utf-8") as f:
    json.dump(rel, f, ensure_ascii=False, indent=1, default=float)

# montagem (posição real) para conferência
Vm, Fm = [], []
mont_parts = []
for ob in (tronco, braco, base, haste):
    V, _ = arrays(ob)
    mont_parts.append((V, [tuple(p.vertices) for p in ob.data.polygons]))
Vm, Fm = combine(mont_parts)
mont = make_obj("montagem", Vm, Fm)
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
sc.display.shading.show_object_outline = False
if sc.world is None:
    sc.world = bpy.data.worlds.new("w")
sc.world.color = (1, 1, 1)
sc.render.resolution_x = 1200; sc.render.resolution_y = 1650
sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"
for ob, col in ((tronco, (0.93, 0.80, 0.66, 1)), (braco, (0.93, 0.80, 0.66, 1)),
                (base, (0.15, 0.15, 0.15, 1)), (haste, (0.25, 0.25, 0.25, 1))):
    ob.color = col
    for p in ob.data.polygons:
        p.use_smooth = True

cam_data = bpy.data.cameras.new("cam"); cam_data.type = "ORTHO"; cam_data.ortho_scale = 340
cam = bpy.data.objects.new("cam", cam_data); sc.collection.objects.link(cam); sc.camera = cam
D = 800.0; ZC = 160.0
vistas = {
    "frente":   ((0, D, ZC), (90, 0, 180)),
    "lado":     ((-D, 0, ZC), (90, 0, -90)),
    "costas":   ((0, -D, ZC), (90, 0, 0)),
    "tres_quartos": ((-D*0.7071, D*0.7071, ZC), (90, 0, -135)),
}
for nome, (loc, rot) in vistas.items():
    cam.location = loc
    cam.rotation_euler = tuple(math.radians(r) for r in rot)
    sc.render.filepath = os.path.join(OUT, "previa_%s.png" % nome)
    bpy.ops.render.render(write_still=True)
log("FIM")
