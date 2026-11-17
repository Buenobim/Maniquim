# -*- coding: utf-8 -*-
"""
Servidor local da plataforma do gerador de manequim.

  python servidor.py            -> abre http://localhost:8770 no navegador

API (JSON):
  GET  /api/campos             definições das medidas (rótulo, grupo, descrição, faixa usual)
  GET  /api/planilha           colunas e valores da planilha_medidas.xlsx
  POST /api/planilha           {nome, medidas}  grava/atualiza a coluna na planilha
  POST /api/previa             {nome, medidas}  projeto (alturas, avisos) + geometria da prévia
  POST /api/gerar              {nome, medidas}  inicia o gerador completo (Blender) -> {job}
  GET  /api/job/<id>           andamento e resultado da geração
  GET  /saida/<nome>/<arquivo> arquivos gerados (STL, PDF, PNG)
"""
import json, os, sys, threading, traceback, uuid, webbrowser, mimetypes, unicodedata, re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, urlparse

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import medidas as M      # noqa: E402
import previa            # noqa: E402

PLANILHA = os.path.join(AQUI, "planilha_medidas.xlsx")
SAIDA = os.path.join(AQUI, "saida")
WEB = os.path.join(AQUI, "web")
PORTA = int(os.environ.get("PORTA", "8770"))
JOBS = {}
LOCK = threading.Lock()


def nome_seguro(nome):
    s = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", s).strip("_")
    return s or "manequim"


def limpar_medidas(med):
    out = {}
    for k, v in (med or {}).items():
        if k not in M.ROTULO or v in (None, ""):
            continue
        n = M._num(v)
        out[k] = n
    return out


def gravar_planilha(nome, med):
    import openpyxl
    from openpyxl.styles import Alignment, Border, Side
    wb = openpyxl.load_workbook(PLANILHA)
    ws = wb.worksheets[0]
    cab_l = cab_c = None
    for row in ws.iter_rows():
        for c in row:
            if c.value is not None and M._norm(c.value) == "medidas":
                cab_l, cab_c = c.row, c.column; break
        if cab_l:
            break
    col = None
    ultima = cab_c
    for c in ws[cab_l]:
        if c.column > cab_c and c.value not in (None, ""):
            ultima = max(ultima, c.column)
            if str(c.value).strip() == nome:
                col = c.column
    if col is None:
        col = ultima + 1
        ws.cell(cab_l, col, nome)
    fino = Side(style="thin", color="808080")
    for row in ws.iter_rows(min_row=cab_l + 1):
        rot = row[cab_c - 1].value
        if rot is None:
            continue
        k = M._MAPA.get(M._norm(rot))
        if not k:
            continue
        cel = ws.cell(row[0].row, col)
        cel.value = med.get(k)
        cel.alignment = Alignment(horizontal="center")
        cel.border = Border(left=fino, right=fino, top=fino, bottom=fino)
    wb.save(PLANILHA)


