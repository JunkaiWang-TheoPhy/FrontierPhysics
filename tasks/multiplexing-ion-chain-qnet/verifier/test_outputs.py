"""Deterministic blockers for multiplexing-ion-chain-qnet.

Evaluation follows the FrontierCode split (cognition.com/blog/frontier-code):
this file holds the deterministic blockers — input integrity, report structure,
and hard physics outcomes — and owns the rollout reward. Soft scientific
quality (is paper.pdf publishable?) is scored afterwards by the detached
rubric review against rubric.json, which also defines how blockers and
weighted criteria aggregate into a publication decision.

Every expected value here is independent of the oracle's implementation:
a frozen provenance-pinned reference for the BEM frequency, physics invariants
(force balance, symmetry) for the chain statics, and a classical dynamics
simulation of the *submitted* waveform for the transport. Any physically valid
construction passes; no specific ansatz or solver is required.

Gate calibration (2026-08-17, independent NumPy/SciPy implementation):
  single 100 um / 10 us move          -> residual quanta
    quintic + trap-center correction     3.4e-10   pass
    sine-ramp STA + correction           1.5e-10   pass  (valid alternative)
    quintic without correction           4.8e+04   fail
    linear ramp                          1.3e+05   fail
  9-ion chain, correction omitted        1.5e+03   fail (COM-mode quanta, 9m)
  force residual: correct spacings 5.5e-14; rounded to 2 decimals 2.7e-3;
    one spacing off by 1% 6.8e-2; equal spacings 8.7e-1.
  100 kHz filter stage (chain COM-mode quanta, effective mass 9m):
    ideal quintic sequence, filtered     533.5 at the final sample (grid-
      insensitive to 5e-6 rel); duration scan monotone 3.0e4 (T=2) -> 25
      (T=20), fast/slow mean ratio 273
    valid compensated control (7th-order family, one-pole pre-emphasis)
      2.7e-07 quanta worst dwell, 4e-06 um dwell-position error  pass
    naive quintic pre-emphasis (control jumps at ends)  1.5e+03   fail
    ideal waveform submitted as control   567 quanta + 1.1 um mispoint  fail
CSV round-off at 4 decimals contributes ~1e-6 quanta — margins are >2 orders
on the fail side and ~8 on the pass side.
"""

import csv
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np

ROOT = Path("/root")
LOGS = Path("/logs/verifier")

# Frozen ground truth. Provenance: constant-panel FastLap BEM solve on the
# 13,883-panel mesh derived from surface_trap.stl (mesh sha256 c85d5f0b...,
# geometry from HaeffnerLab/integrated_photonics_bem @ a58710a1, examples/sqip
# htrap; fit-grid center [0.00375, 0.075, -0.1] mm), 80 V RF at 39.15 MHz,
# solver settings num_mom=4 num_lev=3 tol=1e-5 (143 iterations, 9.87e-6
# achieved), computed by the 2026-08-17 oracle run (reward 1.0). Regenerate by
# running oracle/solve.sh in the task image and reading
# /root/oracle_diagnostics.json -> bem.radial_parallel_mhz. The verifier
# deliberately does not ship the BEM pipeline so grader truth stays independent
# of the oracle implementation. ALPHA was retuned from 0.00174 to 0.00121 on
# 2026-08-17: the old value made the published 0.179 MHz axial operating point
# of arXiv:2405.10501 invert (through the alpha given in task.md) to within
# 0.11% of this reference; the same inversion now lands 19.8% away, outside
# the acceptance band.
RADIAL_REFERENCE_MHZ = 4.295858149
RADIAL_REL_TOL = 0.10  # covers legitimate mesh/method variation
RADIAL_ABS_TOL_MHZ = 0.05
ALPHA = 0.00121
STL_SHA256 = "d79517f36a46215cc852c452af47961b2374f3882efb717ef120dffe9593941f"

ION_MASS_KG = 40.0 * 1.66053906660e-27
ELEMENTARY_CHARGE_C = 1.602176634e-19
COULOMB_CONSTANT = 1.0 / (4.0 * math.pi * 8.8541878128e-12)
HBAR = 1.054571817e-34

