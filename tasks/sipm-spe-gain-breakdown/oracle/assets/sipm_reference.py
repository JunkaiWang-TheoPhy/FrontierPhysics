"""Reference SiPM single-photoelectron gain calibration.

Deterministic, non-interactive refactor of the original cold-test analysis.
The scientific method is unchanged from the run that produced the published
calibration:

  merge the segments of a (bias, threshold) setting
    -> dual-window mean baseline subtraction
    -> 1st-order Butterworth low pass at 50 MHz (causal `lfilter`, as used
       originally)
    -> fixed-window pulse-area integration
    -> reject the trigger noise with an area region of interest
    -> Gaussian fit of the single-photoelectron peak, truncated above the peak
       so the cross-talk / 2-p.e. shoulder does not pull the mean
    -> gain(V) = mean over DAQ thresholds, uncertainty = half spread
    -> weighted straight-line fit, breakdown voltage = x-intercept

Areas are reported in ADC counts x ns. No ADC-to-volt conversion is applied
anywhere: the analog chain in front of the digitizer was never calibrated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.optimize import curve_fit
from scipy.signal import butter, lfilter

# ---------------------------------------------------------------------------
# CAEN DT5720 standard firmware event format
# ---------------------------------------------------------------------------

HEADER_WORDS = 4
SAMPLES_PER_CHANNEL = 1024
SAMPLES_PER_WORD = 2
HEADER_MARKER = 0xA
TIME_TAG_MASK = 0x7FFFFFFF
NS_PER_SAMPLE = 4.0  # DT5720 at 250 MS/s

FILENAME_PATTERN = re.compile(
    r"sipm_group(?P<group>\d+)"
    r"_threshold(?P<threshold>\d+)"
    r"_(?P<temperature>-?\d+\.\d+)C"
    r"_(?P<voltage>\d+\.\d+)V"
    r"_(?P<nominal_events>\d+)"
    r"_(?P<channels>\d+)"
    r"_raw_b\d+_seg(?P<segment>\d+)"
    r"_(?P<timestamp>\d{8}T\d{6})\.bin$"
)

# ---------------------------------------------------------------------------
# Analysis constants
#
# The area selections below were fixed when the original analysis was tuned on
# this dataset. They were originally written in volt-nanoseconds assuming a
# 1/4096 V per count scale; the values here are the identical selections
# restated in ADC counts x ns. They are selection windows, not a calibration.
# ---------------------------------------------------------------------------

BASELINE_FRONT = (0.2, 0.4)  # fractions of the record
BASELINE_BACK = (0.6, 0.8)
INTEGRATION_WINDOW = (0.4, 0.6)
FILTER_CUTOFF_HZ = 50e6
SAMPLING_RATE_HZ = 250e6
FILTER_ORDER = 1

NOISE_REJECT_ROI = (1228.8, 7372.8)  # ADC counts x ns
SPE_MEAN_BOUNDS = (819.2, 6144.0)
SPE_SIGMA_BOUNDS = (49.152, 1638.4)
SPE_FIT_UPPER_FRACTION = 1.1  # fit only below 1.1 x median
HISTOGRAM_BINS = 150


@dataclass(frozen=True)
class RunFile:
    path: Path
    group: int
    threshold: int
    temperature: float
    voltage: float
    nominal_events: int
    segment: int
    timestamp: datetime

    @property
    def name(self) -> str:
        return self.path.name


def parse_run_file(path: Path) -> RunFile | None:
    """Return acquisition settings encoded in a file name, or None."""
    match = FILENAME_PATTERN.match(path.name)
    if match is None:
        return None
    return RunFile(
        path=path,
        group=int(match["group"]),
        threshold=int(match["threshold"]),
        temperature=float(match["temperature"]),
        voltage=float(match["voltage"]),
        nominal_events=int(match["nominal_events"]),
        segment=int(match["segment"]),
        timestamp=datetime.strptime(match["timestamp"], "%Y%m%dT%H%M%S"),
    )


def index_run_files(data_dir: Path) -> list[RunFile]:
    files = [parse_run_file(path) for path in sorted(Path(data_dir).iterdir())]
    return [entry for entry in files if entry is not None]


# ---------------------------------------------------------------------------
# Decoding
# ---------------------------------------------------------------------------


def read_events(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decode one DT5720 binary file.

    Returns ``(samples, event_counters, trigger_time_tags)`` where ``samples``
    has shape ``(n_events, n_channels, n_samples)`` in raw ADC counts.

    The event count is taken from the file itself. The value encoded in the
    file name is the requested acquisition length and does not match what was
    written; trusting it silently discards whole files.
    """
    raw = np.fromfile(path, dtype="<u4")
    if raw.size < HEADER_WORDS:
        raise ValueError(f"{path.name}: file is shorter than one event header")

    first = int(raw[0])
    if (first >> 28) != HEADER_MARKER:
        raise ValueError(f"{path.name}: missing 0xA event-header marker")

    record_words = first & 0x0FFFFFFF
    channel_mask = int(raw[1])
    n_channels = bin(channel_mask).count("1")
    payload_words = record_words - HEADER_WORDS
    n_samples = payload_words * SAMPLES_PER_WORD // n_channels

    n_events = raw.size // record_words
    if n_events == 0:
        raise ValueError(f"{path.name}: no complete event in file")

    records = raw[: n_events * record_words].reshape(n_events, record_words)

    markers = records[:, 0] >> 28
    if not np.all(markers == HEADER_MARKER):
        raise ValueError(f"{path.name}: event-header marker lost mid-file")
    if not np.all((records[:, 0] & 0x0FFFFFFF) == record_words):
        raise ValueError(f"{path.name}: event size is not constant")

    # Pack2 mode: each 32-bit word holds two 12-bit samples right-aligned in
    # 16-bit halves, the EARLIER sample in the low half (UM3244 Fig. 8.4).
    # Reading the high half first transposes every adjacent pair. That leaves
    # sums, minima and maxima untouched — which is why it survives a careless
    # check — but it puts a 2-sample zig-zag on the rising edge of the pulse.
    payload = records[:, HEADER_WORDS:].ravel()
    samples = np.empty(payload.size * SAMPLES_PER_WORD, dtype=np.float64)
    samples[0::2] = payload & 0xFFFF
    samples[1::2] = payload >> 16

    return (
        samples.reshape(n_events, n_channels, n_samples),
        records[:, 2].astype(np.int64),
        (records[:, 3] & TIME_TAG_MASK).astype(np.int64),
    )


