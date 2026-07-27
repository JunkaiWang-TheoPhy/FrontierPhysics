"""Outcome-based verifier for the shot-noise characterization task.

Every reference quantity is recomputed independently from the frozen inputs in
/root/input; the agent's four artifacts are then checked with tolerance bands
that absorb legitimate method variation (variance defined from covariance
eigenvalues vs. a single quadrature, analytic vs. Monte-Carlo theory, minor
differences in reading detector constants from the manual). No expected answers
are stored.
"""

from __future__ import annotations

import stat
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.constants import c, e, h

ROOT = Path("/root")
INPUT = ROOT / "input" / "shot_noise"
HET = INPUT / "heterodyne_data"
SPEC = INPUT / "spectrum"

IQ_CSV = ROOT / "IQ_demodulation.csv"
THEO_CSV = ROOT / "theo_var.csv"
SPEC_CSV = ROOT / "spectrum_analyzer.csv"
VRMS_TXT = ROOT / "theoretical_Vrms.txt"

# Measurement constants (independent copy for the reference computation).
FS = 50e6
F_IQ = 0.5e6
NUM_PERIOD = 1
NU = c / 795e-9
GAIN_G = 257.988e3
MONITOR_SCALE = 100.0
Z_TRANS = 175e3
RESP = 0.57
SA_LOAD = 50.0
N_HET = 9


# --------------------------------------------------------------------------
# helpers: independent reference computation
# --------------------------------------------------------------------------
def read_voltage(path: Path) -> np.ndarray:
    return pd.read_csv(path)["Voltage (V)"].to_numpy()


def iq_demod(data: np.ndarray, num_pts: int, t_div: float, f: float):
    t = np.linspace(0.0, (num_pts - 1) * t_div, num_pts)
    w = 2.0 * np.pi * f
    return np.sum(data * np.sin(w * t) * t_div), np.sum(data * np.cos(w * t) * t_div)


def principal_stds(x, y):
    cov = np.cov(np.vstack((x, y)), bias=True)
    eig = np.sqrt(np.sort(np.linalg.eigh(cov)[0])[::-1])
    return eig[0], eig[1]


