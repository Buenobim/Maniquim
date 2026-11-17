# -*- coding: utf-8 -*-
"""
Leitura da planilha de medidas e montagem do "projeto" de cada manequim.

A planilha segue a tabela da cliente (mesmas linhas e mesma ordem), com uma coluna
por pessoa/tamanho. No fim há linhas opcionais (medidas extras e opções do manequim).

Este módulo roda no Python normal (não precisa do Blender). Ele:
  1. lê a coluna da pessoa;
  2. confere se as medidas fecham entre si e gera avisos;
  3. calcula as alturas verticais (landmarks) usadas pelo modelo;
  4. estima, por proporção, o que não foi informado.
"""
import math, unicodedata, re

# ----------------------------------------------------------------------------
# Linhas da tabela (rótulo exatamente como na planilha da cliente -> chave interna)
# ----------------------------------------------------------------------------
LINHAS_CONTORNO = [
    ("Busto", "busto"), ("Cintura", "cintura"), ("Quadril", "quadril"),
    ("Pequeno Quadril", "peq_quadril"), ("Pescoço", "pescoco"), ("Ombro", "ombro"),
    ("Braço", "braco"), ("Cotovelo", "cotovelo"), ("Pulso", "pulso"),
    ("Joelho", "joelho"), ("Gancho", "gancho"),
]
LINHAS_ALTURA = [
    ("Altura Corpo Frente", "alt_frente"), ("Altura Corpo Costas", "alt_costas"),
    ("Altura Busto", "alt_busto"), ("Altura da Cava", "alt_cava"),
    ("Altura Cintura ao Quadril", "cint_quadril"), ("Altura Cintura ao Joelho", "cint_joelho"),
    ("Altura Cintura ao Solo", "cint_solo"), ("Altura Cintura ao Gancho", "cint_gancho"),
    ("Comprimento do Braço", "comp_braco"), ("Altura do Cotovelo", "alt_cotovelo"),
    ("Altura da Cintura ao Pequeno Quadril", "cint_peq"), ("Altura Entrepernas", "entrepernas"),
]
LINHAS_OUTRAS = [
    ("Abertura do Busto (Entre Mamilos)", "abertura_busto"),
    ("Transversal Frente", "transv_frente"), ("Transversal Costas", "transv_costas"),
    ("Entrecavas Frente", "entrecavas_frente"), ("Entrecavas Costas", "entrecavas_costas"),
    ("Ombro a Ombro Frente", "oo_frente"), ("Ombro a Ombro Costas", "oo_costas"),
]
LINHAS_EXTRAS = [  # opcionais: se vazias, são estimadas por proporção
    ("Altura Total", "altura_total"), ("Coxa", "coxa"),
    ("Panturrilha", "panturrilha"), ("Tornozelo", "tornozelo"),
]
LINHAS_OPCOES = [
    ("Sexo (F/M)", "sexo"), ("Escala (1:N)", "escala"),
    ("Lado da perna e do braço (D/E)", "lado"), ("Com braço (Sim/Não)", "com_braco"),
    ("Abertura do braço (graus)", "abducao"),
]
TODAS = LINHAS_CONTORNO + LINHAS_ALTURA + LINHAS_OUTRAS + LINHAS_EXTRAS + LINHAS_OPCOES
ROTULO = {k: r for r, k in TODAS}

OBRIGATORIAS = ["busto", "cintura", "quadril", "pescoco", "ombro", "braco", "cotovelo", "pulso",
                "joelho", "alt_frente", "alt_costas", "alt_busto", "cint_gancho", "entrepernas",
                "comp_braco", "alt_cotovelo", "abertura_busto"]

OPCOES_PADRAO = {"sexo": "F", "escala": 5, "lado": "D", "com_braco": "Sim", "abducao": 15.0}


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)

_MAPA = {_norm(r): k for r, k in TODAS}


def _num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return s


