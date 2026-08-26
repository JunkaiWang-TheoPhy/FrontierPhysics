"""Multi-campaign SiPM calibration: gain, breakdown voltage, and its temperature dependence."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "assets"))

from sipm_reference import (
    CampaignLadder,
    average_waveform,
    baseline_level,
    calibrate_hierarchically,
    campaign_temperature,
    combine_thresholds,
    group_by_campaign,
    index_run_files,
    is_calibratable,
    load_channel,
    peak_width,
    read_events,
    read_temperature_log,
    robust_pulse_areas,
    spacing_two_population,
    temperature_statistics,
    usable_bias_points,
)

ROOT = Path("/root")
DATA_DIR = ROOT / "data"

CHANNEL = 3  # device under test, per the run log
DECODE_CHECK_FILE = (
    "sipm_group1_threshold30_-58.0C_53.0V_2000_123_raw_b0_seg0_20230714T190127.bin"
)
DECODE_CHECK_EVENTS = 200
AVERAGE_WAVEFORM_SETTING = (-58.0, 53.0, 30)


def temperature_logs() -> list[tuple[np.ndarray, np.ndarray]]:
    return [read_temperature_log(path) for path in sorted(ROOT.glob("temp_record_*.csv"))]


def log_for(entries, logs):
    """The cryostat log that actually covers this campaign's acquisitions.

    Matched by time rather than by file name: the logs are named after the
    setpoint that was aimed for, which is not a reliable label.
    """
    start = min(entry.timestamp for entry in entries).timestamp()
    stop = max(entry.timestamp for entry in entries).timestamp()
    best, best_cover = None, -1.0
    for times, values in logs:
        inside = float(((times >= start) & (times <= stop)).sum())
        if inside > best_cover:
            best, best_cover = (times, values), inside
    if best is None or best_cover <= 0:
        raise SystemExit("no cryostat log covers a campaign's acquisition window")
    return best


def write_decode_check(path: Path) -> None:
    samples, counters, time_tags = read_events(DATA_DIR / DECODE_CHECK_FILE)
    n = min(DECODE_CHECK_EVENTS, samples.shape[0])
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
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
        )
        for index in range(n):
            event = samples[index]
            writer.writerow(
                [
                    index,
                    int(counters[index]),
                    int(time_tags[index]),
                    int(event[0].min()),
                    int(event[0].max()),
                    int(event[1].min()),
                    int(event[1].max()),
                    int(event[2].min()),
                    int(event[2].max()),
                    int(event[2].sum()),
                    int(event[2][0]),
                    int(event[2][-1]),
                ]
            )


def main() -> int:
    run_files = index_run_files(DATA_DIR)
    if not run_files:
        raise SystemExit(f"no run files found under {DATA_DIR}")
    logs = temperature_logs()
    campaigns = group_by_campaign(run_files)

    spe_rows: list[dict] = []
    gain_rows: list[dict] = []
    campaign_rows: list[dict] = []
    ladders: list[CampaignLadder] = []
    campaign_meta: dict[float, tuple[float, float]] = {}
    average_wf: np.ndarray | None = None
    files_used = 0

    for setpoint in sorted(campaigns):
        entries = campaigns[setpoint]
        if not is_calibratable(entries):
            continue

        ladder = usable_bias_points(entries)
        voltages, gains, gain_errors = [], [], []
        point_entries: dict[float, list] = {}
        for voltage in sorted(ladder):
            means = []
            for threshold in sorted(ladder[voltage]):
                point_entries.setdefault(voltage, []).extend(ladder[voltage][threshold])
                segments = sorted(ladder[voltage][threshold], key=lambda item: item.segment)
                files_used += len(segments)
                waveforms = load_channel([entry.path for entry in segments], CHANNEL)
                areas = robust_pulse_areas(waveforms)
                separation = spacing_two_population(areas)
                means.append(separation)
                spe_rows.append(
                    {
                        "campaign_setpoint_c": setpoint,
                        "voltage_v": voltage,
                        "threshold": threshold,
                        "n_events": int(areas.size),
                        "baseline_adc": baseline_level(waveforms),
                        "spe_charge_spacing_adcns": separation,
                        "spe_peak_sigma_adcns": peak_width(areas),
                    }
                )
                if (setpoint, voltage, threshold) == AVERAGE_WAVEFORM_SETTING:
                    average_wf = average_waveform(waveforms)

            gain, gain_error = combine_thresholds(means)
            voltages.append(voltage)
            gains.append(gain)
            gain_errors.append(gain_error)
            gain_rows.append(
                {
                    "campaign_setpoint_c": setpoint,
                    "voltage_v": voltage,
                    "spe_charge_spacing_adcns": gain,
                    "spe_charge_spacing_err_adcns": gain_error,
                }
            )

        times, values = log_for(entries, logs)
        mean_c, std_c = campaign_temperature(times, values, entries)
        # Each bias point also gets the temperature measured over its own
        # acquisitions: that is what lets the extrapolation be corrected to the
        # campaign temperature rather than absorbing the cryostat drift.
        point_temps = np.array(
            [
                temperature_statistics(times, values, [e.timestamp for e in point_entries[v]])[0]
                for v in voltages
            ]
        )
        ladders.append(
            CampaignLadder(
                setpoint=setpoint,
                voltages=np.array(voltages),
                separations=np.array(gains),
                errors=np.array(gain_errors),
                point_temperatures=point_temps,
                campaign_temperature=mean_c,
            )
        )
        campaign_meta[setpoint] = (mean_c, std_c)

    if len(ladders) < 2:
        raise SystemExit("fewer than two calibratable campaigns; no temperature dependence")

    fits, coefficient, coefficient_err, second_stage_chi2, iterations = calibrate_hierarchically(
        ladders
    )
    for ladder in ladders:
        breakdown = fits[ladder.setpoint]
        mean_c, std_c = campaign_meta[ladder.setpoint]
        campaign_rows.append(
            {
                "campaign_setpoint_c": ladder.setpoint,
                "measured_temperature_mean_c": mean_c,
                "measured_temperature_std_c": std_c,
                "breakdown_voltage_v": breakdown.breakdown_voltage,
                "breakdown_voltage_err_v": breakdown.breakdown_voltage_err,
                "spacing_slope_adcns_per_v": breakdown.slope,
                "spacing_fit_chi2_per_dof": breakdown.chi2 / max(breakdown.dof, 1),
            }
        )

    (ROOT / "result.md").write_text(
        f"breakdown_voltage_temperature_coefficient_mv_per_k: {coefficient:.4f}\n"
        f"breakdown_voltage_temperature_coefficient_err_mv_per_k: {coefficient_err:.4f}\n"
        f"n_campaigns_calibrated: {len(campaign_rows)}\n"
    )

    campaign_fields = [
        "campaign_setpoint_c",
        "measured_temperature_mean_c",
        "measured_temperature_std_c",
        "breakdown_voltage_v",
        "breakdown_voltage_err_v",
        "spacing_slope_adcns_per_v",
        "spacing_fit_chi2_per_dof",
    ]
    with (ROOT / "campaigns.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=campaign_fields)
        writer.writeheader()
        for row in campaign_rows:
            record = {"campaign_setpoint_c": f"{row['campaign_setpoint_c']:.1f}"}
            record.update({key: f"{row[key]:.4f}" for key in campaign_fields[1:]})
            writer.writerow(record)

    with (ROOT / "gain_vs_voltage.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["campaign_setpoint_c", "voltage_v", "spe_charge_spacing_adcns", "spe_charge_spacing_err_adcns"],
        )
        writer.writeheader()
        for row in gain_rows:
            writer.writerow(
                {
                    "campaign_setpoint_c": f"{row['campaign_setpoint_c']:.1f}",
                    "voltage_v": f"{row['voltage_v']:.1f}",
                    "spe_charge_spacing_adcns": f"{row['spe_charge_spacing_adcns']:.4f}",
                    "spe_charge_spacing_err_adcns": f"{row['spe_charge_spacing_err_adcns']:.4f}",
                }
            )

    with (ROOT / "spe_fits.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "campaign_setpoint_c",
                "voltage_v",
                "threshold",
                "n_events",
                "baseline_adc",
                "spe_charge_spacing_adcns",
                "spe_peak_sigma_adcns",
            ],
        )
        writer.writeheader()
        for row in spe_rows:
            writer.writerow(
                {
                    "campaign_setpoint_c": f"{row['campaign_setpoint_c']:.1f}",
                    "voltage_v": f"{row['voltage_v']:.1f}",
                    "threshold": row["threshold"],
                    "n_events": row["n_events"],
                    "baseline_adc": f"{row['baseline_adc']:.4f}",
                    "spe_charge_spacing_adcns": f"{row['spe_charge_spacing_adcns']:.4f}",
                    "spe_peak_sigma_adcns": f"{row['spe_peak_sigma_adcns']:.4f}",
                }
            )

    write_decode_check(ROOT / "decode_check.csv")

    if average_wf is None:
        raise SystemExit(f"setting {AVERAGE_WAVEFORM_SETTING} not present in the data")
    with (ROOT / "average_waveform.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample_index", "amplitude_adc"])
        for index, amplitude in enumerate(average_wf):
            writer.writerow([index, f"{amplitude:.6f}"])

    (ROOT / "ANALYSIS.md").write_text(ANALYSIS_NOTE)

    diagnostics = {
        "channel": CHANNEL,
        "n_files_supplied": len(run_files),
        "n_files_used": files_used,
        "campaigns_supplied": sorted(campaigns),
        "campaigns_calibrated": [row["campaign_setpoint_c"] for row in campaign_rows],
        "campaigns_excluded": {
            f"{setpoint:.1f}": {
                "n_files": len(entries),
                "usable_bias_points": len(usable_bias_points(entries)),
                "reason": "fewer than three bias points carried at more than one "
                "threshold; a breakdown voltage is an extrapolation of gain "
                "against bias and cannot come from a single operating point",
            }
            for setpoint, entries in sorted(campaigns.items())
            if not is_calibratable(entries)
        },
        "campaigns": campaign_rows,
        "gain_vs_voltage": gain_rows,
        "spe_fits": spe_rows,
        "temperature_coefficient_mv_per_k": coefficient,
        "temperature_coefficient_err_mv_per_k": coefficient_err,
        "second_stage_chi2": second_stage_chi2,
        "hierarchical_iterations": iterations,
    }
    (ROOT / "oracle_diagnostics.json").write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True, default=float) + "\n"
    )

    for row in campaign_rows:
        print(
            f"  {row['campaign_setpoint_c']:7.1f} C nominal | measured "
            f"{row['measured_temperature_mean_c']:7.2f} +- {row['measured_temperature_std_c']:.2f}"
            f" | V_bd = {row['breakdown_voltage_v']:.3f} +- {row['breakdown_voltage_err_v']:.3f} V"
            f" | slope {row['spacing_slope_adcns_per_v']:6.1f} | chi2/dof {row['spacing_fit_chi2_per_dof']:.2f}"
        )
    print(
        f"  dV_bd/dT = {coefficient:.1f} +- {coefficient_err:.1f} mV/K   "
        f"({len(campaign_rows)} campaigns, {files_used}/{len(run_files)} files)"
    )
    return 0


ANALYSIS_NOTE = """# SiPM breakdown voltage versus temperature — channel 3