def demod_iq(voltage: np.ndarray):
    period = 1.0 / F_IQ
    win = int(period * FS) * NUM_PERIOD
    n_win = int(((len(voltage) - 1) / FS) // (period * NUM_PERIOD))
    i_vals = np.empty(n_win)
    q_vals = np.empty(n_win)
    for k in range(n_win):
        seg = voltage[win * k : win * (k + 1)]
        i_vals[k], q_vals[k] = iq_demod(seg, win, 1.0 / FS, F_IQ)
    return i_vals, q_vals


def reference_measured():
    """Return sorted arrays (lo_power_uw, variance_eig, variance_max)."""
    lo, var_eig, var_max = [], [], []
    for i in range(1, N_HET + 1):
        v = read_voltage(HET / f"vac_{i}_CHAN1.csv")
        m1 = read_voltage(HET / f"vac_{i}_CHAN2.csv")
        m2 = read_voltage(HET / f"vac_{i}_CHAN3.csv")
        iq_i, iq_q = demod_iq(v)
        smax, smin = principal_stds(iq_i, iq_q)
        lo.append((float(np.mean(m1)) + float(np.mean(m2))) * MONITOR_SCALE)
        var_eig.append(((smax + smin) / 2.0) ** 2)
        var_max.append(smax**2)
    order = np.argsort(lo)
    return (np.asarray(lo)[order], np.asarray(var_eig)[order], np.asarray(var_max)[order])


def theory_variance(power_uw: np.ndarray) -> np.ndarray:
    t_window = NUM_PERIOD / F_IQ
    return GAIN_G**2 * (power_uw * 1e-6) * (h * NU) * (t_window / 2.0)


def parse_spectrum(path: Path):
    lines = path.read_text().splitlines()
    start = end = None
    for i, line in enumerate(lines):
        if "# Begin TRACE A Data" in line:
            start = i + 1
        if "# Data Done" in line:
            end = i - 2
            break
    freqs, powers = [], []
    for line in lines[start : end + 1]:
        parts = [p.strip() for p in line.strip().split(",")]
        if len(parts) >= 3:
            try:
                powers.append(float(parts[1]))
                freqs.append(float(parts[2]))
            except ValueError:
                continue
    return np.asarray(freqs), np.asarray(powers)


def dbm_to_vrms(dbm: np.ndarray) -> np.ndarray:
    return np.sqrt(10.0 ** ((np.asarray(dbm) - 30.0) / 10.0) * SA_LOAD)


def reference_theoretical_vrms() -> float:
    m1 = read_voltage(SPEC / "vac_100uW_CHAN2.csv")
    m2 = read_voltage(SPEC / "vac_100uW_CHAN3.csv")
    p_uw = (float(np.mean(m1)) + float(np.mean(m2))) * MONITOR_SCALE
    return float(np.sqrt(2.0 * e * Z_TRANS**2 * RESP * p_uw * 1e-6))


def regular_file(path: Path) -> bool:
    return path.exists() and stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink()


def two_columns(path: Path) -> tuple[np.ndarray, np.ndarray]:
    frame = pd.read_csv(path)
    assert frame.shape[1] >= 2, f"{path} needs >=2 columns, found {frame.shape[1]}"
    x = frame.iloc[:, 0].to_numpy(dtype=float)
    y = frame.iloc[:, 1].to_numpy(dtype=float)
    return x, y


# --------------------------------------------------------------------------
# tests
# --------------------------------------------------------------------------
def test_artifacts_exist() -> None:
    for path in (IQ_CSV, THEO_CSV, SPEC_CSV, VRMS_TXT):
        assert regular_file(path), f"missing or unsafe artifact: {path}"


def test_iq_demodulation_vs_lo_power() -> None:
    lo_ref, var_eig, var_max = reference_measured()
    lo_a, var_a = two_columns(IQ_CSV)
    assert len(lo_a) == N_HET, f"expected {N_HET} rows, found {len(lo_a)}"

    order = np.argsort(lo_a)
    lo_a, var_a = lo_a[order], var_a[order]

    # LO powers: pair by rank; monitor calibration read from the manual may
    # differ slightly, so allow a modest fractional band.
    np.testing.assert_allclose(lo_a, lo_ref, rtol=0.20, atol=1.0)

    # Variance is calibration-independent (CHAN1 only). Accept either the
    # covariance-eigenvalue definition or the single-quadrature definition.
    ok_eig = np.abs(var_a - var_eig) <= 0.15 * var_eig + 1e-24
    ok_max = np.abs(var_a - var_max) <= 0.15 * var_max + 1e-24
    assert np.all(ok_eig | ok_max), f"measured variance mismatch\n agent={var_a}\n eig ref={var_eig}\n max ref={var_max}"


def test_measured_variance_is_shot_noise_linear() -> None:
    """Measured variance must rise ~linearly with LO power at the shot-noise slope."""
    lo_a, var_a = two_columns(IQ_CSV)
    slope, intercept = np.polyfit(lo_a, var_a, 1)
    expected_slope = theory_variance(np.asarray([1.0]))[0]  # per uW
    assert slope > 0.0
    np.testing.assert_allclose(slope, expected_slope, rtol=0.30)
    # near-zero intercept relative to the span of the data
    assert abs(intercept) < 0.5 * float(np.max(var_a))


def test_theoretical_variance_curve() -> None:
    lo_a, var_a = two_columns(THEO_CSV)
    assert len(lo_a) == 101, f"expected 101 points, found {len(lo_a)}"
    assert abs(lo_a.min()) < 1e-9 and abs(lo_a.max() - 400.0) < 1e-6
    ref = theory_variance(lo_a)
    # analytic vs Monte-Carlo: generous absolute floor at P=0, tight elsewhere
    np.testing.assert_allclose(var_a, ref, rtol=0.08, atol=1e-3 * float(np.max(ref)))


def test_theory_consistent_with_measurement() -> None:
    """Cross-check: measured demodulated variance is within a small factor of theory."""
    lo_ref, var_eig, _ = reference_measured()
    ref = theory_variance(lo_ref)
    ratio = var_eig / ref
    # real data carries some excess/technical noise; require order-unity agreement
    assert np.all((ratio > 0.4) & (ratio < 2.5)), f"variance/theory ratios={ratio}"


def test_spectrum_dbm_to_vrms() -> None:
    freq_ref, dbm_ref = parse_spectrum(SPEC / "vac_100uW_spectrum.csv")
    vrms_ref = dbm_to_vrms(dbm_ref)
    freq_a, vrms_a = two_columns(SPEC_CSV)
    assert len(freq_a) >= int(0.95 * len(freq_ref)), f"too few spectrum rows: {len(freq_a)} vs {len(freq_ref)}"
    # match by nearest frequency (frequencies reported in MHz)
    lookup = {round(f, 6): vv for f, vv in zip(freq_a, vrms_a)}
    matched = 0
    for f, vv in zip(freq_ref, vrms_ref):
        got = lookup.get(round(f, 6))
        if got is None:
            j = int(np.argmin(np.abs(freq_a - f)))
            if abs(freq_a[j] - f) > 1e-4:
                continue
            got = vrms_a[j]
        assert abs(got - vv) <= 1e-4 * vv + 1e-12, f"Vrms mismatch at {f} MHz: {got} vs {vv}"
        matched += 1
    assert matched >= int(0.95 * len(freq_ref)), f"only matched {matched}/{len(freq_ref)}"


def test_theoretical_vrms() -> None:
    ref = reference_theoretical_vrms()
    text = VRMS_TXT.read_text().strip().split()[0]
    value = float(text)
    # Z (transimpedance) and R (responsivity) are read from the manual; allow a
    # band that covers reasonable responsivity readings (~0.55-0.60).
    np.testing.assert_allclose(value, ref, rtol=0.25)
