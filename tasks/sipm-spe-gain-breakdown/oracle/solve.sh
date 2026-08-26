#!/bin/bash
set -euo pipefail

# Numeric deliverables: computed from the shipped .bin files and the cryostat
# logs, nothing hardcoded.
python3 /oracle/solve.py

# Paper deliverable: the characterisation note this task was derived from. A
# copy oracle is used here deliberately -- generating the prose programmatically
# would be less faithful than the document the work actually produced. The
# figures in it are not decoration either: assets/paper/make_figures.py draws
# every one of them from the deliverables solve.py just wrote, so a maintainer
# can confirm the paper follows from the shipped data rather than from stored
# answers. The LaTeX source sits beside the PDF.
cp /oracle/assets/paper/sipm_vbd_calibration.pdf /root/paper.pdf
