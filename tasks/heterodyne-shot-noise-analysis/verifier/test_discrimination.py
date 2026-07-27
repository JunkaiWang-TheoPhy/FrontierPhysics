"""Outcome-based verifier for the vacuum-vs-weak-coherent heterodyne task.

Every reference quantity is recomputed independently from the frozen inputs.
The agent's results.json and iq_points.csv are checked with tolerance bands.
The signal-power and (photon-number-sensitive) theoretical-error-rate bands are
set to reject a beat amplitude taken from a windowed FFT (which loses coherent
power to the capture-window phase drift) or from 2*sqrt(2)*RMS (inflated by shot
noise); only a clean, drift-corrected amplitude extraction passes. No expected
answers are stored.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import stat
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.constants import c, h
from scipy.stats import norm

ROOT = Path("/root")
INPUT = ROOT / "input" / "discrimination" / "heterodyne_data"
RESULTS = ROOT / "results.json"
IQ_CSV = ROOT / "iq_points.csv"

FS = 50e6
F_IQ = 0.5e6
T = 1.0 / F_IQ
M = int(FS * T)
DT = 1.0 / FS
NU = c / 795e-9
GAIN_G = 257.988e3
MONITOR_SCALE = 100.0

# Frozen sha256 of every ground-truth input file. The reference truth is
# recomputed from /root/input/heterodyne_data, which lives under an
# agent-writable /root; hashing the inputs against these frozen digests before
# computing the reference makes the verifier fail-closed against any attempt to
# doctor the inputs to move the graded target. A mismatch raises at import, so
# every test errors and the reward is 0.
INPUT_SHA256 = {
    "sig_2_CHAN1.csv": "34e881afdf99691ceabc8bb49c6cef0330dc97fa490cd863d69b2bbfa14e826e",
    "sig_2_CHAN2.csv": "46760a6341328be565016defb6b9ff0c40caacf33fbffd3d8a13d33f3f559889",
    "sig_2_CHAN3.csv": "8816302bdd0d962a11e10d561df8587fec2860646f19be747395ef2b8b201fd5",
    "vac_2_CHAN1.csv": "670ab71bfb2c3643f40bd717af2b39bea3dfa3d17a5dc0b86cdc4ab71cde0344",
    "vac_2_CHAN2.csv": "029005f99b470b37139d1c61eaf467887c65c9a9df98b1c09d6eb7bb97c61512",
    "vac_2_CHAN3.csv": "576373b389a6e4ea625e9ea418d5bf3d9e63be022e5972b84cf6345a50a0a047",
}


def assert_input_integrity():
    """Fail closed if any frozen input file was altered (or is missing)."""
    for name, want in INPUT_SHA256.items():
        p = INPUT / name
        assert p.exists() and not p.is_symlink(), f"missing/invalid input {name}"
        h_ = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h_.update(chunk)
        got = h_.hexdigest()
        assert got == want, f"input {name} sha256 {got} != frozen {want}"


# --------------------------------------------------------------------------
# independent reference computation
# --------------------------------------------------------------------------
def col(name):
    return pd.read_csv(INPUT / name)["Voltage (V)"].to_numpy()


def demod(v):
    n = len(v) // M
    block = v[: n * M].reshape(n, M)
    t = np.arange(M) * DT
    return ((block * np.sin(2 * np.pi * F_IQ * t)).sum(1) * DT, (block * np.cos(2 * np.pi * F_IQ * t)).sum(1) * DT)


def principal_stds(x, y):
    ev = np.sort(np.linalg.eigh(np.cov(np.vstack((x, y)), bias=True))[0])[::-1]
    return math.sqrt(ev[0]), math.sqrt(ev[1])


def heterodyne_error_rate(n):
    sg = math.sqrt(2.0)
    mu = 2.0 * math.sqrt(n)
    xth = mu / 2.0
    return 0.5 * (norm.cdf(xth, mu, sg) + (1.0 - norm.cdf(xth, 0.0, sg)))


def reference():
    assert_input_integrity()
    sig = col("sig_2_CHAN1.csv")
    vac = col("vac_2_CHAN1.csv")
    lo1v = float(col("vac_2_CHAN2.csv").mean()) * MONITOR_SCALE
    lo2v = float(col("vac_2_CHAN3.csv").mean()) * MONITOR_SCALE
    lo1s = float(col("sig_2_CHAN2.csv").mean()) * MONITOR_SCALE
    lo2s = float(col("sig_2_CHAN3.csv").mean()) * MONITOR_SCALE
    sI, sQ = demod(sig)
    vI, vQ = demod(vac)
    theta = np.unwrap(np.arctan2(sQ, sI))
    tw = np.arange(len(sI)) * (M * DT)
    slope, intercept = np.polyfit(tw, theta, 1)
    ideal = slope * tw + intercept
    ideal = ideal[0] - ideal
    z = (sI + 1j * sQ) * np.exp(1j * ideal)
    sIc, sQc = z.real, z.imag
    disp = float(np.hypot(sIc.mean(), sQc.mean()))
    vpp = 4.0 * disp / T
    op_pp = vpp / GAIN_G
    p_sig = (op_pp / 4.0 / (math.sqrt(lo1s * 1e-6) + math.sqrt(lo2s * 1e-6))) ** 2 * 2.0
    rate = p_sig / (h * NU)
    n_win = rate * T
    u = np.array([sIc.mean(), sQc.mean()]) / disp
    thr = disp / 2.0
    sig_err = int((sIc * u[0] + sQc * u[1] < thr).sum())
    vac_err = int((vI * u[0] + vQ * u[1] > thr).sum())
    total = len(sIc) + len(vI)
    err = (sig_err + vac_err) / total
    vmax, vmin = principal_stds(vI, vQ)
    meas_std = (vmax + vmin) / 2.0
    theo_std = disp / math.sqrt(2.0 * n_win)
    n_stat = (disp / meas_std) ** 2 / 2.0
    theo_err = heterodyne_error_rate(n_win)
    p_tot = (lo1v + lo2v) * 1e-6
    sim_std = GAIN_G * math.sqrt(p_tot * (h * NU) * (T / 2.0))
    return {
        "lo": (lo1v, lo2v, lo1s, lo2s),
        "p_sig_pw": p_sig / 1e-12,
        "rate_us": rate * 1e-6,
        "n": n_win,
        "n_stat": n_stat,
        "slope": float(slope),
        "disp": disp,
        "thr": thr,
        "err": err,
        "sig_err": sig_err,
        "vac_err": vac_err,
        "total": total,
        "meas_std": meas_std,
        "theo_std": theo_std,
        "theo_err": theo_err,
        "sim_std": sim_std,
        "shot_frac": (sim_std / meas_std) ** 2,
        "n_windows": len(sI),
    }


REF = reference()


def load_results():
    return json.loads(RESULTS.read_text())


def rel(a, b):
    return abs(float(a) - float(b)) / abs(b) if b else abs(float(a))


# --------------------------------------------------------------------------
# tests
# --------------------------------------------------------------------------
def test_input_integrity():
    """Ground truth is recomputed from these files; they must be pristine."""
    assert_input_integrity()


def test_artifacts_exist_and_schema():
    for p in (RESULTS, IQ_CSV):
        assert p.exists() and stat.S_ISREG(p.lstat().st_mode) and not p.is_symlink()
    r = load_results()
    for k in (
        "lo_power_uw",
        "signal_power_pw",
        "photon_rate_per_us",
        "photons_per_window",
        "photon_number_from_statistics",
        "phase_drift_rate_rad_per_s",
        "displacement",
        "discrimination_threshold",
        "measured_error_rate",
        "measured_std",
        "theoretical_std",
        "theoretical_error_rate",
        "simulated_shot_noise_std",
        "shot_noise_fraction",
    ):
        assert k in r, f"missing key {k}"
    for k in ("lo1_vacuum", "lo2_vacuum", "lo1_signal", "lo2_signal"):
        assert k in r["lo_power_uw"], f"missing lo_power_uw.{k}"


def test_lo_power():
    r = load_results()["lo_power_uw"]
    lo1v, lo2v, lo1s, lo2s = REF["lo"]
    assert rel(r["lo1_vacuum"], lo1v) < 0.10
    assert rel(r["lo2_vacuum"], lo2v) < 0.10
    assert rel(r["lo1_signal"], lo1s) < 0.10
    assert rel(r["lo2_signal"], lo2s) < 0.10


def test_signal_power_and_photon_rate():
    """Rejects rect-FFT / 2*sqrt2*RMS / raw amplitudes; passes a clean extraction."""
    r = load_results()
    assert rel(r["signal_power_pw"], REF["p_sig_pw"]) < 0.10, (
        f"signal power {r['signal_power_pw']:.4f} pW vs reference {REF['p_sig_pw']:.4f} pW"
    )
    assert rel(r["photon_rate_per_us"], REF["rate_us"]) < 0.10
    assert rel(r["photons_per_window"], REF["n"]) < 0.10
    # internal consistency: photon rate * window duration = photons_per_window
    assert rel(r["photons_per_window"], r["photon_rate_per_us"] * 1e6 * T) < 0.02


def test_photon_number_reconciliation():
    """The two independent photon-number estimates must agree.

    ``photons_per_window`` is the power-based (gain-dependent) number; the
    gain-independent number is fixed by the cloud geometry alone,
    ``N = (displacement / vacuum_std)**2 / 2``. For a shot-noise-limited
    coherent state these must coincide. A beat amplitude taken from a windowed
    FFT (biased low by the phase drift) drives the power-based number far below
    the geometric one — the ~45% discrepancy seen in the raw capture — so this
    reconciliation rejects it loudly instead of silently.
    """
    r = load_results()
    # gain-independent number recomputed from the frozen inputs
    assert rel(r["photon_number_from_statistics"], REF["n_stat"]) < 0.10, (
        f"photon_number_from_statistics {r['photon_number_from_statistics']:.4f} vs reference {REF['n_stat']:.4f}"
    )
    # it must actually be the geometric quantity, not a copy of photons_per_window
    disp = float(r["displacement"])
    meas = float(r["measured_std"])
    assert rel(r["photon_number_from_statistics"], (disp / meas) ** 2 / 2.0) < 0.03
    # the power-based and geometry-based numbers must reconcile
    assert rel(r["photons_per_window"], r["photon_number_from_statistics"]) < 0.15, (
        f"photon numbers disagree: power {r['photons_per_window']:.4f} vs statistics {r['photon_number_from_statistics']:.4f}"
    )


def test_iq_demodulation_points():
    r = load_results()
    rows = list(csv.DictReader(IQ_CSV.open()))
    by = {"vacuum": [], "signal": []}
    for row in rows:
        by[row["dataset"].strip().lower()].append(row)
    assert len(by["vacuum"]) == REF["n_windows"], f"{len(by['vacuum'])} vacuum rows"
    assert len(by["signal"]) == REF["n_windows"], f"{len(by['signal'])} signal rows"
    # vacuum cloud std recomputed from the agent's own points matches results + reference
    vI = np.array([float(x["I"]) for x in by["vacuum"]])
    vQ = np.array([float(x["Q"]) for x in by["vacuum"]])
    vmax, vmin = principal_stds(vI, vQ)
    vstd = (vmax + vmin) / 2.0
    assert rel(vstd, REF["meas_std"]) < 0.10
    assert rel(vstd, r["measured_std"]) < 0.10
    # signal corrected centroid magnitude = displacement
    sIc = np.array([float(x["I_corrected"]) for x in by["signal"]])
    sQc = np.array([float(x["Q_corrected"]) for x in by["signal"]])
    disp = math.hypot(sIc.mean(), sQc.mean())
    assert rel(disp, REF["disp"]) < 0.10


def test_phase_drift_correction():
    r = load_results()
    assert rel(r["displacement"], REF["disp"]) < 0.10
    assert rel(r["phase_drift_rate_rad_per_s"], REF["slope"]) < 0.20
    # correction really collapses the ring: corrected signal principal spread
    # must be far smaller than the ring radius (~displacement)
    rows = list(csv.DictReader(IQ_CSV.open()))
    sIc = np.array([float(x["I_corrected"]) for x in rows if x["dataset"].strip().lower() == "signal"])
    sQc = np.array([float(x["Q_corrected"]) for x in rows if x["dataset"].strip().lower() == "signal"])
    smax, smin = principal_stds(sIc, sQc)
    assert (smax + smin) / 2.0 < 0.5 * REF["disp"], "signal cloud not collapsed (still a ring?)"


def test_error_rate():
    r = load_results()
    assert rel(r["measured_error_rate"], REF["err"]) < 0.20, f"measured error rate {r['measured_error_rate']:.4e} vs {REF['err']:.4e}"
    assert rel(r["discrimination_threshold"], REF["thr"]) < 0.12


def test_theoretical_error_rate_and_std():
    """Photon-number-sensitive: rejects a windowed-FFT amplitude (wrong N)."""
    r = load_results()
    assert rel(r["theoretical_error_rate"], REF["theo_err"]) < 0.10, (
        f"theoretical error rate {r['theoretical_error_rate']:.4e} vs {REF['theo_err']:.4e}"
    )
    assert rel(r["theoretical_std"], REF["theo_std"]) < 0.10
    assert rel(r["measured_over_theoretical_std"], REF["meas_std"] / REF["theo_std"]) < 0.12
    assert rel(r["measured_over_theoretical_error_rate"], REF["err"] / REF["theo_err"]) < 0.12
    # a shot-noise-limited state: both ratios must be near unity
    assert 0.80 < r["measured_over_theoretical_std"] < 1.25
    assert 0.80 < r["measured_over_theoretical_error_rate"] < 1.25


def test_shot_noise_budget():
    r = load_results()
    assert rel(r["simulated_shot_noise_std"], REF["sim_std"]) < 0.10
    assert rel(r["shot_noise_fraction"], REF["shot_frac"]) < 0.10
    assert 0.0 < r["shot_noise_fraction"] <= 1.10
