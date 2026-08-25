#!/bin/bash
set -euo pipefail

# Numeric deliverable: computed from the bundled traces, nothing hardcoded.
# Also emits /root/phase_noise_PSD.pdf as a diagnostic, showing that the figure
# in the reference paper is reproducible from those same traces.
python3 /oracle/solve.py

# Paper deliverable: the corresponding section of the author's PhD thesis,
# which is the human-authored write-up this task was derived from. A copy
# oracle is used here deliberately -- regenerating the prose programmatically
# would be less faithful than the document the research actually produced
# (see oracle-patterns.md section 4, "native scientific artifacts").
# assets/ also carries the LaTeX source and figures this PDF was built from.
cp /oracle/assets/rydberg_phase_noise.pdf /root/paper.pdf