# ----------------------------------------------------------------------------
# Leitura da planilha
# ----------------------------------------------------------------------------
def ler_planilha(caminho, todas=False):
    """Retorna {nome_coluna: {chave: valor}} para cada coluna que tenha dados (todas=True: inclui vazias)."""
    import openpyxl
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb.worksheets[0]
    # acha a linha de cabeçalho ("Medidas")
    cab_linha = cab_col = None
    for row in ws.iter_rows():
        for c in row:
            if c.value is not None and _norm(c.value) == "medidas":
                cab_linha, cab_col = c.row, c.column
                break
        if cab_linha:
            break
    if not cab_linha:
        raise ValueError("Não achei a célula 'Medidas' no cabeçalho da planilha.")
    colunas = {}
    for c in ws[cab_linha]:
        if c.column > cab_col and c.value not in (None, ""):
            colunas[c.column] = str(c.value).strip()
    pessoas = {nome: {} for nome in colunas.values()}
    for row in ws.iter_rows(min_row=cab_linha + 1):
        rot = row[cab_col - 1].value
        if rot is None:
            continue
        chave = _MAPA.get(_norm(rot))
        if not chave:
            continue
        for col, nome in colunas.items():
            v = _num(row[col - 1].value)
            if v is not None:
                pessoas[nome][chave] = v
    if todas:
        return pessoas
    # só colunas com alguma medida de contorno
    return {n: d for n, d in pessoas.items() if any(k in d for _, k in LINHAS_CONTORNO)}


