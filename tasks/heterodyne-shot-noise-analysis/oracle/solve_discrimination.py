#!/usr/bin/env python3
"""Reference solution for the vacuum-vs-weak-coherent heterodyne readout task.

Every result is derived through the stated physical workflow:

  1. LO powers from the monitor means.
  2. Signal power / photon rate from the beat amplitude. The beat amplitude is
     taken from the phase-corrected IQ-demodulation displacement (a clean,
     noise-averaged coherent amplitude), so with the true RF conversion gain the
     extracted power is self-consistent with the shot-noise-limited statistics.
  3. IQ demodulation (one point per beat period).
  4. Linear phase-drift correction of the signal cloud.
  5. Discrimination threshold, error rate, measured vs theoretical std.
  5b. Theoretical heterodyne error rate vs measured.
  6. Shot-noise budget: simulated shot-noise std and its fraction of the total.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.constants import c, h
from scipy.stats import norm

INPUT = Path("/root/input/discrimination/heterodyne_data")

FS = 50e6
F_IQ = 0.5e6
T = 1.0 / F_IQ
M = int(FS * T)  # samples per beat period (100)
DT = 1.0 / FS
NU = c / 795e-9
GAIN_G = 257.988e3  # true measured RF conversion gain (V/W)
MONITOR_SCALE = 100.0  # (mean monitor volt) -> uW


def col(name: str) -> np.ndarray:
    return pd.read_csv(INPUT / name)["Voltage (V)"].to_numpy()


def demod(v: np.ndarray):
    """One (I, Q) per beat period: I=int v sin, Q=int v cos, times dt."""
    n = len(v) // M
    block = v[: n * M].reshape(n, M)
    t = np.arange(M) * DT
    i = (block * np.sin(2 * np.pi * F_IQ * t)).sum(1) * DT
    q = (block * np.cos(2 * np.pi * F_IQ * t)).sum(1) * DT
    return i, q


def principal_stds(x, y):
    ev = np.sort(np.linalg.eigh(np.cov(np.vstack((x, y)), bias=True))[0])[::-1]
    return np.sqrt(ev[0]), np.sqrt(ev[1])


def heterodyne_error_rate(n: float) -> float:
    sigma = np.sqrt(2.0)
    mu = 2.0 * np.sqrt(n)
    x_th = mu / 2.0
    return 0.5 * (norm.cdf(x_th, mu, sigma) + (1.0 - norm.cdf(x_th, 0.0, sigma)))


def main() -> None:
    sig = col("sig_2_CHAN1.csv")
    vac = col("vac_2_CHAN1.csv")
    lo1v = float(col("vac_2_CHAN2.csv").mean()) * MONITOR_SCALE
    lo2v = float(col("vac_2_CHAN3.csv").mean()) * MONITOR_SCALE
    lo1s = float(col("sig_2_CHAN2.csv").mean()) * MONITOR_SCALE
    lo2s = float(col("sig_2_CHAN3.csv").mean()) * MONITOR_SCALE

    # --- IQ demodulation ---
    sI, sQ = demod(sig)
    vI, vQ = demod(vac)

    # --- phase-drift correction of the signal cloud ---
    theta = np.unwrap(np.arctan2(sQ, sI))
    t_win = np.arange(len(sI)) * (M * DT)
    slope, intercept = np.polyfit(t_win, theta, 1)
    ideal = slope * t_win + intercept
    ideal = ideal[0] - ideal
    z = (sI + 1j * sQ) * np.exp(1j * ideal)
    sIc, sQc = z.real, z.imag

    # --- signal power from the clean (phase-corrected) beat amplitude ---
    disp = float(np.hypot(sIc.mean(), sQc.mean()))  # |centroid|, V*s
    vpp = 4.0 * disp / T  # A*T/2 = |IQ| -> Vpp = 2A
    op_pp = vpp / GAIN_G
    p_sig = (op_pp / 4.0 / (np.sqrt(lo1s * 1e-6) + np.sqrt(lo2s * 1e-6))) ** 2 * 2.0
    rate = p_sig / (h * NU)  # photons / s
    photons_per_window = rate * T

    # --- discrimination: linear threshold along the signal-centroid axis ---
    u = np.array([sIc.mean(), sQc.mean()]) / disp
    proj_sig = sIc * u[0] + sQc * u[1]
    proj_vac = vI * u[0] + vQ * u[1]
    threshold = disp / 2.0
    sig_err = int((proj_sig < threshold).sum())
    vac_err = int((proj_vac > threshold).sum())
    total = len(proj_sig) + len(proj_vac)
    error_rate = (sig_err + vac_err) / total

    # --- measured vs theoretical std ---
    vmax, vmin = principal_stds(vI, vQ)
    measured_std = (vmax + vmin) / 2.0
    theoretical_std = disp / np.sqrt(2.0 * photons_per_window)

    # --- gain-independent photon number from the cloud geometry ---
    # (displacement over vacuum std); must reconcile with the power-based number.
    photon_number_from_statistics = (disp / measured_std) ** 2 / 2.0

    # --- theoretical error rate ---
    theo_err = heterodyne_error_rate(photons_per_window)

    # --- shot-noise budget (analytic; matches the Monte-Carlo in expectation) ---
    p_total_w = (lo1v + lo2v) * 1e-6
    simulated_std = GAIN_G * np.sqrt(p_total_w * (h * NU) * (T / 2.0))
    shot_noise_fraction = (simulated_std / measured_std) ** 2

    results = {
        "lo_power_uw": {
            "lo1_vacuum": lo1v,
            "lo2_vacuum": lo2v,
            "lo1_signal": lo1s,
            "lo2_signal": lo2s,
        },
        "signal_power_pw": p_sig / 1e-12,
        "photon_rate_per_us": rate * 1e-6,
        "photons_per_window": photons_per_window,
        "photon_number_from_statistics": photon_number_from_statistics,
        "phase_drift_rate_rad_per_s": float(slope),
        "displacement": disp,
        "discrimination_threshold": threshold,
        "measured_error_rate": error_rate,
        "signal_errors": sig_err,
        "vacuum_errors": vac_err,
        "total_events": total,
        "measured_std": measured_std,
        "theoretical_std": theoretical_std,
        "measured_over_theoretical_std": measured_std / theoretical_std,
        "theoretical_error_rate": theo_err,
        "measured_over_theoretical_error_rate": error_rate / theo_err,
        "simulated_shot_noise_std": simulated_std,
        "shot_noise_fraction": shot_noise_fraction,
    }
    Path("/root/results.json").write_text(json.dumps(results, indent=2))

    with open("/root/iq_points.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["dataset", "I", "Q", "I_corrected", "Q_corrected"])
        for i in range(len(vI)):
            w.writerow([f"{'vacuum'}", repr(float(vI[i])), repr(float(vQ[i])), repr(float(vI[i])), repr(float(vQ[i]))])
        for i in range(len(sI)):
            w.writerow(["signal", repr(float(sI[i])), repr(float(sQ[i])), repr(float(sIc[i])), repr(float(sQc[i]))])

    print(f"P_sig = {p_sig / 1e-12:.4f} pW  rate = {rate * 1e-6:.3f}/us  N = {photons_per_window:.3f}")
    print(f"error rate = {error_rate:.4e}  theo = {theo_err:.4e}  ratio = {error_rate / theo_err:.3f}")
    print(f"meas/theo std = {measured_std / theoretical_std:.3f}  shot fraction = {shot_noise_fraction:.3f}")


if __name__ == "__main__":
    main()