def tarefa_gerar(job, nome, med):
    import gerar
    def prog(txt, fr):
        with LOCK:
            JOBS[job].update(texto=txt, fracao=fr)
    try:
        proj = M.montar_projeto(nome, med)
        pasta = os.path.join(SAIDA, nome_seguro(nome))
        prog("Iniciando o Blender", 0.02)
        res = gerar.modelar(proj, pasta, progresso=prog)
        base = "/saida/%s/" % nome_seguro(nome)
        arquivos = [f for f in sorted(os.listdir(pasta))
                    if f.endswith((".stl", ".pdf", ".png")) and not f.startswith("previa_")]
        with LOCK:
            JOBS[job].update(estado="pronto", texto="Pronto em %.0f s" % res["segundos"], fracao=1.0,
                             resultado={"medidas": res["medidas"], "altura_mm": res["altura_mm"],
                                        "arquivos": [{"nome": f, "url": base + f} for f in arquivos]})
    except Exception as e:
        traceback.print_exc()
        with LOCK:
            JOBS[job].update(estado="erro", texto=str(e))


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _arquivo(self, caminho, download=False):
        if not os.path.isfile(caminho):
            return self._json({"erro": "não encontrado"}, 404)
        tipo = mimetypes.guess_type(caminho)[0] or "application/octet-stream"
        if caminho.endswith(".js"):
            tipo = "text/javascript"
        dados = open(caminho, "rb").read()
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        if download:
            self.send_header("Content-Disposition", 'attachment; filename="%s"' % os.path.basename(caminho))
        self.end_headers()
        self.wfile.write(dados)

    def _corpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n).decode("utf-8") or "{}")

    def do_GET(self):
        url = urlparse(self.path); p = unquote(url.path)
        if p in ("/", "/index.html"):
            return self._arquivo(os.path.join(WEB, "index.html"))
        if p.startswith("/web/"):
            alvo = os.path.normpath(os.path.join(WEB, p[5:]))
            if not alvo.startswith(WEB):
                return self._json({"erro": "caminho inválido"}, 400)
            return self._arquivo(alvo)
        if p.startswith("/saida/"):
            alvo = os.path.normpath(os.path.join(SAIDA, p[7:]))
            if not alvo.startswith(SAIDA):
                return self._json({"erro": "caminho inválido"}, 400)
            return self._arquivo(alvo, download=alvo.endswith(".stl"))
        if p == "/api/campos":
            return self._json(M.campos_para_web())
        if p == "/api/planilha":
            try:
                return self._json({"pessoas": M.ler_planilha(PLANILHA, todas=True)})
            except Exception as e:
                return self._json({"erro": str(e)}, 500)
        if p.startswith("/api/job/"):
            with LOCK:
                j = JOBS.get(p.split("/")[-1])
            return self._json(j or {"estado": "desconhecido"})
        return self._json({"erro": "não encontrado"}, 404)

    def do_POST(self):
        p = urlparse(self.path).path
        try:
            d = self._corpo()
        except Exception:
            return self._json({"erro": "JSON inválido"}, 400)
        nome = str(d.get("nome") or "Manequim").strip()
        med = limpar_medidas(d.get("medidas"))
        if p == "/api/previa":
            try:
                proj = M.montar_projeto(nome, med)
            except ValueError as e:
                return self._json({"erro": str(e), "conferencia": M.conferir_faixas(med)})
            try:
                geo = previa.gerar_previa(proj)
            except Exception as e:
                traceback.print_exc()
                return self._json({"erro": "Prévia falhou: %s" % e, "projeto": proj})
            proj["faixas"] = M.conferir_faixas(med)
            return self._json({"projeto": proj, "geo": geo})
        if p == "/api/planilha":
            try:
                gravar_planilha(nome, med)
                return self._json({"ok": True})
            except PermissionError:
                return self._json({"erro": "A planilha está aberta no Excel. Feche e tente de novo."}, 409)
            except Exception as e:
                return self._json({"erro": str(e)}, 500)
        if p == "/api/gerar":
            try:
                M.montar_projeto(nome, med)
            except ValueError as e:
                return self._json({"erro": str(e)}, 400)
            with LOCK:
                if any(j["estado"] == "rodando" for j in JOBS.values()):
                    return self._json({"erro": "Já existe uma geração em andamento."}, 409)
                job = uuid.uuid4().hex[:10]
                JOBS[job] = {"estado": "rodando", "texto": "Na fila", "fracao": 0.0, "nome": nome}
            threading.Thread(target=tarefa_gerar, args=(job, nome, med), daemon=True).start()
            return self._json({"job": job})
        return self._json({"erro": "não encontrado"}, 404)


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORTA), H)
    url = "http://localhost:%d" % PORTA
    print("Gerador de manequim rodando em", url, "(Ctrl+C para parar)")
    if "--sem-navegador" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
