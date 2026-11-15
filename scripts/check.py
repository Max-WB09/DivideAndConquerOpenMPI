#!/usr/bin/env python3
"""Small local correctness checks; performance runs belong on Atlântica."""
import os
import re
import subprocess


def run(command):
    env = os.environ.copy()
    env.setdefault("OMPI_ALLOW_RUN_AS_ROOT", "1")
    env.setdefault("OMPI_ALLOW_RUN_AS_ROOT_CONFIRM", "1")
    output = subprocess.check_output(command, text=True, env=env)
    assert "verificacao=OK" in output, output
    return output


for mode, n, p in (("original", 40, 1), ("original", 41, 7),
                   ("balanced", 41, 7), ("balanced", 40, 8)):
    if mode == "original":
        delta = (n + (p + 1) // 2 - 1) // ((p + 1) // 2)
        run(["bin/sequencial", str(n), str(delta)])
    else:
        run(["bin/sequencial", str(n), "--balanced", str(p)])
    parameter = delta if mode == "original" else p
    output = run(["mpirun", "--oversubscribe", "-np", str(p),
                  "bin/mpi_sort", mode, str(n), str(parameter)])
    if mode == "original":
        assert int(re.search(r"delta=(\d+)", output).group(1)) == delta
print("Todas as verificações locais passaram.")
