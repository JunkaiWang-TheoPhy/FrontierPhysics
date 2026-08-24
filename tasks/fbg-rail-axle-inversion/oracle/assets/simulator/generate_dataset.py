"""Generate the frozen task dataset and the held-out ground truth.

Writes, relative to the task root (three levels up from this file):
  environment/data/sensors/S*.csv.gz    agent-visible interrogator streams
  environment/data/lablog.md            commissioning log: layout + specs
  environment/data/calibration.csv      documented calibration-passage loads
  verifier/assets/ground_truth/*        held out from the agent image

Run:  python generate_dataset.py [--seed 20260812] [--qc DIR]
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import numpy as np
import rail_model as rm
import sensing
import traffic

TASK_ROOT = Path(__file__).resolve().parents[3]
WINDOW_S = 1500.0
FS = sensing.SAMPLE_RATE_HZ
REF_SENSOR_X = 0.0  # S1: t_ref definition


DYN_LOAD_SIGMA = 0.04     # instantaneous wheel/rail load fluctuation (track irregularity)
FLAT_IMPACT_FRAC = 0.6    # impact peak strain vs the axle's static peak
FLAT_RING_HZ = 250.0      # rail-pad-region ringing frequency
FLAT_RING_TAU_S = 0.008


def strain_at_sensor(sensor, trains, t, rng):
    """Total rail-foot strain at one sensor: quasi-static superposition with
    per-site dynamic load variation, plus wheel-flat impact transients."""
    beta = rm.beta_of_k(sensor.k_foundation)
    eps = np.zeros_like(t)
    for train in trains:
        if train.reverses:
            occ = train.occupancy()
            t_first, t_last = occ[0], occ[1]
        else:
            t_first = train.crossing_time(sensor.x_m, 0)
            t_last = train.crossing_time(sensor.x_m, train.n_axles - 1)
        margin = 20.0 / train.v0 + 2.0
        i0 = max(int((t_first - margin) * FS), 0)
        i1 = min(int((t_last + margin) * FS) + 1, len(t))
        if i0 >= i1:
            continue
        tw = t[i0:i1]
        pos = train.axle_positions(tw)                    # (n_axles, nt)
        dyn = 1.0 + np.clip(rng.normal(0.0, DYN_LOAD_SIGMA, train.n_axles), -0.25, 0.25)
        loads = (train.wheel_loads_n() * dyn)[:, None]    # (n_axles, 1)
        eps[i0:i1] += rm.foot_strain_kernel(pos - sensor.x_m, loads, beta).sum(axis=0)

        # wheel-flat impacts: one strike per revolution near the sensor
        for tid, ax in traffic.FLAT_WHEELS:
            if tid != train.train_id:
                continue
            peak = rm.peak_foot_strain(train.wheel_loads_n()[ax], beta)
            phase = rng.uniform(0, traffic.WHEEL_CIRCUMFERENCE_M)
            for k in range(-3, 4):
                x_hit = sensor.x_m + phase - traffic.WHEEL_CIRCUMFERENCE_M * 1.5 \
                        + k * traffic.WHEEL_CIRCUMFERENCE_M
                t_hit = train.crossing_time(x_hit, ax)
                amp = FLAT_IMPACT_FRAC * peak * np.exp(-beta * abs(x_hit - sensor.x_m))
                if amp < 1e-7:
                    continue
                j0 = int(t_hit * FS)
                if j0 < 0 or j0 >= len(t) - 100:
                    continue
                tt = t[j0:j0 + 100] - t_hit
                eps[j0:j0 + 100] += amp * np.exp(-tt / FLAT_RING_TAU_S) \
                    * np.sin(2 * np.pi * FLAT_RING_HZ * tt)
    return eps


def write_stream_csv_gz(path, t, wl1_pm, wl2_pm):
    """Interrogator export format: t_s, wl1_nm, wl2_nm (0.1 pm resolution)."""
    with gzip.open(path, "wt", newline="") as f:
        f.write("t_s,wl1_nm,wl2_nm\n")
        chunk = 100_000
        for i in range(0, len(t), chunk):
            rows = "\n".join(
                f"{ts:.3f},{a / 1000.0:.4f},{b / 1000.0:.4f}"
                for ts, a, b in zip(t[i:i + chunk], wl1_pm[i:i + chunk], wl2_pm[i:i + chunk])
            )
            f.write(rows + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260812)
    ap.add_argument("--qc", type=Path, default=None, help="directory for QC plots")
    ap.add_argument("--out-root", type=Path, default=TASK_ROOT,
                    help="write environment/data and verifier/assets under this root")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    sensors = sensing.make_sensors(rng)
    trains = traffic.build_timetable(rng)
    t = np.arange(0.0, WINDOW_S, 1.0 / FS)

    data_dir = args.out_root / "environment" / "data"
    gt_dir = args.out_root / "verifier" / "assets" / "ground_truth"
    (data_dir / "sensors").mkdir(parents=True, exist_ok=True)
    gt_dir.mkdir(parents=True, exist_ok=True)

    # --- agent-visible streams ---
    streams = {}
    for sensor in sensors:
        eps = strain_at_sensor(sensor, trains, t, rng)
        temp = sensing.rail_temperature_c(t, sensor, window_s=WINDOW_S)
        wl1, wl2 = sensing.transduce(eps, temp, sensor, rng)
        streams[sensor.sensor_id] = (eps, wl1, wl2)
        keep = np.ones(len(t), dtype=bool)
        if sensor.sensor_id == "S2":
            t3 = next(tr for tr in trains if tr.train_id == "T3")
            gap0 = t3.crossing_time(sensor.x_m, t3.n_axles // 2)
            keep[int(gap0 * FS):int((gap0 + 3.0) * FS)] = False   # interrogator dropout
        write_stream_csv_gz(data_dir / "sensors" / f"{sensor.sensor_id}.csv.gz",
                            t[keep], wl1[keep], wl2[keep])

    # --- agent-visible metadata: the commissioning lab log ---
    cal = trains[-2]
    cal2 = trains[-1]
    assert cal.train_id == "T6" and cal2.train_id == "T6R"
    roles = {"S1": "counting point A; section boundary; reference sensor",
             "S2": "counting point A",
             "S3": "counting point B",
             "S4": "counting point B; section boundary"}
    sensor_table = "\n".join(
        f"| {s.sensor_id} | {s.x_m:.1f} | {roles[s.sensor_id]} |"
        for s in sensors)
    lablog = f"""# commissioning log of FBG axle-counting array

