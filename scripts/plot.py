#!/usr/bin/env python3
"""Create report-ready PNG plots from summarize.py's CSV output."""
import csv
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "t3-mplcache"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(path):
    with path.open(newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError("summary.csv está vazio")
    parallel = [r for r in rows if r["mode"] in ("original", "balanced")]
    if not parallel:
        raise ValueError("summary.csv não contém medições paralelas")
    return parallel


def series(rows, mode, yield_mode, maximum=None, minimum=None):
    selected = [r for r in rows if r["mode"] == mode and r["yield"] == yield_mode
                and (maximum is None or int(r["processes"]) <= maximum)
                and (minimum is None or int(r["processes"]) >= minimum)]
    return sorted(selected, key=lambda r: int(r["processes"]))


def plot_metric(ax, data, field, label, marker):
    if data:
        ax.plot([int(r["processes"]) for r in data],
                [float(r[field]) for r in data], marker=marker, label=label)


def finish(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main(summary, out):
    rows = load(summary)
    out.mkdir(parents=True, exist_ok=True)
    original = series(rows, "original", "0", maximum=31)
    balanced = series(rows, "balanced", "0", maximum=32)
    over_active = series(rows, "original", "0", minimum=63)
    over_yield = series(rows, "original", "1", minimum=63)

    fig, ax = plt.subplots(figsize=(7, 4.4))
    for data, label, marker in ((original, "Original", "o"),
                                (balanced, "Balanceada", "s")):
        if data:
            x = [int(r["processes"]) for r in data]
            y = [float(r["median_s"]) for r in data]
            low = [v - float(r["min_s"]) for v, r in zip(y, data)]
            high = [float(r["max_s"]) - v for v, r in zip(y, data)]
            ax.errorbar(x, y, yerr=[low, high], marker=marker, capsize=3,
                        label=label)
    ax.set(xlabel="Processos", ylabel="Tempo (s)", title="Tempo de ordenação: mediana, mínimo e máximo")
    ax.axvline(16, color="gray", linestyle=":", linewidth=1, label="16 núcleos físicos")
    ax.grid(alpha=0.25)
    ax.legend()
    finish(fig, out / "tempos.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.1), sharex=True)
    for ax, (field, title) in zip(axes,
                                  (("speedup_bubble", "Contra Bubble Sort inteiro"),
                                   ("speedup_tree", "Contra a mesma árvore sequencial"))):
        plot_metric(ax, original, field, "Original", "o")
        plot_metric(ax, balanced, field, "Balanceada", "s")
        ax.set(xlabel="Processos", ylabel="Speed-up", title=title)
        ax.grid(alpha=0.25)
        ax.legend()
    finish(fig, out / "speedups.png")

    fig, ax = plt.subplots(figsize=(7, 4.4))
    plot_metric(ax, original, "efficiency", "Original", "o")
    plot_metric(ax, balanced, "efficiency", "Balanceada", "s")
    ax.axvline(16, color="gray", linestyle=":", linewidth=1, label="16 núcleos físicos")
    ax.axvline(32, color="gray", linestyle="--", linewidth=1, label="32 threads HT")
    ax.set(xlabel="Processos", ylabel="Eficiência (T1'/TP)/P", title="Eficiência até 32 processos")
    ax.grid(alpha=0.25)
    ax.legend()
    finish(fig, out / "eficiencia.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.1), sharex=True)
    for ax, field, title, ylabel in ((axes[0], "median_s", "Tempo", "Tempo (s)"),
                                     (axes[1], "speedup_tree", "Paralelismo", "T1'/TP")):
        plot_metric(ax, over_active, field, "Espera ativa (=0)", "o")
        plot_metric(ax, over_yield, field, "Cede o núcleo (=1)", "s")
        ax.set(xlabel="Processos", ylabel=ylabel, title=title)
        ax.set_xscale("log", base=2)
        ax.grid(alpha=0.25)
        ax.legend()
    fig.suptitle("Mais processos que threads de hardware")
    finish(fig, out / "sobrecarga.png")
    print(f"Gráficos gerados em {out}")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("uso: python3 scripts/plot.py result/<job_id>/summary.csv [diretório]")
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2]) if len(sys.argv) == 3 else source.parent / "plots"
    main(source, destination)