# ----------------------------------------------------------------------------
# Projeto: alturas, alvos, estimativas e avisos
# ----------------------------------------------------------------------------
def montar_projeto(nome, med):
    m = dict(med)
    avisos = []        # textos para a prancha ("Para confirmar")
    estimadas = []     # chaves estimadas por proporção
    usados = {}        # valor usado no modelo para cada medida de altura (cm)

    falt = [ROTULO[k] for k in OBRIGATORIAS if not isinstance(m.get(k), float)]
    if falt:
        raise ValueError("%s: faltam medidas obrigatórias: %s" % (nome, ", ".join(falt)))

    op = dict(OPCOES_PADRAO)
    for k in op:
        if k in m and m[k] not in (None, ""):
            op[k] = m[k]
    sexo = "M" if str(op["sexo"]).strip().upper()[:1] in ("M", "H") else "F"
    escala = float(op["escala"])
    lado = "E" if str(op["lado"]).strip().upper().startswith("E") else "D"
    com_braco = not str(op["com_braco"]).strip().lower().startswith(("n", "0", "f"))
    abducao = float(op["abducao"])

    # --- contornos opcionais (proporção a partir do corpo-base) ---
    def estima(k, valor):
        if not isinstance(m.get(k), float):
            m[k] = round(valor, 1); estimadas.append(k)
    if sexo == "M":
        estima("peq_quadril", m["cintura"] + 0.45 * (m["quadril"] - m["cintura"]))
        estima("coxa", 0.57 * m["quadril"])
    else:
        estima("peq_quadril", m["cintura"] + 0.283 * (m["quadril"] - m["cintura"]))
        estima("coxa", 61.0 / 108.0 * m["quadril"])
    estima("panturrilha", 37.0 / 37.5 * m["joelho"])
    estima("tornozelo", 21.5 / 37.5 * m["joelho"])
    m["meia_coxa"] = round(48.0 / 61.0 * m["coxa"], 1)
    m["canela"] = round(22.5 / 21.5 * m["tornozelo"], 1)

    # --- alturas verticais (cm do chão) ---
    L = {}
    L["gancho"] = m["entrepernas"]
    L["cintura"] = m["entrepernas"] + m["cint_gancho"]
    usados["entrepernas"] = L["gancho"]; usados["cint_gancho"] = m["cint_gancho"]
    if isinstance(m.get("cint_solo"), float):
        dif = m["cint_solo"] - L["cintura"]
        f = L["cintura"] / m["cint_solo"]
        if abs(dif) > 3.0:
            avisos.append("Cintura ao solo: %s não fecha com entrepernas %s + cintura ao gancho %s "
                          "(= %s). Usei %s." % (_f(m["cint_solo"]), _f(m["entrepernas"]),
                                                _f(m["cint_gancho"]), _f(L["cintura"]), _f(L["cintura"])))
        if not 0.85 <= f <= 1.05:
            avisos.append("Cintura ao solo muito diferente do esperado: alturas laterais não corrigidas.")
            f = 1.0
    else:
        f = 1.0
    usados["cint_solo"] = L["cintura"]

    def lateral(k, padrao):
        if isinstance(m.get(k), float):
            usados[k] = round(m[k] * f, 1)
        else:
            usados[k] = round(padrao, 1); estimadas.append(k)
        return usados[k]
    cg = m["cint_gancho"]
    L["quadril"] = L["cintura"] - lateral("cint_quadril", 22.5 / 30.0 * cg)
    L["peq"] = L["cintura"] - lateral("cint_peq", 12.2 / 30.0 * cg)
    L["joelho"] = L["cintura"] - lateral("cint_joelho", 63.7 / 110.5 * L["cintura"])
    if not (L["gancho"] + 3 < L["quadril"] < L["peq"] - 3 < L["cintura"] - 6):
        raise ValueError("%s: alturas de quadril / pequeno quadril / gancho não estão em ordem." % nome)
    if not 0.3 * L["gancho"] < L["joelho"] < 0.8 * L["gancho"]:
        avisos.append("Altura do joelho fora da proporção usual; conferir cintura ao joelho.")

    L["jugular"] = L["cintura"] + m["alt_frente"]
    L["c7"] = L["cintura"] + m["alt_costas"] - 0.5
    usados["alt_frente"] = m["alt_frente"]; usados["alt_costas"] = m["alt_costas"] - 0.5
    if not 3.0 <= L["c7"] - L["jugular"] <= 13.0:
        avisos.append("Alturas do corpo frente (%s) e costas (%s) com diferença fora do usual; conferir."
                      % (_f(m["alt_frente"]), _f(m["alt_costas"])))
    sv = (L["c7"] - L["cintura"]) / 36.0                  # escala vertical do tronco
    proj = (4.5 * m["busto"] / 96.0) if sexo == "M" else (6.0 * m["busto"] / 90.0)   # mamilo à frente da jugular
    hor = m["abertura_busto"] / 2.0 * 0.955               # meia distância em linha reta
    vert2 = m["alt_busto"] ** 2 - hor ** 2 - proj ** 2
    if vert2 < (0.45 * m["alt_busto"]) ** 2:
        avisos.append("Altura do busto (%s) curta para a abertura do busto (%s); conferir." %
                      (_f(m["alt_busto"]), _f(m["abertura_busto"])))
        vert2 = (0.45 * m["alt_busto"]) ** 2
    L["busto"] = L["jugular"] - math.sqrt(vert2)
    usados["alt_busto"] = m["alt_busto"]
    usados["abertura_busto"] = round(2 * hor, 1)
    L["ombro"] = L["c7"] - 4.5 * sv
    L["topo"] = L["c7"] + 6.5 * sv
    # cava: precisa ficar entre o busto e a 7ª cervical
    cava_pad = L["busto"] + 0.33 * (L["jugular"] - L["busto"])
    lo, hi = L["busto"] + 2.0, L["c7"] - 13.0 * sv
    if isinstance(m.get("alt_cava"), float):
        cand = L["cintura"] + m["alt_cava"] * f
        if lo <= cand <= hi:
            L["cava"] = cand
        else:
            L["cava"] = min(max(cava_pad, lo), hi)
            avisos.append("Altura da cava: %s cm acima da cintura põe a axila %s. Usei cerca de %s." %
                          (_f(m["alt_cava"]), "na altura do pescoço" if cand > hi else "abaixo do busto",
                           _f(round(L["cava"] - L["cintura"]))))
    else:
        L["cava"] = cava_pad; estimadas.append("alt_cava")
    usados["alt_cava"] = round(L["cava"] - L["cintura"], 1)
    if L["jugular"] >= L["ombro"] - 1.0:
        L["ombro"] = L["jugular"] + 1.0
    if L["busto"] <= L["cintura"] + 4:
        raise ValueError("%s: o busto ficou abaixo da cintura; conferir alturas do corpo/busto." % nome)

    L["chao"] = 0.0
    L["tornozelo"] = 9.0 * L["joelho"] / 46.8
    L["coto"] = L["gancho"] - 14.5 * (L["gancho"] - L["joelho"]) / 33.7

    # --- ombro e pescoço ---
    larg_ombro = m["pescoco"] / (2 * math.pi) + m["ombro"] * 0.95   # meia largura até o ombro
    if isinstance(m.get("oo_frente"), float):
        esperado = 2 * larg_ombro * 1.09
        if abs(m["oo_frente"] - esperado) > 4.0:
            avisos.append("Ombro a ombro (%s) não fecha com pescoço + ombro (≈ %s); prevaleceu o ombro."
                          % (_f(m["oo_frente"]), _f(round(esperado))))
    if m["pescoco"] > (44.0 if sexo == "M" else 40.0):
        avisos.append("Pescoço %s cm mantido como na tabela (acima da média)." % _f(m["pescoco"]))

    # --- braço ---
    if m["comp_braco"] <= m["alt_cotovelo"] + 10:
        raise ValueError("%s: comprimento do braço precisa ser maior que a altura do cotovelo." % nome)
    usados["comp_braco"] = m["comp_braco"]; usados["alt_cotovelo"] = m["alt_cotovelo"]

    if isinstance(m.get("altura_total"), float):
        r = L["c7"] / m["altura_total"]
        if not 0.80 <= r <= 0.89:
            avisos.append("Altura total %s não combina com as alturas do tronco (7ª cervical a %s cm)."
                          % (_f(m["altura_total"]), _f(round(L["c7"], 1))))

    rot_est = [ROTULO.get(k, k) for k in estimadas if k in ROTULO]
    if rot_est:
        avisos.append("Estimadas por proporção (não informadas): %s." % ", ".join(rot_est))

    alvos = {k: m[k] for k in ("busto", "cintura", "quadril", "peq_quadril", "pescoco", "braco",
                               "cotovelo", "pulso", "joelho", "gancho", "coxa", "meia_coxa",
                               "panturrilha", "canela", "tornozelo") if isinstance(m.get(k), float)}
    return {
        "nome": nome, "sexo": sexo, "escala": escala, "esc_mm_por_cm": 10.0 / escala, "lado": lado,
        "com_braco": com_braco, "abducao": abducao,
        "medidas": {k: v for k, v in med.items() if isinstance(v, float)},
        "alvos": alvos, "estimadas": estimadas, "landmarks": {k: round(v, 3) for k, v in L.items()},
        "usados": usados, "larg_ombro": larg_ombro, "avisos": avisos,
    }