SINGLE_DISTANCE_UM = 100.0
SINGLE_DURATION_US = 10.0
MOVE_US = 10.0
DWELL_US = 1.0
STAGES = 8
CHAIN_DURATION_US = STAGES * (MOVE_US + DWELL_US)
SAMPLES = 10_000

RESIDUAL_QUANTA_MAX = 1.0
FORCE_RESIDUAL_MAX = 1e-2
DWELL_FLATNESS_UM = 0.05

# Hardware chain declared in task.md: in-vacuum first-order RC low-pass on the
# DC electrodes, 100 kHz cutoff, output starting settled at the first sample.
FILTER_TAU_US = 1.0 / (2.0 * math.pi * 0.1)
# task.md: herald path is the full 100 km of fiber at 2.0e8 m/s per attempt.
EXPECTED_ATTEMPT_RATE_HZ = 2.0e8 / 100e3
SCAN_DURATIONS_US = list(range(2, 21))

EXPECTED_KEYS = (
    ["W_radial_freq", "W_axial_freq"]
    + [f"d{i}" for i in range(1, 9)]
    + ["attempt_rate_hz", "n_com_filtered", "g2(0)", "n_excitation"]
)

# Frozen time-tagger histogram bundle (/root/g2_data): 54 per-ion files, sha256
# over sorted (name, bytes). Any legitimate analysis of this data shows strong
# antibunching: matched-window peak ratios span ~0.11 (wide windows) to ~0.45
# (single-bin), and background-corrected treatments can go lower, so the
# deterministic gate is a wide sanity band; methodology is judged by the
# rubric. n_excitation is an open research question on the bundled ARTIQ Rabi
# data (run selection and the fit model are the agent's judgment), so it gets
# a physical-range gate only.
G2_BUNDLE_SHA256 = "3c283a21204043db65d97b43a5278b75bcbca6929789ed61eeca4b1ff097d307"
G2_MIN, G2_MAX = 0.01, 0.5
N_EXC_MIN, N_EXC_MAX = 1.0, 5000.0


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def parse_result_markdown() -> dict[str, float]:
    path = ROOT / "result.md"
    assert path.is_file(), "Missing /root/result.md"
    text = path.read_text()
    values: dict[str, float] = {}
    for key in EXPECTED_KEYS:
        match = re.search(
            rf"(?mi)^\s*{re.escape(key)}\s*:\s*"
            rf"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)",
            text,
        )
        assert match, f"Missing numeric line for {key} in /root/result.md"
        values[key] = float(match.group(1))
        assert math.isfinite(values[key]), f"{key} is not finite"
    return values


def read_profile(path: Path, duration_us: float) -> tuple[np.ndarray, np.ndarray]:
    assert path.is_file(), f"Missing {path}"
    with path.open(newline="") as source:
        rows = list(csv.reader(source))
    assert len(rows) == SAMPLES + 1, (
        f"{path.name} must contain a header plus {SAMPLES:,} samples; found {len(rows)} rows"
    )
    assert len(rows[0]) >= 2, f"{path.name} header must contain two columns"
    try:
        values = np.asarray([[float(r[0]), float(r[1])] for r in rows[1:]], dtype=float)
    except (ValueError, IndexError) as error:
        raise AssertionError(f"{path.name} contains non-numeric samples") from error
    assert np.isfinite(values).all(), f"{path.name} contains non-finite values"

    time_us = values[:, 0]
    np.testing.assert_allclose(
        time_us,
        np.linspace(0.0, duration_us, SAMPLES),
        rtol=0.0,
        atol=1e-3,
        err_msg=f"{path.name} time column must uniformly span 0 to {duration_us} us inclusive",
    )
    return time_us, values[:, 1]


def align_direction(position_um: np.ndarray, expected_final_um: float) -> np.ndarray:
    """Normalize start to zero and direction to positive; conventions are free."""
    sign = 1.0 if position_um[-1] >= position_um[0] else -1.0
    aligned = sign * (position_um - position_um[0])
    assert math.isclose(aligned[-1], expected_final_um, rel_tol=1e-2, abs_tol=0.3), (
        f"Final displacement is {aligned[-1]:.6f} um, expected {expected_final_um:.6f} um"
    )
    return aligned


