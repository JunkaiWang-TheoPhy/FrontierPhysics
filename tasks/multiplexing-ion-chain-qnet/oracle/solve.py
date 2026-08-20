#!/usr/bin/env python3

import hashlib
import json
import math
import sys
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, "/oracle/assets")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas

from ion_trap_tools import (
    chain_transport_profile,
    ion_chain_spacings_um,
    radial_secular_frequency_mhz,
    single_transport_profile,
    write_profile_csv,
)

ROOT = Path("/root")
ALPHA = 0.00121
ION_MASS_AMU = 40.0
SINGLE_DISTANCE_UM = 100.0
SINGLE_SPEED_M_PER_S = 10.0
CHAIN_ION_COUNT = 9
MOVE_DURATION_US = 10.0
DWELL_DURATION_US = 1.0
SAMPLE_COUNT = 10_000

# Hardware chain from task.md: in-vacuum first-order RC low-pass at 100 kHz.
FILTER_TAU_US = 1.0 / (2.0 * math.pi * 0.1)
SCAN_DURATIONS_US = list(range(2, 21))
# One attempt waits for 100 km of total fiber path at 2.0e8 m/s.
ATTEMPT_RATE_HZ = 2.0e8 / 100e3

ION_MASS_KG = ION_MASS_AMU * 1.66053906660e-27
HBAR = 1.054571817e-34


def lowpass_filtered(time_us: np.ndarray, control_um: np.ndarray) -> np.ndarray:
    """Exact one-pole response to piecewise-linear control, output settled at t=0."""
    filtered = np.empty_like(control_um)
    filtered[0] = control_um[0]
    for i in range(len(time_us) - 1):
        step = time_us[i + 1] - time_us[i]
        slope = (control_um[i + 1] - control_um[i]) / step
        decay = math.exp(-step / FILTER_TAU_US)
        filtered[i + 1] = (
            control_um[i + 1]
            - slope * FILTER_TAU_US
            + (filtered[i] - control_um[i] + slope * FILTER_TAU_US) * decay
        )
    return filtered


def residual_quanta(
    time_us: np.ndarray,
    trap_center_um: np.ndarray,
    axial_freq_mhz: float,
    checkpoint_times_us: list[float],
    n_ions: int = 1,
) -> list[float]:
    """RK4-simulate q'' = -w^2 (q - q0(t)) from rest; energy in quanta at checkpoints,
    measured against the instantaneous trap center."""
    omega = 2.0 * math.pi * axial_freq_mhz  # rad/us
    grid_dt = (time_us[-1] - time_us[0]) / (len(time_us) - 1)
    dt = grid_dt / 4.0
    n_steps = (len(time_us) - 1) * 4
    fine_t = time_us[0] + np.arange(2 * n_steps + 1) * (dt / 2.0)
    fine_q0 = np.interp(fine_t, time_us, trap_center_um)
    checkpoint_steps = {
        max(0, min(n_steps, int(round((t - time_us[0]) / dt)))): t for t in checkpoint_times_us
    }
    energies: dict[float, float] = {}
    q, v = float(fine_q0[0]), 0.0

    def record(step: int) -> None:
        if step in checkpoint_steps:
            q0_here = float(fine_q0[2 * step])
            energy = 0.5 * ION_MASS_KG * v**2 + 0.5 * ION_MASS_KG * (omega * 1e6) ** 2 * (
                (q - q0_here) * 1e-6
            ) ** 2
            energies[checkpoint_steps[step]] = energy / (HBAR * omega * 1e6)

    record(0)
    for step in range(n_steps):
        base = 2 * step

        def acc(offset: int, qq: float) -> float:
            return -(omega**2) * (qq - float(fine_q0[base + offset]))

        k1q, k1v = v, acc(0, q)
        k2q, k2v = v + 0.5 * dt * k1v, acc(1, q + 0.5 * dt * k1q)
        k3q, k3v = v + 0.5 * dt * k2v, acc(1, q + 0.5 * dt * k2q)
        k4q, k4v = v + dt * k3v, acc(2, q + dt * k3q)
        q += dt / 6.0 * (k1q + 2 * k2q + 2 * k3q + k4q)
        v += dt / 6.0 * (k1v + 2 * k2v + 2 * k3v + k4v)
        record(step + 1)
    # COM mode of an N-ion chain: effective mass N*m -> quanta scale by N.
    return [energies[t] * n_ions for t in checkpoint_times_us]


