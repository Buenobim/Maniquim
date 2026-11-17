# -*- coding: utf-8 -*-
"""
Prévia rápida para a interface web (sem Blender, ~50 ms).

Usa o mesmo corpo-base do gerador (corpo.py), faz uma calibração 2D dos contornos nas
seções e devolve:
  - anéis (seções) do tronco, pernas e braço para o navegador montar a malha;
  - as linhas de cada medida (contornos e alturas) para destacar no 3D;
  - os contornos estimados da prévia.
O arquivo para impressão continua vindo do gerador completo (união suave + calibração 3D).
"""
import math
import numpy as np
import corpo

N = 72
TH = np.linspace(0, 2 * np.pi, N, endpoint=False)


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


def hull_perim(P2):
    pts = sorted(set(map(tuple, np.round(P2, 5))))
    if len(pts) < 3:
        return 0.0
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    h = np.array(lo[:-1] + up[:-1])
    return float(np.sum(np.linalg.norm(np.roll(h, -1, 0) - h, axis=1)))


def ellipse_perim(a, b):
    h = ((a - b) / (a + b)) ** 2
    return math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))


class Corpo:
    def __init__(self, proj):
        self.c = c = corpo.preparar(proj)
        self.T = c["T"].copy(); self.P = c["P"].copy(); self.S = c["S"].copy()
        self.G = c["G"].copy(); self.B = c["B"].copy()
        self.masc = c["MASC"]; self.LM = c["LM"]; self.alvo = c["ALVO"]

    # ---- seção do tronco (com relevo dos seios e glúteos), em cm
    def anel_tronco(self, z):
        T, S, G = self.T, self.S, self.G
        a, bf, bb, yc, n = (float(pchip(T[:, 0], T[:, k], [z])[0]) for k in range(1, 6))
        c = np.cos(TH); s = np.sin(TH)
        x = a * np.sign(c) * np.abs(c) ** (2.0 / n)
        rx = np.sqrt(x * x + 2.0)
        xb, A, zb, sx, szu, szd = S
        bfe = bf + A * math.exp(-0.5 * ((z - zb) / (szu if z > zb else szd)) ** 2) * \
            np.exp(-0.5 * ((rx - xb) / sx) ** 2)
        bbe = bb + G[1] * math.exp(-0.5 * ((z - G[2]) / (G[4] if z > G[2] else G[5])) ** 2) * \
            np.exp(-0.5 * ((rx - G[0]) / G[3]) ** 2)
        y = np.where(s > 0, bfe, bbe) * np.sign(s) * np.abs(s) ** (2.0 / n)
        return np.column_stack([x, y + yc, np.full(N, z)])

    def anel_perna(self, z, lado=-1):
        Pv = self.P[::-1]
        cx, cy, a, b = (float(pchip(Pv[:, 0], Pv[:, k], [z])[0]) for k in range(1, 5))
        cx = cx if lado < 0 else -cx
        return np.column_stack([cx + a * np.cos(TH), cy + b * np.sin(TH), np.full(N, z)])

    def braco_caminho(self, s):
        c = self.c
        d1 = np.array([-math.sin(c["ABDUCAO"]), 0.0, -math.cos(c["ABDUCAO"])])
        d2 = d1 * math.cos(c["FLEXAO"]) + np.array([0, 1.0, 0]) * math.sin(c["FLEXAO"])
        w = np.clip((s - c["S_FLEX0"]) / (c["S_FLEX1"] - c["S_FLEX0"]), 0, 1); w = w*w*(3 - 2*w)
        t = (1 - w)[:, None] * d1 + w[:, None] * d2
        t /= np.linalg.norm(t, axis=1, keepdims=True)
        P = np.zeros((len(s), 3))
        for i in range(1, len(s)):
            P[i] = P[i-1] + 0.5 * (t[i] + t[i-1]) * (s[i] - s[i-1])
        P += c["BRACO_P0"] - P[np.argmin(np.abs(s))]
        return P, t

    def aneis_braco(self, passo=0.8):
        B = self.B
        ss = np.arange(B[0, 0], self.c["BRACO_S_PULSO"] + 1e-6, passo)
        P, t = self.braco_caminho(ss)
        a = pchip(B[:, 0], B[:, 1], ss); b = pchip(B[:, 0], B[:, 2], ss)
        out = []
        for i in range(len(ss)):
            u = np.cross(t[i], [0, 1.0, 0]); u /= np.linalg.norm(u)
            v = np.cross(t[i], u)
            out.append(P[i] + np.outer(a[i] * np.cos(TH), u) + np.outer(b[i] * np.sin(TH), v))
        return ss, out

    # ---- medida de contorno na fatia do MESMO campo usado no arquivo final
    def medir_fatias(self, niveis, h=0.25):
        import corpo as _c
        zs = list(niveis.values())
        arr, xs, ys, _ = _c.campo(self.c, self.T, self.P, self.S, self.G, h, zs_fixos=zs)
        out = {}
        for i, k in enumerate(niveis):
            pts = _c.contorno_fatia(arr[:, :, i], xs, ys)
            out[k] = hull_perim(pts)
        return out

    # ---- calibração (mesma lógica do gerador)
    def calibrar(self, it=8):
        LM, A = self.LM, self.alvo
        mz = self.c["mz"]
        niveis = {"busto": LM["busto"], "cintura": LM["cintura"], "peq_quadril": LM["peq"],
                  "quadril": LM["quadril"], "pescoco": mz(150.0)}
        z_pesc = mz(146.5)
        for _ in range(it):
            med = self.medir_fatias(niveis)
            for k, z in niveis.items():
                m = med[k]
                r = A[k] / m
                w = np.exp(-0.5 * ((self.T[:, 0] - z) / 3.5) ** 2)
                if k == "busto" and not self.masc:
                    self.S[1] = max(0.5, self.S[1] + (A[k] - m) * 0.4)
                elif k == "quadril" and not self.masc:
                    self.G[1] = max(0.5, self.G[1] + (A[k] - m) * 0.35)
                    if self.G[1] <= 0.5 and r < 1:
                        self.T[:, 1] *= r ** np.exp(-0.5 * ((self.T[:, 0] - z) / 4.0) ** 2)
                else:
                    if k == "pescoco":
                        w = np.where(self.T[:, 0] >= z_pesc, 1.0, w * 0.3)
                    self.T[:, 1:4] *= r ** w[:, None]
        # pernas e braço: perímetro da elipse no nível de cada anel
        Pn = {"coxa": 77.0, "meia_coxa": 60.0, "joelho": 46.8, "panturrilha": 34.0, "canela": 15.0,
              "tornozelo": 9.0}
        for k, tz in Pn.items():
            i = int(np.argmin(np.abs(self.P[:, 0] - mz(tz))))
            self.P[i, 3:5] *= A[k] / ellipse_perim(self.P[i, 3], self.P[i, 4])
        maps = self.c["maps"]
        for k, ts in (("braco", 15.0), ("cotovelo", 33.0), ("pulso", 55.0)):
            i = int(np.argmin(np.abs(self.B[:, 0] - float(maps(ts)))))
            r = A[k] / ellipse_perim(self.B[i, 1], self.B[i, 2])
            self.B[i, 1:3] *= r
            if k == "pulso":
                self.B[-1, 1:3] *= r

    def medidas_previa(self):
        LM = self.LM; mz = self.c["mz"]
        r = self.medir_fatias({"busto": LM["busto"], "cintura": LM["cintura"], "peq_quadril": LM["peq"],
                               "quadril": LM["quadril"], "pescoco": mz(150.0)})
        r["gancho"] = self.gancho_campo() if getattr(self, "_campo", None) else self.gancho_comprimento()
        return r

    def gancho_campo(self):
        """Gancho no plano do meio do corpo (x=0), pelo mesmo método do gerador final."""
        import corpo as _c
        arr, xs, ys, zs, h = self._campo
        arr = arr[1:-1, 1:-1, 1:-1]
        i = int(np.argmin(np.abs(xs)))
        pts = _c.contorno_fatia(arr[i], ys, zs)          # (y, z)
        LM = self.LM
        pts = pts[(pts[:, 1] <= LM["cintura"]) & (pts[:, 1] >= LM["gancho"] - 2.0)]
        cy, cz = -0.5, self.c["mz"](97.0)
        ang = np.degrees(np.arctan2(pts[:, 1] - cz, pts[:, 0] - cy)); ang = np.where(ang > 90, ang - 360, ang)
        rr = np.hypot(pts[:, 0] - cy, pts[:, 1] - cz)
        sel = []
        b = np.floor(ang).astype(int)
        for k in np.unique(b):
            m = b == k; j = np.argmax(rr[m]); sel.append((ang[m][j], pts[m][j]))
        sel.sort(key=lambda t: -t[0])
        P2 = np.array([p for _, p in sel])
        return float(np.sum(np.linalg.norm(np.diff(P2, axis=0), axis=1)))

    # ---- contorno sagital (gancho)
    def gancho_linha(self):
        LM = self.LM
        zs = np.linspace(LM["cintura"], self.T[0, 0] + 0.3, 40)
        frente, costas = [], []
        for z in zs:
            an = self.anel_tronco(z)
            frente.append([0.0, an[N // 4, 1], z]); costas.append([0.0, an[3 * N // 4, 1], z])
        return np.array(frente + costas[::-1])

    def gancho_comprimento(self):
        L = self.gancho_linha()
        return float(np.sum(np.linalg.norm(np.diff(L, axis=0), axis=1)))


def _lst(a, nd=1):
    return np.round(np.asarray(a, float), nd).tolist()


def gerar_previa(proj):
    cp = Corpo(proj)
    cp.calibrar()
    c = cp.c; LM = cp.LM; mz = c["mz"]; maps = c["maps"]
    sx = -1.0 if proj["lado"] == "D" else 1.0     # modelado com perna/braço em x<0; espelha para o lado D
    def esp(P):
        P = np.array(P, float)
        if sx < 0:
            P[..., 0] *= -1
        return P

    z_topo = LM["topo"]
    Vm, Tm = malha_corpo(cp)
    Vm = esp(Vm)
    if sx < 0:
        Tm = Tm[:, ::-1]      # espelhar inverte a orientação dos triângulos
    import base64
    malha = {"v": base64.b64encode(np.round(Vm, 2).astype("<f4").tobytes()).decode(),
             "i": base64.b64encode(Tm.astype("<u2" if len(Vm) < 65535 else "<u4").tobytes()).decode(),
             "i16": bool(len(Vm) < 65535)}
    braco = []
    ss = []
    if proj["com_braco"]:
        ss, aneis = cp.aneis_braco()
        braco = [esp(a) for a in aneis]

    # ---- linhas das medidas
    linhas = {}
    def anel_fechado(P):
        P = np.asarray(P); return np.vstack([P, P[:1]])
    for k, z in (("busto", LM["busto"]), ("cintura", LM["cintura"]), ("peq_quadril", LM["peq"]),
                 ("quadril", LM["quadril"]), ("pescoco", mz(150.0))):
        an = cp.anel_tronco(z)
        an = an * np.array([1.03, 1.03, 1]) + np.array([0, 0.02 * an[:, 1].mean(), 0])
        linhas[k] = anel_fechado(esp(an))
    for k, tz in (("coxa", 77.0), ("joelho", 46.8), ("panturrilha", 34.0), ("tornozelo", 10.0)):
        an = cp.anel_perna(mz(tz), -1)
        cxy = an[:, :2].mean(0)
        an[:, :2] = cxy + (an[:, :2] - cxy) * 1.05
        linhas[k] = anel_fechado(esp(an))
    if proj["com_braco"]:
        Bp, Bt = cp.braco_caminho(np.arange(-1.0, c["BRACO_S_PULSO"] + 1e-6, 0.5))
        sarr = np.arange(-1.0, c["BRACO_S_PULSO"] + 1e-6, 0.5)
        for k, s in (("braco", float(maps(15.0))), ("cotovelo", c["BRACO_S_COTOVELO"]),
                     ("pulso", c["BRACO_S_PULSO"] - 1.0)):
            i = int(np.argmin(np.abs(np.asarray(ss) - s)))
            an = braco[i]; ctr = an.mean(0)
            linhas[k] = anel_fechado(ctr + (an - ctr) * 1.06)
        i_cot = int(np.argmin(np.abs(sarr - c["BRACO_S_COTOVELO"])))
        lat = np.array([-1.0, 0, 0]) * 6.5
        linhas["comp_braco"] = esp(Bp + lat)
        linhas["alt_cotovelo"] = esp(Bp[:i_cot + 1] + lat * 1.3)
    linhas["gancho"] = esp(cp.gancho_linha())

    # alturas (linhas de cota na lateral do lado oposto ao braço, ou na frente/costas)
    def x_lado(z):
        an = cp.anel_tronco(min(max(z, cp.T[0, 0]), z_topo))
        return an[:, 0].max()
    xq = max(x_lado(LM["quadril"]), x_lado(LM["busto"])) + 4.0
    def vert(z0, z1, x, y=0.0):
        return esp(np.array([[x, y, z0], [x, y, z1]]))
    linhas["cint_solo"] = vert(0.0, LM["cintura"], xq + 6)
    linhas["cint_joelho"] = vert(LM["joelho"], LM["cintura"], xq + 3)
    linhas["cint_quadril"] = vert(LM["quadril"], LM["cintura"], xq)
    linhas["cint_peq"] = vert(LM["peq"], LM["cintura"], xq - 1.5)
    linhas["cint_gancho"] = vert(LM["gancho"], LM["cintura"], 0.0, cp.anel_tronco(LM["cintura"])[N // 4, 1] + 4)
    linhas["entrepernas"] = vert(0.0, LM["gancho"], 0.0, 0.0)
    yf = cp.anel_tronco(LM["jugular"])[N // 4, 1]
    linhas["alt_frente"] = vert(LM["cintura"], LM["jugular"], 0.0, max(yf, cp.anel_tronco(LM["busto"])[N // 4, 1]) + 3)
    yb = cp.anel_tronco(LM["c7"])[3 * N // 4, 1]
    linhas["alt_costas"] = vert(LM["cintura"], LM["c7"], 0.0, min(yb, cp.anel_tronco(LM["quadril"])[3 * N // 4, 1]) - 3)
    linhas["alt_cava"] = vert(LM["cintura"], LM["cava"], -(x_lado(LM["cava"]) + 1.5))
    xb, A, zb = cp.S[0], cp.S[1], LM["busto"]
    an_b = cp.anel_tronco(zb)
    ymam = an_b[np.argmin(np.abs(an_b[:, 0] - xb) + (an_b[:, 1] < 0) * 99), 1]
    jug = np.array([0.0, yf, LM["jugular"]])
    linhas["alt_busto"] = esp(np.array([jug, [xb, ymam + 0.5, zb]]))
    linhas["abertura_busto"] = esp(np.array([[-xb, ymam + 0.5, zb], [xb, ymam + 0.5, zb]]))
    zo = c["mz"](145.5)
    an_n = cp.anel_tronco(zo)
    linhas["ombro"] = esp(np.array([[-an_n[:, 0].max() * 0.95, -1.5, zo], [c["_X2"] if "_X2" in c else -18, -1.5, c["mz"](142.0)]]))

    # base e haste (para o desenho)
    Pv = cp.P[::-1]
    cxh = -float(pchip(Pv[:, 0], Pv[:, 1], [LM["coto"]])[0]); cyh = float(pchip(Pv[:, 0], Pv[:, 2], [LM["coto"]])[0])
    esc = proj["esc_mm_por_cm"]
    haste_d_cm = max(6.0, min(16.0, 10.0 * esc / 2.0)) / esc
    base_cm = 110.0 * esc / 2.0 / esc

    return {
        "malha": malha, "braco": _lst(braco),
        "linhas": {k: _lst(v) for k, v in linhas.items()},
        "haste": {"x": sx * -cxh * -1 if sx < 0 else cxh, "y": cyh, "d": haste_d_cm, "topo": LM["coto"],
                  "base": base_cm},
        "medidas_previa": {k: round(v, 1) for k, v in cp.medidas_previa().items()},
        "altura_mm": round(z_topo * esc, 1),
    }


# ==========================================================================
# MALHA DA PRÉVIA = mesmo campo do gerador final (corpo.campo), em voxel maior,
# extraída por "surface nets" (numpy puro).
# ==========================================================================
_CANTOS = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1], [1, 1, 1]])
_ARESTAS = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]


def surface_nets(f, origem, h, suavizar=2):
    nx, ny, nz = f.shape
    c = [f[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k] for i, j, k in _CANTOS]
    dentro = [x < 0 for x in c]
    ativo = np.logical_or.reduce(dentro) & ~np.logical_and.reduce(dentro)
    I, J, K = np.nonzero(ativo)
    n = len(I)
    soma = np.zeros((n, 3)); cont = np.zeros(n)
    for a, b in _ARESTAS:
        fa = c[a][ativo]; fb = c[b][ativo]
        m = (fa < 0) != (fb < 0)
        t = fa[m] / (fa[m] - fb[m])
        soma[m] += _CANTOS[a] + t[:, None] * (_CANTOS[b] - _CANTOS[a])
        cont[m] += 1
    V = (soma / cont[:, None] + np.column_stack([I, J, K])) * h + origem
    vid = -np.ones(ativo.shape, np.int64); vid[ativo] = np.arange(n)
    quads = []
    # arestas ao longo de x, y e z da grade: cada uma com troca de sinal gera um quadrilátero
    for eixo in range(3):
        sl0 = [slice(1, -1)] * 3; sl1 = [slice(1, -1)] * 3
        sl0[eixo] = slice(0, -1); sl1[eixo] = slice(1, None)
        a = f[tuple(sl0)] < 0; b = f[tuple(sl1)] < 0
        A, B, C = np.nonzero(a != b)
        p = [A, B, C]
        for d in range(3):
            if d != eixo:
                p[d] = p[d] + 1
        u, v = [d for d in range(3) if d != eixo]
        def cel(du, dv):
            q = list(p); q[u] = q[u] - du; q[v] = q[v] - dv
            return vid[q[0], q[1], q[2]]
        q = np.column_stack([cel(1, 1), cel(0, 1), cel(0, 0), cel(1, 0)])
        inv = a[A, B, C]
        if eixo == 1:
            inv = ~inv
        q[inv] = q[inv][:, ::-1]
        quads.append(q)
    Q = np.vstack(quads)
    Q = Q[(Q >= 0).all(1)]
    # suavização laplaciana leve (vizinhos pelas arestas dos quads)
    if suavizar:
        ei = np.concatenate([Q[:, [0, 1]], Q[:, [1, 2]], Q[:, [2, 3]], Q[:, [3, 0]]])
        for _ in range(suavizar):
            acc = np.zeros_like(V); cnt = np.zeros(len(V))
            np.add.at(acc, ei[:, 0], V[ei[:, 1]]); np.add.at(cnt, ei[:, 0], 1)
            np.add.at(acc, ei[:, 1], V[ei[:, 0]]); np.add.at(cnt, ei[:, 1], 1)
            m = cnt > 0
            V[m] = 0.5 * V[m] + 0.5 * acc[m] / cnt[m, None]
    T = np.vstack([Q[:, [0, 2, 1]], Q[:, [0, 3, 2]]])   # normais para fora
    return V, T


def malha_corpo(cp, h=0.7):
    import corpo as _c
    arr, xs, ys, zs = _c.campo(cp.c, cp.T, cp.P, cp.S, cp.G, h)
    # cortes como no arquivo final: topo do pescoço, coto da perna curta e fim da perna longa
    X = xs[:, None, None]; Z = zs[None, None, :]
    LM = cp.LM
    arr = np.maximum(arr, Z - LM["topo"])
    arr = np.where(X > 0, np.maximum(arr, LM["coto"] - Z), arr)          # perna curta (x>0 antes do espelho)
    arr = np.where(X < 0.5, np.maximum(arr, LM["tornozelo"] - Z), arr)   # perna longa
    arr = np.pad(arr, 1, constant_values=1e3).astype(np.float32)
    org = np.array([xs[0], ys[0], zs[0]]) - h
    V, Tr = surface_nets(arr, org, h)
    cp._campo = (arr, xs, ys, zs, h)
    return V, Tr