def lowpass_filtered(time_us: np.ndarray, control_um: np.ndarray) -> np.ndarray:
    """Exact one-pole low-pass response to the piecewise-linear control samples,
    with the output starting settled at the first sample (task.md hardware)."""
    tau = FILTER_TAU_US
    filtered = np.empty_like(control_um)
    filtered[0] = control_um[0]
    for i in range(len(time_us) - 1):
        step = time_us[i + 1] - time_us[i]
        slope = (control_um[i + 1] - control_um[i]) / step
        decay = math.exp(-step / tau)
        filtered[i + 1] = (
            control_um[i + 1]
            - slope * tau
            + (filtered[i] - control_um[i] + slope * tau) * decay
        )
    return filtered


def residual_quanta_after_transport(
    time_us: np.ndarray,
    trap_center_um: np.ndarray,
    axial_freq_mhz: float,
    checkpoint_times_us: list[float],
    n_ions: int = 1,
) -> list[float]:
    """Simulate q'' = -w^2 (q - q0(t)) from rest and return the motional energy,
    in quanta of the axial mode, at each checkpoint time.

    This is the outcome the physics requires — a transport waveform is correct
    iff the ion arrives (and dwells) cold — so any valid inverse-engineered or
    optimal-control construction passes, and nothing else does.
    """
    omega_per_us = 2.0 * math.pi * axial_freq_mhz  # rad / us
    grid_dt = (time_us[-1] - time_us[0]) / (len(time_us) - 1)
    dt = grid_dt / 4.0
    n_steps = (len(time_us) - 1) * 4
    # Trap center on the half-step grid the RK4 stages sample.
    fine_t = time_us[0] + np.arange(2 * n_steps + 1) * (dt / 2.0)
    fine_q0 = np.interp(fine_t, time_us, trap_center_um)

    checkpoint_steps = {
        max(0, min(n_steps, int(round((t - time_us[0]) / dt)))): t for t in checkpoint_times_us
    }
    energies: dict[float, float] = {}

    q = float(fine_q0[0])
    v = 0.0  # um / us

    def record(step: int) -> None:
        if step in checkpoint_steps:
            q0_here = float(fine_q0[2 * step])
            # J: um/us == m/s for velocity; um -> m for displacement.
            kinetic = 0.5 * ION_MASS_KG * (v * 1.0) ** 2
            potential = 0.5 * ION_MASS_KG * (omega_per_us * 1e6) ** 2 * ((q - q0_here) * 1e-6) ** 2
            energies[checkpoint_steps[step]] = (kinetic + potential) / (
                HBAR * omega_per_us * 1e6
            )

    record(0)
    for step in range(n_steps):
        base = 2 * step

        def acc(offset: int, qq: float) -> float:
            return -(omega_per_us**2) * (qq - float(fine_q0[base + offset]))

        k1q, k1v = v, acc(0, q)
        k2q, k2v = v + 0.5 * dt * k1v, acc(1, q + 0.5 * dt * k1q)
        k3q, k3v = v + 0.5 * dt * k2v, acc(1, q + 0.5 * dt * k2q)
        k4q, k4v = v + dt * k3v, acc(2, q + dt * k3q)
        q += dt / 6.0 * (k1q + 2.0 * k2q + 2.0 * k3q + k4q)
        v += dt / 6.0 * (k1v + 2.0 * k2v + 2.0 * k3v + k4v)
        record(step + 1)

    # The chain's center-of-mass mode carries effective mass n_ions * m, so
    # its quantum occupation for the same trajectory scales linearly with N.
    return [energies[t] * n_ions for t in checkpoint_times_us]


# --------------------------------------------------------------------------
# input integrity
# --------------------------------------------------------------------------
def test_input_stl_untampered():
    digest = hashlib.sha256()
    with (ROOT / "surface_trap.stl").open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    assert digest.hexdigest() == STL_SHA256, (
        "/root/surface_trap.stl does not match its provenance hash — the input model was modified"
    )


