#!/usr/bin/env bash
#SBATCH --job-name=t3-mpi-sort
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=16
#SBATCH --exclusive
#SBATCH --overcommit
#SBATCH --time=08:00:00
#SBATCH --output=result/slurm-%j.out
#SBATCH --error=result/slurm-%j.err
set -euo pipefail

cd "${SLURM_SUBMIT_DIR:?}"
make all
mkdir -p "result/${SLURM_JOB_ID}"
OUT="result/${SLURM_JOB_ID}"

scontrol show hostnames "$SLURM_JOB_NODELIST" > "$OUT/nodes.txt"
srun --nodes=2 --ntasks=2 --ntasks-per-node=1 \
    bash -c 'printf "HOST=%s\n" "$(hostname)"; lscpu' > "$OUT/lscpu.txt"

# É possível passar N já calibrado: sbatch --export=ALL,N=... scripts/experimentos.sbatch.
N="${N:-$(python3 scripts/calibrate.py 2> "$OUT/calibration.log")}" 
printf 'n=%s\njob=%s\nnodes=%s\n' "$N" "$SLURM_JOB_ID" "$SLURM_JOB_NODELIST" > "$OUT/metadata.txt"
printf 'mode\tprocesses\trepetition\tyield\tn\tdelta\tseconds\tverification\n' > "$OUT/raw.tsv"
printf 'mode\tprocesses\tyield\tplacement\n' > "$OUT/placement.tsv"
: > "$OUT/executions.log"

run_case() {
    local mode="$1" p="$2" repetition="$3" yield_mode="$4" output delta seconds verification
    if [[ "$mode" == bubble ]]; then
        output=$(srun --nodes=1 --ntasks=1 bin/sequencial "$N")
    elif [[ "$mode" == original_reference ]]; then
        local leaves=$(((p + 1) / 2))
        delta=$(((N + leaves - 1) / leaves))
        output=$(srun --nodes=1 --ntasks=1 bin/sequencial "$N" "$delta")
    elif [[ "$mode" == balanced_reference ]]; then
        output=$(srun --nodes=1 --ntasks=1 bin/sequencial "$N" --balanced "$p")
    else
        local step_nodes=2
        [[ "$p" == 1 ]] && step_nodes=1
        local tasks_per_node=$(((p + step_nodes - 1) / step_nodes))
        local parameter="$p"
        if [[ "$mode" == original ]]; then
            local leaves=$(((p + 1) / 2))
            parameter=$(((N + leaves - 1) / leaves))
        fi
        output=$(T3_REPORT_PLACEMENT=$([[ "$repetition" == 1 ]] && printf 1 || printf '') \
            OMPI_MCA_mpi_yield_when_idle="$yield_mode" \
            srun --nodes="$step_nodes" --ntasks="$p" \
            --ntasks-per-node="$tasks_per_node" --overcommit \
            --distribution=block:block --cpu-bind=none \
            bin/mpi_sort "$mode" "$N" "$parameter")
    fi
    printf 'mode=%s processes=%s repetition=%s yield=%s output=%s\n' \
        "$mode" "$p" "$repetition" "$yield_mode" "$output" >> "$OUT/executions.log"
    [[ "$output" =~ delta=([0-9]+) ]] && delta="${BASH_REMATCH[1]}"
    [[ "$output" =~ tempo=([0-9.]+) ]] && seconds="${BASH_REMATCH[1]}"
    [[ "$output" =~ verificacao=([A-Z]+) ]] && verification="${BASH_REMATCH[1]}"
    if [[ "${verification:-}" != OK || -z "${seconds:-}" ]]; then
        printf 'falha em %s P=%s repetição=%s: %s\n' "$mode" "$p" "$repetition" "$output" >&2
        exit 1
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$mode" "$p" "$repetition" "$yield_mode" "$N" "$delta" "$seconds" "$verification" \
        >> "$OUT/raw.tsv"
    if [[ "$repetition" == 1 && "$mode" != *reference && "$mode" != bubble ]]; then
        [[ "$output" =~ placement=([^[:space:]]+) ]] || { echo "mapa de nós ausente" >&2; exit 1; }
        printf '%s\t%s\t%s\t%s\n' "$mode" "$p" "$yield_mode" "${BASH_REMATCH[1]}" \
            >> "$OUT/placement.tsv"
    fi
}

original_ps=(1 3 7 15 31 63 127 255 511 1023)
balanced_ps=(2 4 8 16 32 31)
for repetition in {1..10}; do
    run_case bubble 1 "$repetition" NA
    for p in "${original_ps[@]}"; do
        run_case original_reference "$p" "$repetition" NA
    done
    for p in "${balanced_ps[@]}"; do
        run_case balanced_reference "$p" "$repetition" NA
    done
    for p in 1 3 7 15 31; do
        run_case original "$p" "$repetition" 0
    done
    for p in "${balanced_ps[@]}"; do
        run_case balanced "$p" "$repetition" 0
    done
    for p in 63 127 255 511 1023; do
        run_case original "$p" "$repetition" 0
        run_case original "$p" "$repetition" 1
    done
done
python3 scripts/summarize.py "$OUT/raw.tsv" "$OUT/summary.csv"
if python3 -c 'import matplotlib' >/dev/null 2>&1; then
    python3 scripts/plot.py "$OUT/summary.csv"
else
    printf 'matplotlib não disponível; gere os gráficos depois com scripts/plot.py\n' \
        > "$OUT/plots.log"
fi
printf 'Resultados: %s\n' "$OUT"
