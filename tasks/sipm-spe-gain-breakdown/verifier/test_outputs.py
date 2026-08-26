"""Staged verification of the multi-campaign SiPM calibration.

The stages are ordered so a failure localises the problem:

  decoding -> event structure -> waveform reconstruction -> which campaigns can
  be calibrated -> measured temperature -> SPE extraction -> gain per bias point
  -> breakdown voltage per campaign -> temperature coefficient -> internal
  consistency of the two stages

Binary-format checks are strict, because the DT5720 event layout has exactly one
correct reading and it is verified here with a reader that shares no code with
the reference pipeline.

The graded observable is the charge separation between the resolved noise
and one-photoelectron populations. No particular fit model is required, and the
headline results are graded against a *consensus* of ten predeclared pipelines
rather than against any single implementation. Breakdown voltage is an
extrapolation to well below the measured bias range, so sound analyses differ by
more than they differ in the shape of the separation-versus-bias curve; the
consensus median is the operational reference, and the acceptance band is the
measured method systematic of legitimate analyses around it -- re-derived over
an extended family of sixteen peak-position estimator/baseline combinations
(worst 0.166 V) after the original ten were found to under-sample global joint
fits. Passing is central-value correctness only; the submission's stated
uncertainty never enters the verdict.

Be precise about what that family does and does not span. It varies the
baseline treatment, the core-window width, sequential/constrained/regression/
joint estimation, and includes an independently written implementation sharing
no code with the reference; it shares this module's threshold combination and
weighted extrapolation, so those two axes are covered by the band's headroom
rather than by measurement. Nothing here requires an agent to reproduce the
reference pipeline's baseline model, filtering, integration window or threshold
selection.
"""

from __future__ import annotations

import csv
import functools
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, "/verifier/assets")

import caen_reader
import independent_calib

ROOT = Path("/root")
DATA_DIR = ROOT / "data"
LOGS = Path("/logs/verifier")
ASSETS = Path("/verifier/assets")

DECODE_CHECK_FILE = (
    "sipm_group1_threshold30_-58.0C_53.0V_2000_123_raw_b0_seg0_20230714T190127.bin"
)
DECODE_CHECK_EVENTS = 200
CHANNEL = 3

# --- acceptance tolerances -------------------------------------------------
# The reference is the median of ten predeclared pipelines, every one of which
# extrapolates at the campaign temperature: within each campaign the bias ladder
# was stepped upward while the cryostat drifted, so bias and temperature are
# correlated (corr 0.99-1.00) and a fit against bias alone absorbs part of dQ/dT,
# biasing the intercept ~0.10 V low. The task asks for the breakdown voltage at
# the campaign's measured temperature; the reference is that quantity.
#
# Acceptance is central-value correctness only: the reported breakdown voltage
# must lie within the measured method systematic of legitimate analyses of these
# files. That systematic was re-derived from an extended family of sixteen
# predeclared peak-position estimators (Gaussian-core windows of four widths,
# integer-constrained and peak-regression fits, and global noise+1PE+2PE
# joint fits with shared or free centres, each under two baseline models) whose
# worst deviation from the frozen consensus is 0.166 V, at -78 C, for a global
# joint fit under the quadratic baseline. Grading tighter would reject correct
# science for choosing a different fit; grading looser would admit analyses
# whose central value is simply wrong. There is deliberately no second
# acceptance path through the submission's stated uncertainty: an analysis
# that misses the systematic biasing its central value does not recover the
# calibration, however honestly it widens its error bar -- uncertainty quality
# is graded separately by the rubric.
BREAKDOWN_TOL_V = 0.17
# Reported alongside the result as a precision target. Deliberately NOT an
# assertion: the ensemble does not support 0.10 V, so failing it is not
# evidence of an error. It exists so a run that does reach the tighter bar is
# visible in the log.
BREAKDOWN_PRECISION_TARGET_V = 0.10
# Worst coefficient deviation across the extended estimator family is 3.4 mV/K
# (the global joint fits, which tilt the ladder); this leaves ~1.5x. It does
# NOT police use of nominal setpoints -- that error is about 2.4 mV/K and is
# caught directly by the per-campaign temperature checks below.
COEFFICIENT_TOL_MV_PER_K = 5.0
COEFFICIENT_CONSISTENCY_TOL = 5.0

