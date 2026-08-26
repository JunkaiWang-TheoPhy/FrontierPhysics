"""Build the reference paper's figures from the oracle's own deliverables.

Every figure here is drawn from files the oracle writes out of the shipped .bin
data -- nothing is hand-placed and no number is typed in. That is what lets the
paper claim its figures are reproducible from the dataset alone.

    python3 make_figures.py <oracle_verifier_dir> [out_dir]
"""

import csv
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")

import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.linewidth": 0.8,
    "figure.dpi": 200,
    "savefig.bbox": "tight",
})

CAMPAIGNS = ["-102.0", "-78.0", "-58.0"]
COLOURS = {"-102.0": "#1f4e79", "-78.0": "#c1660b", "-58.0": "#6b2d5c"}


def read(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def key(row):
    return f"{float(row['campaign_setpoint_c']):.1f}"


def fig_waveform(src, out):
    rows = read(src / "average_waveform.csv")
    n = np.array([int(r["sample_index"]) for r in rows])
    a = np.array([float(r["amplitude_adc"]) for r in rows])
    t = n * 4.0  # 250 MS/s

    fig, (ax, axz) = plt.subplots(1, 2, figsize=(6.6, 2.4),
                                  gridspec_kw={"width_ratios": [2, 1]})
    ax.plot(t, a, lw=0.7, color="#1f4e79")
    ax.set_xlabel("time (ns)")
    ax.set_ylabel("baseline-subtracted amplitude (ADC)")
    ax.axhline(0, lw=0.5, color="0.6")
    peak = int(np.argmax(np.abs(a)))
    ax.set_title("event-averaged pulse, channel 3", fontsize=9)

    lo, hi = max(peak - 40, 0), min(peak + 160, len(t) - 1)
    axz.plot(t[lo:hi], a[lo:hi], lw=0.9, color="#1f4e79")
    axz.axhline(0, lw=0.5, color="0.6")
    axz.set_xlabel("time (ns)")
    axz.set_title(f"detail, peak at sample {peak}", fontsize=9)
    for x in (ax, axz):
        x.spines[["top", "right"]].set_visible(False)
    fig.savefig(out / "fig1_waveform.pdf")
    plt.close(fig)
    return peak


def fig_spectrum_proxy(src, out):
    """Separation against threshold at each bias point.

    The charge spectrum itself is not among the deliverables, so the figure that
    stands in for it is the one the deliverables do support: how the extracted
    noise-to-1PE separation behaves across the four acquisition thresholds. Flat
    within errors is the statement that the threshold is not selecting on the
    observable.
    """
    rows = read(src / "spe_fits.csv")
    fig, axes = plt.subplots(1, 3, figsize=(6.6, 2.3), sharey=True)
    for ax, camp in zip(axes, CAMPAIGNS):
        sel = [r for r in rows if key(r) == camp]
        volts = sorted({float(r["voltage_v"]) for r in sel})
        for v in volts:
            pts = sorted([r for r in sel if float(r["voltage_v"]) == v],
                         key=lambda r: float(r["threshold"]))
            thr = [float(r["threshold"]) for r in pts]
            sp = [float(r["spe_charge_spacing_adcns"]) for r in pts]
            ax.plot(thr, sp, "o-", ms=2.5, lw=0.8, color=COLOURS[camp], alpha=0.75)
        ax.set_title(f"{camp} $^\\circ$C set", fontsize=9)
        ax.set_xticks(sorted({float(r["threshold"]) for r in sel}))
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("separation (ADC$\\cdot$ns)")
    fig.supxlabel("trigger threshold (ADC above baseline)", fontsize=9, y=0.02)
    fig.savefig(out / "fig2_threshold.pdf")
    plt.close(fig)


def fig_gain_and_breakdown(src, out):
    gain = read(src / "gain_vs_voltage.csv")
    camps = {key(r): r for r in read(src / "campaigns.csv")}

    fig, (ax, axr) = plt.subplots(2, 1, figsize=(3.5, 4.0), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1]})
    for camp in CAMPAIGNS:
        sel = [r for r in gain if key(r) == camp]
        v = np.array([float(r["voltage_v"]) for r in sel])
        s = np.array([float(r["spe_charge_spacing_adcns"]) for r in sel])
        e = np.array([float(r["spe_charge_spacing_err_adcns"]) for r in sel])
        order = np.argsort(v)
        v, s, e = v[order], s[order], e[order]
        vbd = float(camps[camp]["breakdown_voltage_v"])
        slope = float(camps[camp]["spacing_slope_adcns_per_v"])
        grid = np.linspace(vbd, v.max() + 0.4, 100)
        ax.plot(grid, slope * (grid - vbd), lw=0.8, color=COLOURS[camp], alpha=0.8)
        ax.errorbar(v, s, yerr=e, fmt="o", ms=3, lw=0.8, color=COLOURS[camp],
                    label=f"{camp} $^\\circ$C set")
        ax.plot([vbd], [0], "v", ms=5, color=COLOURS[camp])
        axr.errorbar(v, s - slope * (v - vbd), yerr=e, fmt="o", ms=3, lw=0.8,
                     color=COLOURS[camp])
    ax.axhline(0, lw=0.5, color="0.6")
    axr.axhline(0, lw=0.5, color="0.6")
    ax.set_ylabel("separation (ADC$\\cdot$ns)")
    axr.set_ylabel("residual")
    axr.set_xlabel("bias voltage (V)")
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    for x in (ax, axr):
        x.spines[["top", "right"]].set_visible(False)
    fig.savefig(out / "fig3_gain_vs_bias.pdf")
    plt.close(fig)