def load_channel(paths: list[Path], channel: int) -> np.ndarray:
    """Merge one channel across acquisition segments."""
    return np.vstack([read_events(path)[0][:, channel - 1, :] for path in paths])


# ---------------------------------------------------------------------------
# Waveform processing
# ---------------------------------------------------------------------------


def subtract_baseline(waveforms: np.ndarray) -> np.ndarray:
    """Mean baseline from two windows flanking the pulse region."""
    length = waveforms.shape[1]
    front = waveforms[
        :, int(length * BASELINE_FRONT[0]) : int(length * BASELINE_FRONT[1])
    ].mean(axis=1)
    back = waveforms[
        :, int(length * BASELINE_BACK[0]) : int(length * BASELINE_BACK[1])
    ].mean(axis=1)
    return waveforms - ((front + back) / 2.0)[:, None]


def low_pass(waveforms: np.ndarray) -> np.ndarray:
    numerator, denominator = butter(
        FILTER_ORDER,
        FILTER_CUTOFF_HZ / (0.5 * SAMPLING_RATE_HZ),
        btype="low",
        analog=False,
    )
    return lfilter(numerator, denominator, waveforms, axis=-1)


def pulse_areas(waveforms: np.ndarray) -> np.ndarray:
    """Integrated pulse area per event, in ADC counts x ns."""
    processed = low_pass(subtract_baseline(waveforms))
    length = processed.shape[1]
    start = int(length * INTEGRATION_WINDOW[0])
    stop = int(length * INTEGRATION_WINDOW[1])
    return processed[:, start:stop].sum(axis=1) * NS_PER_SAMPLE