# --------------------------------------------------------------------------
# report structure (quality is scored by the rubric review, not here)
# --------------------------------------------------------------------------
def test_report_pdf_has_reviewable_structure():
    from pypdf import PdfReader

    path = ROOT / "paper.pdf"
    assert path.is_file(), "Missing /root/paper.pdf"
    reader = PdfReader(str(path))
    assert len(reader.pages) >= 2, f"paper.pdf has {len(reader.pages)} pages; a paper draft needs at least 2"

    page_text = [(page.extract_text() or "") for page in reader.pages]
    text = "\n\n".join(page_text)
    compact = " ".join(text.lower().split())
    assert len(compact) >= 1500, "paper.pdf contains too little extractable text to review"
    for page_number, extracted in enumerate(page_text, start=1):
        assert len(" ".join(extracted.split())) >= 80, (
            f"paper.pdf page {page_number} is effectively blank or not extractable"
        )

    # The prompt's required components: abstract; introduction; methods;
    # results; discussion; references.
    for section in ["abstract", "introduction", "method", "result", "discussion", "reference"]:
        assert section in compact, f"paper.pdf is missing the '{section}' component"

    identifiers = set(re.findall(r"\b\d{4}\.\d{4,5}\b", text))
    identifiers |= set(re.findall(r"\b[a-z-]+(?:\.[A-Z]{2})?/\d{7}\b", text))
    identifiers |= set(re.findall(r"\b10\.\d{4,9}/[^\s\)\];,]+", text))
    assert len(identifiers) >= 4, (
        f"paper.pdf cites {len(identifiers)} arXiv/DOI identifiers; a reviewable report needs at least 4"
    )

    # Leave the extracted text next to the preserved PDF so the detached
    # rubric review and human referees can quote the manuscript directly.
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "report_text.txt").write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------
# frequencies
# --------------------------------------------------------------------------
def test_radial_frequency_matches_frozen_bem_reference():
    values = parse_result_markdown()
    assert math.isclose(
        values["W_radial_freq"],
        RADIAL_REFERENCE_MHZ,
        rel_tol=RADIAL_REL_TOL,
        abs_tol=RADIAL_ABS_TOL_MHZ,
    ), (
        f"W_radial_freq={values['W_radial_freq']:.6f} MHz; provenance-pinned BEM reference "
        f"is {RADIAL_REFERENCE_MHZ:.6f} MHz (tolerance covers legitimate mesh/method variation)"
    )


def test_axial_frequency_follows_alpha():
    values = parse_result_markdown()
    expected = values["W_radial_freq"] * math.sqrt(ALPHA)
    assert math.isclose(values["W_axial_freq"], expected, rel_tol=2e-2, abs_tol=1e-3), (
        f"W_axial_freq={values['W_axial_freq']:.6f} MHz does not satisfy "
        f"alpha={ALPHA} with the reported radial frequency"
    )


# --------------------------------------------------------------------------
# chain statics — verified through the physics, not through a shared solver
# --------------------------------------------------------------------------
def test_spacings_satisfy_coulomb_equilibrium():
    values = parse_result_markdown()
    spacings = np.array([values[f"d{i}"] for i in range(1, 9)])
    assert (spacings > 0).all(), "All ion-ion spacings must be positive"

    np.testing.assert_allclose(
        spacings,
        spacings[::-1],
        rtol=1e-2,
        atol=0.05,
        err_msg="Nine-ion spacings must be mirror-symmetric",
    )
    assert spacings[0] >= spacings[3] > 0, "Spacings must shrink toward the chain center"

    omega = 2.0 * math.pi * values["W_axial_freq"] * 1e6
    positions_m = np.concatenate([[0.0], np.cumsum(spacings)]) * 1e-6
    positions_m -= positions_m.mean()
    residuals = np.empty(positions_m.size)
    for i, x in enumerate(positions_m):
        coulomb = sum(
            COULOMB_CONSTANT * ELEMENTARY_CHARGE_C**2 * math.copysign(1.0, x - other) / (x - other) ** 2
            for j, other in enumerate(positions_m)
            if j != i
        )
        residuals[i] = -ION_MASS_KG * omega**2 * x + coulomb
    length_scale = (COULOMB_CONSTANT * ELEMENTARY_CHARGE_C**2 / (ION_MASS_KG * omega**2)) ** (1.0 / 3.0)
    normalized = np.max(np.abs(residuals)) / (ION_MASS_KG * omega**2 * length_scale)
    assert normalized < FORCE_RESIDUAL_MAX, (
        f"Reported spacings violate Coulomb/harmonic force balance "
        f"(normalized residual {normalized:.3g} > {FORCE_RESIDUAL_MAX}); "
        "they are not the equilibrium configuration at the reported axial frequency"
    )


