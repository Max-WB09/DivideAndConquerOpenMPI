#!/usr/bin/env python3
"""Summarize raw timings and compute both speed-ups from matched references."""
import csv
import statistics
import sys
from collections import defaultdict


def main(source, target):
    groups = defaultdict(list)
    n_values = set()
    with open(source, newline="") as file:
        for row in csv.DictReader(file, delimiter="\t"):
            if row["verification"] != "OK":
                raise ValueError(f"verification failed: {row}")
            n_values.add(row["n"])
            key = (row["mode"], int(row["processes"]), row["yield"])
            groups[key].append(float(row["seconds"]))
    if len(n_values) != 1:
        raise ValueError("all cases must use the same n")
    for key, values in groups.items():
        if len(values) != 10:
            raise ValueError(f"expected 10 repetitions for {key}, found {len(values)}")

    def median(mode, p, yield_mode="NA"):
        return statistics.median(groups[(mode, p, yield_mode)])

    bubble = median("bubble", 1)
    columns = ["mode", "processes", "yield", "n", "repetitions", "median_s",
               "min_s", "max_s", "bubble_median_s", "tree_median_s",
               "algorithm_gain", "speedup_bubble", "speedup_tree", "efficiency"]
    with open(target, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for (mode, p, yield_mode), values in sorted(groups.items()):
            measured = statistics.median(values)
            row = {
                "mode": mode, "processes": p, "yield": yield_mode,
                "n": next(iter(n_values)), "repetitions": len(values),
                "median_s": f"{measured:.6f}", "min_s": f"{min(values):.6f}",
                "max_s": f"{max(values):.6f}",
            }
            if mode in ("original", "balanced"):
                tree = median(f"{mode}_reference", p)
                threads = 32 if mode == "original" and p >= 63 else p
                row.update({
                    "bubble_median_s": f"{bubble:.6f}",
                    "tree_median_s": f"{tree:.6f}",
                    "algorithm_gain": f"{bubble / tree:.4f}",
                    "speedup_bubble": f"{bubble / measured:.4f}",
                    "speedup_tree": f"{tree / measured:.4f}",
                    "efficiency": f"{tree / measured / threads:.4f}",
                })
            writer.writerow(row)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: summarize.py raw.tsv summary.csv")
    main(sys.argv[1], sys.argv[2])
