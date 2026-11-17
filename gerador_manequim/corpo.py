# -*- coding: utf-8 -*-
"""
Corpo-base (feminino e masculino) e sua deformação para as medidas de um projeto.
Módulo puro (numpy), usado pelo gerador no Blender e pela prévia da interface web.
"""
import math
import numpy as np


def preparar(PROJ):
    """Recebe o projeto (medidas.montar_projeto) e devolve os parâmetros do corpo deformado."""
    ALVO = PROJ["alvos"]
    LM = PROJ["landmarks"]
    # ==========================================================================
    # CORPO-BASE (manequim da Giovanna, cm reais) e suas alturas de referência
    # ==========================================================================
    TPL_LM = {"chao": 0.0, "tornozelo": 9.0, "joelho": 46.8, "coto": 66.0, "gancho": 80.5,
              "quadril": 88.0, "peq": 98.3, "cintura": 110.5, "busto": 122.0, "cava": 127.0,
              "jugular": 137.5, "ombro": 142.0, "c7": 146.5, "topo": 153.0}
    TPL_ALVO = {"busto": 90.0, "cintura": 78.0, "quadril": 108.0, "peq_quadril": 86.5, "pescoco": 43.0,
                "braco": 31.0, "cotovelo": 26.0, "pulso": 15.5, "joelho": 37.5, "coxa": 61.0,
                "meia_coxa": 48.0, "panturrilha": 37.0, "canela": 22.5, "tornozelo": 21.5}
    TPL_LARG_OMBRO = 18.24
    TPL_ABERTURA = 21.0
    TPL_BRACO_COT = 33.0
    TPL_BRACO_COMP = 57.5

    TRONCO_TPL = np.array([
        [ 80.5,  7.0,  3.5,  4.5, -1.0, 2.0],
        [ 82.0, 12.5,  5.5,  8.0, -1.0, 2.1],
        [ 84.0, 15.0,  8.5, 10.0, -1.0, 2.2],
        [ 86.0, 16.2, 10.0, 11.0, -1.0, 2.3],
        [ 88.0, 16.7, 11.0, 11.2, -1.0, 2.4],
        [ 91.0, 17.0, 11.3, 11.2, -0.8, 2.4],
        [ 95.0, 17.0, 11.5, 11.1, -0.3, 2.3],
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
    SEIO_TPL = np.array([10.5, 4.0, 122.0, 5.0, 5.5, 4.0])
    GLUTEO_TPL = np.array([8.5, 5.5, 85.0, 5.5, 9.5, 7.5])
    PERNA_TPL = np.array([
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
    BRACO_TPL = np.array([
        [-1.8, 2.5, 2.5], [-0.5, 4.6, 4.4], [1.5, 5.8, 5.3], [5.0, 5.9, 5.4], [10.0, 5.3, 5.1],
        [15.0, 5.0, 4.9], [24.0, 4.5, 4.4], [33.0, 4.2, 4.1], [38.0, 4.1, 3.9], [46.0, 3.2, 3.5],
        [55.0, 2.25, 2.8], [60.0, 2.2, 2.75],
    ])

    # ---- CORPO-BASE MASCULINO (mesmo referencial de alturas; tronco mais reto e largo em cima,
    #      quadril estreito, peitoral e glúteos discretos, seções mais "quadradas")
    MASC = PROJ.get("sexo", "F") == "M"
    TRONCO_M = np.array([
        [ 80.5,  7.0,  3.5,  4.5, -1.0, 2.0],
        [ 82.0, 12.0,  6.5,  8.5, -1.0, 2.1],
        [ 84.0, 15.2,  9.0, 10.5, -1.0, 2.2],
        [ 86.0, 16.4, 10.0, 11.0, -0.8, 2.3],
        [ 88.0, 16.8,  9.8, 10.0, -0.6, 2.4],
        [ 91.0, 16.8, 10.0, 10.0, -0.4, 2.4],
        [ 95.0, 16.6, 10.2,  9.8, -0.2, 2.4],
        [ 98.3, 16.2, 10.2,  9.6,  0.0, 2.4],
        [104.0, 15.6, 10.0,  9.4,  0.0, 2.4],
        [110.5, 15.4,  9.8,  9.2,  0.0, 2.4],
        [116.0, 15.8,  9.8,  9.6,  0.0, 2.4],
        [122.0, 16.6, 10.2, 10.2,  0.0, 2.4],
        [126.0, 17.4, 10.2, 10.4, -0.3, 2.4],
        [130.0, 18.4, 10.0, 10.2, -0.6, 2.4],
        [134.0, 19.0,  9.6,  9.8, -1.0, 2.4],
        [137.5, 19.2,  9.0,  9.2, -1.4, 2.4],
        [140.0, 19.2,  8.0,  8.6, -1.8, 2.4],
        [142.0, 18.6,  7.0,  8.0, -2.0, 2.3],
        [143.5, 14.8,  6.6,  7.6, -2.2, 2.3],
        [145.0, 10.6,  6.4,  7.2, -2.3, 2.2],
        [146.5,  8.0,  6.4,  6.9, -2.4, 2.1],
        [148.0,  7.4,  6.4,  6.8, -2.4, 2.0],
        [150.0,  7.3,  6.4,  6.8, -2.4, 2.0],
        [156.0,  7.2,  6.3,  6.7, -2.4, 2.0],
    ])

    def _perim(a, bf, bb, n, N=720):
        th = np.linspace(0, 2 * np.pi, N, endpoint=False)
        c = np.cos(th); s = np.sin(th)
        x = a * np.sign(c) * np.abs(c) ** (2.0 / n)
        y = np.where(s > 0, bf, bb) * np.sign(s) * np.abs(s) ** (2.0 / n)
        return float(np.sum(np.hypot(np.diff(np.r_[x, x[0]]), np.diff(np.r_[y, y[0]]))))

    if MASC:
        TRONCO_TPL = TRONCO_M
        _ring = lambda z: TRONCO_M[int(np.argmin(np.abs(TRONCO_M[:, 0] - z)))]
        for _k, _z, _extra in (("busto", 122.0, 1.5), ("cintura", 110.5, 0.0), ("peq_quadril", 98.3, 0.0),
                               ("quadril", 88.0, 1.0), ("pescoco", 150.0, 0.0)):
            _r = _ring(_z)
            TPL_ALVO[_k] = _perim(_r[1], _r[2], _r[3], _r[5]) + _extra
        TPL_LARG_OMBRO = 19.0

    # ==========================================================================
    # DEFORMAÇÃO DO CORPO-BASE PARA A PESSOA
    # ==========================================================================
    _K = ["chao", "tornozelo", "joelho", "coto", "gancho", "quadril", "peq", "cintura", "busto", "cava",
          "jugular", "ombro", "c7", "topo"]
    _TZ = np.array([TPL_LM[k] for k in _K]); _NZ = np.array([LM[k] for k in _K])
    if np.any(np.diff(_NZ) <= 0):
        raise ValueError("Alturas fora de ordem: %s" % dict(zip(_K, _NZ.round(1))))
    SV_TOPO = (LM["topo"] - LM["c7"]) / (TPL_LM["topo"] - TPL_LM["c7"])

    def mapz(z):
        z = np.asarray(z, float)
        r = np.interp(z, _TZ, _NZ)
        return np.where(z > _TZ[-1], _NZ[-1] + (z - _TZ[-1]) * SV_TOPO, r)

    def mz(z):
        return float(mapz(z))

    def razao(k):
        return ALVO[k] / TPL_ALVO[k]

    R_Q, R_PQ, R_C, R_B, R_N = razao("quadril"), razao("peq_quadril"), razao("cintura"), razao("busto"), razao("pescoco")
    R_SH = PROJ["larg_ombro"] / TPL_LARG_OMBRO
    _RZ = [80.5, 88.0, 98.3, 110.5, 122.0, 130.0, 137.5, 142.0, 146.5, 156.0]
    _RA = [R_Q, R_Q, R_PQ, R_C, R_B, R_B, 0.5 * (R_B + R_SH), R_SH, R_N, R_N]
    _RD = [R_Q, R_Q, R_PQ, R_C, R_B, R_B, R_B, R_B, R_N, R_N]

    T = TRONCO_TPL.copy()
    T[:, 1] *= np.interp(TRONCO_TPL[:, 0], _RZ, _RA)
    dep = np.interp(TRONCO_TPL[:, 0], _RZ, _RD)
    T[:, 2] *= dep; T[:, 3] *= dep; T[:, 4] *= dep
    T[:, 0] = mapz(TRONCO_TPL[:, 0])

    SVB = (LM["jugular"] - LM["cintura"]) / (TPL_LM["jugular"] - TPL_LM["cintura"])
    SVL = (LM["cintura"] - LM["gancho"]) / (TPL_LM["cintura"] - TPL_LM["gancho"])
    ab = PROJ["usados"].get("abertura_busto", TPL_ABERTURA)
    if MASC:   # peitoral largo e baixo relevo; glúteo discreto
        S = np.array([9.5 * ab / 20.0, 1.2 * R_B, LM["busto"] + 1.5 * SVB, 6.5 * R_B, 6.0 * SVB, 3.0 * SVB])
        G = np.array([8.0 * R_Q, 3.0 * R_Q, mz(87.0), 6.0 * R_Q, 8.0 * SVL, 5.0 * SVL])
    else:
        S = np.array([10.5 * ab / TPL_ABERTURA, 4.0 * R_B, LM["busto"], 5.0 * R_B, 5.5 * SVB, 4.0 * SVB])
        G = np.array([8.5 * R_Q, 5.5 * R_Q, mz(85.0), 5.5 * R_Q, 9.5 * SVL, 7.5 * SVL])

    _LZ = [97.0, 82.0, 77.0, 60.0, 46.8, 34.0, 15.0, 9.0, 5.0]
    _LR = [razao("coxa"), razao("coxa"), razao("coxa"), razao("meia_coxa"), razao("joelho"),
           razao("panturrilha"), razao("canela"), razao("tornozelo"), razao("tornozelo")]
    P = PERNA_TPL.copy()
    rl = np.interp(PERNA_TPL[:, 0], _LZ[::-1], _LR[::-1])
    P[:, 3] *= rl; P[:, 4] *= rl
    R_PERNAS = ALVO["quadril"] / 108.0
    P[:, 1] *= R_PERNAS ** 0.8; P[:, 2] *= R_PERNAS
    P[:, 0] = mapz(PERNA_TPL[:, 0])

    KU = PROJ["usados"]["alt_cotovelo"] / TPL_BRACO_COT
    KF = (PROJ["usados"]["comp_braco"] - PROJ["usados"]["alt_cotovelo"]) / (TPL_BRACO_COMP - TPL_BRACO_COT)
    def maps(s):
        s = np.asarray(s, float)
        return np.where(s <= TPL_BRACO_COT, s * KU, TPL_BRACO_COT * KU + (s - TPL_BRACO_COT) * KF)
    B = BRACO_TPL.copy()
    rb_ = np.interp(BRACO_TPL[:, 0], [10.0, 33.0, 46.0], [razao("braco"), razao("cotovelo"), razao("pulso")])
    B[:, 1] *= rb_; B[:, 2] *= rb_
    B[:, 0] = maps(BRACO_TPL[:, 0])
    BRACO_S_COTOVELO = PROJ["usados"]["alt_cotovelo"]
    BRACO_S_PULSO = PROJ["usados"]["comp_braco"]
    BRACO_P0 = np.array([-17.0 * R_SH, -1.0 * R_B, mz(138.8)])
    ABDUCAO = math.radians(PROJ["abducao"])
    FLEXAO = math.radians(12.0)
    S_FLEX0, S_FLEX1 = float(maps(29.0)), float(maps(37.0))

    # alturas usadas no modelo
    Z_GANCHO = LM["gancho"]; Z_CINTURA = LM["cintura"]; Z_QUADRIL = LM["quadril"]; Z_PEQ_Q = LM["peq"]
    Z_JOELHO = LM["joelho"]; Z_BUSTO = LM["busto"]
    Z_PESCOCO = mz(150.0); Z_TOPO = LM["topo"]; Z_COTO = LM["coto"]; Z_TORNOZELO = LM["tornozelo"]
    Z_PERNA_TOPO = mz(97.0); Z_PERNA_E_MIN = mz(63.0)

    # plano da cava (lado do braço), definido por 2 pontos do corpo-base levados para a pessoa
    R_CH = float(np.interp(127.0, _RZ, _RA))
    _X1, _Z1 = -15.8 * R_CH, mz(127.0)
    _X2, _Z2 = -17.8 * R_SH, mz(143.0)
    def xplano(z):
        return _X1 + (z - _Z1) * (_X2 - _X1) / (_Z2 - _Z1)
    N_CAVA = np.array([-(_Z2 - _Z1), 0.0, (_X2 - _X1)]); N_CAVA /= np.linalg.norm(N_CAVA)
    Z_CAVA_MIN = mz(121.0)
    Z_PINOS = (mz(130.5), mz(138.0))

    return {k: v for k, v in locals().items() if not k.startswith("__")}


# ==========================================================================
# CAMPO DE DISTÂNCIA DO CORPO (tronco + pernas, união suave)
# Usado pelo gerador final (voxel 0,2 cm) e pela prévia web (voxel ~0,7 cm).
# ==========================================================================
K_UNIAO = 4.5      # raio da concordância tronco/pernas (cm)


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


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def dist_radial(X, Y, a, bpos, bneg, n):
    bsel = np.where(Y > 0, bpos, bneg)
    r = ((np.abs(X) / a) ** n + (np.abs(Y) / bsel) ** n) ** (1.0 / n)
    rho = np.sqrt(X * X + Y * Y)
    return np.where(r > 1e-6, rho * (1.0 - 1.0 / np.maximum(r, 1e-6)), -np.minimum(a, bsel))


def gluteo_z(G, z):
    """Fator vertical do glúteo: sobe suave até a lombar, desce redondo até a coxa."""
    sz = G[4] if z > G[2] else G[5]
    return G[1] * math.exp(-0.5 * ((z - G[2]) / sz) ** 2)


def campo(c, T, P, S, G, h, zs_fixos=None):
    """Campo de distância (negativo dentro) numa grade regular. Retorna (arr, xs, ys, zs).
    zs_fixos: calcula só essas alturas (para medir contornos em fatias)."""
    Zt, Zpt, Zpe = c["Z_TORNOZELO"], c["Z_PERNA_TOPO"], c["Z_PERNA_E_MIN"]
    xmax = max(T[:, 1].max(), (np.abs(P[:, 1]) + P[:, 3]).max()) + 6.0
    ymax = (T[:, 2] + T[:, 4]).max() + S[1] + 6.0
    ymin = -((T[:, 3] - T[:, 4]).max() + G[1] + 6.0)
    xs = np.arange(-xmax, xmax + h / 2, h); ys = np.arange(ymin, ymax + h / 2, h)
    zs = np.arange(max(1.0, Zt - 6.0), T[-1, 0] + 2.0 + h / 2, h) if zs_fixos is None         else np.asarray(zs_fixos, float)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    arr = np.empty((len(xs), len(ys), len(zs)), np.float32)
    zt = np.clip(zs, T[0, 0], T[-1, 0])
    tp = [pchip(T[:, 0], T[:, k], zt) for k in range(1, 6)]
    Pv = P[::-1]
    zl = np.clip(zs, Pv[0, 0], Zpt)
    lp = [pchip(Pv[:, 0], Pv[:, k], zl) for k in range(1, 5)]
    xb, A, zb, sx, szu, szd = S
    gx = np.exp(-0.5 * ((np.sqrt(X * X + 2.0) - G[0]) / G[3]) ** 2)
    bx = np.exp(-0.5 * ((np.sqrt(X * X + 2.0) - xb) / sx) ** 2)
    for iz, z in enumerate(zs):
        gz = gluteo_z(G, z)
        if z >= T[0, 0] - 6.0:
            a, bf, bb, yc, n = (cc[iz] for cc in tp)
            sz = szu if z > zb else szd
            bfe = bf + A * math.exp(-0.5 * ((z - zb) / sz) ** 2) * bx
            bbe = bb + gz * gx
            dT = np.maximum(dist_radial(X, Y - yc, a, bfe, bbe, n), T[0, 0] - z)
        else:
            dT = np.full(X.shape, 1e3)
        cx, cy, la, lb = (cc[iz] for cc in lp)
        # o glúteo continua na parte de trás da coxa (bumbum apoiado na coxa, sem "bolsa")
        kx = math.exp(-0.5 * ((abs(cx) - G[0]) / G[3]) ** 2)
        wz = 1.0 / (1.0 + math.exp((z - G[2]) / 3.0))      # entra suave abaixo do ponto mais saliente
        lbb = lb + 1.0 * gz * kx * wz
        cap = max(z - Zpt, Pv[0, 0] - z)
        dR = np.maximum(dist_radial(X - cx, Y - cy, la, lb, lbb, 2.0), cap)
        capE = max(z - Zpt, Zpe - z)
        dE = np.maximum(dist_radial(X + cx, Y - cy, la, lb, lbb, 2.0), capE)
        arr[:, :, iz] = np.minimum(smin(dT, dR, K_UNIAO), smin(dT, dE, K_UNIAO))
    return arr, xs, ys, zs


def contorno_fatia(f2, xs, ys):
    """Pontos do contorno zero de uma fatia 2D (interpolação nas arestas da grade)."""
    pts = []
    a, b = f2[:-1, :], f2[1:, :]
    m = (a < 0) != (b < 0)
    I, J = np.nonzero(m)
    t = a[I, J] / (a[I, J] - b[I, J])
    pts.append(np.column_stack([xs[I] + t * (xs[I + 1] - xs[I]), ys[J]]))
    a, b = f2[:, :-1], f2[:, 1:]
    m = (a < 0) != (b < 0)
    I, J = np.nonzero(m)
    t = a[I, J] / (a[I, J] - b[I, J])
    pts.append(np.column_stack([xs[I], ys[J] + t * (ys[J + 1] - ys[J])]))
    return np.vstack(pts)
