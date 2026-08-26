"""Recompute the sixteen-member family that sets this task's acceptance band.

Maintainer tool; never runs at solve or verify time. It is the companion to
`method_ensemble.py`, and it exists for one reason: `BREAKDOWN_TOL_V = 0.17` in
`test_outputs.py` is derived from *this* family, not from the ten members that
`method_ensemble.py` regenerates, so without this script the number that decides
pass or fail could not be reproduced by a reviewer.

Why two families
----------------

`method_ensemble.py` builds the ten-member ensemble whose median is the frozen
consensus: three baseline/integration treatments x three population estimators,
plus an independently written implementation. Its worst deviation is 0.138 V.

An automated review then observed that those ten under-sample one axis: they
contain only one estimator that models the 2PE population globally. That axis
matters here, because a global 1PE Gaussian absorbs the afterpulse and
delayed-crosstalk right shoulder (+0.3 to +1.8 % of separation, and more at high
over-voltage), which steepens the ladder and pushes the intercept up. An
estimator family that under-samples it therefore understates how far two
legitimate analyses of these files can disagree.

So the band was re-derived over a family built to cover that axis properly:

    4 Gaussian-core windows (w20/w30/w50/w70)
    + integer-constrained (shared spacing)
    + peak regression
    + 2 global three-Gaussian joint fits (shared spacing; free centres)
    = 8 estimators
    x 2 baseline models (quadratic; pre-pulse window)
    = 16 members

All sixteen estimate the same observable -- the noise-to-1PE charge separation
-- and all extrapolate at the campaign temperature with the drift correction
iterated to self-consistency, exactly as the ten do. Only the estimator and the
baseline vary.

Excluded by rule rather than by result, and recorded here so the exclusions are
auditable: band means and medians (they estimate a different quantity, and land
0.27-0.83 V away on clean data), and KDE-mode and Gaussian-plus-exponential-tail
fits (numerically unstable on these statistics).

The consensus is *not* re-centred on this family. A frozen reference must not
move after the fact, and the verifier compares against the frozen consensus; the
median of the sixteen sits within 0.04 V of it in any case. What this family
sets is the tolerance around that fixed point.

Status of this script, stated plainly
-------------------------------------

This is a **reconstruction**. The band was originally derived by a script that
lived in a working directory and did not survive; this file was rewritten from
its recorded description so the derivation would be reproducible again. It is
faithful on the axis that motivated the extension: `quad+global3-shared` lands
0.146 V from consensus at -78 C, against the 0.166 V recorded for a global joint
fit under the quadratic baseline at the same cooldown.

It also produces one member the record cannot account for. `pre+core-w20`
deviates 0.216 V at -102 C, and that number is not a methodological
disagreement: at the lowest bias point of the coldest cooldown -- the point with
the longest lever on the intercept -- one of its three per-threshold fits
returns 2314 ADC*ns where the same setting under `core-w30` returns 2151, about
7.6 % high, while all seventeen other settings agree between the two windows to
better than 0.5 %. It is a single Gaussian core that did not converge on the
narrowest window over the plain-window baseline at the lowest statistics in the
run, and it drags the whole ladder.

Nothing has been done about it here. Dropping the member, or adding a
convergence rule, after seeing which member it helps would be tuning the
evidence that sets the grading bar, which is precisely what the frozen-reference
discipline exists to prevent. The member is reported with the rest, the raw
worst deviation is printed as it comes out, and the diagnosis above is the
context a reviewer needs to weigh it. Excluding that one member, the family's
worst is 0.146 V, inside the shipped 0.17 V band.

    python3 extended_family.py <data_dir> [out.json]

`<data_dir>` is a directory of decoded `.bin` acquisitions with the cryostat
logs in its parent, i.e. the same layout the agent sees.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "oracle" / "assets"))
sys.path.insert(0, str(HERE))

from method_ensemble import breakdown_by_method  # noqa: E402
from sipm_reference import (  # noqa: E402
    _hist,
    find_peaks,
    gaussian,
    group_by_campaign,
    index_run_files,
    is_calibratable,
    pulse_areas,
    read_temperature_log,
    robust_pulse_areas,
    spacing_integer_constrained,
    spacing_peak_regression,
    usable_bias_points,
)

CHANNEL = 3

# The two baseline models the family varies over. "block-anchored" is left out
# deliberately: it belongs to the independent implementation, which is already a
# member of the ten and is not an estimator axis.
PROCESSINGS = {
    "quad": robust_pulse_areas,
    "pre": pulse_areas,
}


def _core_center(a, centre, spacing, frac):
    """Gaussian core plus a linear background in a window of half-width frac."""
    counts, centres = _hist(a, centre - frac * spacing, centre + frac * spacing, 60)

    def model(x, amplitude, mean, sigma, c0, c1):
        return gaussian(x, amplitude, mean, sigma) + np.maximum(c0 + c1 * (x - centre), 0)

    params, _ = curve_fit(
        model,
        centres,
        counts,
        p0=[max(counts.max(), 1), centre, 0.125 * spacing, 0.0, 0.0],
        maxfev=40000,
    )
    return float(params[1])


def core_window(frac):
    """Two-population separation from Gaussian cores of a given window width."""

    def estimate(a):
        noise, one, spacing = find_peaks(a)
        return _core_center(a, one, spacing, frac) - _core_center(a, noise, spacing, frac)

    return estimate


def _global_three(a, free_centres: bool):
    """Global noise+1PE+2PE fit, with the ladder shared or each centre free.

    The free-centre variant is the one that exposes the axis this family exists
    to cover: with nothing tying the 1PE centre to the ladder, the fit lets that
    Gaussian slide onto the afterpulse shoulder.
    """
    noise, _one, spacing = find_peaks(a)
    # No resolved-orders gate here, deliberately, and it is the whole point of
    # this member. At these statistics the 2PE window holds 18-28 events, so a
    # gate like the reference module's (150 events) would refuse the fit and
    # collapse this member onto the shared-spacing one. An analyst who fits
    # three Gaussians anyway is doing something defensible, and what happens
    # then is the effect this family exists to measure: with almost nothing for
    # the third component to latch onto, the 1PE Gaussian absorbs the
    # afterpulse and delayed-crosstalk shoulder, the ladder steepens, and the
    # intercept moves.
    counts, centres = _hist(a, noise - 0.5 * spacing, noise + 2.8 * spacing, 200)
    sigma = np.sqrt(np.maximum(counts, 1.0))
    amp = counts.max()

    if not free_centres:
        def model(x, a0, s0, a1, s1, a2, s2, mu0, sep):
            return (gaussian(x, a0, mu0, s0)
                    + gaussian(x, a1, mu0 + sep, s1)
                    + gaussian(x, a2, mu0 + 2 * sep, s2))

        p0 = [amp, 0.12 * spacing, amp * 0.4, 0.12 * spacing, amp * 0.05, 0.14 * spacing,
              noise, spacing]
        lo = [0, 0.02 * spacing, 0, 0.02 * spacing, 0, 0.02 * spacing,
              noise - 0.4 * spacing, 0.6 * spacing]
        hi = [np.inf, 0.6 * spacing, np.inf, 0.6 * spacing, np.inf, 0.8 * spacing,
              noise + 0.4 * spacing, 1.5 * spacing]
        params, _ = curve_fit(model, centres, counts, p0=p0, bounds=(lo, hi),
                              sigma=sigma, maxfev=60000)
        return float(params[7])

    def model(x, a0, mu0, s0, a1, mu1, s1, a2, mu2, s2):
        return (gaussian(x, a0, mu0, s0)
                + gaussian(x, a1, mu1, s1)
                + gaussian(x, a2, mu2, s2))

    p0 = [amp, noise, 0.12 * spacing,
          amp * 0.4, noise + spacing, 0.12 * spacing,
          amp * 0.05, noise + 2 * spacing, 0.14 * spacing]
    lo = [0, noise - 0.4 * spacing, 0.02 * spacing,
          0, noise + 0.5 * spacing, 0.02 * spacing,
          0, noise + 1.5 * spacing, 0.02 * spacing]
    hi = [np.inf, noise + 0.4 * spacing, 0.6 * spacing,
          np.inf, noise + 1.6 * spacing, 0.6 * spacing,
          np.inf, noise + 3.0 * spacing, 0.9 * spacing]
    params, _ = curve_fit(model, centres, counts, p0=p0, bounds=(lo, hi),
                          sigma=sigma, maxfev=60000)
    return float(params[4] - params[1])


ESTIMATORS = {
    "core-w20": core_window(0.20),
    "core-w30": core_window(0.30),
    "core-w50": core_window(0.50),
    "core-w70": core_window(0.70),
    "integer-constrained": spacing_integer_constrained,
    "peak-regression": spacing_peak_regression,
    "global3-shared": lambda a: _global_three(a, free_centres=False),
    "global3-free": lambda a: _global_three(a, free_centres=True),
}


def main(data_dir: Path, out_path: Path | None) -> int:
    frozen = json.loads((HERE / "reference_values.json").read_text())["consensus"]
    consensus = {k: float(v) for k, v in frozen["breakdown_voltage_v"].items()}
    consensus_coefficient = float(np.median(list(frozen["method_coefficients"].values())))

    run_files = index_run_files(data_dir)
    campaigns = group_by_campaign(run_files)
    logs = [read_temperature_log(p) for p in sorted(data_dir.parent.glob("temp_record_*.csv"))]
    ladders = {
        setpoint: usable_bias_points(entries)
        for setpoint, entries in sorted(campaigns.items())
        if is_calibratable(entries)
    }

    keys = sorted(consensus)
    print("  " + " " * 40 + " ".join(f"{k:>9s}" for k in keys) + "   coef    worst")
    members: dict[str, dict[str, float]] = {}
    coefficients: dict[str, float] = {}
    for processing, estimator in itertools.product(PROCESSINGS, ESTIMATORS):
        name = f"{processing}+{estimator}"
        try:
            values, coefficient = breakdown_by_method(
                ladders, PROCESSINGS[processing], ESTIMATORS[estimator], logs, campaigns
            )
        except Exception as exc:  # a member that will not converge is reported, not hidden
            print(f"  {name:<40s} FAILED: {type(exc).__name__}: {exc}")
            continue
        members[name] = values
        coefficients[name] = coefficient
        worst = max(abs(values[k] - consensus[k]) for k in keys)
        print(f"  {name:<40s} " + " ".join(f"{values[k]:9.4f}" for k in keys)
              + f"   {coefficient:6.2f}   {worst:.4f}")

    if not members:
        raise SystemExit("no member converged")

    per_campaign = {k: max(abs(m[k] - consensus[k]) for m in members.values()) for k in keys}
    worst = max(per_campaign.values())
    worst_coefficient = max(abs(c - consensus_coefficient) for c in coefficients.values())

    print()
    print(f"  members that converged                   {len(members)}/16")
    print("  frozen consensus                         " + " ".join(f"{consensus[k]:9.4f}" for k in keys))
    print("  worst deviation per campaign             " + " ".join(f"{per_campaign[k]:9.4f}" for k in keys))
    print(f"  worst deviation overall                  {worst:.4f} V   -> band {np.ceil(worst * 100) / 100:.2f} V")
    print(f"  worst coefficient deviation              {worst_coefficient:.4f} mV/K  (band 5.00)")

    payload = {
        "_comment": (
            "Extended sixteen-member estimator family behind BREAKDOWN_TOL_V in "
            "test_outputs.py. Deviations are measured against the FROZEN consensus in "
            "reference_values.json, which this family does not re-centre. Regenerate "
            "with verifier/assets/extended_family.py."
        ),
        "frozen_consensus_vbd": consensus,
        "members": members,
        "member_coefficients": coefficients,
        "worst_deviation_per_campaign_v": per_campaign,
        "worst_deviation_v": worst,
        "worst_coefficient_deviation_mv_per_k": worst_coefficient,
    }
    if out_path is not None:
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(
        main(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else None)
    )