SLOPE_REL_TOL = 0.10
SPACING_SCALE_REL_TOL = 0.10
NORMALIZED_SHAPE_ABS_TOL = 0.03
SPACING_REL_TOL = 0.08
SPE_RESOLUTION_RANGE = (0.015, 0.35)
BASELINE_TOL_ADC = 1.0
LINEARITY_MAX_CHI2_PER_DOF = 10.0
TEMPERATURE_MEAN_TOL_C = 0.5
TEMPERATURE_STD_TOL_C = 0.15
WAVEFORM_MIN_CORRELATION = 0.80
WAVEFORM_PEAK_TOL_SAMPLES = 5
WAVEFORM_SCALE_RANGE = (0.4, 2.5)
SELF_GUARD_TOL_V = 0.05
REFERENCE_AGREEMENT_TOL_V = 0.2
MIN_TOTAL_RETAINED_FRACTION = 0.40
MIN_CELL_RETAINED_FRACTION = 0.15
# A reported campaign must be one of the run's cooldowns. Setpoints are >= 7 C
# apart, so a 2 C snap tolerates sloppy rounding while rejecting invented
# campaigns, and relabelling a real cooldown (-95.06 for -95.0) snaps back to
# the canonical key instead of dodging the checks tied to it.
CAMPAIGN_SETPOINT_TOL_C = 2.0
# Plausibility bound on the stated breakdown uncertainty, communicated in
# output_schema.md. It is a sanity check, not an acceptance lever: the stated
# uncertainty plays no role in whether the breakdown voltage passes. Reference
# pipelines' covariance-only errors are 0.02-0.07 V and a full systematic
# budget legitimately reaches 0.15-0.2 V; beyond 0.25 V a number no longer
# describes a measurement of this extrapolation.
BREAKDOWN_ERR_MAX_V = 0.25
# The scale-free gain-shape comparison runs on the bias points the submission
# and the reference share, so a justified exclusion of one point is not an
# error; below this many shared points the shape is no longer being checked.
MIN_SHAPE_POINTS = 4


@functools.lru_cache(maxsize=1)
def reference() -> dict:
    return json.loads((ASSETS / "reference_values.json").read_text())


def _fail(message: str) -> None:
    raise AssertionError(message)


def read_csv_rows(path: Path, expected_columns: list[str]) -> list[dict[str, str]]:
    if not path.is_file():
        _fail(f"missing required artifact {path}")
    # utf-8-sig strips a leading byte-order mark (what pandas' encoding
    # "utf-8-sig" emits) that would otherwise corrupt the first column name;
    # plain ASCII and UTF-8 files read identically.
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            _fail(f"{path.name} has no header row")
        missing = [name for name in expected_columns if name not in reader.fieldnames]
        if missing:
            _fail(f"{path.name} is missing required column(s) {missing}; found {reader.fieldnames}")
        rows = list(reader)
    if not rows:
        _fail(f"{path.name} contains no data rows")
    return rows


def as_float(row: dict[str, str], column: str, name: str, index: int) -> float:
    raw = (row.get(column) or "").strip()
    try:
        value = float(raw)
    except ValueError:
        _fail(f"{name} row {index}: column {column!r} is not numeric ({raw!r})")
    if not math.isfinite(value):
        _fail(f"{name} row {index}: column {column!r} is not finite")
    return value


def as_int(row: dict[str, str], column: str, name: str, index: int) -> int:
    value = as_float(row, column, name, index)
    if value != int(value):
        _fail(f"{name} row {index}: column {column!r} must be an integer")
    return int(value)


@functools.lru_cache(maxsize=1)
def parse_result() -> dict[str, float]:
    path = ROOT / "result.md"
    if not path.is_file():
        _fail("missing required artifact /root/result.md")
    text = path.read_text()
    keys = [
        "breakdown_voltage_temperature_coefficient_mv_per_k",
        "breakdown_voltage_temperature_coefficient_err_mv_per_k",
        "n_campaigns_calibrated",
    ]
    values: dict[str, float] = {}
    for key in keys:
        match = re.search(
            rf"(?mi)^\s*{re.escape(key)}\s*:\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)",
            text,
        )
        if match is None:
            _fail(f"result.md has no numeric line for {key!r}")
        value = float(match.group(1))
        if not math.isfinite(value):
            _fail(f"result.md value for {key!r} is not finite")
        values[key] = value
    return values


@functools.lru_cache(maxsize=1)
def parse_campaigns() -> dict[str, dict[str, float]]:
    columns = [
        "campaign_setpoint_c",
        "measured_temperature_mean_c",
        "measured_temperature_std_c",
        "breakdown_voltage_v",
        "breakdown_voltage_err_v",
        "spacing_slope_adcns_per_v",
        "spacing_fit_chi2_per_dof",
    ]
    rows = read_csv_rows(ROOT / "campaigns.csv", columns)
    known = sorted(
        set(reference()["calibratable_campaigns"])
        | set(reference()["non_calibratable_campaigns"])
    )
    out: dict[str, dict[str, float]] = {}
    for index, row in enumerate(rows):
        setpoint = as_float(row, "campaign_setpoint_c", "campaigns.csv", index)
        # Every reported campaign must be one of the run's cooldowns: a row for
        # a cooldown that never happened has nothing it can be graded against,
        # yet would otherwise feed the cross-campaign consistency fit. Snapping
        # to the nearest real setpoint also stops a relabelled cooldown from
        # dodging the checks attached to its canonical key.
        nearest = min(known, key=lambda c: abs(c - setpoint))
        if abs(nearest - setpoint) > CAMPAIGN_SETPOINT_TOL_C:
            _fail(
                f"campaigns.csv row {index}: {setpoint} C is not one of this run's "
                f"cooldowns ({known})"
            )
        key = f"{nearest:.1f}"
        # A campaign reported twice is ambiguous, not merely redundant: the two
        # rows may disagree, and silently keeping the last one would grade a
        # number the submission did not unambiguously claim.
        if key in out:
            _fail(f"campaigns.csv reports campaign {key} C more than once")
        out[key] = {c: as_float(row, c, "campaigns.csv", index) for c in columns[1:]}
    return out