def average_waveform(waveforms: np.ndarray) -> np.ndarray:
    """Event-averaged baseline-subtracted waveform, in ADC counts."""
    return subtract_baseline(waveforms).mean(axis=0)


def baseline_level(waveforms: np.ndarray) -> float:
    """Mean raw baseline level of a set of waveforms, in ADC counts.

    The DC level each channel sits at. It is set by the readout, not by the
    photon signal, so it is the same for any sensible choice of baseline
    window and it identifies which channel was analysed.
    """
    length = waveforms.shape[1]
    front = waveforms[
        :, int(length * BASELINE_FRONT[0]) : int(length * BASELINE_FRONT[1])
    ].mean(axis=1)
    back = waveforms[
        :, int(length * BASELINE_BACK[0]) : int(length * BASELINE_BACK[1])
    ].mean(axis=1)
    return float(((front + back) / 2.0).mean())


# ---------------------------------------------------------------------------
# Single-photoelectron extraction
# ---------------------------------------------------------------------------


def gaussian(x, amplitude, mean, sigma):
    return amplitude * np.exp(-0.5 * ((x - mean) / sigma) ** 2)


def linear_with_intercept(voltage, slope, breakdown_voltage):
    return slope * (voltage - breakdown_voltage)


@dataclass(frozen=True)
class BreakdownFit:
    slope: float
    slope_err: float
    breakdown_voltage: float
    breakdown_voltage_err: float
    chi2: float
    dof: int


def fit_breakdown(
    voltages: np.ndarray, gains: np.ndarray, gain_errors: np.ndarray
) -> BreakdownFit:
    # `absolute_sigma` is left at the SciPy default, matching the original
    # analysis: the quoted parameter errors are rescaled by the reduced chi2.
    popt, pcov = curve_fit(
        linear_with_intercept,
        voltages,
        gains,
        sigma=gain_errors,
        maxfev=5000,
    )
    perr = np.sqrt(np.diag(pcov))
    residuals = (gains - linear_with_intercept(voltages, *popt)) / gain_errors
    return BreakdownFit(
        slope=float(popt[0]),
        slope_err=float(perr[0]),
        breakdown_voltage=float(popt[1]),
        breakdown_voltage_err=float(perr[1]),
        chi2=float(np.sum(residuals**2)),
        dof=int(len(voltages) - len(popt)),
    )


def combine_thresholds(means: list[float]) -> tuple[float, float]:
    """Gain and its systematic uncertainty from repeats at different thresholds.

    The DAQ threshold must not change the physical gain, so the spread across
    threshold settings is the uncertainty estimate.
    """
    values = np.asarray(means, dtype=float)
    return float(values.mean()), float((values.max() - values.min()) / 2.0)


# ---------------------------------------------------------------------------
# Temperature
# ---------------------------------------------------------------------------


