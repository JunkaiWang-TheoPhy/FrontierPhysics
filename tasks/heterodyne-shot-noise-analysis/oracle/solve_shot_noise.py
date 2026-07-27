#!/usr/bin/env python3
"""Reference solution for the shot-noise characterization task.

Derives every result through the stated scientific workflow:

  1. IQ-demodulate each heterodyne (vacuum) record and report the demodulated
     variance versus local-oscillator (LO) power.
  2. Compute the theoretical shot-noise variance versus LO power over
     0..400 uW (101 points).
  3. Convert the spectrum-analyzer trace from dBm to Vrms.
  4. Compute the theoretical shot-noise Vrms (noise density) for the
     spectrum-analyzer measurement.

Detector constants used here (conversion gain, monitor calibration,
transimpedance, responsivity) are the values documented for the Thorlabs
PDB210A / this measurement; an agent recovers them from the bundled manual and
the prompt.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.constants import c, e, h

INPUT = Path("/root/input/shot_noise")
HET = INPUT / "heterodyne_data"
SPEC = INPUT / "spectrum"

# --- fixed measurement parameters -----------------------------------------
FS = 50e6  # oscilloscope sampling rate (Hz)
F_IQ = 0.5e6  # heterodyne modulation / beat frequency (Hz)
NUM_PERIOD = 1  # IQ integration window length, in beat periods
WAVELENGTH = 795e-9  # probe wavelength (m)
NU = c / WAVELENGTH  # optical frequency (Hz)
GAIN_G = 257.988e3  # measured RF-output conversion gain (V/W)
MONITOR_SCALE = 100.0  # (mean(mon1)+mean(mon2)) [V] -> LO power [uW]

# spectrum-analyzer / shot-noise-density constants (from the PDB210A manual)
Z_TRANS = 175e3  # transimpedance (V/A)
RESP = 0.57  # responsivity at 795 nm (A/W)
SA_LOAD = 50.0  # spectrum-analyzer input load (ohm)

N_HET = 9  # number of LO-power records (vac_1 .. vac_9)


def read_voltage(path: Path) -> np.ndarray:
    return pd.read_csv(path)["Voltage (V)"].to_numpy()


def iq_demod(data: np.ndarray, num_pts: int, t_div: float, f: float):
    """One (I, Q) point for a window: I = sum v sin(2 pi f t) dt, Q likewise cos."""
    t = np.linspace(0.0, (num_pts - 1) * t_div, num_pts)
    w = 2.0 * np.pi * f
    int_i = np.sum(data * np.sin(w * t) * t_div)
    int_q = np.sum(data * np.cos(w * t) * t_div)
    return int_i, int_q


def principal_stds(x, y):
    """Principal standard deviations from the 2x2 covariance eigenvalues."""
    cov = np.cov(np.vstack((x, y)), bias=True)
    eig = np.linalg.eigh(cov)[0]
    stds = np.sqrt(np.sort(eig)[::-1])
    return stds[0], stds[1]


def demod_variance(voltage: np.ndarray) -> float:
    """Variance of the IQ cloud = ((sigma_major + sigma_minor) / 2) ** 2."""
    period = 1.0 / F_IQ
    num_pts_period = int(period * FS)  # 100 samples / period
    win = num_pts_period * NUM_PERIOD
    t_capture = (len(voltage) - 1) / FS
    n_win = int(t_capture // (period * NUM_PERIOD))
    i_vals = np.empty(n_win)
    q_vals = np.empty(n_win)
    for k in range(n_win):
        seg = voltage[win * k : win * (k + 1)]
        i_vals[k], q_vals[k] = iq_demod(seg, win, 1.0 / FS, F_IQ)
    smax, smin = principal_stds(i_vals, q_vals)
    return ((smax + smin) / 2.0) ** 2


def lo_power_uw(mon1: np.ndarray, mon2: np.ndarray) -> float:
    return (float(np.mean(mon1)) + float(np.mean(mon2))) * MONITOR_SCALE


# --- Deliverable 1: measured demodulated variance vs LO power --------------
def deliverable_1() -> pd.DataFrame:
    rows = []
    for i in range(1, N_HET + 1):
        v = read_voltage(HET / f"vac_{i}_CHAN1.csv")
        m1 = read_voltage(HET / f"vac_{i}_CHAN2.csv")
        m2 = read_voltage(HET / f"vac_{i}_CHAN3.csv")
        rows.append((lo_power_uw(m1, m2), demod_variance(v)))
    rows.sort(key=lambda r: r[0])
    return pd.DataFrame(rows, columns=["LO power (µW)", "Variance (V^2*s^2)"])


# --- Deliverable 2: theoretical shot-noise variance vs LO power ------------
def theoretical_variance(power_uw: np.ndarray) -> np.ndarray:
    """Analytic expectation of the demodulated shot-noise variance.

    White shot noise with per-sample power variance P*h*nu*fs, scaled by the
    conversion gain and integrated over one beat period, gives
        Var = GAIN_G**2 * P[W] * h*nu * (T/2),  T = 1/F_IQ.
    (fs cancels; equals the Monte-Carlo simulation in expectation.)
    """
    t_window = NUM_PERIOD / F_IQ
    p_w = power_uw * 1e-6
    return GAIN_G**2 * p_w * (h * NU) * (t_window / 2.0)


def deliverable_2() -> pd.DataFrame:
    power = np.linspace(0.0, 400.0, 101)
    return pd.DataFrame({"LO power (µW)": power, "Variance (V^2*s^2)": theoretical_variance(power)})


# --- Deliverable 3: spectrum-analyzer trace, dBm -> Vrms -------------------
def parse_spectrum_file(path: Path):
    lines = path.read_text().splitlines()
    start_idx = end_idx = None
    for i, line in enumerate(lines):
        if "# Begin TRACE A Data" in line:
            start_idx = i + 1
        if "# Data Done" in line:
            end_idx = i - 2
            break
    freqs, powers = [], []
    for line in lines[start_idx : end_idx + 1]:
        parts = [p.strip() for p in line.strip().split(",")]
        if len(parts) >= 3:
            try:
                powers.append(float(parts[1]))
                freqs.append(float(parts[2]))
            except ValueError:
                continue
    return np.asarray(freqs), np.asarray(powers)


def dbm_to_vrms(dbm: np.ndarray, load: float = SA_LOAD) -> np.ndarray:
    return np.sqrt(10.0 ** ((np.asarray(dbm) - 30.0) / 10.0) * load)


def deliverable_3() -> pd.DataFrame:
    freq, power_dbm = parse_spectrum_file(SPEC / "vac_100uW_spectrum.csv")
    return pd.DataFrame({"Frequency (MHz)": freq, "Vrms (Volt)": dbm_to_vrms(power_dbm)})


# --- Deliverable 4: theoretical shot-noise Vrms density -------------------
def deliverable_4() -> float:
    m1 = read_voltage(SPEC / "vac_100uW_CHAN2.csv")
    m2 = read_voltage(SPEC / "vac_100uW_CHAN3.csv")
    p_uw = lo_power_uw(m1, m2)
    sv = 2.0 * e * Z_TRANS**2 * RESP * p_uw * 1e-6  # V^2/Hz
    return float(np.sqrt(sv))  # V/sqrt(Hz)


def main() -> None:
    deliverable_1().to_csv("/root/IQ_demodulation.csv", index=False)
    deliverable_2().to_csv("/root/theo_var.csv", index=False)
    deliverable_3().to_csv("/root/spectrum_analyzer.csv", index=False)
    Path("/root/theoretical_Vrms.txt").write_text(f"{deliverable_4():.12e}\n")
    print("Wrote IQ_demodulation.csv, theo_var.csv, spectrum_analyzer.csv, theoretical_Vrms.txt")


if __name__ == "__main__":
    main()