@functools.lru_cache(maxsize=1)
def parse_gain_table() -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    rows = read_csv_rows(
        ROOT / "gain_vs_voltage.csv",
        ["campaign_setpoint_c", "voltage_v", "spe_charge_spacing_adcns", "spe_charge_spacing_err_adcns"],
    )
    grouped: dict[str, list[tuple[float, float, float]]] = {}
    for index, row in enumerate(rows):
        key = f"{as_float(row, 'campaign_setpoint_c', 'gain_vs_voltage.csv', index):.1f}"
        voltage = as_float(row, "voltage_v", "gain_vs_voltage.csv", index)
        if any(abs(v - voltage) < 1e-6 for v, _, _ in grouped.get(key, [])):
            _fail(f"gain_vs_voltage.csv reports {key} C at {voltage:.1f} V more than once")
        grouped.setdefault(key, []).append(
            (
                as_float(row, "voltage_v", "gain_vs_voltage.csv", index),
                as_float(row, "spe_charge_spacing_adcns", "gain_vs_voltage.csv", index),
                as_float(row, "spe_charge_spacing_err_adcns", "gain_vs_voltage.csv", index),
            )
        )
    out = {}
    for key, values in grouped.items():
        values.sort()
        out[key] = (
            np.array([v[0] for v in values]),
            np.array([v[1] for v in values]),
            np.array([v[2] for v in values]),
        )
    return out


@functools.lru_cache(maxsize=1)
def parse_spe_fits() -> dict[str, tuple[float, float, int, float]]:
    rows = read_csv_rows(
        ROOT / "spe_fits.csv",
        [
            "campaign_setpoint_c",
            "voltage_v",
            "threshold",
            "n_events",
            "baseline_adc",
            "spe_charge_spacing_adcns",
            "spe_peak_sigma_adcns",
        ],
    )
    out: dict[str, tuple[float, float, int, float]] = {}
    for index, row in enumerate(rows):
        key = (
            f"{as_float(row, 'campaign_setpoint_c', 'spe_fits.csv', index):.1f}"
            f"|{as_float(row, 'voltage_v', 'spe_fits.csv', index):.1f}"
            f"|{as_int(row, 'threshold', 'spe_fits.csv', index)}"
        )
        # Same ambiguity rule as the other two tables: a setting reported twice
        # may disagree with itself, and last-wins would grade an unclaimed row.
        if key in out:
            _fail(f"spe_fits.csv reports setting {key} more than once")
        out[key] = (
            as_float(row, "spe_charge_spacing_adcns", "spe_fits.csv", index),
            as_float(row, "spe_peak_sigma_adcns", "spe_fits.csv", index),
            as_int(row, "n_events", "spe_fits.csv", index),
            as_float(row, "baseline_adc", "spe_fits.csv", index),
        )
    return out


def ols_slope(x: np.ndarray, y: np.ndarray) -> float:
    design = np.vstack([x, np.ones_like(x)]).T
    solution, *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(solution[0])


# ---------------------------------------------------------------------------
# Stage 0 — the frozen reference must still describe the delivered data
# ---------------------------------------------------------------------------


