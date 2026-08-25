#!/usr/bin/env python3
"""Reference solution: 840 nm laser phase noise -> Rydberg CZ gate infidelity.

Human-authored from the original thesis analysis (phase_noise.py and
gate_infidelity_cutoff_study.py). Every number below is computed from the four
frozen spectrum-analyzer traces in /root/inputs/; nothing is hardcoded.

Pipeline
--------
1. Single-sideband phase noise L(f) and frequency noise S_nu(f) from two
   independent measurements of the same 840 nm laser:
     (a) the 80 MHz beatnote against the cavity transmission,
     (b) the PDH in-loop error signal.
2. Overlay both on shared axes -> phase_noise_PSD.pdf. This figure is a
   diagnostic, not the deliverable: it demonstrates that the figure in the
   reference paper follows from the bundled traces. The paper deliverable
   itself is the author's thesis section, copied by solve.sh (see there).
3. Fidelity Response Theory (Tsai et al., PRX Quantum (2025)) maps
   S_nu(f) onto the CZ gate infidelity as a function of Rabi frequency:

       eps_nu(Omega) = \\int_0^\\infty S_nu(f) * Omega^-2 * g_nu(2 pi f / Omega) df

   The 840 nm light is frequency-doubled to 420 nm before it drives the first
   leg of the Rydberg excitation, so the frequency-noise PSD entering the FRT
   integral is 4x the measured 840 nm PSD.

The bandwidth caveat
--------------------
The PDH trace stops at 8 MHz and the PSD has *not* begun to roll off there, so
the integral's implicit "zero noise above f_max" is an assumption, not a
measurement. Two bracketing scenarios are therefore computed:

  optimistic  (a): S_nu = 0 above 8 MHz          -> lower bound
  pessimistic (b): S_nu stays flat out to 30 MHz -> upper bound

The reported answer uses a flat extension to 15 MHz, which sits inside the
bracket and matches the delivered thesis artifact.

Both bounds, and the widened band the verifier actually applies, are written to
oracle_diagnostics.json. verifier/reference_bounds.json is that file's band
fields verbatim: regenerate it by running this script and copying them across,
so the accepted band always traces to a computation rather than to a constant
someone typed in.
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

INPUTS = "/root/inputs"
# Diagnostic only: paper.pdf itself is the thesis section, delivered by
# solve.sh. Regenerating the figure here proves it follows from the inputs.
OUT_FIG = "/root/phase_noise_PSD.pdf"
OUT_CSV = "/root/gate_infidelity.csv"
OUT_DIAG = "/root/oracle_diagnostics.json"

# ── measurement constants (from the lab notebook / instrument settings) ───────
RBW = 1e3           # Hz, spectrum-analyzer resolution bandwidth
Z0 = 50.0           # ohm, system impedance
FWHM = 68e3         # Hz, ULE cavity linewidth
K0 = 1500e-3 / 34e3 / 2   # V/Hz, PDH error-signal slope at DC
CARRIER_PEAK = -6.54      # dBm, beatnote carrier power
F_BEAT = 80e6       # Hz, AOM offset of the beatnote
I_SKIP = 120        # samples to skip around the beatnote carrier
DOUBLING = 4        # S_nu scales as the square of the harmonic order (840 -> 420 nm)


def watt(dbm):
    """dBm -> W."""
    return 10 ** (dbm / 10 - 3)


def load_trace(name):
    """Spectrum-analyzer CSV -> (frequency [Hz], amplitude [dBm per RBW])."""
    data = np.loadtxt(f"{INPUTS}/{name}", skiprows=2, delimiter=",", dtype=str)
    return data[:, 0].astype(float), data[:, 2].astype(float)


# ── method (a): 80 MHz beatnote ──────────────────────────────────────────────

def beatnote_noise(name):
    freqs, power = load_trace(name)
    power_per_hz = power - 10 * np.log10(RBW)      # dBm/Hz
    L = power_per_hz - CARRIER_PEAK                # dBc/Hz
    offset = freqs - F_BEAT                        # offset from carrier
    S_nu = 10 ** (L / 10) * 2 * offset ** 2        # Hz^2/Hz, one-sided
    return offset, L, S_nu


# ── method (b): PDH in-loop error signal ─────────────────────────────────────

def pdh_noise(name):
    freqs, power = load_trace(name)
    # error-signal slope rolls off with the cavity response
    k = K0 / np.sqrt(1 + 4 * (freqs / FWHM) ** 2)  # V/Hz
    power_per_hz_w = watt(power - 10 * np.log10(RBW))
    S_nu = power_per_hz_w * Z0 / k ** 2            # Hz^2/Hz
    L = 10 * np.log10(S_nu / (2 * (freqs + 1e-3) ** 2))
    return freqs, L, S_nu


# ── Fidelity Response Theory ─────────────────────────────────────────────────

def g_nu(x):
    """Universal CZ frequency-noise response, Tsai et al. PRX Quantum 6, 010331
    (2025), Appendix L: a two-Gaussian fit to the numerically exact response.
    Support is effectively x <~ 2.5, which sets the bandwidth requirement."""
    a, b, c = 3.062, -0.01507, 0.5588
    d, e, f = 2.843, 1.232, 0.5339
    return (2 * np.pi) ** 2 * (
        a * np.exp(-((x - b) / c) ** 2) + d * np.exp(-((x - e) / f) ** 2)
    )


def infidelity_vs_omega(freqs, S_nu, omega_rad):
    """eps_nu(Omega) = \\int S_nu(f) Omega^-2 g_nu(2 pi f / Omega) df."""
    eps = np.zeros_like(omega_rad)
    for idx, omega in enumerate(omega_rad):
        response = g_nu(2 * np.pi * freqs / omega) / omega ** 2
        eps[idx] = np.trapezoid(S_nu * response, freqs)
    return eps


def main():
    # ── phase-noise figure: both methods on shared axes ──────────────────────
    off_b, L_b, S_b = beatnote_noise("beat_3.csv")
    off_bg, L_bg, S_bg = beatnote_noise("BG_80MHz_3.csv")
    f_pdh, L_pdh, S_pdh = pdh_noise("PDH_2025_2.csv")
    _f_pbg, _L_pbg, S_pbg = pdh_noise("BG_3.csv")

    fig, (ax_L, ax_S) = plt.subplots(1, 2, figsize=(12, 4))

    ax_L.plot(off_b[I_SKIP:] * 1e-6, L_b[I_SKIP:], label="beatnote")
    ax_L.plot(f_pdh * 1e-6, L_pdh, color="salmon", label="PDH error signal")
    ax_L.plot(off_bg[I_SKIP:] * 1e-6, L_bg[I_SKIP:], color="gray", lw=0.8,
              label="beatnote noise floor")
    ax_L.set_xlabel("Offset frequency (MHz)")
    ax_L.set_ylabel(r"$\mathcal{L}(f)$ (dBc/Hz)")
    ax_L.set_title("Single-sideband phase noise (840 nm)")
    ax_L.set_ylim(-130, -80)
    ax_L.grid(True)
    ax_L.legend(fontsize=8)

    ax_S.plot(off_b[I_SKIP:] * 1e-6, S_b[I_SKIP:], label="beatnote")
    ax_S.plot(f_pdh * 1e-6, S_pdh, color="salmon", label="PDH error signal")
    ax_S.plot(off_bg[I_SKIP:] * 1e-6, S_bg[I_SKIP:], color="gray", lw=0.8,
              label="beatnote noise floor")
    ax_S.set_xlabel("Offset frequency (MHz)")
    ax_S.set_ylabel(r"$S_\nu(f)$ (Hz$^2$/Hz)")
    ax_S.set_title("Frequency noise (840 nm)")
    ax_S.set_yscale("log")
    ax_S.set_ylim(1, 1e4)
    ax_S.grid(True)
    ax_S.legend(fontsize=8)

    fig.tight_layout()

    # ── infidelity: PDH trace, background-subtracted, doubled to 420 nm ──────
    S_meas = DOUBLING * np.maximum(S_pdh - S_pbg, 0.0)
    f_max = f_pdh.max()

    tail = (f_pdh >= 7e6) & (f_pdh <= f_max)
    S_tail = float(S_meas[tail].mean())

    def extend_flat(f_end, df=2e4):
        f_ext = np.arange(f_max + df, f_end + df, df)
        return (np.concatenate([f_pdh, f_ext]),
                np.concatenate([S_meas, np.full_like(f_ext, S_tail)]))

    omega_over_2pi = np.linspace(1, 10, 200)          # MHz
    omega_rad = 2 * np.pi * omega_over_2pi * 1e6

    eps_optimistic = infidelity_vs_omega(f_pdh, S_meas, omega_rad)      # (a)
    eps_reported = infidelity_vs_omega(*extend_flat(15e6), omega_rad)   # answer
    eps_pessimistic = infidelity_vs_omega(*extend_flat(30e6), omega_rad)  # (b)

    np.savetxt(OUT_CSV, np.column_stack((omega_over_2pi, eps_reported)),
               delimiter=",")

    # The band the verifier applies: the a-to-b bracket, widened 20% each side.
    # verifier/reference_bounds.json is these two arrays verbatim.
    eps_lo = 0.8 * np.minimum(eps_optimistic, eps_pessimistic)
    eps_hi = 1.2 * np.maximum(eps_optimistic, eps_pessimistic)

    fig.savefig(OUT_FIG, format="pdf", bbox_inches="tight")
    plt.close(fig)

    with open(OUT_DIAG, "w") as fh:
        json.dump({
            "rabi_MHz": omega_over_2pi.tolist(),
            "eps_optimistic_cut_8MHz": eps_optimistic.tolist(),
            "eps_reported_flat_to_15MHz": eps_reported.tolist(),
            "eps_pessimistic_flat_to_30MHz": eps_pessimistic.tolist(),
            "eps_lo": eps_lo.tolist(),
            "eps_hi": eps_hi.tolist(),
            "S_nu_tail_level_Hz2_per_Hz_doubled": S_tail,
            "f_max_measured_Hz": float(f_max),
        }, fh, indent=2)

    print(f"S_nu tail level (doubled, 7-8 MHz mean): {S_tail:.1f} Hz^2/Hz")
    for target in (1.0, 4.0, 6.0, 8.0, 10.0):
        j = int(np.argmin(np.abs(omega_over_2pi - target)))
        a, r, b = eps_optimistic[j], eps_reported[j], eps_pessimistic[j]
        # "how far below the pessimistic answer the truncated one sits",
        # relative to the truncated value itself -- i.e. the factor by which
        # truncating at 8 MHz understates the infidelity.
        print(f"  Omega/2pi = {omega_over_2pi[j]:5.2f} MHz   "
              f"a={a:.4e}  reported={r:.4e}  b={b:.4e}  "
              f"truncation understates by {(b - a) / a * 100:5.1f}%")


if __name__ == "__main__":
    main()
