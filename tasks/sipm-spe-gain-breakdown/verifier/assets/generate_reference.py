"""Regenerate `reference_values.json` for the multi-campaign task.

Maintainer tool; never runs at solve or verify time.

Two kinds of number go in here, and they are not the same kind of thing.

The headline results -- the breakdown voltage of each campaign and the
temperature coefficient -- are frozen from a *consensus* of ten predeclared,
scientifically defensible pipelines, not from any single implementation. A
breakdown voltage is an extrapolation to roughly 6-11 V below the lowest
measured bias point, so a one-percent difference in gain shape moves it by
0.1-0.2 V. Treating one script's estimate as exact truth would reject correct
analyses; the consensus median is an operational benchmark reference, and the
spread of the ensemble around it is the measured method systematic.

The intermediate quantities -- per-setting SPE fits, gain tables, noise
levels, the averaged waveform -- come from the reference pipeline, and are
checked with tolerances wide enough for the ensemble's own variation.

    python3 generate_reference.py <data_dir> <consensus.json>
"""

from __future__ import annotations

import hashlib
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
    read_temperature_log,
    robust_pulse_areas,
    spacing_two_population,
    temperature_statistics,
    usable_bias_points,
)

CHANNEL = 3
AVERAGE_WAVEFORM_SETTING = (-58.0, 53.0, 30)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def log_for(entries, logs):
    start = min(e.timestamp for e in entries).timestamp()
    stop = max(e.timestamp for e in entries).timestamp()
    best, count = None, -1
    for times, values in logs:
        inside = int(((times >= start) & (times <= stop)).sum())
        if inside > count:
            best, count = (times, values), inside
    return best


def main(data_dir: Path, consensus_path: Path, out_path: Path) -> int:
    consensus = json.loads(consensus_path.read_text())
    run_files = index_run_files(data_dir)
    logs = [read_temperature_log(p) for p in sorted(data_dir.parent.glob("temp_record_*.csv"))]
    campaigns = group_by_campaign(run_files)

    spe_fits, gains_by_campaign, campaign_rows = {}, {}, []
    ladders: list[CampaignLadder] = []
    campaign_meta: dict[float, tuple[float, float]] = {}
    waveform = None
    for setpoint in sorted(campaigns):
        entries = campaigns[setpoint]
        if not is_calibratable(entries):
            continue
        ladder = usable_bias_points(entries)
        voltages, gains, errors = [], [], []
        point_entries: dict[float, list] = {}
        for voltage in sorted(ladder):
            means = []
            for threshold in sorted(ladder[voltage]):
                segments = sorted(ladder[voltage][threshold], key=lambda i: i.segment)
                point_entries.setdefault(voltage, []).extend(segments)
                waveforms = load_channel([e.path for e in segments], CHANNEL)
                areas = robust_pulse_areas(waveforms)
                spacing = spacing_two_population(areas)
                means.append(spacing)
                spe_fits[f"{setpoint:.1f}|{voltage:.1f}|{threshold}"] = {
                    "spe_charge_spacing_adcns": spacing,
                    "spe_peak_sigma_adcns": peak_width(areas),
                    "n_events": int(areas.size),
                    "baseline_adc": baseline_level(waveforms),
                }
                if (setpoint, voltage, threshold) == AVERAGE_WAVEFORM_SETTING:
                    waveform = average_waveform(waveforms)
            gain, error = combine_thresholds(means)
            voltages.append(voltage)
            gains.append(gain)
            errors.append(error)
        times, values = log_for(entries, logs)
        mean_c, std_c = campaign_temperature(times, values, entries)
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
                errors=np.array(errors),
                point_temperatures=point_temps,
                campaign_temperature=mean_c,
            )
        )
        gains_by_campaign[f"{setpoint:.1f}"] = {
            "voltages": voltages,
            "spacings_adcns": gains,
            "spacing_errors_adcns": errors,
            "normalized_spacing": (np.array(gains) / gains[-1]).tolist(),
        }
        campaign_meta[setpoint] = (mean_c, std_c)

    fits, _, _, _, _ = calibrate_hierarchically(ladders)
    for ladder in ladders:
        breakdown = fits[ladder.setpoint]
        mean_c, std_c = campaign_meta[ladder.setpoint]
        campaign_rows.append(
            {
                "campaign_setpoint_c": ladder.setpoint,
                "measured_temperature_mean_c": mean_c,
                "measured_temperature_std_c": std_c,
                "reference_breakdown_voltage_v": consensus["consensus_vbd"][f"{ladder.setpoint:.1f}"],
                "pipeline_breakdown_voltage_v": breakdown.breakdown_voltage,
                "pipeline_spacing_slope_adcns_per_v": breakdown.slope,
                "pipeline_spacing_fit_chi2_per_dof": breakdown.chi2 / max(breakdown.dof, 1),
            }
        )

    independent = independent_calib.calibrate(data_dir, CHANNEL, logs_dir=data_dir.parent)

    payload = {
        "_comment": (
            "Frozen reference for the multi-campaign SiPM calibration task. "
            "Headline results are a consensus of ten predeclared pipelines, every one "
            "extrapolating at the campaign temperature with the temperature-drift "
            "correction iterated to self-consistency; "
            "intermediate quantities come from the reference pipeline. "
            "Regenerate with verifier/assets/generate_reference.py."
        ),
        "channel": CHANNEL,
        "expected_events_per_file": 700,
        "average_waveform_setting": list(AVERAGE_WAVEFORM_SETTING),
        "calibratable_campaigns": [row["campaign_setpoint_c"] for row in campaign_rows],
        "non_calibratable_campaigns": [
            setpoint for setpoint, entries in sorted(campaigns.items())
            if not is_calibratable(entries)
        ],
        "consensus": {
            "breakdown_voltage_v": consensus["consensus_vbd"],
            "temperature_coefficient_mv_per_k": consensus["consensus_coefficient_mv_per_k"],
            "max_method_deviation_v": consensus["max_method_deviation_v"],
            "max_method_coefficient_deviation_mv_per_k": consensus[
                "max_method_coefficient_deviation_mv_per_k"
            ],
            "methods": consensus["methods"],
            "method_coefficients": consensus["method_coefficients"],
        },
        "campaigns": campaign_rows,
        "gains": gains_by_campaign,
        "spe_fits": spe_fits,
        "average_waveform_adc": [round(float(v), 6) for v in waveform],
        "average_waveform_peak_sample": int(np.argmax(waveform)),
        "independent": independent,
        "data_manifest": {
            p.name: sha256(p) for p in sorted(data_dir.iterdir()) if p.name.endswith(".bin")
        },
    }
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=float) + "\n")
    print(f"wrote {out_path}")
    for row in campaign_rows:
        print(
            f"  {row['campaign_setpoint_c']:7.1f} C  consensus V_bd "
            f"{row['reference_breakdown_voltage_v']:.4f}  pipeline "
            f"{row['pipeline_breakdown_voltage_v']:.4f}  T "
            f"{row['measured_temperature_mean_c']:.2f}"
        )
    print(f"  consensus coefficient {consensus['consensus_coefficient_mv_per_k']:.4f} mV/K")
    return 0


if __name__ == "__main__":
    raise SystemExit(
        main(Path(sys.argv[1]), Path(sys.argv[2]),
             Path(sys.argv[3]) if len(sys.argv) > 3 else HERE / "reference_values.json")
    )
