# -*- coding: utf-8 -*-
"""Prancha de conferência (PDF de 2 páginas + PNG da página 1) a partir do projeto e do relatório."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.backends.backend_pdf import PdfPages
from medidas import ROTULO, _f as f1

COR = "#2b2b2b"; CINZA = "#8a8a8a"; DEST = "#b0413e"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": COR})

CONTORNOS = ["busto", "cintura", "peq_quadril", "quadril", "pescoco", "joelho", "braco", "cotovelo",
             "pulso", "gancho"]
NOMES = {"busto": "Busto", "cintura": "Cintura", "peq_quadril": "Pequeno quadril", "quadril": "Quadril",
         "pescoco": "Pescoço", "joelho": "Joelho", "braco": "Braço (bíceps)", "cotovelo": "Cotovelo",
         "pulso": "Pulso", "gancho": "Gancho", "coxa": "Coxa (topo)", "meia_coxa": "Meio da coxa",
         "panturrilha": "Panturrilha", "canela": "Canela", "tornozelo": "Tornozelo"}
ALTURAS = ["entrepernas", "cint_gancho", "cint_solo", "cint_joelho", "cint_quadril", "cint_peq",
           "alt_cava", "alt_frente", "alt_costas", "alt_busto", "abertura_busto", "comp_braco", "alt_cotovelo"]


def _fmt(v, casas=1):
    return ("%.*f" % (casas, v)).replace(".", ",")


def _tabela(ax, linhas, cab, larg, y0=1.0, alt=0.052, fs=9, destaque=()):
    ax.axis("off")
    x = 0
    for c, w in zip(cab, larg):
        ax.text(x + 0.01, y0, c, fontsize=fs, weight="bold", va="top", transform=ax.transAxes)
        x += w
    ax.plot([0, 1], [y0 - alt * 0.75] * 2, color=COR, lw=0.8, transform=ax.transAxes)
    y = y0 - alt
    for i, ln in enumerate(linhas):
        if i % 2 == 0:
            ax.add_patch(plt.Rectangle((0, y - alt * 0.78), 1, alt, color="#f2efea",
                                       transform=ax.transAxes, zorder=0, lw=0))
        x = 0
        for j, (c, w) in enumerate(zip(ln, larg)):
            ax.text(x + 0.01, y, c, fontsize=fs, va="top", transform=ax.transAxes,
                    color=DEST if (i in destaque and j > 0) else COR)
            x += w
        y -= alt


def _quebra(txt, n=56):
    pal = txt.split(); lin = []; cur = ""
    for p in pal:
        if len(cur) + len(p) + 1 > n:
            lin.append(cur); cur = p
        else:
            cur = (cur + " " + p).strip()
    lin.append(cur)
    return "\n".join(lin)


def gerar(pasta):
    proj = json.load(open(os.path.join(pasta, "projeto.json"), encoding="utf-8"))
    rel = json.load(open(os.path.join(pasta, "relatorio_medidas.json"), encoding="utf-8"))
    med = dict(rel["corpo_cm_reais"]); med.update(rel.get("braco_cm_reais", {}))
    tab = proj["medidas"]; est = set(proj["estimadas"]); esc = proj["esc_mm_por_cm"]
    if proj.get("sexo") == "M":
        NOMES["busto"] = "Tórax (busto)"
    nome = proj["nome"]; escala = "1:%s" % f1(proj["escala"])
    lado_txt = "direito" if proj["lado"] == "D" else "esquerdo"

    # -------- contornos
    lin_c, dest_c, avisos_pos = [], [], []
    for k in CONTORNOS:
        if k not in med:
            continue
        t = tab.get(k)
        v = med[k]
        lin_c.append((NOMES[k], _fmt(t) if t is not None else "estim.", _fmt(v), _fmt(v * esc) + " mm"))
        if t is not None and abs(v - t) > 1.0:
            dest_c.append(len(lin_c) - 1)
            extra = " Para chegar no valor da tabela seria preciso achatar barriga ou bumbum; vale remedir." \
                if k == "gancho" else ""
            avisos_pos.append("%s: o modelo deu %s cm (tabela %s).%s" % (NOMES[k], _fmt(v), _fmt(t), extra))
    lin_e = [(NOMES[k], _fmt(tab[k]) if k in tab else "—", _fmt(med[k]), _fmt(med[k] * esc) + " mm")
             for k in ("coxa", "meia_coxa", "panturrilha", "canela", "tornozelo") if k in med]
    avisos = avisos_pos + [a for a in proj["avisos"]]

    # -------- alturas
    us = proj["usados"]; lin_a = []; dest_a = []
    obs = {"cint_solo": "vertical; a fita lateral passa sobre o quadril",
           "cint_joelho": "corrigida pela curva do quadril", "cint_quadril": "corrigida pela curva do quadril",
           "cint_peq": "corrigida pela curva do quadril", "alt_busto": "em diagonal",
           "abertura_busto": "em linha reta", "comp_braco": "do acrômio ao pulso",
           "alt_cotovelo": "do acrômio ao cotovelo"}
    for k in ALTURAS:
        if k not in us:
            continue
        t = tab.get(k)
        u = us[k]
        ajust = t is not None and abs(u - t) > {"cint_solo": 3.0, "alt_cava": 2.0}.get(k, 99)
        o = obs.get(k, "")
        if k in est:
            o = "estimada por proporção"
        elif ajust:
            o = "AJUSTADA: " + ("não fecha c/ entrepernas + gancho" if k == "cint_solo"
                                else "tabela põe a axila fora do lugar")
        lin_a.append((ROTULO[k], _fmt(t) if t is not None else "—", _fmt(u), o))
        if ajust:
            dest_a.append(len(lin_a) - 1)

    # -------- imagens: recorte comum e mapeamento altura -> pixel
    imgs = {v: mpimg.imread(os.path.join(pasta, "previa_%s.png" % v)) for v in
            ("frente", "lado", "costas", "tres_quartos")}
    mask = np.zeros(imgs["frente"].shape[:2], bool)
    for im in imgs.values():
        mask |= im[:, :, :3].mean(2) < 0.97
    rows = np.where(mask.any(1))[0]; cols = np.where(mask.any(0))[0]
    r0, r1 = max(0, rows.min() - 15), rows.max() + 15
    c0, c1 = max(0, cols.min() - 15), cols.max() + 15
    rd = rel["render"]; resy = rd["res"][1]
    def linha_px(z_cm):
        return resy / 2 - (z_cm * esc - rd["zc_mm"]) * resy / rd["ortho_mm"] - r0
    L = proj["landmarks"]
    cotas = [(L["topo"] - 3 * (L["topo"] - L["c7"]) / 6.5, "pescoço"), (L["busto"], "busto"),
             (L["cintura"], "cintura"), (L["peq"], "peq. quadril"), (L["quadril"], "quadril"),
             (L["gancho"], "gancho"), (L["joelho"], "joelho")]

    pdf_path = os.path.join(pasta, "prancha_manequim_%s.pdf" % nome)
    png_path = os.path.join(pasta, "prancha_manequim_%s.png" % nome)
    with PdfPages(pdf_path) as pdf:
        fig = plt.figure(figsize=(16.54, 11.69))
        fig.text(0.035, 0.955, "Manequim de moulage · %s · escala %s" % (nome, escala), fontsize=20, weight="bold")
        fig.text(0.035, 0.925, "Prancha de conferência · perna longa%s do lado %s · altura montado %s mm" %
                 (" e braço removível" if proj["com_braco"] else "", lado_txt, _fmt(rel["altura_montado_mm"], 0)),
                 fontsize=10.5, color=CINZA)
        for x, w, (v, t) in zip([0.015, 0.215, 0.36, 0.505], [0.2, 0.145, 0.145, 0.145],
                                (("frente", "Frente"), ("lado", "Lado " + lado_txt), ("costas", "Costas"),
                                 ("tres_quartos", "Três quartos"))):
            ax = fig.add_axes([x, 0.05, w, 0.84])
            im = imgs[v][r0:r1, c0:c1]
            ax.imshow(im); ax.axis("off"); ax.set_anchor("N")
            ax.set_title(t, fontsize=11, pad=4)
            if v == "frente":
                margem = int(0.4 * im.shape[1])
                for z, txt in cotas:
                    y = linha_px(z)
                    ax.plot([-margem + 5, im.shape[1]], [y, y], color=DEST, lw=0.7, ls=(0, (4, 3)))
                    ax.text(-margem + 5, y - 8, "%s %s" % (txt, _fmt(z)), fontsize=7.5, color=DEST)
                ax.set_xlim(-margem, im.shape[1])
        fig.text(0.685, 0.912, "Contornos (cm do corpo)", fontsize=12, weight="bold")
        _tabela(fig.add_axes([0.685, 0.43, 0.29, 0.46]), lin_c, ("Medida", "Tabela", "Modelo", "No manequim"),
                (0.38, 0.17, 0.17, 0.28), alt=0.085, fs=9.5, destaque=dest_c)
        fig.text(0.685, 0.395, "Para confirmar com você", fontsize=12, weight="bold")
        y = 0.37
        for a in avisos[:7]:
            t = _quebra(a)
            fig.text(0.685, y, "•", fontsize=11, color=DEST, va="top")
            fig.text(0.697, y, t, fontsize=9.3, va="top", linespacing=1.35)
            y -= 0.02 + 0.018 * (t.count("\n") + 1)
        fig.text(0.035, 0.03, "Linhas tracejadas na vista de frente: alturas usadas no modelo (cm do chão, tamanho real). "
                 "Escala %s: cada 1 cm do corpo vira %s mm no manequim." % (escala, _fmt(esc)), fontsize=8.5, color=CINZA)
        pdf.savefig(fig); fig.savefig(png_path, dpi=110); plt.close(fig)

        fig = plt.figure(figsize=(16.54, 11.69))
        fig.text(0.035, 0.955, "Relatório de medidas · %s · escala %s" % (nome, escala), fontsize=20, weight="bold")
        fig.text(0.035, 0.925, "Valores em cm do corpo real. \"No manequim\" = valor já na escala %s." % escala,
                 fontsize=10.5, color=CINZA)
        fig.text(0.035, 0.89, "1. Contornos medidos no modelo 3D", fontsize=12, weight="bold")
        _tabela(fig.add_axes([0.035, 0.42, 0.42, 0.45]), lin_c, ("Medida", "Tabela", "Modelo", "No manequim"),
                (0.40, 0.18, 0.18, 0.24), alt=0.085, fs=9.5, destaque=dest_c)
        fig.text(0.035, 0.375, "2. Pernas (tabela ou estimado por proporção)", fontsize=12, weight="bold")
        _tabela(fig.add_axes([0.035, 0.08, 0.42, 0.27]), lin_e, ("Medida", "Tabela", "Modelo", "No manequim"),
                (0.40, 0.18, 0.18, 0.24), alt=0.15, fs=9.5)
        fig.text(0.52, 0.89, "3. Alturas e comprimentos usados", fontsize=12, weight="bold")
        _tabela(fig.add_axes([0.52, 0.30, 0.45, 0.57]), lin_a, ("Medida", "Tabela", "Usado", "Observação"),
                (0.36, 0.09, 0.09, 0.46), alt=0.066, fs=8.6, destaque=dest_a)
        fig.text(0.52, 0.255, "4. Não conferidas no modelo", fontsize=12, weight="bold")
        nc = [("transv_frente", "Transversal frente"), ("transv_costas", "Transversal costas"),
              ("entrecavas_frente", "Entrecavas frente"), ("entrecavas_costas", "Entrecavas costas"),
              ("oo_frente", "Ombro a ombro frente"), ("oo_costas", "Ombro a ombro costas")]
        fig.text(0.52, 0.235, _quebra(" · ".join("%s (%s)" % (n, _fmt(tab[k])) for k, n in nc if k in tab), 120),
                 fontsize=9, va="top")
        fig.text(0.52, 0.17, "5. Peças para impressão", fontsize=12, weight="bold")
        bb = rel["tronco_perna"]["bbox_mm"]
        dims = " × ".join(_fmt(bb[1][i] - bb[0][i], 0) for i in range(3))
        txt = "Tronco + perna longa + coto (%s mm)" % dims
        if proj["com_braco"]:
            txt += " · Braço removível, preso por 2 pinos de 2 mm"
        txt += "\nBase %s × %s mm · Haste Ø%s × %s mm (ou cavilha/tubo) · Altura montado %s mm" % (
            rel["base_lado_mm"], rel["base_lado_mm"], rel["haste"]["diametro_mm"],
            _fmt(rel["haste"]["comprimento_mm"], 0), _fmt(rel["altura_montado_mm"], 0))
        if proj["com_braco"]:
            txt += "\nBraço aberto %s° em relação ao corpo, antebraço 12° à frente." % f1(proj["abducao"])
        fig.text(0.52, 0.15, txt, fontsize=9, va="top", linespacing=1.5)
        pdf.savefig(fig); fig.savefig(png_path.replace(".png", "_relatorio.png"), dpi=110); plt.close(fig)
    return pdf_path, png_path


if __name__ == "__main__":
    import sys
    print(gerar(sys.argv[1]))