def test_reference_values_still_describe_the_shipped_dataset():
    LOGS.mkdir(parents=True, exist_ok=True)
    expected = reference()

    # AppleDouble sidecars are skipped: they carry no samples and appear only
    # when the archives pass through a macOS host on the way into the sandbox.
    # Integrity of the real files is enforced by hash in the next test.
    present = sorted(
        p.name
        for p in DATA_DIR.iterdir()
        if p.name.endswith(".bin") and not p.name.startswith("._")
    )
    assert present == sorted(expected["data_manifest"]), (
        "the raw dataset in /root/data does not match the recorded manifest"
    )

    # Read the cryostat logs from the verifier's own copy. /root is sticky, so
    # the shipped logs cannot be altered, but an agent can still *add* files
    # there, and this guard must not depend on anything the agent can create.
    recomputed = independent_calib.calibrate(DATA_DIR, CHANNEL, logs_dir=ASSETS / "logs")

    frozen = {
        f"{c['campaign_setpoint_c']:.1f}": c["breakdown_voltage"]
        for c in expected["independent"]["campaigns"]
    }
    # Audit trail: log only the drift of the recomputation against the frozen
    # values, not the recomputed calibration itself -- /logs stays readable
    # around the verifier run, and absolute breakdown voltages there would be
    # an answer channel in any multi-round setting.
    (LOGS / "independent_reference_drift.json").write_text(
        json.dumps(
            {
                f"{c['campaign_setpoint_c']:.1f}": c["breakdown_voltage"]
                - frozen[f"{c['campaign_setpoint_c']:.1f}"]
                for c in recomputed["campaigns"]
                if f"{c['campaign_setpoint_c']:.1f}" in frozen
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    for campaign in recomputed["campaigns"]:
        key = f"{campaign['campaign_setpoint_c']:.1f}"
        assert abs(campaign["breakdown_voltage"] - frozen[key]) < SELF_GUARD_TOL_V, (
            f"the verifier's own independent calibration of the {key} C campaign now "
            f"gives {campaign['breakdown_voltage']:.4f} V against a frozen "
            f"{frozen[key]:.4f} V; regenerate verifier/assets/reference_values.json"
        )
        consensus = expected["consensus"]["breakdown_voltage_v"][key]
        assert abs(campaign["breakdown_voltage"] - consensus) < REFERENCE_AGREEMENT_TOL_V, (
            "an independent implementation disagrees with the consensus reference by "
            "more than a method offset can explain; the reference is not trustworthy"
        )


def test_raw_data_was_not_modified():
    manifest = reference()["data_manifest"]
    corrupted = []
    for name, expected_digest in sorted(manifest.items()):
        path = DATA_DIR / name
        if not path.is_file():
            corrupted.append(f"{name}: missing")
            continue
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        if digest.hexdigest() != expected_digest:
            corrupted.append(f"{name}: content changed")
    assert not corrupted, "raw input files were modified: " + ", ".join(corrupted[:5])


# ---------------------------------------------------------------------------
# Stage 1 — binary decoding, against an independent reader
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def decode_check_rows() -> list[dict[str, str]]:
    columns = [
        "event_index",
        "event_counter",
        "trigger_time_tag",
        "ch1_raw_min",
        "ch1_raw_max",
        "ch2_raw_min",
        "ch2_raw_max",
        "ch3_raw_min",
        "ch3_raw_max",
        "ch3_raw_sum",
        "ch3_raw_first",
        "ch3_raw_last",
    ]
    return read_csv_rows(ROOT / "decode_check.csv", columns)


def test_decode_check_matches_an_independent_reader():
    rows = decode_check_rows()
    assert len(rows) == DECODE_CHECK_EVENTS, (
        f"decode_check.csv must cover the first {DECODE_CHECK_EVENTS} events; found {len(rows)}"
    )
    events = caen_reader.read_events(DATA_DIR / DECODE_CHECK_FILE, DECODE_CHECK_EVENTS)
    mismatches: list[str] = []
    for index, (row, event) in enumerate(zip(rows, events)):
        channel_1, channel_2, channel_3 = event.channels
        expected = {
            "event_index": index,
            "event_counter": event.counter,
            "trigger_time_tag": event.time_tag,
            "ch1_raw_min": min(channel_1),
            "ch1_raw_max": max(channel_1),
            "ch2_raw_min": min(channel_2),
            "ch2_raw_max": max(channel_2),
            "ch3_raw_min": min(channel_3),
            "ch3_raw_max": max(channel_3),
            "ch3_raw_sum": sum(channel_3),
            # Order sensitive: sums, minima and maxima are all invariant under
            # swapping the two samples packed in each 32-bit word.
            "ch3_raw_first": channel_3[0],
            "ch3_raw_last": channel_3[-1],
        }
        for column, want in expected.items():
            got = as_int(row, column, "decode_check.csv", index)
            if got != want:
                mismatches.append(f"event {index} {column}: got {got}, expected {want}")
    assert not mismatches, (
        f"{len(mismatches)} decoded value(s) disagree with an independent reading of the "
        f"DT5720 event stream. First few: " + "; ".join(mismatches[:6])
    )


# ---------------------------------------------------------------------------
# Stage 2 — event structure per the DT5720 event format
# ---------------------------------------------------------------------------


def test_event_counter_is_contiguous():
    rows = decode_check_rows()
    counters = [as_int(r, "event_counter", "decode_check.csv", i) for i, r in enumerate(rows)]
    width = 1 << caen_reader.EVENT_COUNTER_BITS
    assert all(0 <= v < width for v in counters), (
        "event counters fall outside the DT5720 event-counter field width"
    )
    bad = [i for i, step in enumerate(caen_reader.counter_steps(counters)) if step != 1]
    assert not bad, (
        f"the reported event counter is not contiguous (first break after event {bad[0]})"
    )


def test_trigger_time_tag_advances():
    rows = decode_check_rows()
    tags = [as_int(r, "trigger_time_tag", "decode_check.csv", i) for i, r in enumerate(rows)]
    width = 1 << caen_reader.TIME_TAG_BITS
    assert all(0 <= v < width for v in tags), (
        "trigger time tags fall outside the DT5720 time-tag field width"
    )
    stalled = [i for i, step in enumerate(caen_reader.time_tag_steps(tags)) if step <= 0]
    assert not stalled, (
        f"the trigger time tag does not advance between consecutive events "
        f"(first at event {stalled[0]}), even after unwrapping"
    )


def test_every_file_holds_the_expected_number_of_events():
    expected = reference()["expected_events_per_file"]
    wrong = []
    for name in sorted(reference()["data_manifest"]):
        count = caen_reader.count_events(DATA_DIR / name)
        if count != expected:
            wrong.append(f"{name}: {count}")
    assert not wrong, f"expected {expected} events per file; got " + ", ".join(wrong[:5])


# ---------------------------------------------------------------------------
# Stage 3 — waveform reconstruction (diagnostic, deliberately permissive)
# ---------------------------------------------------------------------------


def test_average_waveform_is_a_plausible_reconstruction():
    rows = read_csv_rows(ROOT / "average_waveform.csv", ["sample_index", "amplitude_adc"])
    expected_wave = np.asarray(reference()["average_waveform_adc"])
    assert len(rows) == expected_wave.size, (
        f"average_waveform.csv must have one row per sample ({expected_wave.size}); "
        f"found {len(rows)}"
    )
    indices = np.asarray(
        [as_int(r, "sample_index", "average_waveform.csv", i) for i, r in enumerate(rows)]
    )
    amplitudes = np.asarray(
        [as_float(r, "amplitude_adc", "average_waveform.csv", i) for i, r in enumerate(rows)]
    )
    assert np.array_equal(indices, np.arange(expected_wave.size)), (
        "average_waveform.csv sample_index must run in order from 0"
    )
    design = np.vstack([amplitudes, np.ones_like(amplitudes)]).T
    (scale, _offset), *_ = np.linalg.lstsq(design, expected_wave, rcond=None)
    correlation = float(np.corrcoef(amplitudes, expected_wave)[0, 1])
    assert correlation >= WAVEFORM_MIN_CORRELATION, (
        f"the average waveform does not resemble the reference pulse shape "
        f"(correlation {correlation:.3f}); check the channel, the sample ordering "
        f"and the channel de-interleaving"
    )
    assert WAVEFORM_SCALE_RANGE[0] <= scale <= WAVEFORM_SCALE_RANGE[1], (
        f"the average waveform amplitude is off by a factor {1 / scale:.2f}; "
        f"it should be in raw ADC counts"
    )
    peak = int(np.argmax(amplitudes - np.median(amplitudes)))
    expected_peak = int(reference()["average_waveform_peak_sample"])
    assert abs(peak - expected_peak) <= WAVEFORM_PEAK_TOL_SAMPLES, (
        f"the averaged pulse peaks at sample {peak}, expected near {expected_peak}"
    )


# ---------------------------------------------------------------------------
# Stage 4 — which campaigns can carry a calibration
# ---------------------------------------------------------------------------


def test_calibrated_the_campaigns_that_can_be_calibrated():
    expected = {f"{c:.1f}" for c in reference()["calibratable_campaigns"]}
    reported = set(parse_campaigns())
    missing = sorted(expected - reported)
    assert not missing, (
        f"no calibration reported for campaign(s) {missing}, which do carry a bias "
        f"ladder and can each yield a breakdown voltage"
    )


def test_did_not_calibrate_a_campaign_with_no_bias_ladder():
    """A single operating point cannot give a breakdown voltage.

    Using such a campaign as a cross-check or inside a joint model is fine; what
    is not fine is reporting an independently determined breakdown voltage for
    it, since there is nothing to extrapolate.
    """
    forbidden = {f"{c:.1f}" for c in reference()["non_calibratable_campaigns"]}
    claimed = sorted(forbidden & set(parse_campaigns()))
    assert not claimed, (
        f"a breakdown voltage is reported for campaign(s) {claimed}, which have too "
        f"few distinct bias points to support the extrapolation that defines it"
    )


def test_reported_campaign_count_matches_the_table():
    stated = int(parse_result()["n_campaigns_calibrated"])
    actual = len(parse_campaigns())
    assert stated == actual, (
        f"result.md states {stated} calibrated campaigns but campaigns.csv has {actual} rows"
    )


# ---------------------------------------------------------------------------
# Stage 5 — measured temperature, not the nominal setpoint
# ---------------------------------------------------------------------------


def test_campaign_temperatures_come_from_the_cryostat_log():
    expected = {
        f"{c['campaign_setpoint_c']:.1f}": c for c in reference()["campaigns"]
    }
    problems = []
    for key, row in sorted(parse_campaigns().items()):
        if key not in expected:
            continue
        want_mean = expected[key]["measured_temperature_mean_c"]
        want_std = expected[key]["measured_temperature_std_c"]
        if abs(row["measured_temperature_mean_c"] - want_mean) > TEMPERATURE_MEAN_TOL_C:
            problems.append(
                f"{key} C: reported {row['measured_temperature_mean_c']:.2f} C against a "
                f"logged {want_mean:.2f} C"
            )
        if abs(row["measured_temperature_std_c"] - want_std) > TEMPERATURE_STD_TOL_C:
            problems.append(
                f"{key} C: reported spread {row['measured_temperature_std_c']:.2f} C "
                f"against a logged {want_std:.2f} C"
            )
    assert not problems, (
        "campaign temperatures do not match the cryostat logs — the setpoint in the "
        "file names is not the measurement: " + "; ".join(problems)
    )


# ---------------------------------------------------------------------------
# Stage 6 — single-photoelectron extraction
# ---------------------------------------------------------------------------


def test_spe_fits_match_the_reference():
    """Compare only where the agent and the reference analysed the same setting.

    Which threshold settings to use, and how to combine them, is the analyst's
    choice: a hierarchical model over thresholds, one threshold as the primary
    calibration with the rest as a systematic check, or sparse settings kept
    only as diagnostics are all defensible. So this compares on the
    intersection and never demands the reference's set of settings. Whether the
    data was used well enough is judged by the gain shape, the linearity, the
    breakdown voltage and the rubric, not here.
    """
    expected = reference()["spe_fits"]
    seen = parse_spe_fits()
    shared = sorted(set(expected) & set(seen))
    assert shared, (
        "spe_fits.csv shares no (campaign, bias, threshold) setting with the "
        "reference, so nothing about the single-photoelectron extraction can be "
        "checked; at least some settings must be reported as analysed"
    )

    problems: list[str] = []
    for key in shared:
        mean, sigma, _n_events, _baseline = seen[key]
        want = expected[key]["spe_charge_spacing_adcns"]
        if abs(mean - want) > SPACING_REL_TOL * want:
            problems.append(f"{key}: SPE mean {mean:.1f} vs reference {want:.1f} ADC*ns")
        resolution = sigma / mean if mean else float("inf")
        if not SPE_RESOLUTION_RANGE[0] <= resolution <= SPE_RESOLUTION_RANGE[1]:
            problems.append(f"{key}: SPE width/mean = {resolution:.3f} is not physical")
    assert not problems, "; ".join(problems[:8])


def test_reported_fits_support_the_reported_calibration():
    """Every bias point behind a calibration must have a fit behind it.

    Method agnostic: it does not ask which thresholds were used, how many, or
    that they match the reference — only that the gain table an agent fitted is
    backed by single-photoelectron fits it actually reported, and that each
    calibrated campaign really does rest on a bias ladder.
    """
    tables = parse_gain_table()
    seen = parse_spe_fits()
    covered: dict[str, set[str]] = {}
    for key in seen:
        campaign, voltage, _threshold = key.split("|")
        covered.setdefault(campaign, set()).add(voltage)

    problems = []
    for campaign, (voltages, _gains, _errors) in sorted(tables.items()):
        if len(voltages) < 3:
            problems.append(
                f"{campaign} C: only {len(voltages)} bias points in the gain table, "
                f"too few to extrapolate a breakdown voltage"
            )
        missing = [f"{v:.1f}" for v in voltages if f"{v:.1f}" not in covered.get(campaign, set())]
        if missing:
            problems.append(
                f"{campaign} C: gain reported at bias {missing} with no "
                f"single-photoelectron fit behind it in spe_fits.csv"
            )
    assert not problems, "; ".join(problems)


def test_analysis_used_the_device_under_test():
    """The noise level identifies which channel was analysed."""
    expected = reference()["spe_fits"]
    seen = parse_spe_fits()
    wrong = []
    for key, fit in sorted(expected.items()):
        if key not in seen:
            continue
        want = fit["baseline_adc"]
        got = seen[key][3]
        if abs(got - want) > BASELINE_TOL_ADC:
            wrong.append(f"{key}: {got:.2f} vs {want:.2f}")
    assert not wrong, (
        "the reported noise level does not match the device under test named in "
        "the run log: " + "; ".join(wrong[:5])
    )


def test_analysis_did_not_discard_most_of_the_campaign():
    """A quality cut may remove data; it may not remove the measurement."""
    delivered_per_cell = reference()["expected_events_per_file"] * 3
    seen = parse_spe_fits()
    total_kept = sum(v[2] for v in seen.values())
    total_delivered = delivered_per_cell * len(seen)
    assert total_kept >= MIN_TOTAL_RETAINED_FRACTION * total_delivered, (
        f"only {total_kept} of about {total_delivered} delivered events survive the "
        f"analysis; a calibration cannot rest on that little of the campaign"
    )
    starved = [
        key
        for key, values in sorted(seen.items())
        if values[2] < MIN_CELL_RETAINED_FRACTION * delivered_per_cell
    ]
    assert not starved, f"these settings retain almost no events: {starved[:5]}"


# ---------------------------------------------------------------------------
# Stage 7 — gain per bias point, per campaign
# ---------------------------------------------------------------------------


def test_gain_tables_cover_every_calibrated_campaign():
    tables = parse_gain_table()
    for key in sorted(parse_campaigns()):
        assert key in tables, f"gain_vs_voltage.csv has no rows for the {key} C campaign"
        _voltages, gains, errors = tables[key]
        assert np.all(gains > 0), f"{key} C: gains must be positive"
        assert np.all(errors > 0), f"{key} C: each gain needs a positive uncertainty"
        assert np.all(errors < gains), f"{key} C: gain uncertainties exceed the gains"


def _match_reference_points(table, expected):
    """Pair reported bias points with the reference's by voltage.

    A submission may justifiably exclude a bias point, so the comparison runs
    on the intersection rather than demanding the reference's exact ladder.
    """
    voltages, gains, _errors = table
    want_v = np.asarray(expected["voltages"], dtype=float)
    want_s = np.asarray(expected["spacings_adcns"], dtype=float)
    ref_idx, rep_idx = [], []
    for i, v in enumerate(want_v):
        hit = np.where(np.abs(voltages - v) < 1e-6)[0]
        if hit.size:
            ref_idx.append(i)
            rep_idx.append(int(hit[0]))
    return want_s[ref_idx], gains[rep_idx]


def test_normalized_gain_shape_per_campaign():
    """Scale-free check, independent of any ADC or amplifier normalisation."""
    tables = parse_gain_table()
    problems = []
    for key, expected in sorted(reference()["gains"].items()):
        if key not in tables:
            continue
        want, got = _match_reference_points(tables[key], expected)
        if len(got) < MIN_SHAPE_POINTS:
            problems.append(
                f"{key} C: only {len(got)} of the reference's "
                f"{len(expected['voltages'])} bias points are reported"
            )
            continue
        actual = got / got[-1]
        target = want / want[-1]
        if np.abs(actual - target).max() > NORMALIZED_SHAPE_ABS_TOL:
            problems.append(
                f"{key} C: normalized gains {np.round(actual, 4).tolist()} vs "
                f"{np.round(target, 4).tolist()}"
            )
    assert not problems, "the shape of the gain-versus-bias curve is wrong: " + "; ".join(problems)


def test_absolute_gain_scale_per_campaign():
    tables = parse_gain_table()
    problems = []
    for key, expected in sorted(reference()["gains"].items()):
        if key not in tables:
            continue
        want, gains = _match_reference_points(tables[key], expected)
        if len(gains) < MIN_SHAPE_POINTS:
            continue  # already reported by the shape test
        relative = np.abs(gains - want) / want
        if relative.max() > SPACING_SCALE_REL_TOL:
            problems.append(f"{key} C: {np.round(gains, 1).tolist()} vs {np.round(want, 1).tolist()}")
    assert not problems, (
        "absolute gains are off; they must be integrated pulse areas in ADC counts x ns: "
        + "; ".join(problems)
    )


def test_gain_is_linear_in_bias_per_campaign():
    problems = []
    for key, (voltages, gains, errors) in sorted(parse_gain_table().items()):
        if not np.all(np.diff(gains) > 0):
            problems.append(f"{key} C: gain is not monotonic in bias")
            continue
        design = np.vstack([voltages, np.ones_like(voltages)]).T
        weights = 1.0 / errors
        solution, *_ = np.linalg.lstsq(design * weights[:, None], gains * weights, rcond=None)
        residuals = (gains - design @ solution) / errors
        dof = max(len(voltages) - 2, 1)
        chi2 = float(np.sum(residuals**2) / dof)
        if chi2 > LINEARITY_MAX_CHI2_PER_DOF:
            problems.append(f"{key} C: chi2/dof = {chi2:.1f}")
    assert not problems, (
        "gains are not consistent with a straight line given the quoted uncertainties: "
        + "; ".join(problems)
    )


# ---------------------------------------------------------------------------
# Stage 8 — breakdown voltage per campaign, against the consensus reference
# ---------------------------------------------------------------------------


def test_breakdown_voltage_per_campaign():
    """Breakdown voltage at the campaign temperature, against the consensus.

    Central-value correctness only: each reported breakdown voltage must lie
    within the measured method systematic of legitimate analyses. The
    submission's stated uncertainty is printed for the record but plays no part
    in the verdict -- a biased central value is not rescued by a wide error bar
    (uncertainty quality is the rubric's job), and a correct one is not
    penalised for a tight one.
    """
    consensus = reference()["consensus"]["breakdown_voltage_v"]
    problems, deviations = [], []
    for key, row in sorted(parse_campaigns().items()):
        if key not in consensus:
            continue
        deviation = abs(row["breakdown_voltage_v"] - consensus[key])
        error = row["breakdown_voltage_err_v"]
        deviations.append((key, deviation, error))
        if deviation <= BREAKDOWN_TOL_V:
            continue
        problems.append(
            f"{key} C: {row['breakdown_voltage_v']:.3f} V against a consensus "
            f"{consensus[key]:.3f} V (off by {deviation:.3f} V; stated uncertainty "
            f"{error:.3f} V, not a factor in the verdict)"
        )

    # Reported, never asserted.
    worst = max((d for _, d, _ in deviations), default=float("nan"))
    within = all(d <= BREAKDOWN_PRECISION_TARGET_V for _, d, _ in deviations)
    print(
        f"[precision target] worst deviation {worst:.3f} V against the "
        f"{BREAKDOWN_PRECISION_TARGET_V} V target: {'met' if within else 'not met'}"
        + "".join(f"\n    {k} C: {d:.3f} V (stated err {e:.3f})" for k, d, e in deviations)
    )

    assert not problems, (
        f"breakdown voltage outside the {BREAKDOWN_TOL_V} V correctness band. The band is "
        f"the worst deviation of sixteen predeclared legitimate estimator/baseline "
        f"combinations from the consensus, so this is not a demand to match one recipe; "
        f"a central value beyond it has not recovered the calibration: "
        + "; ".join(problems)
    )


def test_breakdown_voltage_uncertainties_are_sane():
    """Bounded both ways: zero is not an uncertainty, and neither is a number
    larger than the whole method band -- a submission quoting one would turn
    the extended acceptance tier into a free pass rather than an honesty rule.
    """
    problems = [
        f"{key}: {row['breakdown_voltage_err_v']}"
        for key, row in sorted(parse_campaigns().items())
        if not 0.0 < row["breakdown_voltage_err_v"] <= BREAKDOWN_ERR_MAX_V
    ]
    assert not problems, f"implausible breakdown-voltage uncertainties: {problems}"


def test_spacing_slope_per_campaign():
    expected = {f"{c['campaign_setpoint_c']:.1f}": c for c in reference()["campaigns"]}
    problems = []
    for key, row in sorted(parse_campaigns().items()):
        if key not in expected:
            continue
        want = expected[key]["pipeline_spacing_slope_adcns_per_v"]
        if abs(row["spacing_slope_adcns_per_v"] - want) > SLOPE_REL_TOL * want:
            problems.append(
                f"{key} C: {row['spacing_slope_adcns_per_v']:.1f} vs {want:.1f}"
            )
    assert not problems, "charge-spacing slope out of tolerance: " + "; ".join(problems)


# ---------------------------------------------------------------------------
# Stage 9 — the temperature coefficient, and the two stages agreeing
# ---------------------------------------------------------------------------


def test_temperature_coefficient():
    reported = parse_result()["breakdown_voltage_temperature_coefficient_mv_per_k"]
    consensus = reference()["consensus"]["temperature_coefficient_mv_per_k"]
    spread = reference()["consensus"]["max_method_coefficient_deviation_mv_per_k"]
    assert abs(reported - consensus) <= COEFFICIENT_TOL_MV_PER_K, (
        f"temperature coefficient {reported:.2f} mV/K against a consensus "
        f"{consensus:.2f} mV/K; legitimate pipelines span {spread:.2f} mV/K "
        f"about that value"
    )


def test_coefficient_follows_from_the_reported_campaigns():
    """The headline number must be a fit to the agent's own first-stage results.

    Guards against a correct-looking coefficient that does not follow from the
    per-campaign numbers reported alongside it. Refitted by ordinary least
    squares; any sensible weighting of three points lands within the band.
    """
    campaigns = parse_campaigns()
    if len(campaigns) < 2:
        pytest.skip("fewer than two campaigns reported")
    temperatures = np.array([row["measured_temperature_mean_c"] for row in campaigns.values()])
    breakdowns = np.array([row["breakdown_voltage_v"] for row in campaigns.values()])
    implied = ols_slope(temperatures, breakdowns) * 1000.0
    reported = parse_result()["breakdown_voltage_temperature_coefficient_mv_per_k"]
    assert abs(implied - reported) <= COEFFICIENT_CONSISTENCY_TOL, (
        f"the reported coefficient ({reported:.2f} mV/K) does not follow from the "
        f"campaign table, which implies {implied:.2f} mV/K"
    )


def test_coefficient_uncertainty_is_sane():
    error = parse_result()["breakdown_voltage_temperature_coefficient_err_mv_per_k"]
    assert 0.0 < error < 100.0, (
        f"coefficient uncertainty {error} mV/K is not a credible error for this measurement"
    )


# ---------------------------------------------------------------------------
# Deliverable completeness
# ---------------------------------------------------------------------------


def test_paper_was_delivered():
    """The write-up exists and is a PDF.

    Deliberately minimal, and it stays that way on purpose. Whether the paper
    is any good -- whether it justifies the fit it extrapolated, whether it
    took temperatures from the log, whether its figures support what its text
    claims -- is the rubric's job. Asserting on extracted text here would grade
    formatting rather than physics, and would reward whichever LaTeX or
    matplotlib route happened to produce extractable strings. This only catches
    a deliverable that is missing, empty, or not actually a PDF.
    """
    path = ROOT / "paper.pdf"
    assert path.is_file(), "missing required artifact /root/paper.pdf"

    size = path.stat().st_size
    assert size > 1024, f"/root/paper.pdf is only {size} bytes; it holds no document"

    with path.open("rb") as handle:
        header = handle.read(5)
        handle.seek(max(0, size - 2048))
        trailer = handle.read()

    assert header == b"%PDF-", (
        f"/root/paper.pdf does not start with the PDF magic bytes (got {header!r}); "
        "the deliverable must be a PDF, not a renamed file of another format"
    )
    assert b"%%EOF" in trailer, (
        "/root/paper.pdf has no %%EOF marker near the end of the file; it looks "
        "truncated rather than finished"
    )