# --------------------------------------------------------------------------
# transport waveforms — outcome-based dynamics gate
# --------------------------------------------------------------------------
def test_single_ion_transport_arrives_cold():
    values = parse_result_markdown()
    time_us, position_um = read_profile(ROOT / "1.csv", SINGLE_DURATION_US)
    aligned = align_direction(position_um, SINGLE_DISTANCE_UM)
    (residual,) = residual_quanta_after_transport(
        time_us, aligned, values["W_axial_freq"], [SINGLE_DURATION_US]
    )
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "single_residual_quanta.json").write_text(json.dumps({"quanta": residual}) + "\n")
    assert residual < RESIDUAL_QUANTA_MAX, (
        f"An ion transported by 1.csv arrives with {residual:.3g} motional quanta "
        f"(limit {RESIDUAL_QUANTA_MAX}); the waveform is not a valid low-excitation transport"
    )


def test_chain_transport_addresses_every_ion_cold():
    values = parse_result_markdown()
    spacings = np.array([values[f"d{i}"] for i in range(1, 9)])
    offsets = np.concatenate([[0.0], np.cumsum(spacings)])

    time_us, position_um = read_profile(ROOT / "2.csv", CHAIN_DURATION_US)
    aligned = align_direction(position_um, float(spacings.sum()))

    # The trap must hold still at the right position during every dwell.
    for stage in range(STAGES):
        dwell_start = stage * (MOVE_US + DWELL_US) + MOVE_US
        window = (time_us > dwell_start + 0.15) & (time_us < dwell_start + DWELL_US - 0.05)
        assert window.any(), f"No samples inside dwell {stage + 1}"
        dwell_positions = aligned[window]
        assert float(np.std(dwell_positions)) < DWELL_FLATNESS_UM, (
            f"Trap center moves during dwell {stage + 1} (std {np.std(dwell_positions):.3g} um)"
        )
        assert math.isclose(
            float(np.mean(dwell_positions)), float(offsets[stage + 1]), rel_tol=1e-2, abs_tol=0.3
        ), (
            f"Dwell {stage + 1} sits at {np.mean(dwell_positions):.3f} um, "
            f"expected cumulative spacing {offsets[stage + 1]:.3f} um"
        )

    # The chain center-of-mass mode must be cold at the end of every dwell,
    # otherwise that ion is not addressed cold. For rigid translation of
    # identical ions only the center-of-mass mode is driven, at the axial
    # frequency, so a single-particle simulation is exact.
    checkpoints = [
        stage * (MOVE_US + DWELL_US) + MOVE_US + DWELL_US - 0.05 for stage in range(STAGES)
    ]
    residuals = residual_quanta_after_transport(
        time_us, aligned, values["W_axial_freq"], checkpoints, n_ions=9
    )
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "chain_residual_quanta.json").write_text(
        json.dumps({f"dwell_{i + 1}": r for i, r in enumerate(residuals)}, indent=2) + "\n"
    )
    for stage, residual in enumerate(residuals):
        assert residual < RESIDUAL_QUANTA_MAX, (
            f"Ion addressed at dwell {stage + 1} carries {residual:.3g} motional quanta "
            f"(limit {RESIDUAL_QUANTA_MAX}); the chain is not addressed cold"
        )


