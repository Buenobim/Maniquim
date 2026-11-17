# -*- coding: utf-8 -*-
"""
GERADOR DE MANEQUIM DE MOULAGE (perna longa, braço removível)

Uso:
  python gerar.py                              # todas as colunas preenchidas da planilha_medidas.xlsx
  python gerar.py minha_planilha.xlsx          # outra planilha no mesmo formato
  python gerar.py --pessoa Giovanna --pessoa M # só algumas colunas
  python gerar.py --conferir                   # só confere a planilha (não modela)

Saída: saida/<Nome>/  (STL das peças, prévias, prancha PDF/PNG e relatório JSON)
"""
import argparse, glob, json, os, shutil, subprocess, sys, time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from medidas import ler_planilha, montar_projeto  # noqa: E402


def achar_blender():
    if os.environ.get("BLENDER"):
        return os.environ["BLENDER"]
    w = shutil.which("blender")
    if w:
        return w
    cand = sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender*\blender.exe"))
    if cand:
        return cand[-1]
    raise SystemExit("Blender não encontrado. Instale o Blender 4.2+ ou defina a variável BLENDER.")


def modelar(proj, pasta, blender=None, progresso=None):
    """Roda o gerador completo (Blender) + prancha. progresso(texto, fração) é opcional."""
    blender = blender or achar_blender()
    os.makedirs(pasta, exist_ok=True)
    pj = os.path.join(pasta, "projeto.json")
    json.dump(proj, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    t0 = time.time()
    etapas = [("iter 0 corpo", "Calibrando o corpo", 0.05), ("iter 6 corpo", "Calibrando o corpo", 0.35),
              ("iter 11 corpo", "Corpo calibrado", 0.6), ("braco:", "Calibrando o braço", 0.7),
              ("cortando", "Cortando peças e encaixes", 0.78), ("furos", "Furos da haste e pinos", 0.85),
              ("tronco_perna {", "Exportando STL", 0.9), ("FIM", "Imagens prontas", 0.95)]
    proc = subprocess.Popen([blender, "-b", "-P", os.path.join(AQUI, "nucleo_blender.py"), "--", pj, pasta],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace")
    linhas = []
    for linha in proc.stdout:
        linhas.append(linha)
        if progresso:
            for chave, txt, fr in etapas:
                if chave in linha:
                    progresso(txt, fr)
    proc.wait()
    log = "".join(linhas)
    open(os.path.join(pasta, "log_blender.txt"), "w", encoding="utf-8").write(log)
    if proc.returncode != 0 or "FIM" not in log:
        erro = " | ".join(l for l in log.splitlines() if "Error" in l or "Traceback" in l or "line " in l)
        raise RuntimeError("Blender falhou (veja log_blender.txt): " + erro[-800:])
    if progresso:
        progresso("Montando a prancha", 0.97)
    import prancha
    pdf, png = prancha.gerar(pasta)
    rel = json.load(open(os.path.join(pasta, "relatorio_medidas.json"), encoding="utf-8"))
    cm = dict(rel["corpo_cm_reais"]); cm.update(rel.get("braco_cm_reais", {}))
    return {"pasta": pasta, "pdf": pdf, "png": png, "medidas": cm, "altura_mm": rel["altura_montado_mm"],
            "segundos": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser(description="Gera manequins a partir da planilha de medidas.")
    ap.add_argument("planilha", nargs="?", default=os.path.join(AQUI, "planilha_medidas.xlsx"))
    ap.add_argument("--pessoa", action="append", help="nome da coluna (pode repetir)")
    ap.add_argument("--saida", default=os.path.join(AQUI, "saida"))
    ap.add_argument("--conferir", action="store_true", help="só confere as medidas, sem modelar")
    a = ap.parse_args()

    pessoas = ler_planilha(a.planilha)
    if a.pessoa:
        falt = [p for p in a.pessoa if p not in pessoas]
        if falt:
            raise SystemExit("Coluna(s) sem medidas na planilha: %s. Disponíveis: %s"
                             % (", ".join(falt), ", ".join(pessoas)))
        pessoas = {p: pessoas[p] for p in a.pessoa}
    if not pessoas:
        raise SystemExit("Nenhuma coluna com medidas na planilha.")

    blender = None if a.conferir else achar_blender()
    for nome, med in pessoas.items():
        print("\n=== %s ===" % nome)
        try:
            proj = montar_projeto(nome, med)
        except ValueError as e:
            print("ERRO:", e); continue
        for av in proj["avisos"]:
            print("  aviso:", av)
        if a.conferir:
            continue
        try:
            res = modelar(proj, os.path.join(a.saida, nome), blender)
        except RuntimeError as e:
            print("ERRO:", e); continue
        cm = res["medidas"]
        print("  modelado em %.0f s · altura %s mm" % (res["segundos"], res["altura_mm"]))
        print("  " + " · ".join("%s %.1f" % (k, cm[k]) for k in
                                ("busto", "cintura", "quadril", "pescoco", "gancho") if k in cm))
        print("  prancha:", res["pdf"])

if __name__ == "__main__":
    main()