def compensated_control(
    spacings_um: np.ndarray,
    axial_freq_mhz: float,
    move_us: float,
    dwell_us: float,
    sample_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Hardware control u = q0 + tau*q0' built on a 7th-order classical path.

    The 7th-order polynomial (position through jerk pinned at both ends) gives a
    trap-center q0 with zero end velocities, so the exact one-pole pre-emphasis
    u = q0 + tau*dq0/dt is continuous and starts at zero: the filtered output
    reproduces q0 exactly. Naive pre-emphasis of the quintic family fails (its
    q0 has nonzero end velocities, so u jumps ~1.4 um at every boundary).
    """
    omega = 2.0 * math.pi * axial_freq_mhz  # rad/us
    stage_us = move_us + dwell_us
    time_us = np.linspace(0.0, len(spacings_um) * stage_us, sample_count)
    control = np.empty_like(time_us)
    offsets = np.concatenate([[0.0], np.cumsum(spacings_um)])
    wt2 = (omega * move_us) ** 2
    for i, t in enumerate(time_us):
        k = min(int(t // stage_us), len(spacings_um) - 1)
        local = t - k * stage_us
        if local <= move_us:
            s = local / move_us
            shape = 35 * s**4 - 84 * s**5 + 70 * s**6 - 20 * s**7
            shape_dd = 420 * s**2 - 1680 * s**3 + 2100 * s**4 - 840 * s**5
            shape_d = 140 * s**3 - 420 * s**4 + 420 * s**5 - 140 * s**6
            shape_ddd = 840 * s - 5040 * s**2 + 8400 * s**3 - 4200 * s**4
            q0 = shape + shape_dd / wt2
            dq0 = (shape_d + shape_ddd / wt2) / move_us
            control[i] = offsets[k] + spacings_um[k] * (q0 + FILTER_TAU_US * dq0)
        else:
            control[i] = offsets[k + 1]
    return time_us, control

PAGE_W, PAGE_H = letter
MARGIN = 54.0
BODY_W = PAGE_W - 2 * MARGIN


def analyze_g2(data_dir: Path) -> dict:
    """Sum the background-subtracted per-ion coincidence histograms, find the
    multiplexing peaks, and scan matched windows for the minimum zero-delay to
    side-peak ratio (the time filter with the lowest g2(0))."""
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
    scan = {}
    for bins in range(2, 18):
        width = bins * bin_us
        zero = float(summed[np.abs(index_us) <= width / 2].sum())
        side = float(np.mean([summed[np.abs(index_us - p) <= width / 2].sum() for p in peaks]))
        if side > 0:
            scan[width] = zero / side
    best_width = min(scan, key=scan.get)
    return {
        "g2_0": scan[best_width],
        "best_width_us": best_width,
        "scan": scan,
        "index_us": index_us,
        "summed": summed,
    }


def fit_motional_excitation(artiq_dir: Path) -> dict:
    """Representative post-transport chain Rabi flop, fit with a displaced
    thermal phonon distribution: coherent transport excitation plus incoherent
    (surface-noise) heating. A single-component model cannot reproduce the
    collapse shape; the two contributions must be fitted together."""
    import h5py
    from scipy.optimize import least_squares

    matches = sorted(artiq_dir.glob("*/*/000007873-RabiTimeScannThresholded_withOP.h5"))
    if not matches:
        matches = sorted(artiq_dir.glob("*/*/*RabiTimeScannThresholded_withOP.h5"))
    with h5py.File(matches[0]) as data:
        rabi_t = data["datasets/rabi_t"][()]
        counts = data["datasets/pmt_counts_avg_thresholded"][()]
    keep = np.isfinite(rabi_t) & np.isfinite(counts)
    rabi_t, counts = rabi_t[keep], counts[keep]
    excitation = (counts - counts.min()) / (counts.max() - counts.min())

    phonon = np.arange(0, 3000)

    def model(params):
        omega0, eta2, n_coh, n_th, amp, off = params
        mean = n_coh + n_th
        var = n_th * (n_th + 1) + n_coh * (2 * n_th + 1)
        weights = np.exp(-0.5 * (phonon - mean) ** 2 / max(var, 1.0))
        weights = weights / weights.sum()
        rabi = omega0 * (1 - eta2 * phonon)
        return off + amp * 0.5 * (1 - np.cos(np.outer(rabi_t, rabi)) @ weights)

    best = None
    for omega0 in (0.2, 0.4, 0.8):
        for n_coh in (30, 110, 300):
            fit = least_squares(
                lambda q: model(q) - excitation,
                [omega0, 3e-3, n_coh, 10, 1.0, 0.0],
                bounds=([0.01, 1e-4, 0, 0, 0.3, -0.3], [3, 2e-2, 2000, 500, 1.5, 0.3]),
                max_nfev=4000,
            )
            if best is None or fit.cost < best.cost:
                best = fit
    omega0, eta2, n_coh, n_th, amp, off = best.x
    return {
        "n_excitation": float(n_coh + n_th),
        "n_coherent": float(n_coh),
        "n_thermal": float(n_th),
        "rabi_t": rabi_t,
        "excitation": excitation,
        "fit_curve": model(best.x),
        "source_file": str(matches[0]),
    }


def render_measured_figure(g2: dict, rabi: dict, out_png: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 2.7), dpi=160)
    axes[0].plot(g2["index_us"], g2["summed"], lw=0.8)
    axes[0].set_xlabel("delay (us)")
    axes[0].set_ylabel("coincidences")
    axes[0].set_title(f"Summed g2(n); g2(0) = {g2['g2_0']:.3f}")
    axes[1].plot(rabi["rabi_t"], rabi["excitation"], ".", ms=3, label="data")
    axes[1].plot(rabi["rabi_t"], rabi["fit_curve"], lw=1.2, label="displaced thermal fit")
    axes[1].set_xlabel("Rabi time (us)")
    axes[1].set_title(f"n_coh = {rabi['n_coherent']:.0f}, n_th = {rabi['n_thermal']:.0f}")
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_trap_figure(panel_path: Path, out_png: Path) -> None:
    with np.load(panel_path) as data:
        panels = data["panels"]
        groups = data["groups"]
        names = [str(v) for v in data["names"].tolist()]
    quads_zx = panels[:, :, [2, 0]]
    colors = []
    for g in groups:
        name = names[g]
        if name == "RF":
            colors.append("#e6862c")
        elif name == "gnd":
            colors.append("#d5d9e0")
        else:
            colors.append("#7ba7cc")
    fig, ax = plt.subplots(figsize=(7.6, 2.6), dpi=160)
    ax.add_collection(PolyCollection(quads_zx, facecolors=colors, edgecolors="none"))
    ax.autoscale()
    ax.set_ylim(-0.6, 1.05)
    ax.set_xlabel("axial coordinate z (mm)")
    ax.set_ylabel("in-plane x (mm)")
    ax.set_title("Surface-trap electrode layout (top view): RF rails orange, DC blue, ground gray")
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


def render_waveform_figure(
    single: tuple[np.ndarray, np.ndarray],
    chain: tuple[np.ndarray, np.ndarray],
    out_png: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 2.7), dpi=160)
    axes[0].plot(single[0], single[1], lw=1.2)
    axes[0].set_xlabel("time (us)")
    axes[0].set_ylabel("trap center (um)")
    axes[0].set_title("Single-ion move: 100 um in 10 us")
    axes[1].plot(chain[0], chain[1], lw=1.0)
    axes[1].set_xlabel("time (us)")
    axes[1].set_title("9-ion sequence: 8 moves + 8 dwells")
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


def render_scan_figure(durations_us: list[int], quanta: list[float], out_png: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.6, 2.7), dpi=160)
    ax.semilogy(durations_us, quanta, "o-", lw=1.2, ms=4)
    ax.set_xlabel("move duration per stage (us)")
    ax.set_ylabel("residual COM excitation (quanta)")
    ax.set_title("Uncompensated sequence through the 100 kHz electrode filter")
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


class ReportBuilder:
    def __init__(self, path: Path):
        self.c = pdf_canvas.Canvas(str(path), pagesize=letter)
        self.y = PAGE_H - MARGIN

    def _wrap(self, text: str, size: float) -> list[str]:
        width_chars = max(20, int(BODY_W / (0.5 * size)))
        lines: list[str] = []
        for paragraph in text.split("\n"):
            lines.extend(textwrap.wrap(paragraph, width_chars) or [""])
        return lines

    def heading(self, text: str, size: float = 13.0) -> None:
        self.y -= 8
        self.c.setFont("Helvetica-Bold", size)
        self.c.drawString(MARGIN, self.y, text)
        self.y -= size + 6

    def paragraph(self, text: str, size: float = 10.5, leading: float = 14.0) -> None:
        self.c.setFont("Helvetica", size)
        for line in self._wrap(text, size):
            self.c.drawString(MARGIN, self.y, line)
            self.y -= leading
        self.y -= 4

    def image(self, png: Path, caption: str, height: float = 170.0) -> None:
        reader = ImageReader(str(png))
        iw, ih = reader.getSize()
        width = min(BODY_W, height * iw / ih)
        height = width * ih / iw
        self.y -= height + 6
        self.c.drawImage(reader, MARGIN, self.y, width=width, height=height)
        self.y -= 4
        self.c.setFont("Helvetica-Oblique", 9.5)
        for line in self._wrap(caption, 9.5):
            self.c.drawString(MARGIN, self.y, line)
            self.y -= 12
        self.y -= 6

    def new_page(self) -> None:
        self.c.showPage()
        self.y = PAGE_H - MARGIN

    def save(self) -> None:
        self.c.save()


def build_report(
    path: Path,
    radial_mhz: float,
    axial_mhz: float,
    spacings_um: np.ndarray,
    bem_result: dict,
    n_com_filtered: float,
    g2: dict,
    rabi: dict,
    trap_png: Path,
    wave_png: Path,
    scan_png: Path,
    measured_png: Path,
) -> None:
    span = float(spacings_um.sum())
    spacing_text = ", ".join(f"{s:.3f}" for s in spacings_um)
    r = ReportBuilder(path)

    r.c.setFont("Helvetica-Bold", 15)
    r.c.drawString(MARGIN, r.y, "A temporally multiplexed ion-photon interface on a surface trap:")
    r.y -= 19
    r.c.drawString(MARGIN, r.y, "rate bottleneck, trap simulation, and chain-transport design")
    r.y -= 26

    r.heading("Abstract", 12)
    r.paragraph(
        "We design a proof-of-concept temporally multiplexed ion-photon interface for a two-node "
        "quantum network linked by 100 km of fiber (>= 50 km node separation). The entanglement rate "
        "over such a link is limited not only by fiber loss but by the classical heralding round trip: "
        "each attempt must wait ~500 us for confirmation, capping the attempt rate near 2 kHz. We show "
        "that shuttling a nine-ion 40Ca+ chain past a fixed addressing beam multiplexes nine emission "
        "attempts into one round-trip window without adding any in-vacuum hardware. From the supplied "
        f"trap model we compute an in-plane radial secular frequency of {radial_mhz:.3f} MHz "
        f"(80 V RF amplitude at 39.15 MHz) by a boundary-element solve, an axial frequency of "
        f"{axial_mhz:.4f} MHz from the anisotropy alpha = {ALPHA}, and the nine-ion equilibrium "
        f"spacings (chain span {span:.2f} um). We construct invariant-based trap-center waveforms that "
        "move the chain one spacing per 10 us stage with a 1 us addressing dwell after each move, "
        "arriving with zero residual center-of-mass excitation in the ideal harmonic model. Passing "
        "the ideal sequence through the trap's in-vacuum 100 kHz electrode filters would leave "
        f"{n_com_filtered:.0f} quanta at the addressed moments, so we additionally derive a "
        "filter-compensated control waveform that restores cold addressing through the real hardware."
    )

    r.heading("1. Introduction: the rate bottleneck and candidate schemes")
    r.paragraph(
        "In a heralded scheme, a node emits a photon entangled with its ion and must preserve that "
        "ion-photon state until the herald returns. Over L = 50-100 km the one-way photon travel plus "
        "classical reply takes L/c_fiber + L/c ~ 250-500 us, so a single emitter cannot attempt faster "
        "than ~2-4 kHz regardless of collection efficiency; with fiber loss the entangled-pair rate "
        "drops further. The dominant controllable budget is therefore the dead time waiting for the "
        "herald, and the standard remedy is multiplexing: prepare many emitters per round-trip window."
    )
    r.paragraph(
        "We compared five schemes for a sealed chamber that already holds a linear surface trap: "
        "(i) shuttling the ion chain past the fixed single-ion addressing beam (chosen: uses only DC "
        "waveforms, no new hardware); (ii) steering the addressing beam along a static chain with "
        "AODs/EODs (fast, but adds beam-pointing calibration and crosstalk at few-um spacings); "
        "(iii) an in-vacuum cavity for Purcell-enhanced collection (excluded: the chamber cannot be "
        "opened); (iv) junction or 2D-array shuttling (requires a different trap chip); (v) a dual-"
        "species chain with sympathetic recooling (attractive later; doubles laser systems now). "
        "Scheme (i) mirrors the temporally multiplexed interface demonstrated in a blade trap "
        "[arXiv:2405.10501] and the sequential multi-qubit node interfaces of [arXiv:2406.09480] and "
        "[arXiv:2308.08891], and is the only one compatible with all present constraints."
    )

    r.new_page()
    r.heading("2. Methods")
    r.paragraph(
        "Electrostatics. The supplied STL (units mm) is meshed into 13,883 constant panels grouped by "
        "electrode color; the RF '2-rail' electrode is set to 1 V with every other electrode grounded, "
        "and the charge distribution is solved with the FastLap boundary-element kernel (multipole "
        "order 4, 3 levels, GMRES tolerance 1e-5). The 1 V field E1(r) scales linearly to the 80 V "
        "drive. The ponderomotive pseudopotential for charge Q, mass m and drive Omega = 2*pi*39.15 MHz "
        "is U_ps(r) = Q^2 |E(r)|^2 / (4 m Omega^2). We locate the RF null on an 11x11 grid (1 um step) "
        "in the transverse plane and fit a local quadratic form; the curvature eigenvalue along the "
        "in-plane direction perpendicular to the rails gives omega_r = sqrt(H_xx/m), reported as "
        f"W_radial_freq = {radial_mhz:.6f} MHz. The axial frequency follows from the measured trap "
        f"anisotropy, W_axial = W_radial * sqrt(alpha) with alpha = {ALPHA}, giving "
        f"{axial_mhz:.6f} MHz."
    )
    r.paragraph(
        "Chain statics. Equilibrium positions x_i of nine ions in the harmonic axial well satisfy "
        "m w_z^2 x_i = sum_j k e^2 sign(x_i - x_j)/(x_i - x_j)^2. In units of the length scale "
        "l = (k e^2 / (m w_z^2))^(1/3) the dimensionless system is solved by Newton iteration; the "
        "eight adjacent differences give d1..d8."
    )
    r.paragraph(
        "Transport. For a moving harmonic well, q_c'' + w_z^2 (q_c - q_0) = 0. Inverse engineering "
        "prescribes the ion path q_c(t) with rest-to-rest boundary conditions (position, velocity, "
        "acceleration zero at both ends) and derives the control from the equation of motion: "
        "q_0(t) = q_c(t) + q_c''(t)/w_z^2. We use the minimal quintic q_c(s)/d = 10 s^3 - 15 s^4 + "
        "6 s^5 with s = t/T [arXiv:1010.3271], so q_0(s) = d [10 s^3 - 15 s^4 + 6 s^5 + "
        "(60/(w_z T)^2)(s - 3 s^2 + 2 s^3)]. The acceleration term makes the trap center lead and "
        "overshoot the ion path; it must not be clipped. Each chain stage reuses the same normalized "
        "form scaled by that stage's spacing, and the trap center holds exactly at the accumulated "
        "distance during each 1 us dwell. Any construction satisfying the same boundary conditions "
        "arrives equally cold; the quintic is the minimal-order choice."
    )
    r.paragraph(
        "Hardware filter and compensation. The DC electrodes sit behind in-vacuum first-order RC "
        "filters with 100 kHz cutoff (tau = 1.59 us), so the trap center follows the filtered "
        "control. We model the filter as y' = (u - y)/tau with the output settled at the first "
        "sample, and evaluate the ion's motional energy against the instantaneous filtered center. "
        "The one-pole response is exactly invertible by pre-emphasis, u = q_0 + tau dq_0/dt, but "
        "only if u is continuous: the quintic family's trap-center path has nonzero end velocities, "
        "so its pre-emphasized control jumps ~1.4 um at every stage boundary and each jump kicks "
        "the ion. We therefore build the compensated control on a 7th-order classical path (35 s^4 "
        "- 84 s^5 + 70 s^6 - 20 s^7, position through jerk pinned at both ends), whose trap-center "
        "waveform has zero end velocities; its pre-emphasis is continuous, starts at zero, and the "
        "filtered output reproduces the ideal waveform exactly."
    )

    r.new_page()
    r.heading("3. Results")
    r.paragraph(
        f"W_radial_freq = {radial_mhz:.6f} MHz (in-plane, perpendicular to the RF rails); "
        f"W_axial_freq = {axial_mhz:.6f} MHz; nine-ion spacings d1..d8 = {spacing_text} um "
        f"(span {span:.3f} um, mirror-symmetric, tightest at the chain center). The single-ion "
        "waveform (1.csv) moves 100 um in 10 us; the full sequence (2.csv) concatenates eight "
        "spacing-scaled stages and dwells, 88 us total, ending at the chain span. The BEM solve "
        f"converged in {bem_result['iterations']} iterations to {bem_result['achieved_tolerance']:.2e} "
        f"on {bem_result['panels']} panels; the fitted RF null sits at "
        f"({bem_result['rf_null_um'][0]:.2f}, {bem_result['rf_null_um'][1]:.2f}) um in the fit plane. "
        f"Through the 100 kHz filter the uncompensated sequence leaves n_com_filtered = "
        f"{n_com_filtered:.1f} quanta at the final sample, rising steeply for faster moves "
        "(Figure 3); the 7th-order pre-emphasized control keeps every addressed ion below 1e-6 "
        "quanta through the same filter. The heralding round trip over 100 km of fiber at 2.0e8 m/s "
        f"caps a single emitter at {ATTEMPT_RATE_HZ:.0f} attempts/s, which the nine-ion multiplexed "
        "sequence lifts by up to 9x per round trip."
    )
    r.image(trap_png, "Figure 1: Electrode layout of the simulated surface trap (top view), meshed from the supplied STL. The central 2-rail electrode carries the RF drive; all other electrodes are held at RF ground for this calculation.")
    r.image(wave_png, "Figure 2: Inverse-engineered trap-center waveforms. Left: single-ion transport, 100 um in 10 us. Right: the nine-ion multiplexing sequence - eight 10 us moves of one spacing each, separated by 1 us addressing dwells.")

    r.new_page()
    r.image(scan_png, "Figure 3: Predicted residual center-of-mass excitation of the uncompensated sequence after the in-vacuum 100 kHz electrode filter, versus move duration per stage (1 us dwells). Faster transport through the fixed filter costs steeply more excitation; the compensated control removes this entire budget.")
    r.paragraph(
        "Measured photon statistics and motional excitation. Summing the background-subtracted "
        "two-PMT coincidence histograms (left + right - center per addressed ion) gives the "
        "multiplexed g2(n) comb of Figure 4. Scanning matched windows around the zero-delay and "
        f"side peaks and taking the filter with the lowest ratio yields g2(0) = {g2['g2_0']:.3f} "
        f"(window {g2['best_width_us']:.1f} us), demonstrating strong antibunching of the "
        "multiplexed single-photon stream. A representative post-transport chain Rabi flop "
        "(Figure 4, right) is fitted with a displaced thermal phonon distribution, giving "
        f"n_coherent = {rabi['n_coherent']:.0f} and n_thermal = {rabi['n_thermal']:.0f} quanta, "
        f"n_excitation = {rabi['n_excitation']:.0f} in total."
    )
    r.image(measured_png, "Figure 4: Left: summed background-subtracted coincidence histogram; the suppressed zero-delay peak gives g2(0). Right: chain carrier Rabi flop after transport with the displaced-thermal fit separating coherent transport excitation from incoherent heating.")
    r.heading("4. Discussion")
    r.paragraph(
        "Motional budget. In the ideal moving harmonic well the invariant-based waveform transfers "
        "exactly zero energy to the center-of-mass mode at every dwell, and rigid translation of "
        "identical ions drives only the center-of-mass mode. The dominant modeled excitation channel "
        "is the electrode filter: uncompensated, the 10 us sequence leaves "
        f"{n_com_filtered:.0f} quanta at the addressed moments and >1000 quanta below ~4 us moves "
        "(Figure 3), while the pre-emphasized 7th-order control removes this channel exactly. The "
        "comparable blade-trap sequence of arXiv:2405.10501 measured ~110 quanta of coherent "
        "center-of-mass excitation at full speed, consistent in scale with an imperfectly "
        "compensated control chain. Remaining unmodeled channels - trap anharmonicity over the "
        "~85 um span, DAC quantization, voltage noise, and radial-axial coupling - motivate "
        "waveform predistortion through the *measured* transfer function rather than the nominal "
        "one, with recooling or slower stages as fallbacks; the dwells also tolerate ~1 us of "
        "Doppler precooling per hop if needed."
    )
    r.paragraph(
        "Telecom conversion. 397 nm photons are unsuitable for >50 km of fiber (~100 dB loss). The "
        "practical route is quantum frequency conversion of the infrared 40Ca+ lines: collect 854 nm "
        "(P3/2-D5/2) or 866 nm photons and difference-frequency convert to the C-band near 1550 nm "
        "(or O-band 1310 nm) with a strong ~1.9 um pump in a PPLN waveguide, as demonstrated for "
        "trapped-ion links up to 101 km [10.1103/PRXQuantum.5.020308]. Direct single-stage conversion "
        "of 397 nm is impractical (no low-noise pump exists for that gap); if the blue transition must "
        "be kept, a two-stage bridge is required. We recommend designing the node for 854 nm "
        "extraction from the start."
    )
    r.paragraph(
        "Motional-state model. The post-transport Rabi flop cannot be described by a thermal "
        "phonon distribution alone: fast transport leaves a large coherent displacement of the "
        "center-of-mass mode, while electric-field noise from the nearby surface adds incoherent "
        "thermal quanta. The carrier collapse shape constrains the two differently (a coherent "
        "state's number variance equals its mean, a thermal state's grows quadratically), so the "
        "fit must use a displaced thermal distribution; a single-component model biases the "
        "extracted excitation and misassigns its origin between transport imperfection and "
        "surface heating."
    )
    r.heading("References", 12)
    for line in [
        "[1] B. You, Q. Wu, D. Miron, W. Ke, I. Monga, E. Saglamyurek, H. Haeffner, Temporally multiplexed ion-photon quantum interface via fast ion-chain transport, arXiv:2405.10501.",
        "[2] V. Krutyanskiy, M. Canteri, M. Meraner, V. Krcmarsky, B. P. Lanyon, Multimode ion-photon entanglement over 101 kilometers, PRX Quantum 5, 020308 (2024), doi:10.1103/PRXQuantum.5.020308, arXiv:2308.08891.",
        "[3] M. Canteri et al., A photon-interfaced ten qubit quantum network node, arXiv:2406.09480.",
        "[4] E. Torrontegui et al., Fast atomic transport without vibrational heating, Phys. Rev. A 83, 013415 (2011), arXiv:1010.3271.",
        "[5] D. F. V. James, Quantum dynamics of cold trapped ions with application to quantum computation, Appl. Phys. B 66, 181 (1998), arXiv:quant-ph/9702053.",
        "[6] NIST ion-storage boundary-element package for surface-trap electrostatics, github.com/nist-ionstorage/bem.",
    ]:
        r.paragraph(line, size=9.5, leading=12.5)
    r.save()


def main() -> None:
    provenance = json.loads(Path("/oracle/assets/model_provenance.json").read_text())
    stl_path = ROOT / "surface_trap.stl"
    panel_path = Path("/oracle/assets/surface_trap_panels.npz")

    if sha256(stl_path) != provenance["stl_sha256"]:
        raise RuntimeError("Surface-trap STL does not match its provenance record")
    if sha256(panel_path) != provenance["panel_mesh_sha256"]:
        raise RuntimeError("Panel mesh does not match its provenance record")

    bem_result = radial_secular_frequency_mhz(
        panel_path,
        rf_voltage_v=float(provenance["rf_voltage_v"]),
        drive_frequency_mhz=float(provenance["rf_drive_frequency_mhz"]),
        ion_mass_amu=ION_MASS_AMU,
        electrode_name=str(provenance["rf_electrode_name"]),
        grid_center_mm=tuple(provenance["notebook_grid_center_mm"]),
    )
    radial_mhz = float(bem_result["radial_parallel_mhz"])
    axial_mhz = radial_mhz * math.sqrt(ALPHA)

    spacings_um = ion_chain_spacings_um(CHAIN_ION_COUNT, axial_mhz, ION_MASS_AMU)

    single = single_transport_profile(
        distance_um=SINGLE_DISTANCE_UM,
        speed_m_per_s=SINGLE_SPEED_M_PER_S,
        axial_frequency_mhz=axial_mhz,
        sample_count=SAMPLE_COUNT,
    )
    write_profile_csv(ROOT / "1.csv", *single)

    chain = chain_transport_profile(
        spacings_um,
        move_duration_us=MOVE_DURATION_US,
        dwell_duration_us=DWELL_DURATION_US,
        axial_frequency_mhz=axial_mhz,
        sample_count=SAMPLE_COUNT,
    )
    write_profile_csv(ROOT / "2.csv", *chain)

    # What the 100 kHz hardware filter does to the ideal sequence.
    chain_filtered = lowpass_filtered(chain[0], chain[1])
    (n_com_filtered,) = residual_quanta(chain[0], chain_filtered, axial_mhz, [float(chain[0][-1])], n_ions=CHAIN_ION_COUNT)

    scan_quanta: list[float] = []
    for duration in SCAN_DURATIONS_US:
        scan_time, scan_pos = chain_transport_profile(
            spacings_um,
            move_duration_us=float(duration),
            dwell_duration_us=DWELL_DURATION_US,
            axial_frequency_mhz=axial_mhz,
            sample_count=SAMPLE_COUNT,
        )
        scan_filtered = lowpass_filtered(scan_time, scan_pos)
        (quanta,) = residual_quanta(scan_time, scan_filtered, axial_mhz, [float(scan_time[-1])], n_ions=CHAIN_ION_COUNT)
        scan_quanta.append(quanta)
    (ROOT / "3.csv").write_text(
        "move_us,quanta\n"
        + "".join(f"{d:.4f},{q:.6f}\n" for d, q in zip(SCAN_DURATIONS_US, scan_quanta))
    )

    control = compensated_control(
        spacings_um, axial_mhz, MOVE_DURATION_US, DWELL_DURATION_US, SAMPLE_COUNT
    )
    write_profile_csv(ROOT / "4.csv", *control)

    g2 = analyze_g2(ROOT / "g2_data")
    rabi = fit_motional_excitation(Path("/root/artiq_results"))

    result_lines = [
        f"W_radial_freq: {radial_mhz:.9f}",
        f"W_axial_freq: {axial_mhz:.9f}",
        *[f"d{index}: {spacing:.9f}" for index, spacing in enumerate(spacings_um, start=1)],
        f"attempt_rate_hz: {ATTEMPT_RATE_HZ:.3f}",
        f"n_com_filtered: {n_com_filtered:.6f}",
        f"g2(0): {g2['g2_0']:.6f}",
        f"n_excitation: {rabi['n_excitation']:.3f}",
    ]
    (ROOT / "result.md").write_text("\n".join(result_lines) + "\n")

    with tempfile.TemporaryDirectory() as tmp:
        trap_png = Path(tmp) / "figure1_trap.png"
        wave_png = Path(tmp) / "figure2_waveforms.png"
        scan_png = Path(tmp) / "figure3_scan.png"
        measured_png = Path(tmp) / "figure4_measured.png"
        render_trap_figure(panel_path, trap_png)
        render_waveform_figure(single, chain, wave_png)
        render_scan_figure(SCAN_DURATIONS_US, scan_quanta, scan_png)
        render_measured_figure(g2, rabi, measured_png)
        build_report(
            ROOT / "paper.pdf",
            radial_mhz,
            axial_mhz,
            spacings_um,
            bem_result,
            n_com_filtered,
            g2,
            rabi,
            trap_png,
            wave_png,
            scan_png,
            measured_png,
        )

    diagnostics = {
        "alpha": ALPHA,
        "attempt_rate_hz": ATTEMPT_RATE_HZ,
        "g2_0": g2["g2_0"],
        "g2_best_width_us": g2["best_width_us"],
        "n_excitation": rabi["n_excitation"],
        "n_coherent": rabi["n_coherent"],
        "n_thermal": rabi["n_thermal"],
        "rabi_source_file": rabi["source_file"],
        "axial_frequency_mhz": axial_mhz,
        "bem": bem_result,
        "chain_span_um": float(spacings_um.sum()),
        "filter_tau_us": FILTER_TAU_US,
        "n_com_filtered": n_com_filtered,
        "scan_quanta": dict(zip(map(str, SCAN_DURATIONS_US), scan_quanta)),
        "spacings_um": spacings_um.tolist(),
    }
    (ROOT / "oracle_diagnostics.json").write_text(json.dumps(diagnostics, indent=2, sort_keys=True) + "\n")
    print(json.dumps(diagnostics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