# --------------------------------------------------------------------------
# network-rate budget
# --------------------------------------------------------------------------
def test_attempt_rate_matches_herald_round_trip():
    values = parse_result_markdown()
    assert math.isclose(values["attempt_rate_hz"], EXPECTED_ATTEMPT_RATE_HZ, rel_tol=1e-2), (
        f"attempt_rate_hz={values['attempt_rate_hz']:.3f}; one attempt waits for 100 km of "
        f"fiber path at 2.0e8 m/s, so the ceiling is {EXPECTED_ATTEMPT_RATE_HZ:.1f} Hz"
    )


# --------------------------------------------------------------------------
# hardware filter — predict, scan, and defeat it
# --------------------------------------------------------------------------
def test_filtered_sequence_excitation_predicted_correctly():
    values = parse_result_markdown()
    spacings = np.array([values[f"d{i}"] for i in range(1, 9)])
    time_us, position_um = read_profile(ROOT / "2.csv", CHAIN_DURATION_US)
    aligned = align_direction(position_um, float(spacings.sum()))
    filtered = lowpass_filtered(time_us, aligned)
    (computed,) = residual_quanta_after_transport(
        time_us, filtered, values["W_axial_freq"], [CHAIN_DURATION_US], n_ions=9
    )
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "filtered_residual_quanta.json").write_text(
        json.dumps({"reported": values["n_com_filtered"], "recomputed": computed}) + "\n"
    )
    assert math.isclose(values["n_com_filtered"], computed, rel_tol=0.05, abs_tol=0.1), (
        f"n_com_filtered={values['n_com_filtered']:.3f} quanta, but simulating the submitted "
        f"2.csv through the declared 100 kHz filter gives {computed:.3f} quanta"
    )


def test_duration_scan_shows_the_speed_tradeoff():
    values = parse_result_markdown()
    path = ROOT / "3.csv"
    assert path.is_file(), "Missing /root/3.csv"
    with path.open(newline="") as source:
        rows = list(csv.reader(source))
    assert len(rows) == len(SCAN_DURATIONS_US) + 1, (
        f"3.csv must contain a header plus {len(SCAN_DURATIONS_US)} rows; found {len(rows)}"
    )
    try:
        data = np.asarray([[float(r[0]), float(r[1])] for r in rows[1:]], dtype=float)
    except (ValueError, IndexError) as error:
        raise AssertionError("3.csv contains non-numeric samples") from error
    np.testing.assert_allclose(
        data[:, 0],
        np.asarray(SCAN_DURATIONS_US, dtype=float),
        rtol=0.0,
        atol=1e-6,
        err_msg="3.csv first column must be the move durations 2, 3, ..., 20 us",
    )
    quanta = data[:, 1]
    assert np.isfinite(quanta).all() and (quanta > 0).all(), (
        "3.csv excitation values must be positive and finite"
    )
    row_10 = float(quanta[SCAN_DURATIONS_US.index(10)])
    assert math.isclose(row_10, values["n_com_filtered"], rel_tol=0.05, abs_tol=0.1), (
        f"3.csv at 10 us reports {row_10:.3f} quanta but n_com_filtered is "
        f"{values['n_com_filtered']:.3f}; the scan must contain the 2.csv design at T=10"
    )
    fast = float(np.mean(quanta[:4]))  # 2-5 us
    slow = float(np.mean(quanta[-6:]))  # 15-20 us
    assert fast > 3.0 * slow, (
        f"Faster transport through the fixed filter must cost more excitation: "
        f"mean(2-5 us)={fast:.3f} is not well above mean(15-20 us)={slow:.3f}"
    )


