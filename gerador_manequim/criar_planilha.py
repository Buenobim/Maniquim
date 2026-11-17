# -*- coding: utf-8 -*-
"""Cria a planilha-modelo (mesmo formato da tabela da cliente) com a Giovanna preenchida."""
import os, sys
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from medidas import LINHAS_CONTORNO, LINHAS_ALTURA, LINHAS_OUTRAS, LINHAS_EXTRAS, LINHAS_OPCOES

GIOVANNA = {
    "busto": 90, "cintura": 78, "quadril": 108, "peq_quadril": 86.5, "pescoco": 43, "ombro": 12,
    "braco": 31, "cotovelo": 26, "pulso": 15.5, "joelho": 37.5, "gancho": 74.5,
    "alt_frente": 27, "alt_costas": 36.5, "alt_busto": 20, "alt_cava": 26, "cint_quadril": 24,
    "cint_joelho": 68, "cint_solo": 118, "cint_gancho": 30, "comp_braco": 57.5, "alt_cotovelo": 33,
    "cint_peq": 13, "entrepernas": 80.5, "abertura_busto": 22, "transv_frente": 40,
    "transv_costas": 44, "entrecavas_frente": 39.5, "entrecavas_costas": 40, "oo_frente": 40,
    "oo_costas": 40,
    "sexo": "F", "escala": 5, "lado": "D", "com_braco": "Sim", "abducao": 15,
}
COLUNAS = ["Giovanna", "Rafael", "P", "M", "G"]

AMARELO = PatternFill("solid", fgColor="FFF59D")
AZUL = PatternFill("solid", fgColor="7FA7DC")
VERDE = PatternFill("solid", fgColor="C8E6C9")
CINZA = PatternFill("solid", fgColor="E0E0E0")
fino = Side(style="thin", color="808080")
BORDA = Border(left=fino, right=fino, top=fino, bottom=fino)
CENTRO = Alignment(horizontal="center", vertical="center")


def criar(caminho):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Medidas"
    ncol = 1 + len(COLUNAS)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncol)
    ws.cell(1, 1, "Tabela de Medidas do Corpo (cm)").font = Font(size=13)
    ws.cell(1, 1).alignment = CENTRO
    ws.cell(2, 1, "Medidas")
    for j, c in enumerate(COLUNAS):
        ws.cell(2, 2 + j, c)
    for j in range(ncol):
        ws.cell(2, 1 + j).alignment = CENTRO; ws.cell(2, 1 + j).border = BORDA
    r = 3
    def bloco(linhas, cor, giov=True):
        nonlocal r
        for rot, k in linhas:
            ws.cell(r, 1, rot).fill = cor
            for j in range(ncol):
                ws.cell(r, 1 + j).border = BORDA; ws.cell(r, 1 + j).alignment = CENTRO
            if giov and k in GIOVANNA:
                v = GIOVANNA[k]
                ws.cell(r, 2, v).number_format = "0.0###" if isinstance(v, (int, float)) else "@"
            r += 1
    bloco(LINHAS_CONTORNO, AMARELO)
    bloco(LINHAS_ALTURA, AZUL)
    bloco(LINHAS_OUTRAS, PatternFill(fill_type=None))
    r += 1
    ws.cell(r, 1, "Medidas extras (opcional: se vazio, estima por proporção)").font = Font(bold=True)
    r += 1
    bloco(LINHAS_EXTRAS, VERDE)
    r += 1
    ws.cell(r, 1, "Opções do manequim (se vazio, usa o padrão)").font = Font(bold=True)
    r += 1
    bloco(LINHAS_OPCOES, CINZA)
    r += 1
    notas = [
        "Padrões: Sexo F · Escala 5 (1:5) · Lado D (perna longa e braço do lado direito) · Com braço Sim · Abertura do braço 15°.",
        "Alturas laterais (cintura ao quadril, ao joelho, ao solo) são corrigidas pela curva do quadril.",
        "Altura Total: serve só para conferir as proporções. Coxa/Panturrilha/Tornozelo: contorno na parte mais grossa (tornozelo: logo acima do osso).",
    ]
    for n in notas:
        ws.cell(r, 1, n).font = Font(italic=True, size=9, color="606060"); r += 1
    ws.column_dimensions["A"].width = 38
    for j in range(len(COLUNAS)):
        ws.column_dimensions[openpyxl.utils.get_column_letter(2 + j)].width = 12
    wb.save(caminho)


if __name__ == "__main__":
    destino = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                  "planilha_medidas.xlsx")
    criar(destino)
    print("ok", destino)
