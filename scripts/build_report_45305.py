#!/usr/bin/env python3
"""Build the submission-style report for Slurm job 45305 from its CSV data."""
import csv
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "result/45305"
OUTPUT = ROOT / "docs/relatorio-execucao-45305.pdf"
rows = list(csv.DictReader((DATA / "summary.csv").open(newline="")))
idx = {(r["mode"], int(r["processes"]), r["yield"]): r for r in rows}
raw = list(csv.DictReader((DATA / "raw.tsv").open(newline=""), delimiter="\t"))
assert len(raw) == 380 and all(r["verification"] == "OK" for r in raw)
assert all(int(r["repetitions"]) == 10 for r in rows)

font_dir = Path("/usr/share/fonts/truetype/dejavu")
pdfmetrics.registerFont(TTFont("DejaVu", str(font_dir / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(font_dir / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Mono", str(font_dir / "DejaVuSansMono.ttf")))

W, H = A4
M = 33
INK = colors.HexColor("#202B36")
ACCENT = colors.HexColor("#193A54")
MUTED = colors.HexColor("#5D6A74")
RULE = colors.HexColor("#C8D0D5")
PALE = colors.HexColor("#EAF0F3")
c = canvas.Canvas(str(OUTPUT), pagesize=A4)
c.setTitle("T3 - Relatório da execução 45305")
c.setAuthor("Projeto DivideAndConquerOpenMPI")


def txt(x, y, s, size=8, bold=False, color=INK):
    c.setFont("DejaVu-Bold" if bold else "DejaVu", size)
    c.setFillColor(color)
    c.drawString(x, y, s)


def para(y, s, size=8.6, leading=12.3, indent=0):
    for line in simpleSplit(s, "DejaVu", size, W - 2 * M - indent):
        txt(M + indent, y, line, size)
        y -= leading
    return y


def rule(y):
    c.setStrokeColor(RULE)
    c.setLineWidth(0.45)
    c.line(M, y, W - M, y)


def table(y, title, headers, entries, widths, size=7.6, leading=13.1, group_after=None):
    assert abs(sum(widths) - (W - 2 * M)) < 1
    txt(M, y, title, 8.8, True, ACCENT)
    y -= 14
    c.setFillColor(PALE)
    c.rect(M, y - 4, sum(widths), 15, fill=1, stroke=0)
    x = M
    for j, (h, width) in enumerate(zip(headers, widths)):
        c.setFont("DejaVu-Bold", size)
        c.setFillColor(ACCENT)
        if j == 0:
            c.drawString(x + 4, y, h)
        else:
            c.drawRightString(x + width - 4, y, h)
        x += width
    y -= 15
    for i, entry in enumerate(entries):
        if i % 2:
            c.setFillColor(colors.HexColor("#F7F9FA"))
            c.rect(M, y - 3, sum(widths), leading, fill=1, stroke=0)
        x = M
        for j, (value, width) in enumerate(zip(entry, widths)):
            c.setFont("DejaVu", size)
            c.setFillColor(INK)
            if j == 0:
                c.drawString(x + 4, y, str(value))
            else:
                c.drawRightString(x + width - 4, y, str(value))
            x += width
        y -= leading
        if group_after is not None and i + 1 == group_after:
            rule(y + leading - 3)
    rule(y + leading - 3)
    return y - 5


def f(r, key, digits=3):
    return f"{float(r[key]):.{digits}f}"


def footer(page):
    rule(26)
    txt(M, 15, "T3  /  JOB 45305  /  ATLÂNTICA", 6.8, True, MUTED)
    c.setFont("DejaVu", 6.8)
    c.setFillColor(MUTED)
    c.drawRightString(W - M, 15, str(page))


# Page 1: one page of analysis.
y = H - M
txt(M, y, "T3 - Divisão e conquista com MPI", 14, True, ACCENT)
y -= 17
txt(M, y, "George Rother | Max Weiss Breuel", 8.5, True)
y -= 13
txt(M, y, "Análise da execução 45305 | 2 nós exclusivos | n = 212.118 | 10 repetições por caso", 8.5)
y -= 13
txt(M, y, "Repositório: github.com/Max-WB09/DivideAndConquerOpenMPI", 7.8)
y -= 11
rule(y)
y -= 13
y = para(y, "Ambiente: atlantica03 e atlantica04, cada um com 2 Xeon E5520 de 4 núcleos, HT ativo: 8 núcleos físicos e 16 threads por nó. Compilação -O2. Os ranks foram distribuídos quase igualmente (31: 16+15; 32: 16+16; 1023: 512+511). Todos os 380 resultados brutos tiveram verificação OK.")
y -= 3
y = para(y, "T1 (Bubble Sort integral): mediana 45,346466 s [mín. 45,328378; máx. 45,364726], dentro dos 30-60 s exigidos. A calibração testou n=20.000, 80.000 e 212.118. T1' percorre, em um processo, as mesmas divisões de cada árvore; a referência balanceada reproduz inclusive P=31. As Tabelas 1 e 2 apresentam medianas, mínimos e máximos. S = T1/TP; S' = T1'/TP; ganho algorítmico = T1/T1'; E = S'/P (ou S'/32 acima de 32 ranks).")
y -= 6

main_cases = [("Original", p, "0") for p in (1, 3, 7, 15, 31)] + [("Balanceada", p, "0") for p in (2, 4, 8, 16, 31, 32)]
main = []
for mode_label, p, idle in main_cases:
    r = idx[("original" if mode_label == "Original" else "balanced", p, idle)]
    main.append((mode_label, p, f(r,"median_s"), f(r,"min_s"), f(r,"max_s"), f(r,"algorithm_gain",1), f(r,"speedup_bubble",1), f(r,"speedup_tree",2), f(r,"efficiency",2)))
y = table(y, "Tabela 1 - Tempos (s), ganho algorítmico e paralelismo até 32 ranks", ["Modo", "P", "Med.", "Mín.", "Máx.", "T1/T1'", "S", "S'", "E"], main, [82, 25, 62, 62, 62, 63, 55, 57, 61], size=7.7, leading=13.1, group_after=5)

oversub = []
for p in (63, 127, 255, 511, 1023):
    for idle in ("0", "1"):
        r = idx[("original", p, idle)]
        oversub.append((p, idle, f(r,"median_s"), f(r,"min_s"), f(r,"max_s"), f(r,"speedup_bubble",1), f(r,"speedup_tree",3), f(r,"efficiency",4)))
y = table(y, "Tabela 2 - Versão original acima de 32 threads; espera ativa (0) e cessão (1)", ["P", "yield", "Med.", "Mín.", "Máx.", "S", "S'", "E/32"], oversub, [38, 43, 75, 75, 75, 75, 75, 73], size=7.7, leading=13.1)

def bullet(y, body):
    txt(M, y, "•", 8.5)
    return para(y, body, size=8.2, leading=11.5, indent=10) - 4


txt(M, y, "Árvores, algoritmo e HT", 8.8, True, ACCENT)
y -= 13
y = bullet(y, "Original (mpi_sort.c, linhas 48-65): em P=31, 16 folhas fazem Bubble Sort e 15 ranks aguardam. T1/T1'=16,87 explica S=132,78 acima de P; o ganho paralelo isolado é S'=7,87 (E=0,254). De P=15 a 31, o tempo cai 2,30x, mas S' sobe só de 7,04 a 7,87: o benefício adicional do HT é modesto.")
y = bullet(y, "Balanceada (linhas 67-99): cada rank ordena a metade esquerda. Em P=31, 30 ranks recebem 6.628/6.629 elementos e um recebe 13.258, cerca de 4x o custo local quadrático. A mediana é 2,48x a de P=32; a carga desigual é uma causa plausível, embora a variação do escalonamento também possa influir.")

txt(M, y, "Ganho com balanceamento", 8.8, True, ACCENT)
y -= 13
y = bullet(y, "Sem alterar o código: com P fixo em 63, yield=1 reduz 0,2512 para 0,1706 s (1,47x); em P=511, reduz 0,9763 para 0,0625 s (15,62x). Ceder o núcleo permite que o escalonador priorize as folhas enquanto os pais esperam. O melhor tempo é P=511; P=1023 volta a 0,1184 s por custo crescente de processos e mensagens.")
y = bullet(y, "Alterando o código: em P=31, a balanceada leva 0,2126 s contra 0,3415 s da original (1,61x). Contudo, T1' cai de 2,6884 para 1,3483 s (1,99x) e S' cai de 7,87 para 6,34: o ganho total inclui mais divisões do Bubble Sort; os dados não demonstram aumento do paralelismo isolado. Em P=32, a balanceada chega a 0,0858 s e S'=14,71.")

txt(M, y, "Medição: MPI_Wtime na raiz cobre distribuição até intercalação; inicialização, verificação e placement ficam fora.", 7.5, True)
y -= 13
txt(M, y, "O stderr contém avisos do srun sobre --ntasks-per-node ímpar; o placement registra a distribuição real.", 7.5)
assert y > 31, f"Page 1 overflow: y={y}"
footer(1)
c.showPage()


# Source code: every requested function has its own captioned text box and
# retains its original line numbers. Long functions continue in a new box.
page = 2
code_y = None
line_height = 9.5


def start_code_page():
    global code_y
    txt(M, H - M, "Código-fonte", 11, True, ACCENT)
    c.setFont("DejaVu", 7.7)
    c.setFillColor(MUTED)
    c.drawRightString(W - M, H - M, "Execução 45305  |  linhas originais")
    rule(H - M - 13)
    code_y = H - M - 28


def end_code_page():
    global page, code_y
    footer(page)
    c.showPage()
    page += 1
    code_y = None


segments = [
    ("src/mpi_sort.c", ROOT / "src/mpi_sort.c", [
        (1, 12, "Declarações e constantes"),
        (13, 18, "die() - tratamento de falha"),
        (19, 25, "allocate() - alocação"),
        (26, 35, "parse_positive() - parâmetros"),
        (36, 47, "receive_vector() - recepção MPI"),
        (48, 66, "original() - árvore original"),
        (67, 84, "balanced() - árvore balanceada"),
        (85, 101, "balanced_group() - pai e subárvore"),
        (102, 183, "main() - execução MPI e verificação"),
    ]),
    ("src/sequintial/sequencial.c", ROOT / "src/sequintial/sequencial.c", [
        (1, 22, "Declarações e contexto"),
        (23, 39, "bubble_sort() - conquista"),
        (40, 59, "intercala() - combinação"),
        (60, 75, "ordena() - referência original"),
        (76, 89, "ordena_balanceada() - referência balanceada"),
        (90, 97, "agora() - relógio sequencial"),
        (98, 145, "main() - referências e verificação"),
    ]),
    ("scripts/experimentos.sbatch", ROOT / "scripts/experimentos.sbatch", [
        (1, 27, "Configuração do job e calibração"),
        (28, 72, "run_case() - medição e registro"),
        (73, 101, "Repetições e consolidação"),
    ]),
]

for filename, path, parts in segments:
    source = path.read_text().splitlines()
    assert sum(end - start + 1 for start, end, _ in parts) == len(source)
    for start, end, label in parts:
        position = start
        while position <= end:
            if code_y is None:
                start_code_page()
            capacity = int((code_y - 44 - 30) // line_height)
            if capacity < 8:
                end_code_page()
                continue
            take = min(end - position + 1, capacity)
            top = code_y
            box_height = 27 + take * line_height
            bottom = top - box_height
            c.setStrokeColor(RULE)
            c.setLineWidth(0.55)
            c.rect(M, bottom, W - 2 * M, box_height, fill=0, stroke=1)
            c.setFillColor(PALE)
            c.rect(M, top - 21, W - 2 * M, 21, fill=1, stroke=0)
            caption = f"{filename}  /  {label}"
            if position > start:
                caption += " (continuação)"
            txt(M + 8, top - 14, caption, 8.0, True, ACCENT)
            c.setFont("DejaVu", 7.2)
            c.setFillColor(MUTED)
            c.drawRightString(W - M - 8, top - 14, f"{position}-{position + take - 1}")
            c.setStrokeColor(RULE)
            c.line(M + 42, top - 21, M + 42, bottom)
            for i in range(take):
                number = position + i
                baseline = top - 32 - i * line_height
                c.setFont("DejaVu-Mono", 7.0)
                c.setFillColor(MUTED)
                c.drawRightString(M + 36, baseline, str(number))
                c.setFillColor(INK)
                source_line = source[number - 1].expandtabs(4)
                assert pdfmetrics.stringWidth(source_line, "DejaVu-Mono", 7.0) < W - 2 * M - 55
                c.drawString(M + 49, baseline, source_line)
            code_y = bottom - 12
            position += take

if code_y is not None:
    end_code_page()


# Full sequential references, including minimum and maximum.
y = H - M
txt(M, y, "Apêndice - Referências sequenciais T1'", 10, True)
y -= 16
y = para(y, "A Tabela 3 mostra dez repetições por configuração; os tempos são de ordenação em segundos, sem inicialização e sem verificação. Original: delta = ceil(212.118/folhas); balanceada: a árvore de P ranks é percorrida sequencialmente.")
y -= 8
seq = []
for mode, ps in [("original_reference", (1,3,7,15,31,63,127,255,511,1023)), ("balanced_reference", (2,4,8,16,31,32))]:
    for p in ps:
        r = idx[(mode,p,"NA")]
        seq.append(("Original" if mode.startswith("original") else "Balanceada",p, f(r,"median_s",6),f(r,"min_s",6),f(r,"max_s",6)))
y = table(y, "Tabela 3 - Mediana, mínimo e máximo das referências T1' (s)", ["Árvore", "P", "Mediana", "Mínimo", "Máximo"], seq, [110,45,124,125,125], size=8.0, leading=15)
txt(M, y-9, "Fonte: result/45305/raw.tsv e summary.csv; cálculos em scripts/summarize.py.", 7.2)
y -= 36
rule(y)
y -= 23
txt(M, y, "Uso de inteligência artificial", 10, True, ACCENT)
y -= 18
y = para(y, "O Codex foi utilizado para organizar os resultados da execução 45305, conferir as comparações numéricas, redigir a análise e diagramar este relatório em PDF. Os tempos e as verificações apresentados foram extraídos de result/45305/raw.tsv, summary.csv e dos registros do job; a ferramenta não executou as medições no cluster durante a elaboração deste documento.", size=8.6, leading=13)
assert y > 45, f"Appendix overflow: y={y}"
footer(page)
c.showPage()
c.save()
print(OUTPUT)