def test_compensated_control_defeats_filter():
    values = parse_result_markdown()
    spacings = np.array([values[f"d{i}"] for i in range(1, 9)])
    offsets = np.concatenate([[0.0], np.cumsum(spacings)])
    time_us, control_um = read_profile(ROOT / "4.csv", CHAIN_DURATION_US)
    aligned = align_direction(control_um, float(spacings.sum()))
    filtered = lowpass_filtered(time_us, aligned)

    # The *filtered* trap must sit at the addressing beam during every dwell.
    for stage in range(STAGES):
        dwell_start = stage * (MOVE_US + DWELL_US) + MOVE_US
        window = (time_us > dwell_start + 0.15) & (time_us < dwell_start + DWELL_US - 0.05)
        assert math.isclose(
            float(np.mean(filtered[window])), float(offsets[stage + 1]), rel_tol=1e-2, abs_tol=0.3
        ), (
            f"After the filter, dwell {stage + 1} of the compensated control sits at "
            f"{np.mean(filtered[window]):.3f} um, expected {offsets[stage + 1]:.3f} um"
        )

    checkpoints = [
        stage * (MOVE_US + DWELL_US) + MOVE_US + DWELL_US - 0.05 for stage in range(STAGES)
    ]
    residuals = residual_quanta_after_transport(
        time_us, filtered, values["W_axial_freq"], checkpoints, n_ions=9
    )
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "compensated_residual_quanta.json").write_text(
        json.dumps({f"dwell_{i + 1}": r for i, r in enumerate(residuals)}, indent=2) + "\n"
    )
    for stage, residual in enumerate(residuals):
        assert residual < RESIDUAL_QUANTA_MAX, (
            f"Through the filter, the compensated control leaves {residual:.3g} quanta at "
            f"dwell {stage + 1} (limit {RESIDUAL_QUANTA_MAX}); the hardware waveform does not "
            "deliver cold addressed ions"
        )


# --------------------------------------------------------------------------
# measured data: photon statistics and motional excitation
# --------------------------------------------------------------------------
def test_photon_and_motional_measurements():
    values = parse_result_markdown()

    data_dir = ROOT / "g2_data"
    assert data_dir.is_dir(), "Missing /root/g2_data"
    digest = hashlib.sha256()
    for entry in sorted(data_dir.iterdir()):
        digest.update(entry.name.encode())
        digest.update(entry.read_bytes())
    assert digest.hexdigest() == G2_BUNDLE_SHA256, (
        "/root/g2_data does not match its provenance hash; the measured data was modified"
    )

    # Independent reference: sum the background-subtracted per-ion histograms,
    # locate the multiplexing peaks, and scan matched windows for the minimum
    # zero-delay to side-peak ratio. Logged for the audit trail.
    index_us = np.load(data_dir / "1_index_left_ion_data.npy")
    summed = np.zeros_like(index_us)
    for ion in range(1, 10):
        left = np.load(data_dir / f"{ion}_final_result_left_ion_data.npy")
        right = np.load(data_dir / f"{ion}_final_result_right_ion_data.npy")
        center = np.load(data_dir / f"{ion}_final_result_center_ion_data.npy")
        summed = summed + left + right - center
    bin_us = float(index_us[1] - index_us[0])
    smooth = np.convolve(summed, np.ones(max(1, int(round(1.7 / bin_us)))), mode="same")
    peaks: list[float] = []
    for j in np.argsort(smooth)[::-1]:
        tau = float(index_us[j])
        if abs(tau) < 5.0:
            continue
        if all(abs(tau - p) > 5.0 for p in peaks):
            peaks.append(tau)
        if len(peaks) >= 16:
            break
    reference_scan = {}
    for bins in range(2, 18):
        width = bins * bin_us
        zero = float(summed[np.abs(index_us) <= width / 2].sum())
        side = float(np.mean([summed[np.abs(index_us - p) <= width / 2].sum() for p in peaks]))
        if side > 0:
            reference_scan[round(width, 1)] = zero / side
    reference_min = min(reference_scan.values())
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "g2_reference.json").write_text(
        json.dumps({"reported": values["g2(0)"], "reference_scan_min": reference_min,
                    "scan": reference_scan}, indent=2) + "\n"
    )

    assert G2_MIN <= values["g2(0)"] <= G2_MAX, (
        f"g2(0)={values['g2(0)']:.4f} is outside the plausible band for this dataset "
        f"[{G2_MIN}, {G2_MAX}]; the matched-window reference minimum is {reference_min:.3f} "
        "and only background corrections justifiably go below it"
    )
    assert N_EXC_MIN <= values["n_excitation"] <= N_EXC_MAX, (
        f"n_excitation={values['n_excitation']:.3f} quanta is outside the physical range "
        f"[{N_EXC_MIN}, {N_EXC_MAX}] for post-transport motional excitation in this system"
    )
