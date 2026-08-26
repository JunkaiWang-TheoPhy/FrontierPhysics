"""An independent SPE gain calibration, used only to guard the reference values.

This is a second implementation of the physics, written to disagree with the
oracle wherever the choice is free:

  * the baseline shape traced through means of six short pulse-free blocks
    and a quadratic through those anchors, not a least-squares fit over every
    sample of two long stretches
  * no filtering at all
  * a wider, differently placed integration window
  * coherent interference found by the peak of the event-averaged residual,
    not by its spread, and removed rather than used to reject the acquisition
  * the charge separation obtained from a simultaneous two-population fit with
    the separation as a free parameter, rather than locating each peak in turn

If both implementations land on the same breakdown voltage, that number is a
property of the data rather than of either recipe. The verifier grades agents
against frozen constants and uses this module to detect the constants going
stale.

Deliberately does not import anything from the oracle.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.optimize import curve_fit
from scipy.signal import find_peaks

NS_PER_SAMPLE = 4.0
BASELINE_SLICE = slice(50, 400)
INTEGRATION_SLICE = slice(405, 620)

SEED_BINS = 60  # coarse enough that Poisson bumps do not look like peaks
SPECTRUM_BINS = 300

NAME_PATTERN = re.compile(
    r"sipm_group\d+_threshold(?P<threshold>\d+)_(?P<campaign>-?\d+\.\d+)C"
    r"_(?P<voltage>\d+\.\d+)V_\d+_\d+_raw_b\d+_seg(?P<segment>\d+)"
    r"_(?P<stamp>\d{8}T\d{6})\.bin$"
)

HEADER_WORDS = 4


def decode_channel(path: Path, channel: int) -> np.ndarray:
    """Raw ADC samples of one channel, shape (n_events, n_samples)."""
    raw = np.fromfile(path, dtype="<u4")
    record_words = int(raw[0]) & 0x0FFFFFFF
    n_channels = bin(int(raw[1])).count("1")
    n_events = raw.size // record_words
    records = raw[: n_events * record_words].reshape(n_events, record_words)

    payload = records[:, HEADER_WORDS:].ravel()
    samples = np.empty(payload.size * 2, dtype=np.float64)
    samples[0::2] = payload & 0xFFFF  # earlier sample is the low half
    samples[1::2] = payload >> 16
    n_samples = (record_words - HEADER_WORDS) * 2 // n_channels
    return samples.reshape(n_events, n_channels, n_samples)[:, channel - 1, :]


# Pulse-free sub-windows used to trace the baseline shape. Deliberately a
# different construction from the oracle's: medians of six short blocks with a
# quadratic through them, rather than a least-squares fit over every sample of
# two long stretches. Same physics, independent arithmetic.
_BLOCKS = [(130, 190), (220, 290), (320, 395), (630, 700), (730, 800), (830, 895)]
_BLOCK_CENTRES = np.array([(a + b - 1) / 2.0 for a, b in _BLOCKS])
_BLOCK_DESIGN = np.vstack(
    [np.ones_like(_BLOCK_CENTRES), _BLOCK_CENTRES - 511.0, (_BLOCK_CENTRES - 511.0) ** 2]
).T
_BLOCK_PINV = np.linalg.pinv(_BLOCK_DESIGN)
_GATE = np.arange(INTEGRATION_SLICE.start, INTEGRATION_SLICE.stop)
_GATE_DESIGN = np.vstack(
    [np.ones_like(_GATE, dtype=float), _GATE - 511.0, (_GATE - 511.0) ** 2]
).T


def _baseline_coefficients(waveforms: np.ndarray) -> np.ndarray:
    # Block means, not medians: the samples are 12-bit integers with a baseline
    # spread of a couple of counts, so a median snaps onto integer steps and
    # injects a systematic offset that the gate then multiplies up.
    anchors = np.vstack([waveforms[:, a:b].mean(axis=1) for a, b in _BLOCKS])
    return _BLOCK_PINV @ anchors


def areas(waveforms: np.ndarray) -> np.ndarray:
    coefficients = _baseline_coefficients(waveforms)
    corrected = waveforms[:, INTEGRATION_SLICE] - (_GATE_DESIGN @ coefficients).T
    return corrected.sum(axis=1) * NS_PER_SAMPLE


_QUIET = np.hstack([np.arange(a, b) for a, b in _BLOCKS])
_QUIET_DESIGN = np.vstack(
    [np.ones_like(_QUIET, dtype=float), _QUIET - 511.0, (_QUIET - 511.0) ** 2]
).T
_QUIET_PINV = np.linalg.pinv(_QUIET_DESIGN)
_SEARCH = (0.004, 0.12)
_MIN_COHERENT_PEAK = 1.2  # ADC counts, peak of the event-averaged residual


def _coherent_residual(waveforms: np.ndarray) -> np.ndarray:
    coefficients = _QUIET_PINV @ waveforms[:, _QUIET].T
    residual = waveforms[:, _QUIET] - (_QUIET_DESIGN @ coefficients).T
    averaged = residual.mean(axis=0)
    return averaged - averaged.mean()


def disturbance(waveforms: np.ndarray) -> float:
    """Peak excursion of the event-averaged pulse-free residual, in ADC counts.

    Averaging is what does the work: anything phase locked to the trigger keeps
    its amplitude, while uncorrelated noise falls away as 1/sqrt(N). Peak rather
    than spread, so this is a different summary from the oracle's.
    """
    return float(np.max(np.abs(_coherent_residual(waveforms))))


def interference_frequency(waveforms: np.ndarray) -> float | None:
    """Frequency of the coherent tone, or None if the acquisition looks quiet."""
    averaged = _coherent_residual(waveforms)
    if float(np.max(np.abs(averaged))) < _MIN_COHERENT_PEAK:
        return None
    index = _QUIET.astype(float)
    grid = np.linspace(_SEARCH[0], _SEARCH[1], 6000)
    angle = 2.0 * np.pi * np.outer(grid, index)
    power = (np.cos(angle) @ averaged) ** 2 + (np.sin(angle) @ averaged) ** 2
    coarse = float(grid[int(np.argmax(power))])
    step = float(grid[1] - grid[0])
    fine = np.linspace(coarse - step, coarse + step, 401)
    angle = 2.0 * np.pi * np.outer(fine, index)
    power = (np.cos(angle) @ averaged) ** 2 + (np.sin(angle) @ averaged) ** 2
    return float(fine[int(np.argmax(power))])


def remove_interference(waveforms: np.ndarray, frequency: float) -> np.ndarray:
    design = np.vstack(
        [
            np.sin(2.0 * np.pi * frequency * _QUIET),
            np.cos(2.0 * np.pi * frequency * _QUIET),
            np.ones_like(_QUIET, dtype=float),
            _QUIET - 511.0,
            (_QUIET - 511.0) ** 2,
        ]
    ).T
    coefficients = np.linalg.pinv(design) @ waveforms[:, _QUIET].T
    full = np.arange(waveforms.shape[1], dtype=float)
    tone = np.outer(coefficients[0], np.sin(2.0 * np.pi * frequency * full)) + np.outer(
        coefficients[1], np.cos(2.0 * np.pi * frequency * full)
    )
    return waveforms - tone


def _gaussian(x, amplitude, mean, sigma):
    return amplitude * np.exp(-0.5 * ((x - mean) / sigma) ** 2)


def _two_population(x, a0, mu0, s0, a1, spacing, s1):
    """Noise and one-photoelectron populations sharing one separation."""
    return _gaussian(x, a0, mu0, s0) + _gaussian(x, a1, mu0 + spacing, s1)


def spe_charge_spacing(area: np.ndarray) -> tuple[float, float]:
    """Charge separation between the noise and one-photoelectron populations.

    Fitted simultaneously with the separation as a free parameter, rather than
    locating the two peaks one at a time. Only populations that are actually
    resolved are used: at these light levels the two-photoelectron peak carries
    a few tens of events and cannot locate anything.
    """
    lower = float(np.quantile(area, 0.001))
    upper = float(np.quantile(area, 0.995))

    # Locate the two populations on a coarse histogram and fit on a fine one.
    # A few thousand events spread over fine bins leaves the noise flank
    # covered in Poisson bumps, and a peak finder run there seeds on noise.
    coarse, edges = np.histogram(area, bins=SEED_BINS, range=(lower, upper))
    coarse_centres = (edges[:-1] + edges[1:]) / 2.0
    smoothed = uniform_filter1d(coarse.astype(float), 3)
    peaks, _ = find_peaks(smoothed, prominence=0.05 * smoothed.max(), distance=2)
    if len(peaks) < 2:
        raise ValueError("one-photoelectron population not resolved")
    top = int(peaks[np.argmax(smoothed[peaks])])
    after = peaks > top
    if not after.any():
        raise ValueError("one-photoelectron population not resolved")
    noise = float(coarse_centres[top])
    guess = float(coarse_centres[int(peaks[after][0])]) - noise
    if guess <= 0:
        raise ValueError("degenerate spectrum")

    counts, edges = np.histogram(area, bins=SPECTRUM_BINS, range=(lower, upper))
    centres = (edges[:-1] + edges[1:]) / 2.0
    window = (centres > noise - 0.5 * guess) & (centres < noise + 1.7 * guess)
    x, y = centres[window], counts[window].astype(float)
    popt, _ = curve_fit(
        _two_population,
        x,
        y,
        p0=[y.max(), noise, 0.12 * guess, 0.4 * y.max(), guess, 0.12 * guess],
        bounds=(
            [0.0, noise - 0.4 * guess, 0.02 * guess, 0.0, 0.6 * guess, 0.02 * guess],
            [np.inf, noise + 0.4 * guess, 0.7 * guess, np.inf, 1.5 * guess, 0.7 * guess],
        ),
        sigma=np.sqrt(np.maximum(y, 1.0)),
        maxfev=60000,
    )
    return float(popt[4]), float(abs(popt[5]))


def _linear(voltage, slope, breakdown):
    return slope * (voltage - breakdown)


def calibrate(data_dir: Path, channel: int = 3, logs_dir: Path | None = None) -> dict:
    """Independent hierarchical calibration over every delivered campaign."""
    from datetime import datetime

    grouped: dict[float, dict[tuple[float, int], list[Path]]] = {}
    stamps: dict[float, list[datetime]] = {}
    point_stamps: dict[tuple[float, float], list[datetime]] = {}
    for path in sorted(Path(data_dir).iterdir()):
        match = NAME_PATTERN.match(path.name)
        if match is None:
            continue
        setpoint = float(match["campaign"])
        key = (float(match["voltage"]), int(match["threshold"]))
        grouped.setdefault(setpoint, {}).setdefault(key, []).append(path)
        moment = datetime.strptime(match["stamp"], "%Y%m%dT%H%M%S")
        stamps.setdefault(setpoint, []).append(moment)
        point_stamps.setdefault((setpoint, key[0]), []).append(moment)

    def cleaned_areas(path: Path) -> np.ndarray:
        waveforms = decode_channel(path, channel)
        frequency = interference_frequency(waveforms)
        if frequency is not None:
            waveforms = remove_interference(waveforms, frequency)
        return areas(waveforms)

    logs = [
        _read_log(p)
        for p in sorted(Path(logs_dir or Path(data_dir).parent).glob("temp_record_*.csv"))
    ]

    pending = []
    for setpoint in sorted(grouped):
        cells = grouped[setpoint]
        ladder: dict[float, list[int]] = {}
        for voltage, threshold in cells:
            ladder.setdefault(voltage, []).append(threshold)
        # Drop threshold settings that were not carried across the ladder. A
        # setting that appears at one bias point only is not a repeat condition
        # and averaging it into that point tips it relative to its neighbours.
        seen: dict[int, int] = {}
        for thresholds in ladder.values():
            for threshold in thresholds:
                seen[threshold] = seen.get(threshold, 0) + 1
        carried = {t for t, n in seen.items() if 2 * n >= len(ladder)}
        ladder = {
            v: [t for t in thresholds if t in carried] for v, thresholds in ladder.items()
        }
        # A bias point is only usable if more than one threshold stands behind
        # it, and a campaign needs several such points before an extrapolation
        # to zero gain means anything.
        usable = sorted(v for v, t in ladder.items() if len(t) >= 2)
        if len(usable) < 3:
            continue

        voltages, gains, errors = [], [], []
        for voltage in usable:
            means = []
            for threshold in sorted(ladder[voltage]):
                merged = np.concatenate(
                    [cleaned_areas(p) for p in cells[(voltage, threshold)]]
                )
                means.append(spe_charge_spacing(merged)[0])
            values = np.asarray(means)
            voltages.append(voltage)
            gains.append(float(values.mean()))
            errors.append(max(float((values.max() - values.min()) / 2.0), 1.0))

        temperature = _window_temperature(logs, stamps[setpoint])
        # Temperature over each bias point's own acquisitions. The ladder was
        # stepped while the cryostat drifted, so bias and temperature move
        # together within a campaign; the extrapolation below is made at the
        # campaign temperature rather than at whatever temperature each rung
        # happened to be taken at.
        point_temps = [_window_temperature(logs, point_stamps[(setpoint, v)])[0] for v in usable]
        pending.append(
            {
                "campaign_setpoint_c": setpoint,
                "measured_temperature_mean_c": temperature[0],
                "measured_temperature_std_c": temperature[1],
                "voltages": voltages,
                "gains": gains,
                "errors": errors,
                "point_temperatures": point_temps,
            }
        )

    # Extrapolate every campaign at its own temperature, with the coefficient
    # that sets the correction taken from the cross-campaign fit and iterated
    # to self-consistency. Independent of the oracle's implementation: a plain
    # loop over a scalar with its own weighted least squares.
    beta = 0.0
    for _ in range(25):
        results = []
        for cell in pending:
            v = np.asarray(cell["voltages"])
            t = np.asarray(cell["point_temperatures"])
            x = v - beta * (t - cell["measured_temperature_mean_c"])
            g = np.asarray(cell["gains"])
            e = np.asarray(cell["errors"])
            popt, pcov = curve_fit(_linear, x, g, sigma=e, maxfev=5000)
            residuals = (g - _linear(x, *popt)) / e
            results.append(
                {
                    **{k: cell[k] for k in ("campaign_setpoint_c", "measured_temperature_mean_c",
                                              "measured_temperature_std_c", "voltages")},
                    "breakdown_voltage": float(popt[1]),
                    "breakdown_voltage_err": float(np.sqrt(np.diag(pcov))[1]),
                    "gain_slope": float(popt[0]),
                    "normalized_gain": (g / g[-1]).tolist(),
                    "chi2": float(np.sum(residuals**2)),
                }
            )
        temps = np.array([r["measured_temperature_mean_c"] for r in results])
        vbd = np.array([r["breakdown_voltage"] for r in results])
        err = np.array([max(r["breakdown_voltage_err"], 1e-3) for r in results])
        design = np.vstack([temps, np.ones_like(temps)]).T
        weights = 1.0 / err
        solution, *_ = np.linalg.lstsq(design * weights[:, None], vbd * weights, rcond=None)
        if abs(float(solution[0]) - beta) < 1e-5:
            break
        beta = float(solution[0])
    return {
        "campaigns": results,
        "temperature_coefficient_mv_per_k": float(solution[0]) * 1000.0,
    }


def _read_log(path: Path) -> tuple[np.ndarray, np.ndarray]:
    from datetime import datetime

    times, values = [], []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        stamp, _index, temperature = line.split(",")
        times.append(datetime.fromisoformat(stamp.strip()).timestamp())
        values.append(float(temperature))
    order = np.argsort(np.asarray(times))
    return np.asarray(times)[order], np.asarray(values)[order]


def _window_temperature(logs, moments) -> tuple[float, float]:
    """Mean and spread of the log over a campaign's full acquisition window.

    The window comes from every delivered file of the campaign, so the number
    does not depend on which of them an analysis chooses to use. The log is
    picked by time coverage, because the logs are named after setpoints.
    """
    start = min(m.timestamp() for m in moments)
    stop = max(m.timestamp() for m in moments)
    best, best_count = None, -1
    for times, values in logs:
        inside = (times >= start) & (times <= stop)
        if int(inside.sum()) > best_count:
            best, best_count = values[inside], int(inside.sum())
    if best is None or best.size == 0:
        raise ValueError("no cryostat log covers this campaign")
    return float(best.mean()), float(best.std())
