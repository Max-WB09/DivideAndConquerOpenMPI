#!/usr/bin/env python3
"""Choose n so one Bubble Sort run takes roughly 30-60 s on this node."""
import math
import re
import subprocess
import sys

n = 20000
for attempt in range(8):
    output = subprocess.check_output(
        ["srun", "--nodes=1", "--ntasks=1", "bin/sequencial", str(n)],
        text=True,
    )
    if "verificacao=OK" not in output:
        raise RuntimeError(output)
    seconds = float(re.search(r"tempo=([0-9.]+)", output).group(1))
    print(f"calibracao n={n} tempo={seconds:.3f}s", file=sys.stderr)
    if 30 <= seconds <= 60:
        print(n)
        break
    factor = max(0.5, min(4.0, math.sqrt(45 / max(seconds, 0.001))))
    n = max(2, round(n * factor))
else:
    raise RuntimeError("calibração não convergiu em oito tentativas")
