#!/bin/bash
set -euo pipefail

# Part A: balanced-heterodyne shot-noise characterization (LO-power sweep +
# spectrum-analyzer trace) -> IQ_demodulation.csv, theo_var.csv,
# spectrum_analyzer.csv, theoretical_Vrms.txt
cp /oracle/solve_shot_noise.py /root/solve_shot_noise.py
python3 /root/solve_shot_noise.py

# Part B: vacuum-vs-weak-coherent-state heterodyne discrimination ->
# results.json, iq_points.csv
cp /oracle/solve_discrimination.py /root/solve_discrimination.py
python3 /root/solve_discrimination.py