def _f(v):
    s = ("%.1f" % v).replace(".", ",")
    return s[:-2] if s.endswith(",0") else s



# ----------------------------------------------------------------------------
# Definições (conforme as instruções de tomada de medidas do livro da cliente) e faixas usuais
# ----------------------------------------------------------------------------
DESCRICAO = {
    "busto": "Contorno do tórax passando pelos mamilos.",
    "cintura": "Contorno da região mais estreita do tronco (marcar a linha de cintura com fita ou elástico).",
    "quadril": "Contorno da parte mais saliente do quadril, passando pelas nádegas.",
    "peq_quadril": "Contorno da parte mais saliente do abdômen, cerca de 9 a 11 cm abaixo da cintura.",
    "pescoco": "Contorno do pescoço passando pela 7ª vértebra cervical (costas) e pela incisura jugular (frente).",
    "ombro": "Comprimento do ombro: do ponto do pescoço até o acrômio.",
    "braco": "Maior volume do braço, na região do bíceps, com o braço tensionado e flexionado em ângulo reto.",
    "cotovelo": "Contorno do cotovelo com o braço flexionado em ângulo reto.",
    "pulso": "Contorno do pulso passando pelos ossos salientes.",
    "joelho": "Contorno do joelho pelo osso mais saliente na frente e pela articulação atrás; sentada, perna a 90°.",
    "gancho": "Medido na vertical: da cintura no meio da frente, entre as pernas, até a cintura no meio das costas.",
    "alt_frente": "Da incisura jugular até a cintura, sobre o meio da frente.",
    "alt_costas": "Da 7ª vértebra cervical até a cintura, sobre o meio das costas.",
    "alt_busto": "Da incisura jugular até o mamilo, na diagonal.",
    "alt_cava": "Da cintura até a axila, pela lateral (uma régua sob o braço ajuda).",
    "cint_quadril": "Da cintura até o quadril, pela lateral sobre o corpo.",
    "cint_joelho": "Da cintura até o joelho, pela lateral sobre o corpo.",
    "cint_solo": "Da cintura até o chão, pela lateral sobre o corpo.",
    "cint_gancho": "Da linha de cintura até a região do gancho, pela lateral, na posição sentada.",
    "comp_braco": "Do acrômio ao pulso, com o braço semiflexionado, passando pelo cotovelo.",
    "alt_cotovelo": "Do acrômio ao cotovelo, com o braço semiflexionado.",
    "cint_peq": "Da cintura até o pequeno quadril, pela lateral, com a fita apoiada no pequeno quadril.",
    "entrepernas": "Da região do gancho até o chão, com os pés levemente afastados.",
    "abertura_busto": "Distância entre os mamilos.",
    "transv_frente": "Da cintura no meio da frente até o acrômio, na diagonal.",
    "transv_costas": "Da cintura no meio das costas até o acrômio, na diagonal.",
    "entrecavas_frente": "Distância entre as axilas, pela frente.",
    "entrecavas_costas": "Distância entre as axilas, pelas costas.",
    "oo_frente": "Distância entre os acrômios, pela frente do corpo.",
    "oo_costas": "Distância entre os acrômios, pelas costas.",
    "altura_total": "Estatura, descalço. Usada só para conferir proporções.",
    "coxa": "Contorno da coxa na parte mais grossa, logo abaixo do gancho.",
    "panturrilha": "Contorno da panturrilha na parte mais grossa.",
    "tornozelo": "Contorno do tornozelo logo acima do osso.",
    "sexo": "Corpo-base feminino ou masculino.", "escala": "Escala do manequim (5 = 1:5).",
    "lado": "Lado da perna longa e do braço.", "com_braco": "Inclui o braço removível.",
    "abducao": "Abertura do braço em relação ao corpo (graus).",
}
# Faixas usuais de adultos (cm). Fora delas a medida pode estar certa, mas vale conferir.
FAIXAS = {
    "busto": (70, 150), "cintura": (55, 140), "quadril": (75, 160), "peq_quadril": (65, 150),
    "pescoco": (28, 50), "ombro": (9, 18), "braco": (20, 45), "cotovelo": (18, 35), "pulso": (12, 22),
    "joelho": (28, 50), "gancho": (50, 100), "alt_frente": (22, 45), "alt_costas": (32, 52),
    "alt_busto": (14, 32), "alt_cava": (12, 30), "cint_quadril": (14, 30), "cint_joelho": (45, 75),
    "cint_solo": (85, 125), "cint_gancho": (20, 38), "comp_braco": (45, 70), "alt_cotovelo": (25, 42),
    "cint_peq": (6, 16), "entrepernas": (60, 95), "abertura_busto": (14, 28), "transv_frente": (30, 55),
    "transv_costas": (32, 58), "entrecavas_frente": (26, 48), "entrecavas_costas": (28, 50),
    "oo_frente": (30, 52), "oo_costas": (30, 52), "altura_total": (140, 205), "coxa": (40, 80),
    "panturrilha": (28, 50), "tornozelo": (17, 30),
}
GRUPOS = [("contorno", "Contornos", LINHAS_CONTORNO), ("altura", "Alturas e comprimentos", LINHAS_ALTURA),
          ("outras", "Outras medidas", LINHAS_OUTRAS), ("extras", "Medidas extras (opcional)", LINHAS_EXTRAS)]


def campos_para_web():
    grupos = []
    for gid, titulo, linhas in GRUPOS:
        grupos.append({"id": gid, "titulo": titulo, "campos": [
            {"chave": k, "rotulo": r, "descricao": DESCRICAO.get(k, ""), "faixa": FAIXAS.get(k),
             "obrigatorio": k in OBRIGATORIAS} for r, k in linhas]})
    return {"grupos": grupos, "opcoes": [{"chave": k, "rotulo": r, "descricao": DESCRICAO.get(k, ""),
                                           "padrao": OPCOES_PADRAO.get(k)} for r, k in LINHAS_OPCOES]}


def conferir_faixas(med):
    fora = []
    for k, (lo, hi) in FAIXAS.items():
        v = med.get(k)
        if isinstance(v, float) and not lo <= v <= hi:
            fora.append({"chave": k, "valor": v, "faixa": [lo, hi],
                         "texto": "%s = %s fora da faixa usual (%s a %s cm)." % (ROTULO[k], _f(v), lo, hi)})
    return fora