## Reading the files

DT5720 standard firmware: four header words carrying the 0xA marker and event
size, channel mask, event counter and trigger time tag, then the enabled
channels in order, two 12-bit samples per 32-bit word with the earlier sample in
the low half. Event counts were taken by walking each file; the count in the
file name is what was requested, not what was written. The pair ordering matters
and is easy to get backwards: it leaves every per-event sum, minimum and maximum
unchanged and only shows as a two-sample zig-zag on the rising edge.

## Which cooldowns were calibrated

Only cooldowns with a real bias ladder can give a breakdown voltage, since it is
an extrapolation of gain against bias to zero. Cooldowns whose bias points do
not reach three, counting only points carried at more than one threshold, were
recorded and left out; the excluded data is not bad, it simply cannot answer
this question on its own.

The calibrated cooldowns use different bias lists. That is deliberate on the
experiment's part: breakdown moves with temperature, and shifting the ladder
keeps the over-voltage range comparable. The ladders were left as they are.

## Per-cooldown analysis

Per-event baseline fitted over the pulse-free regions and subtracted, area
integrated over the pulse window and scaled by the 4 ns sampling period. The
noise from shared-trigger events is excluded before fitting, and the
single-photoelectron peak is fitted so that the cross-talk shoulder above it
cannot pull the mean. Threshold settings at a bias point are repeats: their mean
is the gain and their spread the uncertainty. A weighted straight line through
gain against bias gives the breakdown voltage as its x-intercept.

## Temperature and the second stage

Cryostat logs were matched to cooldowns by time, not by their file names, and
each cooldown's temperature is the mean and standard deviation of the readings
across the window spanned by all of its delivered files. Using the nominal
setpoints instead would move the coefficient noticeably, because at least one
setpoint is several kelvin from what the sensor actually read.

Breakdown voltage against measured temperature is then fitted weighted by the
per-cooldown errors. With so few cooldowns the fit has almost no freedom, so the
residuals are quoted rather than a reduced chi-square.

Areas are in ADC counts x ns throughout; the amplifier chain was never
calibrated, so no charge or electron gain is claimed.
"""


if __name__ == "__main__":
    raise SystemExit(main())
