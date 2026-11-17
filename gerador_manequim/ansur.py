# -*- coding: utf-8 -*-
"""
Modelos estatísticos a partir da base antropométrica ANSUR II (2012, Exército dos EUA,
1.986 mulheres e 4.082 homens medidos; dados públicos da Penn State OpenLab):
https://www.openlab.psu.edu/ansur2/

Gera dados/ansur2_modelos.json com, para cada sexo:
  - faixas (percentis 0,5 % e 99,5 %) das medidas que existem nas duas tabelas;
  - regressões lineares para estimar coxa, panturrilha e tornozelo quando faltarem,
    e para conferir se o pescoço é coerente com o resto do corpo;
  - proporções verticais (axila, mamilo, jugular, ombro entre o gancho e a 7ª cervical)
    para estimar e conferir a altura da cava e do busto.
Unidade da base: mm (convertida para cm).

Rodar:  python ansur.py
Atenção: é uma população militar norte-americana. Serve como referência estatística,
não como padrão de tamanhos brasileiro.
"""
import csv, json, os
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(AQUI, "dados", "ansur2")
ARQ = {"F": "ANSUR_II_FEMALE_Public.csv", "M": "ANSUR_II_MALE_Public.csv"}
SAIDA = os.path.join(AQUI, "dados", "ansur2_modelos.json")

# medida da tabela da cliente -> coluna(s) da ANSUR II (soma quando são duas)
MAPA = {
    "busto": ["chestcircumference"],
    "quadril": ["buttockcircumference"],
    "pescoco": ["neckcircumferencebase"],
    "braco": ["bicepscircumferenceflexed"],
    "pulso": ["wristcircumference"],
    "coxa": ["thighcircumference"],
    "panturrilha": ["calfcircumference"],
    "tornozelo": ["anklecircumference"],
    "entrepernas": ["crotchheight"],
    "altura_total": ["stature"],
    "ombro": ["shoulderlength"],
    "alt_cotovelo": ["acromionradialelength"],
    "comp_braco": ["acromionradialelength", "radialestylionlength"],
    "gancho": ["crotchlengthomphalion"],          # medido a partir do umbigo (omphalion)
}
SEM_FAIXA = {"gancho"}   # definição diferente da tabela (umbigo × cintura natural)
ALTURAS = {"c7": "cervicaleheight", "jugular": "suprasternaleheight", "ombro_pt": "acromialheight",
           "cava": "axillaheight", "busto_pt": "chestheight", "gancho_pt": "crotchheight",
           "joelho_pt": "kneeheightmidpatella", "estatura": "stature"}
REGRESSOES = {
    "coxa": ["quadril", "braco", "entrepernas"],
    "panturrilha": ["quadril", "braco", "pulso", "entrepernas"],
    "tornozelo": ["pulso", "quadril", "entrepernas"],
    "pescoco": ["busto", "braco", "pulso"],
    "gancho": ["v_cintura_gancho", "quadril"],   # v = altura vertical do ponto de partida até o gancho
}


def ler(sexo):
    with open(os.path.join(PASTA, ARQ[sexo]), encoding="latin-1") as f:
        r = csv.DictReader(f)
        linhas = list(r)
    def col(nomes):
        return np.array([sum(float(l[n]) for n in nomes) for l in linhas]) / 10.0   # mm -> cm
    med = {k: col(v) for k, v in MAPA.items()}
    alt = {k: col([v]) for k, v in ALTURAS.items()}
    med["v_cintura_gancho"] = col(["waistheightomphalion"]) - col(["crotchheight"])
    return med, alt, len(linhas)


def regressao(med, y, xs):
    X = np.column_stack([np.ones(len(med[y]))] + [med[x] for x in xs])
    coef, *_ = np.linalg.lstsq(X, med[y], rcond=None)
    pred = X @ coef
    res = med[y] - pred
    r2 = 1 - res.var() / med[y].var()
    return {"y": y, "x": xs, "coef": coef.round(5).tolist(), "dp_residuo": round(float(res.std()), 3),
            "r2": round(float(r2), 3)}


def construir():
    out = {"fonte": "ANSUR II (2012), Penn State OpenLab - https://www.openlab.psu.edu/ansur2/",
           "aviso": "População militar dos EUA; referência estatística, não padrão brasileiro."}
    for sexo in ("F", "M"):
        med, alt, n = ler(sexo)
        d = {"n": n, "faixas": {}, "media": {}, "regressoes": {}, "proporcoes": {}}
        for k, v in med.items():
            if k in SEM_FAIXA or k.startswith("v_"):
                continue
            d["faixas"][k] = [round(float(np.percentile(v, 0.5)), 1), round(float(np.percentile(v, 99.5)), 1)]
            d["media"][k] = round(float(v.mean()), 1)
        for y, xs in REGRESSOES.items():
            d["regressoes"][y] = regressao(med, y, xs)
        base = alt["gancho_pt"]; topo = alt["c7"]
        for k in ("cava", "busto_pt", "jugular", "ombro_pt"):
            r = (alt[k] - base) / (topo - base)
            d["proporcoes"][k] = {"p0_5": round(float(np.percentile(r, 0.5)), 4),
                                  "p50": round(float(np.median(r)), 4),
                                  "p99_5": round(float(np.percentile(r, 99.5)), 4)}
        rc = alt["c7"] / alt["estatura"]
        d["proporcoes"]["c7_estatura"] = {"p0_5": round(float(np.percentile(rc, 0.5)), 4),
                                          "p50": round(float(np.median(rc)), 4),
                                          "p99_5": round(float(np.percentile(rc, 99.5)), 4)}
        rg = alt["gancho_pt"] / alt["estatura"]
        d["proporcoes"]["gancho_estatura"] = {"p0_5": round(float(np.percentile(rg, 0.5)), 4),
                                              "p50": round(float(np.median(rg)), 4),
                                              "p99_5": round(float(np.percentile(rg, 99.5)), 4)}
        out[sexo] = d
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    json.dump(out, open(SAIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    o = construir()
    for s in ("F", "M"):
        d = o[s]
        print("\n== %s (n=%d) ==" % (s, d["n"]))
        for y, r in d["regressoes"].items():
            print("  %-12s R²=%.2f  dp=%.2f cm  ~ %s" % (y, r["r2"], r["dp_residuo"], " + ".join(r["x"])))
        for k, p in d["proporcoes"].items():
            print("  prop %-16s p0.5=%.3f  mediana=%.3f  p99.5=%.3f" % (k, p["p0_5"], p["p50"], p["p99_5"]))
        print("  faixas:", {k: v for k, v in d["faixas"].items()})
    print("\nsalvo em", SAIDA)