Site: single-track block section, one rail instrumented.
Instrument: 4 dual-grating FBG strain sensor units clamped to the rail foot.
Interrogator: {int(FS)} Hz sampling, {sensing.QUANT_PM:g} pm wavelength quantization, noise ~{sensing.NOISE_PM_RMS:g} pm rms per grating.

## 1. installation

Each sensor unit carries two gratings bonded to opposite faces of one bending substrate (center wavelengths 1530 nm and 1535 nm). Nominal sensitivities from the unit datasheet: strain ~{sensing.K_EPS_PM_PER_UE:.1f} pm/ue, temperature ~{sensing.K_T_PM_PER_C:g} pm/degC per grating. Units bonded and zero-referenced at {sensing.T_REF_C:g} degC.

Positions measured from the entry-side boundary along the instrumented rail:

| unit | x (m) | role |
|---|---|---|
{sensor_table}

Section boundaries: x = {traffic.SECTION_ENTRY:.1f} m (S1) and x = {traffic.SECTION_EXIT:.1f} m (S4).

Track: CN60 rail (60 kg/m), E = 215 GPa, section moment of inertia I = 3.217e-5 m^4, section centroid 80.9 mm above the rail base. Sleeper spacing 0.54 m. Ballast support is Winkler-like; on this line k is typically 40e6 to 90e6 N/m^2 and varies from sensor to sensor — do not assume one
shared value.

## 2. commissioning recording

Recording starts at t = 0 s and runs {int(WINDOW_S)} s (~25 min) of mixed traffic, written per unit to `sensors/S1.csv.gz` .. `sensors/S4.csv.gz`, columns
`t_s,wl1_nm,wl2_nm` (time and the two grating wavelengths).
Calibration: the track-inspection car (4 axles) ran through the section twice. Its per-axle static loads are from the weigh certificate, copied to
`calibration.csv` (`axle_index,load_kN`). Average over both passes when calibrating.

