# -*- coding: utf-8 -*-
"""Gera a prancha de conferência (PDF de 2 páginas + PNG da página 1) para a cliente."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.backends.backend_pdf import PdfPages

AQUI = os.path.dirname(os.path.abspath(__file__))
rel = json.load(open(os.path.join(AQUI, "relatorio_medidas.json"), encoding="utf-8"))
mc = rel["corpo_cm_reais"]; mb = rel["braco_cm_reais"]

COR = "#2b2b2b"; CINZA = "#8a8a8a"; DEST = "#b0413e"; OK = "#2e7d4f"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": COR})

def f1(v):
    return ("%.1f" % v).replace(".", ",")

# pixel <-> altura (render ortográfico 1650 px = 340 mm, centro em z = 160 mm)
def linha_px(z_cm):
    return 825 - (z_cm * 2 - 160) * 1650 / 340

CROP = (slice(105, 1615), slice(285, 935))

def vista(ax, nome, titulo, cotas=False):
    img = mpimg.imread(os.path.join(AQUI, "previa_%s.png" % nome))[CROP]
    ax.imshow(img); ax.axis("off"); ax.set_anchor("N")
    ax.set_title(titulo, fontsize=11, color=COR, pad=4)
    if cotas:
        for z, txt in ((150, "pescoço"), (122, "busto"), (110.5, "cintura"), (98.3, "peq. quadril"),
                       (88, "quadril"), (80.5, "gancho"), (46.8, "joelho")):
            y = linha_px(z) - CROP[0].start
            ax.plot([-255, img.shape[1]], [y, y], color=DEST, lw=0.7, ls=(0, (4, 3)))
            ax.text(-255, y - 8, "%s %s" % (txt, f1(z)), fontsize=7.5, color=DEST)
        ax.set_xlim(-260, img.shape[1])

def tabela(ax, linhas, cab, larg, y0=1.0, alt=0.052, fs=9, destaque=()):
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
            cor = DEST if (i in destaque and j > 0) else COR
            ax.text(x + 0.01, y, c, fontsize=fs, va="top", color=cor, transform=ax.transAxes)
            x += w
        y -= alt
    return y

# ----------------------------------------------------------------------------- dados
CONTORNOS = [  # nome, tabela, chave
    ("Busto", 90, "busto"), ("Cintura", 78, "cintura"), ("Pequeno quadril", 86.5, "peq_quadril"),
    ("Quadril", 108, "quadril"), ("Pescoço", 43, "pescoco"), ("Joelho", 37.5, "joelho"),
    ("Braço (bíceps)", 31, "braco"), ("Cotovelo", 26, "cotovelo"), ("Pulso", 15.5, "pulso"),
    ("Gancho", 74.5, "gancho"),
]
def medido(k):
    return mc.get(k, mb.get(k))

linhas_c = []; dest_c = []
for i, (n, t, k) in enumerate(CONTORNOS):
    v = medido(k)
    linhas_c.append((n, f1(t), f1(v), f1(v * 2) + " mm"))
    if abs(v - t) > 1.0:
        dest_c.append(i)

ESTIMADAS = [("Coxa (topo)", "coxa"), ("Meio da coxa", "meia_coxa"), ("Panturrilha", "panturrilha"),
             ("Canela", "canela"), ("Tornozelo", "tornozelo")]
linhas_e = [(n, "—", f1(mc[k]), f1(mc[k] * 2) + " mm") for n, k in ESTIMADAS]

ALTURAS = [  # medida, tabela, usado, observação
    ("Altura entrepernas", "80,5", "80,5", "base das alturas (gancho a 80,5 cm do chão)"),
    ("Altura cintura ao gancho", "30", "30", "cintura a 110,5 cm do chão"),
    ("Altura cintura ao solo", "118", "110,5", "AJUSTADA: não fecha com 80,5 + 30"),
    ("Altura cintura ao joelho", "68", "63,7", "proporcional à correção acima"),
    ("Altura cintura ao quadril", "24", "22,5", "proporcional à correção acima"),
    ("Altura cintura ao peq. quadril", "13", "12,2", "proporcional à correção acima"),
    ("Altura da cava", "26", "≈ 17", "AJUSTADA: 26 põe a axila na altura do pescoço"),
    ("Altura corpo frente", "27", "27", "jugular a 137,5 cm"),
    ("Altura corpo costas", "36,5", "36", "7ª cervical a 146,5 cm"),
    ("Altura do busto", "20", "20", "medida em diagonal, mamilo a 122 cm"),
    ("Abertura do busto", "22", "21 / 22", "21 em linha reta, ≈ 22 sobre o corpo"),
    ("Comprimento do ombro", "12", "≈ 12", ""),
    ("Comprimento do braço", "57,5", "57,5", "do acrômio ao pulso"),
    ("Altura do cotovelo", "33", "33", "do acrômio ao cotovelo"),
]
dest_a = [2, 6]

NAO_CONF = "Transversal frente (40) e costas (44), entrecavas frente (39,5) e costas (40), ombro a ombro frente e costas (40)."

# ----------------------------------------------------------------------------- página 1
pdf_path = os.path.join(AQUI, "prancha_manequim_giovanna_1-5.pdf")
with PdfPages(pdf_path) as pdf:
    fig = plt.figure(figsize=(16.54, 11.69))
    fig.patch.set_facecolor("white")
    fig.text(0.035, 0.955, "Manequim de moulage · Giovanna · escala 1:5", fontsize=20, weight="bold")
    fig.text(0.035, 0.925, "Prancha de conferência · perna longa e braço removível do lado direito · altura montado 306 mm", fontsize=10.5, color=CINZA)
    for x, w, (n, t) in zip([0.015, 0.215, 0.36, 0.505], [0.2, 0.145, 0.145, 0.145],
                            (("frente", "Frente"), ("lado", "Lado direito"), ("costas", "Costas"),
                             ("tres_quartos", "Três quartos"))):
        ax = fig.add_axes([x, 0.05, w, 0.84])
        vista(ax, n, t, cotas=(n == "frente"))
    axt = fig.add_axes([0.685, 0.43, 0.29, 0.46])
    fig.text(0.685, 0.912, "Contornos (cm do corpo)", fontsize=12, weight="bold")
    tabela(axt, linhas_c, ("Medida", "Tabela", "Modelo", "No manequim"), (0.38, 0.17, 0.17, 0.28),
           alt=0.085, fs=9.5, destaque=dest_c)
    fig.text(0.685, 0.395, "Para confirmar com você", fontsize=12, weight="bold")
    itens = [
        "Gancho: o modelo deu %s cm (tabela 74,5). Para chegar\nem 74,5 seria preciso achatar barriga ou bumbum.\n"
        "Vale remedir o gancho na Giovanna." % f1(mc["gancho"]),
        "Altura da cava: 26 cm acima da cintura põe a axila na\naltura do pescoço. Usei cerca de 17 cm. Vale remedir.",
        "Cintura ao solo: 118 não fecha com entrepernas 80,5 +\ncintura ao gancho 30. Usei 110,5 (a fita lateral passa\n"
        "por cima da curva do quadril).",
        "Pescoço 43 cm mantido como na tabela (acima da média).",
        "Coxa, panturrilha e tornozelo não estavam na tabela:\nestimados por proporção.",
    ]
    y = 0.37
    for it in itens:
        fig.text(0.685, y, "•", fontsize=11, color=DEST, va="top")
        fig.text(0.697, y, it, fontsize=9.5, va="top", linespacing=1.35)
        y -= 0.022 + 0.0185 * (it.count("\n") + 1)
    fig.text(0.035, 0.235, "Linhas tracejadas na vista de frente: alturas usadas no modelo (cm do chão, tamanho real).\n"
             "Escala 1:5: cada 1 cm do corpo vira 2 mm no manequim.",
             fontsize=8.5, color=CINZA)
    pdf.savefig(fig); fig.savefig(os.path.join(AQUI, "prancha_manequim_giovanna_1-5.png"), dpi=110)
    plt.close(fig)

    # ------------------------------------------------------------------------- página 2
    fig = plt.figure(figsize=(16.54, 11.69))
    fig.text(0.035, 0.955, "Relatório de medidas · manequim Giovanna 1:5", fontsize=20, weight="bold")
    fig.text(0.035, 0.925, "Valores em cm do corpo real. \"No manequim\" = valor já na escala 1:5.",
             fontsize=10.5, color=CINZA)
    ax1 = fig.add_axes([0.035, 0.42, 0.42, 0.47])
    fig.text(0.035, 0.912, "1. Contornos medidos no modelo 3D", fontsize=12, weight="bold")
    tabela(ax1, linhas_c, ("Medida", "Tabela", "Modelo", "No manequim"), (0.40, 0.18, 0.18, 0.24),
           alt=0.085, fs=9.5, destaque=dest_c)
    ax2 = fig.add_axes([0.035, 0.08, 0.42, 0.27])
    fig.text(0.035, 0.375, "2. Contornos estimados por proporção (não constam na tabela)", fontsize=12, weight="bold")
    tabela(ax2, linhas_e, ("Medida", "Tabela", "Modelo", "No manequim"), (0.40, 0.18, 0.18, 0.24),
           alt=0.15, fs=9.5)
    ax3 = fig.add_axes([0.52, 0.30, 0.45, 0.59])
    fig.text(0.52, 0.912, "3. Alturas e comprimentos usados", fontsize=12, weight="bold")
    tabela(ax3, ALTURAS, ("Medida", "Tabela", "Usado", "Observação"), (0.33, 0.1, 0.1, 0.47),
           alt=0.066, fs=9, destaque=dest_a)
    fig.text(0.52, 0.255, "4. Não conferidas no modelo", fontsize=12, weight="bold")
    fig.text(0.52, 0.235, NAO_CONF, fontsize=9, va="top", wrap=True)
    fig.text(0.52, 0.185, "5. Peças para impressão", fontsize=12, weight="bold")
    pecas = ("Tronco + perna longa + coto (80 × 58 × 288 mm) · Braço direito removível, preso por 2 pinos de 2 mm\n"
             "Base 110 × 110 mm · Haste Ø10 × %s mm (ou cavilha/tubo de 10 mm) · Altura montado 306 mm"
             % f1(rel["haste_comprimento_mm"]).replace(",0", ""))
    fig.text(0.52, 0.165, pecas, fontsize=9, va="top")
    fig.text(0.52, 0.10, "Braço: aberto 15° em relação ao corpo, antebraço 12° à frente.\n"
             "Seios: mamilos a 122 cm do chão, 21 cm entre si.", fontsize=9, va="top")
    pdf.savefig(fig)
    if os.environ.get("CHECK_P2"):
        fig.savefig(os.environ["CHECK_P2"], dpi=80)
    plt.close(fig)
print("ok", pdf_path)
