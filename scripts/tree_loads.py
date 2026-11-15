#!/usr/bin/env python3
"""Show leaf sizes of the balanced rank tree, especially useful for P=31."""
import sys


def sizes(base, workers, n):
    if workers == 1:
        yield base, n
        return
    left = (workers + 1) // 2
    half = n // 2
    yield from sizes(base, left, half)
    yield from sizes(base + left, workers - left, n - half)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: tree_loads.py n processes")
    n, p = map(int, sys.argv[1:])
    for rank, count in sorted(sizes(0, p, n)):
        print(f"rank={rank} elements={count}")