def read_temperature_log(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (epoch seconds, temperature) sorted by time.

    Sorting matters: the interpolation below requires monotonic sample times.
    """
    times: list[float] = []
    values: list[float] = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        stamp, _index, temperature = line.split(",")
        times.append(datetime.fromisoformat(stamp.strip()).timestamp())
        values.append(float(temperature))
    order = np.argsort(np.asarray(times))
    return np.asarray(times)[order], np.asarray(values)[order]


def temperature_statistics(
    log_times: np.ndarray, log_values: np.ndarray, moments: list[datetime]
) -> tuple[float, float]:
    """Mean and standard deviation of the logged readings over the acquisition.

    The window runs from the earliest to the latest acquisition timestamp, and
    every logged reading inside it is used. "Spread" has no unique definition,
    so the deliverable asks for the standard deviation specifically; note that
    it is insensitive to whether the log is sampled at its own cadence or
    interpolated onto the acquisition timestamps (0.4043 vs 0.4039 here), while
    the mean does depend on that choice at the 0.08 C level.
    """
    stamps = [moment.timestamp() for moment in moments]
    inside = (log_times >= min(stamps)) & (log_times <= max(stamps))
    readings = log_values[inside]
    if readings.size == 0:
        raise ValueError("temperature log does not cover the acquisition window")
    return float(readings.mean()), float(readings.std())


# ---------------------------------------------------------------------------
# Robust treatment of non-ideal acquisitions
#
# Everything below is derived from the delivered waveforms alone. Nothing here
# consults any record of how the data was produced; if it did, this would stop
# being a meaningful reference for what an analyst can achieve.
# ---------------------------------------------------------------------------

BASELINE_SUPPORT = np.r_[np.arange(120, 409), np.arange(614, 900)]
_SUPPORT_DESIGN = np.vstack(
    [
        np.ones_like(BASELINE_SUPPORT, dtype=float),
        BASELINE_SUPPORT - 511.0,
        (BASELINE_SUPPORT - 511.0) ** 2,
    ]
).T
_SUPPORT_PINV = np.linalg.pinv(_SUPPORT_DESIGN)
_GATE_INDEX = np.arange(409, 614)
_GATE_DESIGN = np.vstack(
    [
        np.ones_like(_GATE_INDEX, dtype=float),
        _GATE_INDEX - 511.0,
        (_GATE_INDEX - 511.0) ** 2,
    ]
).T


def _baseline_coefficients(waveforms: np.ndarray) -> np.ndarray:
    """Per-event quadratic baseline fitted to the regions flanking the pulse."""
    return _SUPPORT_PINV @ waveforms[:, BASELINE_SUPPORT].T


def robust_pulse_areas(waveforms: np.ndarray) -> np.ndarray:
    """Pulse area with a per-event curved baseline removed, in ADC counts x ns.

    A single constant, or the mean of two symmetric windows, is only adequate
    while the baseline is flat. The two-window mean happens to cancel a linear
    tilt exactly -- its centroid coincides with the gate centroid -- but it does
    not cancel curvature, which then feeds straight into the area.
    """
    coefficients = _baseline_coefficients(waveforms)
    corrected = waveforms[:, 409:614] - (_GATE_DESIGN @ coefficients).T
    return low_pass(corrected).sum(axis=1) * NS_PER_SAMPLE


# ---------------------------------------------------------------------------
# Campaign structure and hierarchical calibration
# ---------------------------------------------------------------------------

MIN_BIAS_POINTS_FOR_CALIBRATION = 3
MIN_THRESHOLDS_PER_BIAS_POINT = 2
# A threshold has to have been carried across a fair part of the bias ladder to
# count as one of the campaign's repeat conditions. One-off settings taken at a
# single bias point are not repeats of anything: they cannot be compared against
# the rest of the ladder, and averaging them into one point tilts that point
# relative to its neighbours.
MIN_LADDER_COVERAGE = 0.5


def group_by_campaign(run_files: list[RunFile]) -> dict[float, list[RunFile]]:
    campaigns: dict[float, list[RunFile]] = {}
    for entry in run_files:
        campaigns.setdefault(entry.temperature, []).append(entry)
    return campaigns


def usable_bias_points(entries: list[RunFile]) -> dict[float, dict[int, list[RunFile]]]:
    """Bias points of a campaign that carry enough repeats to be fitted.

    A bias point needs more than one threshold setting behind it: with a single
    setting there is nothing to compare it against and no handle on how much the
    acquisition condition moved the answer.
    """
    ladder: dict[float, dict[int, list[RunFile]]] = {}
    for entry in entries:
        ladder.setdefault(entry.voltage, {}).setdefault(entry.threshold, []).append(entry)

    coverage: dict[int, int] = {}
    for thresholds in ladder.values():
        for threshold in thresholds:
            coverage[threshold] = coverage.get(threshold, 0) + 1
    carried = {
        threshold
        for threshold, count in coverage.items()
        if count >= MIN_LADDER_COVERAGE * len(ladder)
    }

    trimmed = {
        voltage: {t: files for t, files in thresholds.items() if t in carried}
        for voltage, thresholds in ladder.items()
    }
    return {
        voltage: thresholds
        for voltage, thresholds in trimmed.items()
        if len(thresholds) >= MIN_THRESHOLDS_PER_BIAS_POINT
    }


def is_calibratable(entries: list[RunFile]) -> bool:
    """Whether a campaign can yield a breakdown voltage on its own.

    Breakdown voltage is an extrapolation of gain against bias to zero gain, so
    it needs a bias ladder. A campaign parked at a single operating point can be
    perfectly good data and still not support this measurement.
    """
    return len(usable_bias_points(entries)) >= MIN_BIAS_POINTS_FOR_CALIBRATION


def campaign_temperature(
    log_times: np.ndarray, log_values: np.ndarray, entries: list[RunFile]
) -> tuple[float, float]:
    """Mean and standard deviation of the log over a campaign's own window.

    The window is spanned by every delivered file of the campaign, so the number
    does not move when a later analysis decides to use only some of them.
    """
    stamps = [entry.timestamp for entry in entries]
    return temperature_statistics(log_times, log_values, stamps)


# ---------------------------------------------------------------------------
# Temperature-drift correction of the per-campaign extrapolation
#
# Within every campaign the bias ladder was stepped upward while the cryostat
# was still drifting, so bias and sensor temperature are strongly correlated
# (corr = 0.99-1.00, dT/dV = 0.2-0.26 K/V on this data). A fit of separation
# against bias alone therefore absorbs part of dQ/dT into dQ/dV and biases the
# extrapolated intercept: with dV_bd/dT ~ 48 mV/K and ~8.5 V of over-voltage,
# the naive intercept sits ~0.10 V low in every campaign.
#
# The task asks for the breakdown voltage AT the campaign's measured
# temperature. That is the intercept of the separation against a bias corrected
# to the campaign mean temperature,
#
#     X_i = V_i - beta * (T_i - T_campaign),
#
# where beta = dV_bd/dT is the very quantity the second stage measures. Within
# one campaign beta is nearly collinear with the slope (design condition ~30-50),
# so it has to be constrained by the cross-campaign fit and fed back; the two
# stages are iterated to self-consistency. It converges in a few passes because
# the correction is nearly uniform across campaigns and barely moves beta.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CampaignLadder:
    """One campaign's per-bias-point measurements, ready to extrapolate."""

    setpoint: float
    voltages: np.ndarray
    separations: np.ndarray
    errors: np.ndarray
    point_temperatures: np.ndarray  # measured over each bias point's own acquisitions
    campaign_temperature: float     # measured over the whole campaign window


def drift_corrected_bias(ladder: CampaignLadder, beta_v_per_k: float) -> np.ndarray:
    """Bias corrected to the campaign mean temperature for a given dV_bd/dT."""
    return ladder.voltages - beta_v_per_k * (
        ladder.point_temperatures - ladder.campaign_temperature
    )


def calibrate_hierarchically(
    ladders: list[CampaignLadder],
    max_iterations: int = 20,
    tolerance_v_per_k: float = 1e-5,
) -> tuple[dict[float, BreakdownFit], float, float, float, int]:
    """Per-campaign breakdown voltages and dV_bd/dT, iterated to self-consistency.

    Returns (fits by setpoint, coefficient mV/K, coefficient error mV/K,
    second-stage chi2, iterations used).
    """
    beta = 0.0
    for iteration in range(1, max_iterations + 1):
        fits = {
            ladder.setpoint: fit_breakdown(
                drift_corrected_bias(ladder, beta), ladder.separations, ladder.errors
            )
            for ladder in ladders
        }
        temps = np.array([ladder.campaign_temperature for ladder in ladders])
        vbds = np.array([fits[ladder.setpoint].breakdown_voltage for ladder in ladders])
        errs = np.array(
            [max(fits[ladder.setpoint].breakdown_voltage_err, 1e-3) for ladder in ladders]
        )
        coefficient, coefficient_err, chi2 = temperature_coefficient(temps, vbds, errs)
        new_beta = coefficient / 1000.0
        if abs(new_beta - beta) < tolerance_v_per_k:
            return fits, coefficient, coefficient_err, chi2, iteration
        beta = new_beta
    return fits, coefficient, coefficient_err, chi2, max_iterations


def temperature_coefficient(
    temperatures: np.ndarray, breakdowns: np.ndarray, errors: np.ndarray
) -> tuple[float, float, float]:
    """Slope of breakdown voltage against temperature, in mV/K, with its error."""
    design = np.vstack([temperatures, np.ones_like(temperatures)]).T
    weights = 1.0 / errors
    solution, *_ = np.linalg.lstsq(design * weights[:, None], breakdowns * weights, rcond=None)
    residuals = (breakdowns - design @ solution) / errors
    covariance = np.linalg.inv((design * weights[:, None]).T @ (design * weights[:, None]))
    dof = max(len(temperatures) - 2, 1)
    scale = float(np.sum(residuals**2) / dof)
    slope_err = float(np.sqrt(covariance[0, 0] * max(scale, 1.0)))
    return float(solution[0]) * 1000.0, slope_err * 1000.0, float(np.sum(residuals**2))


# ---------------------------------------------------------------------------
# The measured observable
#
# G_SPE is the charge separation between the resolved noise and
# first-photoelectron populations of the integrated-charge spectrum, in
# ADC counts x ns:
#
#     G_SPE = mu_1PE - mu_noise
#
# This is a separation, not an absolute peak position. The two coincide only if
# the noise sits exactly at zero charge, which it does not: residual baseline
# and gate conventions leave it tens of ADC counts x ns away, and extrapolating
# the gain line 6-11 V below the measured bias range turns that into ~0.1 V on
# the breakdown voltage. No intrinsic electron gain is claimed; the analog chain
# was never calibrated.
#
# How the two populations are located is an analysis choice, not part of the
# definition. What is not optional is using populations that are actually
# resolved -- see `resolved_orders`.
# ---------------------------------------------------------------------------
def _hist(a, lo=None, hi=None, nb=260):
    if lo is None:
        lo, hi = np.percentile(a, [0.3, 99.7])
    counts, edges = np.histogram(a, bins=np.linspace(lo, hi, nb))
    return counts, (edges[:-1] + edges[1:]) / 2


def find_peaks(a):
    """Locate the noise and the first photoelectron peak in a charge spectrum."""
    counts, centres = _hist(a)
    smoothed = uniform_filter1d(counts.astype(float), 3)
    noise = centres[int(np.argmax(smoothed))]
    far = centres > noise + 0.25 * (centres[-1] - noise)
    if far.sum() < 8:
        raise ValueError("no 1PE candidate")
    one = centres[far][int(np.argmax(smoothed[far]))]
    spacing = one - noise
    if spacing <= 0:
        raise ValueError("bad spacing")
    return noise, one, spacing


def _local_center(a, centre, spacing, frac=0.30):
    """Gaussian core plus a linear background, fitted in a window around a peak."""
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
    return params[1]


# --- method 1: noise-to-1PE two-population spacing -----------------------
def spacing_two_population(a):
    noise, one, spacing = find_peaks(a)
    return _local_center(a, one, spacing) - _local_center(a, noise, spacing)


MIN_PEAK_EVENTS = 150          # a population must be populated enough to locate
MIN_PEAK_FRACTION = 0.05       # ...and not negligible against the one-PE peak


def resolved_orders(a, ped, sp, orders=(0, 1, 2, 3)):
    """Which photoelectron populations are actually resolved in this spectrum.

    At these light levels the two-photoelectron peak often carries a few tens of
    events against a thousand in the noise. Fitting a centre to it, or
    letting it drive a common spacing, imports a large error while looking like
    extra information, so an order has to earn its place first.
    """
    ref = int(((a > ped + sp - 0.28 * sp) & (a < ped + sp + 0.28 * sp)).sum())
    keep = []
    for n in orders:
        c = ped + n * sp
        count = int(((a > c - 0.28 * sp) & (a < c + 0.28 * sp)).sum())
        if count >= MIN_PEAK_EVENTS and count >= MIN_PEAK_FRACTION * max(ref, 1):
            keep.append(n)
    return keep


# --- method 2: constrained integer-spaced multi-peak fit --------------------
def spacing_integer_constrained(a):
    noise, _one, spacing = find_peaks(a)
    keep = resolved_orders(a, noise, spacing)

    if 2 not in keep:
        # Only noise and one-PE are resolved: fit those two simultaneously
        # with a shared spacing rather than inventing a third component.
        counts, centres = _hist(a, noise - 0.5 * spacing, noise + 1.6 * spacing, 160)

        def two_peaks(x, a0, s0, a1, s1, mu0, separation):
            return gaussian(x, a0, mu0, s0) + gaussian(x, a1, mu0 + separation, s1)

        params, _ = curve_fit(
            two_peaks,
            centres,
            counts,
            p0=[counts.max(), 0.12 * spacing, counts.max() * 0.4, 0.12 * spacing, noise, spacing],
            bounds=(
                [0, 0.02 * spacing, 0, 0.02 * spacing, noise - 0.4 * spacing, 0.6 * spacing],
                [np.inf, 0.6 * spacing, np.inf, 0.6 * spacing, noise + 0.4 * spacing, 1.5 * spacing],
            ),
            sigma=np.sqrt(np.maximum(counts, 1.0)),
            maxfev=60000,
        )
        return float(params[5])

    counts, centres = _hist(a, noise - 0.5 * spacing, noise + 2.8 * spacing, 200)

    def three_peaks(x, a0, s0, a1, s1, a2, s2, mu0, separation):
        return (
            gaussian(x, a0, mu0, s0)
            + gaussian(x, a1, mu0 + separation, s1)
            + gaussian(x, a2, mu0 + 2 * separation, s2)
        )

    params, _ = curve_fit(
        three_peaks,
        centres,
        counts,
        p0=[
            counts.max(), 0.12 * spacing,
            counts.max() * 0.4, 0.12 * spacing,
            counts.max() * 0.05, 0.14 * spacing,
            noise, spacing,
        ],
        bounds=(
            [0, 0.02 * spacing, 0, 0.02 * spacing, 0, 0.02 * spacing, noise - 0.4 * spacing, 0.6 * spacing],
            [np.inf, 0.6 * spacing, np.inf, 0.6 * spacing, np.inf, 0.8 * spacing, noise + 0.4 * spacing, 1.5 * spacing],
        ),
        sigma=np.sqrt(np.maximum(counts, 1.0)),
        maxfev=60000,
    )
    return float(params[7])


# --- method 3: regression of peak centres against PE index ------------------
def spacing_peak_regression(a):
    noise, _one, spacing = find_peaks(a)
    orders, centres = [], []
    for n in resolved_orders(a, noise, spacing):
        expected = noise + n * spacing
        try:
            centre = _local_center(a, expected, spacing, frac=0.28)
        except Exception:
            continue
        if abs(centre - expected) < 0.45 * spacing:
            orders.append(n)
            centres.append(centre)
    if len(orders) < 2:
        raise ValueError("too few resolved peaks")
    design = np.vstack([np.array(orders, float), np.ones(len(orders))]).T
    solution, *_ = np.linalg.lstsq(design, np.array(centres), rcond=None)
    return float(solution[0])


def peak_width(a) -> float:
    """Gaussian core width of the one-photoelectron population, in ADC counts x ns."""
    _noise, one, sp = find_peaks(a)
    lo, hi = one - 0.30 * sp, one + 0.30 * sp
    h, bc = _hist(a, lo, hi, 60)

    def model(x, A, mu, s, c0, c1):
        return gaussian(x, A, mu, s) + np.maximum(c0 + c1 * (x - one), 0)

    p, _ = curve_fit(
        model, bc, h, p0=[max(h.max(), 1), one, 0.12 * sp, 0.0, 0.0], maxfev=40000
    )
    return float(abs(p[2]))
