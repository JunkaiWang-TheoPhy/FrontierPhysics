#!/usr/bin/env bash
# Reference solution: the task author's patented signal chain (CN106476845B;
# the author is the inventor), implemented in solve.py. Derives everything
# from /root/data at run time — no stored answers anywhere.
set -euo pipefail

python3 /oracle/solve.py