def fig_vbd_vs_t(src, out):
    camps = read(src / "campaigns.csv")
    t = np.array([float(r["measured_temperature_mean_c"]) for r in camps])
    ts = np.array([float(r["measured_temperature_std_c"]) for r in camps])
    v = np.array([float(r["breakdown_voltage_v"]) for r in camps])
    ve = np.array([float(r["breakdown_voltage_err_v"]) for r in camps])
    order = np.argsort(t)
    t, ts, v, ve = t[order], ts[order], v[order], ve[order]

    w = 1.0 / ve**2
    slope, intercept = np.polyfit(t, v, 1, w=np.sqrt(w))
    grid = np.linspace(t.min() - 4, t.max() + 4, 50)

    fig, (ax, axr) = plt.subplots(2, 1, figsize=(3.5, 3.6), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1]})
    ax.plot(grid, slope * grid + intercept, lw=0.9, color="0.35")
    ax.errorbar(t, v, yerr=ve, xerr=ts, fmt="o", ms=4, lw=0.9, color="#1f4e79")
    ax.set_ylabel("breakdown voltage (V)")
    ax.text(0.04, 0.9, f"$dV_{{bd}}/dT = {slope*1000:.1f}$ mV/K",
            transform=ax.transAxes, fontsize=8.5)
    axr.errorbar(t, v - (slope * t + intercept), yerr=ve, fmt="o", ms=4, lw=0.9,
                 color="#1f4e79")
    axr.axhline(0, lw=0.5, color="0.6")
    axr.set_ylabel("residual (V)")
    axr.set_xlabel("measured temperature ($^\\circ$C)")
    for x in (ax, axr):
        x.spines[["top", "right"]].set_visible(False)
    fig.savefig(out / "fig4_vbd_vs_temperature.pdf")
    plt.close(fig)
    return slope * 1000


def main() -> int:
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent / "figures"
    out.mkdir(parents=True, exist_ok=True)
    peak = fig_waveform(src, out)
    fig_spectrum_proxy(src, out)
    fig_gain_and_breakdown(src, out)
    coefficient = fig_vbd_vs_t(src, out)
    print(f"figures -> {out}")
    print(f"  pulse peak sample {peak}")
    print(f"  refitted coefficient from campaigns.csv: {coefficient:.2f} mV/K")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
