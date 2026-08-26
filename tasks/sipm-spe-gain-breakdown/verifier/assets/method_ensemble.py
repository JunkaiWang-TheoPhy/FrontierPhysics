"""Recompute the method ensemble that sets this task's acceptance tolerance.

Maintainer tool; never runs at solve or verify time. It exists so a reviewer can
reproduce the number that decides the grading bar, rather than taking it on
trust from the PR description.

The problem it answers
----------------------

`task.md` defines *what* to measure -- the charge separation between the
resolved noise and first-photoelectron populations -- but deliberately not
*how*. A breakdown voltage is an extrapolation to 6-11 V below the lowest
measured bias point, so two defensible analyses of the same files land on
noticeably different `V_bd`. Grading against one implementation would therefore
reject correct science.

So the reference is the median of a predeclared ensemble, and the acceptance
tolerance is set from the ensemble's own spread. The ensemble is the full
cross-product of

    3 baseline/integration treatments  x  3 ways of resolving the two populations

plus the independently written implementation in `independent_calib.py`, which
shares no code with the oracle. Ten members in total. All ten estimate the
*same* observable; an earlier ensemble mixed absolute-peak and separation
estimators, which is not a method systematic but a definition disagreement, and
it is what motivated the current measurement contract.

    python3 method_ensemble.py <data_dir> [out.json]

`<data_dir>` is a directory of decoded `.bin` acquisitions with the cryostat
logs in its parent, i.e. the same layout the agent sees.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "oracle" / "assets"))
sys.path.insert(0, str(HERE))

import independent_calib  # noqa: E402
from sipm_reference import (  # noqa: E402
    CampaignLadder,
    calibrate_hierarchically,
    campaign_temperature,
    combine_thresholds,
    group_by_campaign,
    index_run_files,
    is_calibratable,
    load_channel,
    pulse_areas,
    read_temperature_log,
    robust_pulse_areas,
    spacing_integer_constrained,
    spacing_peak_regression,
    spacing_two_population,
    temperature_statistics,
    usable_bias_points,
)

CHANNEL = 3

# Baseline and integration treatments. These differ in the two choices that
# actually move a pulse area: what the baseline is fitted to, and where the
# gate sits.
PROCESSINGS = {
    "reference-quadratic": robust_pulse_areas,
    "plain-window": pulse_areas,
    "block-anchored": independent_calib.areas,
}

# Ways of turning a charge spectrum into one separation.
ESTIMATORS = {
    "two-population": spacing_two_population,
    "simultaneous": spacing_integer_constrained,
    "peak-regression": spacing_peak_regression,
}


def log_for(entries, logs):
    start = min(e.timestamp for e in entries).timestamp()
    stop = max(e.timestamp for e in entries).timestamp()
    return max(logs, key=lambda log: int(((log[0] >= start) & (log[0] <= stop)).sum()))


def breakdown_by_method(ladders, areas_of, estimate, logs, campaigns) -> tuple[dict[str, float], float]:
    """One member's breakdown voltage per campaign and its coefficient.

    Every member extrapolates at the campaign temperature: bias and sensor
    temperature are correlated within each campaign, so the per-bias-point
    temperature enters the fit and the temperature coefficient is iterated to
    self-consistency across campaigns. Only the processing and the estimator
    differ between members.
    """
    built = []
    for setpoint, ladder in ladders.items():
        times, values = log_for(campaigns[setpoint], logs)
        campaign_t = campaign_temperature(times, values, campaigns[setpoint])[0]
        voltages, spacings, errors, point_t = [], [], [], []
        for voltage in sorted(ladder):
            per_threshold, entries = [], []
            for threshold in sorted(ladder[voltage]):
                segments = sorted(ladder[voltage][threshold], key=lambda i: i.segment)
                try:
                    per_threshold.append(
                        estimate(areas_of(load_channel([e.path for e in segments], CHANNEL)))
                    )
                    entries += segments
                except Exception:
                    continue
            if len(per_threshold) < 2:
                continue
            spacing, error = combine_thresholds(per_threshold)
            voltages.append(voltage)
            spacings.append(spacing)
            errors.append(max(error, 1.0))
            point_t.append(temperature_statistics(times, values, [e.timestamp for e in entries])[0])
        built.append(
            CampaignLadder(
                setpoint=setpoint,
                voltages=np.array(voltages),
                separations=np.array(spacings),
                errors=np.array(errors),
                point_temperatures=np.array(point_t),
                campaign_temperature=campaign_t,
            )
        )
    fits, coefficient, _, _, _ = calibrate_hierarchically(built)
    return {f"{k:.1f}": float(v.breakdown_voltage) for k, v in fits.items()}, float(coefficient)


def main(data_dir: Path, out_path: Path | None) -> int:
    run_files = index_run_files(data_dir)
    campaigns = group_by_campaign(run_files)
    logs = [read_temperature_log(p) for p in sorted(data_dir.parent.glob("temp_record_*.csv"))]

    ladders = {
        setpoint: usable_bias_points(entries)
        for setpoint, entries in sorted(campaigns.items())
        if is_calibratable(entries)
    }
    temperatures = {
        f"{setpoint:.1f}": campaign_temperature(*log_for(campaigns[setpoint], logs), campaigns[setpoint])[0]
        for setpoint in ladders
    }

    methods: dict[str, dict[str, float]] = {}
    coefficients: dict[str, float] = {}
    for processing, estimator in itertools.product(PROCESSINGS, ESTIMATORS):
        name = f"{processing}+{estimator}"
        methods[name], coefficients[name] = breakdown_by_method(
            ladders, PROCESSINGS[processing], ESTIMATORS[estimator], logs, campaigns
        )
        print(f"  {name:<40s} " + " ".join(f"{v:9.4f}" for _, v in sorted(methods[name].items())) + f"   {coefficients[name]:6.2f}")

    independent = independent_calib.calibrate(data_dir, CHANNEL, logs_dir=data_dir.parent)
    methods["independent-implementation"] = {
        f"{c['campaign_setpoint_c']:.1f}": float(c["breakdown_voltage"])
        for c in independent["campaigns"]
    }
    coefficients["independent-implementation"] = float(independent["temperature_coefficient_mv_per_k"])
    print(
        f"  {'independent-implementation':<40s} "
        + " ".join(f"{v:9.4f}" for _, v in sorted(methods["independent-implementation"].items()))
        + f"   {coefficients['independent-implementation']:6.2f}"
    )

    keys = sorted(next(iter(methods.values())))
    consensus = {k: float(np.median([m[k] for m in methods.values()])) for k in keys}
    max_deviation = max(abs(m[k] - consensus[k]) for m in methods.values() for k in keys)
    consensus_coefficient = float(np.median(list(coefficients.values())))
    max_coefficient_deviation = max(abs(v - consensus_coefficient) for v in coefficients.values())

    print()
    print("  consensus (median)                       " + " ".join(f"{consensus[k]:9.4f}" for k in keys))
    print(f"  worst deviation                          {max_deviation:.4f} V")
    print(f"  consensus coefficient                    {consensus_coefficient:.4f} mV/K")
    print(f"  worst coefficient deviation              {max_coefficient_deviation:.4f} mV/K")

    payload = {
        "_comment": (
            "Method ensemble behind this task's acceptance tolerance. Ten members, "
            "all estimating the noise-to-1PE charge separation and all extrapolating "
            "at the campaign temperature with the drift correction iterated to "
            "self-consistency. Regenerate with verifier/assets/method_ensemble.py."
        ),
        "consensus_vbd": consensus,
        "consensus_coefficient_mv_per_k": consensus_coefficient,
        "max_method_deviation_v": max_deviation,
        "max_method_coefficient_deviation_mv_per_k": max_coefficient_deviation,
        "measured_temperature_c": temperatures,
        "methods": methods,
        "method_coefficients": coefficients,
    }
    if out_path is not None:
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(
        main(
            Path(sys.argv[1]),
            Path(sys.argv[2]) if len(sys.argv) > 2 else None,
        )
    )