| pass | direction | speed (m/s) | entered section (approx) |
|---|---|---|---|
| 1 | A to B | {cal.v0:.1f} | t ~ {int(cal.t0)} s |
| 2 | B to A | {cal2.v0:.1f} | t ~ {int(cal2.t0)} s |
"""
    (data_dir / "lablog.md").write_text(lablog)

    with open(data_dir / "calibration.csv", "w") as f:
        f.write("axle_index,load_kN\n")
        for j, load_t in enumerate(cal.axle_loads_t):
            f.write(f"{j},{load_t * rm.G_ACCEL:.1f}\n")

    # --- held-out ground truth ---
    trains_gt = []
    axle_rows = []
    for train in trains:
        t_in, t_out = train.occupancy()
        d_section = traffic.SECTION_EXIT - traffic.SECTION_ENTRY
        trains_gt.append({
            "train_id": train.train_id,
            "n_axles": train.n_axles,
            "direction": 0 if train.reverses else train.direction,
            "reverses": train.reverses,
            "v_entry_mps": round(train.v0, 4),
            "v_exit_mps": round(train.v_return if train.reverses
                                else train.speed_at_distance(d_section), 4),
            "occupancy_s": [round(t_in, 4), round(t_out, 4)],
            "accel_mps2": train.accel,
            "note": train.note,
        })
        for j in range(train.n_axles):
            vehicle = 0 if (train.n_axles == 4 or j < 6) else 1 + (j - 6) // 4
            axle_rows.append((
                train.train_id, j, vehicle,
                round(train.crossing_time(REF_SENSOR_X, j, "first"), 4),
                round(train.crossing_speed(REF_SENSOR_X, j, "first"), 4),
                round(train.axle_loads_t[j] * rm.G_ACCEL, 3),
            ))

    (gt_dir / "trains.json").write_text(json.dumps(trains_gt, indent=2) + "\n")
    with open(gt_dir / "axles.csv", "w") as f:
        f.write("train_id,axle_index,vehicle_index,t_ref_s,speed_at_ref_mps,load_kN\n")
        for row in axle_rows:
            f.write(",".join(str(v) for v in row) + "\n")

    internals = {
        "seed": args.seed,
        "faulted_sensor": next(s.sensor_id for s in sensors if s.is_faulted),
        "sensors": [{
            "id": s.sensor_id, "x_m": s.x_m, "k_n_per_m2": s.k_foundation,
            "beta_per_m": rm.beta_of_k(s.k_foundation), "transfer": s.transfer,
            "kt_mismatch": s.kt_mismatch, "temp_lag_s": s.temp_lag_s,
            "temp_offset_c": s.temp_offset_c, "faulted": s.is_faulted,
        } for s in sensors],
    }
    (gt_dir / "sensors_internal.json").write_text(json.dumps(internals, indent=2) + "\n")

    # --- console summary ---
    print(f"seed={args.seed}  samples={len(t):,} @ {FS:.0f} Hz  window={WINDOW_S:.0f} s")
    for s in sensors:
        eps, wl1, wl2 = streams[s.sensor_id]
        diff = (wl1 - wl2) - np.median(wl1 - wl2)
        print(f"  {s.sensor_id}: beta={rm.beta_of_k(s.k_foundation):.3f}/m "
              f"transfer={s.transfer:.3f} peak_diff={diff.max():.0f} pm "
              f"peak_eps={eps.max() * 1e6:.0f} ue faulted={s.is_faulted}")
    for tr, gt in zip(trains, trains_gt):
        print(f"  {tr.train_id}: axles={tr.n_axles} dir={tr.direction:+d} "
              f"v={gt['v_entry_mps']:.1f}->{gt['v_exit_mps']:.1f} m/s "
              f"occ=[{gt['occupancy_s'][0]:.1f},{gt['occupancy_s'][1]:.1f}] s")

    if args.qc:
        make_qc_plots(args.qc, t, sensors, streams, trains)


def make_qc_plots(qc_dir, t, sensors, streams, trains):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    qc_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
    for ax, sensor in zip(axes, sensors):
        _eps, wl1, wl2 = streams[sensor.sensor_id]
        ax.plot(t[::20], (wl1 - wl2)[::20] - np.median(wl1 - wl2), lw=0.3)
        ax.set_ylabel(f"{sensor.sensor_id}\ndiff [pm]")
    axes[-1].set_xlabel("t [s]")
    axes[0].set_title("Differential channel, full window (all six passages)")
    fig.savefig(qc_dir / "qc_overview.png", dpi=110)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    _eps, wl1, wl2 = streams["S1"]
    sl = slice((95 * 1000), (135 * 1000))
    axes[0].plot(t[sl], wl1[sl] - np.median(wl1[sl]), lw=0.4, label="wl1 (raw)")
    axes[0].plot(t[sl], wl2[sl] - np.median(wl2[sl]), lw=0.4, label="wl2 (raw)")
    axes[0].legend()
    axes[0].set_ylabel("raw [pm]")
    axes[0].set_title("T1 freight at S1: raw channels vs differential")
    axes[1].plot(t[sl], (wl1 - wl2)[sl] - np.median((wl1 - wl2)[sl]), lw=0.4)
    axes[1].set_ylabel("diff [pm]")
    axes[1].set_xlabel("t [s]")
    fig.savefig(qc_dir / "qc_T1_S1.png", dpi=110)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5))
    sl = slice((99 * 1000), (103 * 1000))
    ax.plot(t[sl], (wl1 - wl2)[sl] - np.median(wl1 - wl2), lw=0.6)
    ax.set_title("Zoom: loco + first wagons (bogie pulse pairs, uplift lobes)")
    ax.set_xlabel("t [s]")
    ax.set_ylabel("diff [pm]")
    fig.savefig(qc_dir / "qc_zoom_bogies.png", dpi=110)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    _eps5, wl1_5, wl2_5 = streams["S4"]
    sl = slice((950 * 1000), (1250 * 1000), 10)
    axes[0].plot(t[sl], wl1_5[sl] - np.median(wl1_5[sl]), lw=0.4)
    axes[0].set_ylabel("wl1 raw [pm]")
    axes[0].set_title("Thermal transient + T5 at S4: raw channel drifts, differential stays flat")
    axes[1].plot(t[sl], (wl1_5 - wl2_5)[sl] - np.median(wl1_5 - wl2_5), lw=0.4)
    axes[1].set_ylabel("diff [pm]")
    axes[1].set_xlabel("t [s]")
    fig.savefig(qc_dir / "qc_transient.png", dpi=110)
    plt.close(fig)

    print(f"QC plots -> {qc_dir}")


if __name__ == "__main__":
    main()
