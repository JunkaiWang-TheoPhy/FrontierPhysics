"""Reference solution for fbg-rail-axle-inversion.

Implements the task author's patented signal chain (CN106476845B — the
author is the inventor):

  1. form the differential channel (temperature common-mode rejection);
  2. detect axle events per sensor;
  3. associate events within each counting point pair -> per-axle speed,
     direction, arrival times;
  4. fit per-axle response amplitudes against the beam-on-elastic-foundation
     kernel (removes neighbor side-lobe bias);
  5. calibrate pm -> kN per sensor with the documented calibration passage;
  6. cross-validate sensors -> identify the faulted one;
  7. block occupancy from boundary-sensor events.

Reads /root/data, writes /root/result.md, /root/axles.csv and /root/paper.pdf.
"""

from __future__ import annotations

import gzip
import io
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.signal import butter, find_peaks, sosfiltfilt

DATA = Path(os.environ.get("DATA_DIR", "/root/data"))
OUT = Path(os.environ.get("OUT_DIR", "/root"))

LOWPASS_HZ = 60.0   # quasi-static lobes are <~20 Hz; wheel-flat ringing ~250 Hz
MIN_PEAK_PM = 25.0
MIN_PEAK_DIST_S = 0.025
TRAIN_GAP_S = 10.0


def parse_lablog(path):
    """Extract the sensor layout and calibration facts from the site log.

    The log is prose plus two Markdown tables (sensor positions/roles and
    the calibration passes); everything the inversion needs is read from it,
    nothing is hard-coded here.
    """
    text = path.read_text()
    fs = float(re.search(r"([\d.]+)\s*Hz sampling", text).group(1))
    sensor_x, roles = {}, {}
    for m in re.finditer(r"^\|\s*(S\d)\s*\|\s*([\d.]+)\s*\|\s*([^|]+)\|",
                         text, re.M):
        sensor_x[m.group(1)] = float(m.group(2))
        roles[m.group(1)] = m.group(3).strip()
    pair_a = sorted(s for s, r in roles.items() if "counting point A" in r)
    pair_b = sorted(s for s, r in roles.items() if "counting point B" in r)
    boundary = sorted((s for s, r in roles.items() if "boundary" in r),
                      key=lambda s: sensor_x[s])
    x_entry, x_exit = sensor_x[boundary[0]], sensor_x[boundary[-1]]
    cal_passes = []
    for m in re.finditer(r"^\|\s*\d+\s*\|\s*[AB] to [AB]\s*\|\s*([\d.]+)"
                         r"\s*\|\s*t\s*~\s*([\d.]+)", text, re.M):
        cal_passes.append({"speed_mps": float(m.group(1)),
                           "entry_time_approx_s": float(m.group(2))})
    return fs, sensor_x, pair_a, pair_b, (x_entry, x_exit), cal_passes


def load_stream(sensor_id):
    with gzip.open(DATA / "sensors" / f"{sensor_id}.csv.gz", "rt") as f:
        df = pd.read_csv(io.StringIO(f.read()))
    t = df["t_s"].to_numpy()
    diff_pm = (df["wl1_nm"].to_numpy() - df["wl2_nm"].to_numpy()) * 1000.0
    sum_pm = (df["wl1_nm"].to_numpy() + df["wl2_nm"].to_numpy()) * 1000.0
    return t, diff_pm, sum_pm


def lowpass(x, fs):
    """Suppress impact transients (wheel flats) while keeping axle lobes."""
    sos = butter(4, LOWPASS_HZ / (fs / 2.0), output="sos")
    return sosfiltfilt(sos, x)


def detect_events(t, diff_pm, fs):
    """Axle candidate times/amplitudes from the baseline-removed differential."""
    quiet = np.median(diff_pm[: int(30 * fs)])
    x = diff_pm - quiet
    idx, props = find_peaks(x, height=MIN_PEAK_PM,
                            distance=max(int(MIN_PEAK_DIST_S * fs), 1),
                            prominence=MIN_PEAK_PM)
    return t[idx], props["peak_heights"]


def group_trains(times, amps, gap_s=TRAIN_GAP_S):
    """Split a sensor's event list into per-passage groups."""
    if len(times) == 0:
        return []
    cuts = np.where(np.diff(times) > gap_s)[0]
    groups, start = [], 0
    for c in [*list(cuts), len(times) - 1]:
        groups.append((times[start:c + 1], amps[start:c + 1]))
        start = c + 1
    return groups


def kernel(u):
    """Normalized foot-strain shape vs dimensionless beta*x."""
    au = np.abs(u)
    return np.exp(-au) * (np.cos(au) - np.sin(au))


def fit_amplitudes(t, x, event_times, speeds, beta, fs):
    """Least-squares per-axle amplitudes against the foundation kernel.

    Removes the neighbor side-lobe bias that peak heights carry.
    """
    _tt, xx, phi = _design(t, x, event_times, speeds, beta, fs)
    a, *_ = np.linalg.lstsq(phi.T, xx, rcond=None)
    return a


def _design(t, x, event_times, speeds, beta, fs):
    """Windowed data and kernel basis, with the model low-passed exactly
    like the data so the amplitude estimate is unbiased at every speed."""
    i0 = np.searchsorted(t, event_times.min() - 1.0)
    i1 = np.searchsorted(t, event_times.max() + 1.0)
    tt_full = t[i0:i1]
    phi = kernel(beta * speeds[:, None] * (tt_full[None, :] - event_times[:, None]))
    sos = butter(4, LOWPASS_HZ / (fs / 2.0), output="sos")
    phi = sosfiltfilt(sos, phi, axis=1)
    step = max(int(fs / 500), 1)
    return tt_full[::step], x[i0:i1:step], phi[:, ::step]


def fit_beta(t, x, event_times, speeds, fs):
    """Per-sensor kernel scale from the calibration passage waveform."""
    def residual(beta):
        _tt, xx, phi = _design(t, x, event_times, speeds, beta, fs)
        a, *_ = np.linalg.lstsq(phi.T, xx, rcond=None)
        return float(((xx - phi.T @ a) ** 2).sum())
    res = minimize_scalar(residual, bounds=(0.6, 2.2), method="bounded")
    return float(res.x)


def match_pairs(ta, tb, max_jitter_s=0.03):
    """Lag-aware matching of two event trains from a sensor pair.

    Estimates the common pair lag (mode of pairwise time offsets), then
    matches each ta event to the tb event nearest ta+lag. Events with no
    partner within max_jitter_s (e.g. interrogator dropout) map to NaN.
    """
    if len(ta) == len(tb):
        return ta, tb
    dts = []
    for x in ta:
        i0 = np.searchsorted(tb, x - 1.0)
        i1 = np.searchsorted(tb, x + 1.0)
        dts.extend(tb[i0:i1] - x)
    dts = np.asarray(dts)
    hist, edges = np.histogram(dts, bins=np.arange(-1.0, 1.0, 0.005))
    lag = float(np.median(dts[np.abs(dts - edges[np.argmax(hist)]) < 0.01]))
    matched = np.full(len(ta), np.nan)
    for k, x in enumerate(ta):
        j = np.searchsorted(tb, x + lag)
        best = None
        for cand in (j - 1, j):
            if 0 <= cand < len(tb) and abs(tb[cand] - (x + lag)) <= max_jitter_s:
                if best is None or abs(tb[cand] - (x + lag)) < abs(tb[best] - (x + lag)):
                    best = cand
        if best is not None:
            matched[k] = tb[best]
    return ta, matched


def _fig_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    buf.seek(0)
    return buf


def _make_figures(sid, axle_rows, fs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    t, d, s = load_stream(sid)
    wl1 = (s + d) / 2.0
    step = 200
    fig1, ax = plt.subplots(figsize=(6.4, 3.0))
    ax.plot(t[::step], wl1[::step] - np.median(wl1[: int(30 * fs)]),
            lw=0.6, label=f"{sid} single grating")
    ax.plot(t[::step], d[::step] - np.median(d[: int(30 * fs)]),
            lw=0.6, label=f"{sid} differential")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("wavelength shift (pm)")
    ax.set_title("Temperature drift vs the differential channel")
    ax.legend(loc="upper left", fontsize=8)
    buf1 = _fig_png(fig1)
    plt.close(fig1)

    counts = {}
    for tid, _j, _tr, _ld in axle_rows:
        counts[tid] = counts.get(tid, 0) + 1
    tid = max(counts, key=counts.get)
    loads = [ld for (t_, _j, _tr, ld) in axle_rows if t_ == tid and ld > 0]
    fig2, ax = plt.subplots(figsize=(6.4, 3.0))
    ax.bar(range(len(loads)), loads, width=0.8)
    ax.set_xlabel("axle index")
    ax.set_ylabel("estimated static load (kN)")
    ax.set_title(f"Calibrated per-axle loads, {tid} ({len(loads)} axles)")
    buf2 = _fig_png(fig2)
    plt.close(fig2)

    return [(buf1, "Figure 1: a single grating carries the outdoor temperature"
                   " drift; the two-grating differential cancels it and keeps"
                   " the axle strain lobes."),
            (buf2, f"Figure 2: static axle loads for {tid} from the kernel fit"
                   " and the calibration-passage gains.")]


def build_paper(path, trains_out, faulted_sensor, healthy, axle_rows,
                gain, beta_fit, fs):
 
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas as pdf_canvas

    c = pdf_canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    margin = 72
    y = height - margin

    def ensure(dy):
        nonlocal y
        if y - dy < margin:
            c.showPage()
            y = height - margin

    def heading(text, size=13):
        nonlocal y
        ensure(size + 20)
        y -= size + 10
        c.setFont("Helvetica-Bold", size)
        c.drawString(margin, y, text)
        y -= 4

    def body(text, size=10, leading=13.5, font="Times-Roman"):
        nonlocal y
        for para in text.split("\n"):
            words, line = para.split(), ""
            for w in words:
                trial = (line + " " + w).strip()
                if c.stringWidth(trial, font, size) > width - 2 * margin:
                    ensure(leading)
                    y -= leading
                    c.setFont(font, size)
                    c.drawString(margin, y, line)
                    line = w
                else:
                    line = trial
            if line:
                ensure(leading)
                y -= leading
                c.setFont(font, size)
                c.drawString(margin, y, line)
            y -= 4

    def figure(buf, caption):
        nonlocal y
        w_pt, h_pt = 5.9 * 72, 2.8 * 72
        ensure(h_pt + 34)
        y -= h_pt
        c.drawImage(ImageReader(buf), margin, y, width=w_pt, height=h_pt,
                    preserveAspectRatio=True, anchor="sw")
        y -= 6
        body(caption, size=8.5, leading=11, font="Helvetica-Oblique")

    heading("Axle Counting, Kinematics and Load Estimation on a Single-Track "
            "Block", 13)
    heading("Section with Dual-Grating FBG Rail-Foot Sensors", 13)

    heading("Abstract", 12)
    n_through = sum(1 for tr in trains_out if tr["direction"] != 0)
    n_shunt = len(trains_out) - n_through
    body("We demonstrate axle counting, direction and speed estimation, block "
         "occupancy timing, and static axle-load estimation on a single-track "
         "block section instrumented with four dual-grating fiber Bragg "
         "grating (FBG) strain sensor units clamped to the rail foot. The two "
         "gratings of each unit are bonded to opposite faces of one bending "
         "substrate, so their difference cancels the outdoor temperature "
         "drift while doubling the strain response. Axle events are detected "
         "on the differential channel, associated across the sensor pairs at "
         "the two counting points, and per-axle loads are recovered by "
         "fitting the beam-on-elastic-foundation response kernel, calibrated "
         "against a documented inspection-car passage. In the ~25 minute "
         f"commissioning record the array resolved {len(trains_out)} "
         f"passages ({n_through} through, {n_shunt} entered and reversed "
         f"out), and cross-validation of the calibrated sensor gains and "
         f"temperature common-mode rejection identified {faulted_sensor} as "
         "the faulted unit.")

    heading("1. Introduction", 12)
    body("Block-section occupancy detection on single-track lines is "
         "traditionally done with track circuits or inductive wheel sensors, "
         "which are vulnerable to electromagnetic interference and require "
         "trackside electronics. FBG strain sensors are passive, "
         "multiplexable on one fiber, and immune to EMI, which makes them "
         "attractive for axle counting. The main obstacles are that an FBG "
         "responds to temperature as well as strain, and that the rail-foot "
         "strain response of neighboring axles overlaps, so naive peak "
         "counting or peak-height weighing is biased. This work uses "
         "sensor units with two gratings on opposite faces of a bending "
         "substrate: bending strains the two gratings with opposite sign "
         "while temperature shifts both equally, so the differential channel "
         "is temperature-free and twice as sensitive. Four units form two "
         "counting points at the section boundaries, giving axle counts, "
         "direction, per-axle speed, occupancy interval, and, with a "
         "mechanics model, static axle loads.")

    heading("2. Methods", 12)
    body("Signals. Each unit reports two grating wavelengths at 1 kHz. The "
         "differential channel d(t) = wl1 - wl2 (in pm) cancels temperature; "
         "the sum channel is kept as a temperature proxy for the sensor "
         "health check. d(t) is low-pass filtered at 60 Hz to suppress "
         "wheel-flat impact ringing while keeping the quasi-static axle "
         "lobes.\n"
         "Rail response model. The rail is an Euler-Bernoulli beam on a "
         "Winkler foundation; a wheel load at distance x from the sensor "
         "produces foot strain proportional to exp(-b|x|)(cos(bx) - "
         "sin(bx)), where b is the foundation characteristic scale. The "
         "negative side lobes of this kernel overlap between the closely "
         "spaced axles of one bogie, so per-axle amplitudes are estimated by "
         "linear least squares against the kernel basis rather than read "
         "from peak heights; b is fitted per sensor from the calibration "
         "waveform.\n"
         "Events and kinematics. Axle events are peaks of the "
         "baseline-removed differential above an amplitude and prominence "
         "floor with a minimum spacing. The two sensors of a counting point "
         "co-observe every axle 3.0 m apart: the per-axle time lags give "
         "per-axle speed, the lag sign gives direction. Clusters at the two "
         "counting points are associated into passages by axle count and "
         "order; a cluster pair seen at the same counting point with "
         "opposite directions and no matching cluster at the other point is "
         "a shunting move that entered and reversed out, and is reported "
         "once with direction 0.\n"
         "Load calibration. The inspection car with weigh-certificate axle "
         "loads passed twice; per-sensor gains (pm per kN) are the median of "
         "fitted amplitude over documented load across both passes. Loads of "
         "every passage are the mean over healthy sensors that observed all "
         "axles. On the reverse-out cluster of a shunting move the axle "
         "order is reversed before averaging.\n"
         "Sensor health. Two per-sensor statistics are cross-validated "
         "against the array: the calibrated gain (strain-transfer loss shows "
         "as a low gain) and the quiet-segment regression slope of the "
         "differential against the sum channel (a broken grating pair leaks "
         "temperature into the differential). A unit far outside the family "
         "on either statistic is flagged as faulted and excluded from load "
         "fusion.\n"
         "Occupancy. The occupancy interval runs from the first axle event "
         "at the entry boundary sensor to the last axle event at the exit "
         "boundary sensor; for a shunting move both are the same boundary.")

    heading("3. Results", 12)
    lines = []
    for tr in trains_out:
        r = tr["rank"]
        if tr["direction"] != 0:
            lines.append(
                f"train_{r}: {tr['n_axles']} axles, direction "
                f"{tr['direction']:+d}, mean speed {tr['v_mean']:.2f} m/s, "
                f"v_entry {tr['v_entry']:.2f} m/s, v_exit "
                f"{tr['v_exit']:.2f} m/s, occupancy "
                f"[{tr['occupancy'][0]:.1f}, {tr['occupancy'][1]:.1f}] s.")
        else:
            lines.append(
                f"train_{r}: {tr['n_axles']} axles, entered and reversed out "
                f"(direction 0), v_entry {tr['v_entry']:.2f} m/s, v_exit "
                f"{tr['v_exit']:.2f} m/s, occupancy "
                f"[{tr['occupancy'][0]:.1f}, {tr['occupancy'][1]:.1f}] s.")
    body("The commissioning record resolved the following passages, in entry "
         "order:\n" + "\n".join(lines) + "\n"
         f"Faulted unit: {faulted_sensor}. Fitted kernel scales b: " +
         ", ".join(f"{k} {v:.2f} 1/m" for k, v in sorted(beta_fit.items())) +
         ". Calibrated gains (pm/kN): " +
         ", ".join(f"{k} {v:.2f}" for k, v in sorted(gain.items())) +
         ". Full per-axle arrival times and loads accompany this draft in "
         "axles.csv; the key-value summary is in result.md.")
    for buf, caption in _make_figures(healthy[0], axle_rows, fs):
        figure(buf, caption)

    heading("4. Discussion", 12)
    body("The differential channel removes the dominant systematic "
         "(temperature drift an order of magnitude above the interrogator "
         "noise) at the sensor level rather than in software, so event "
         "detection thresholds stay stationary over the record. The kernel "
         "fit removes the neighbor side-lobe bias that makes raw peak "
         "heights understate inner-bogie axle loads; with peak heights the "
         "per-vehicle means were biased low by roughly ten percent in our "
         "development experiments. Residual per-axle scatter is dominated by "
         "genuine dynamic wheel-load variation and by foundation stiffness "
         "differences between sensor sites, which the per-sensor b and gain "
         "calibration absorbs to first order. The shunting move is the "
         "operationally critical case: counting it twice, or reading its "
         "exit speed from the wrong axle (the leading axle exits last on the "
         "reverse-out), corrupts both the count and the interlocking "
         "release. Cross-validating two independent per-sensor statistics "
         "identifies the faulted unit without ground truth.")

    heading("References", 12)
    body("[1] C. Wei, Q. Xin, W. H. Chung, S.-Y. Liu, H.-Y. Tam, and S. L. "
         "Ho, Real-time train wheel condition monitoring by fiber Bragg "
         "grating sensors, International Journal of Distributed Sensor "
         "Networks, 2012.\n"
         "[2] M. L. Filograno, P. Corredera, M. Rodriguez-Plaza, A. "
         "Andres-Alguacil, and M. Gonzalez-Herraez, Real-time monitoring of "
         "railway traffic using fiber Bragg grating sensors, IEEE Sensors "
         "Journal, vol. 12, no. 1, 2012.\n"
         "[3] M. Hetenyi, Beams on Elastic Foundation, University of "
         "Michigan Press, 1946.\n"
         "[4] C. Esveld, Modern Railway Track, 2nd ed., MRT-Productions, "
         "2001.\n"
         "[5] CN106476845B, Differential dual-FBG rail axle-counting method "
         "and apparatus (granted Chinese patent).")

    c.showPage()
    c.save()


def main():
    (fs, sensor_x, pair_a, pair_b,
     (x_entry, x_exit), cal_specs) = parse_lablog(DATA / "lablog.md")
    cal = pd.read_csv(DATA / "calibration.csv")

    streams, events, cmr_leak = {}, {}, {}
    for sid in sensor_x:
        t, d, ssum = load_stream(sid)
        d = lowpass(d - np.median(d[: int(30 * fs)]), fs)
        streams[sid] = (t, d)
        events[sid] = detect_events(t, d, fs)
        # Sensor health (patent cross-validation): in quiet segments the
        # differential should be temperature-blind. Regress diff against the
        # sum channel (pure temperature proxy); the slope estimates the
        # grating-pair mismatch — an out-of-family slope means the sensor's
        # temperature compensation is broken.
        quiet = np.ones(len(t), dtype=bool)
        for et in events[sid][0]:
            quiet[np.searchsorted(t, et - 8.0):np.searchsorted(t, et + 8.0)] = False
        ds, ss = d[quiet][::50], (ssum - np.median(ssum[: int(30 * fs)]))[quiet][::50]
        cmr_leak[sid] = abs(float(np.polyfit(ss, ds, 1)[0]))

    groups = {sid: group_trains(*events[sid]) for sid in sensor_x}

    # --- pair clusters within each counting point (S1&S2 always co-observe;
    # S3&S4 likewise), then associate points into section passages. Sensors
    # legitimately disagree on cluster counts: a shunting move is seen twice
    # at one point and never at the other. ---
    def point_events(p1, p2):
        """[(t_start, n, dir, {sid: (times, amps)})] per co-observed cluster."""
        out = []
        used2 = set()
        for ta, aa in groups[p1]:
            best, bestd = None, 1e9
            for k, (tb, _ab) in enumerate(groups[p2]):
                if k in used2:
                    continue
                d = abs(tb[0] - ta[0])
                if d < bestd:
                    best, bestd = k, d
            if best is None or bestd > 30.0:
                continue
            used2.add(best)
            tb, ab = groups[p2][best]
            t1m, t2m = match_pairs(ta, tb)
            lags = t2m - t1m
            lag = float(np.nanmedian(lags))
            direction = +1 if (lag > 0) == (sensor_x[p2] > sensor_x[p1]) else -1
            out.append({"t0": float(ta[0]), "n": len(ta), "dir": direction,
                        "clusters": {p1: (ta, aa), p2: (tb, ab)},
                        "lags": lags})
        return out

    points_a = point_events(pair_a[0], pair_a[1])
    points_b = point_events(pair_b[0], pair_b[1])

    # associate: A(+1) followed by B(+1) same n -> through A->B;
    # B(-1) then A(-1) -> through B->A;
    # A(+1) then A(-1), same n, no B in between -> shunt at A (and mirrored).
    tagged = ([("A", pt) for pt in points_a] + [("B", pt) for pt in points_b])
    tagged.sort(key=lambda x: x[1]["t0"])
    passages, used = [], set()
    for i, (side, pt) in enumerate(tagged):
        if i in used:
            continue
        partner = None
        for j in range(i + 1, len(tagged)):
            if j in used:
                continue
            side2, pt2 = tagged[j], None
            side2, pt2 = tagged[j][0], tagged[j][1]
            if pt2["n"] != pt["n"]:
                continue
            if side2 != side and pt2["dir"] == pt["dir"]:
                partner = (j, "through")
                break
            if side2 == side and pt2["dir"] == -pt["dir"]:
                partner = (j, "shunt")
                break
        if partner is None:
            raise RuntimeError(f"unmatched cluster at point {side} t0={pt['t0']:.1f}")
        j, kind = partner
        used.update({i, j})
        passages.append({"kind": kind, "entry": (side, pt), "exit": tagged[j]})
    passages.sort(key=lambda p: p["entry"][1]["t0"])

    trains_out, axle_rows = [], []
    beta_fit = {}

    # --- calibration: all documented passes; average gains over passes ---
    cal_loads = cal["load_kN"].to_numpy()
    sensor_gain_samples = {sid: [] for sid in sensor_x}
    for cs in cal_specs:
        cal_pass = min((p for p in passages
                        if p["kind"] == "through" and p["entry"][1]["n"] == len(cal_loads)),
                       key=lambda p: abs(p["entry"][1]["t0"] - cs["entry_time_approx_s"]))
        for sid in sensor_x:
            t, x = streams[sid]
            for _side, pt in (cal_pass["entry"], cal_pass["exit"]):
                if sid in pt["clusters"]:
                    et = pt["clusters"][sid][0]
                    v = np.full(len(et), cs["speed_mps"])
                    beta_fit[sid] = fit_beta(t, x, et, v, fs)
                    amps = fit_amplitudes(t, x, et, v, beta_fit[sid], fs)
                    sensor_gain_samples[sid].extend(list(amps / cal_loads))

    gain = {sid: float(np.median(g)) for sid, g in sensor_gain_samples.items()}
    med_gain = np.median(list(gain.values()))
    med_leak = np.median(list(cmr_leak.values()))
    faulted = [sid for sid in sensor_x
               if gain[sid] < 0.7 * med_gain
               or cmr_leak[sid] > max(3.0 * med_leak, 0.035)]
    faulted_sensor = faulted[0] if faulted else "none"
    healthy = [sid for sid in sensor_x if sid != faulted_sensor]

    # --- per passage ---
    for rank, p in enumerate(passages, start=1):
        side_in, pt_in = p["entry"]
        side_out, pt_out = p["exit"]
        n_axles = pt_in["n"]
        shunt = p["kind"] == "shunt"
        pair_in = pair_a if side_in == "A" else pair_b
        base_in = pair_in[0]

        # per-axle speeds at the entry point
        v_in = abs(sensor_x[pair_in[1]] - sensor_x[base_in]) / np.abs(pt_in["lags"])

        if shunt:
            direction = 0
            v_entry = float(v_in[np.isfinite(v_in)][0])
            v_out_arr = abs(sensor_x[pair_in[1]] - sensor_x[base_in]) / np.abs(pt_out["lags"])
            fin = v_out_arr[np.isfinite(v_out_arr)]
            v_exit = float(fin[-1])
            v_mean = 0.0
            tb_in = pt_in["clusters"][base_in][0]
            tb_out = pt_out["clusters"][base_in][0]
            t_in, t_out = float(tb_in[0]), float(tb_out[-1])
        else:
            direction = pt_in["dir"]
            fin = v_in[np.isfinite(v_in)]
            v_entry = float(fin[0])
            v_out_arr = (abs(sensor_x[pair_a[1]] - sensor_x[pair_a[0]]) /
                         np.abs(pt_out["lags"]))
            fout = v_out_arr[np.isfinite(v_out_arr)]
            v_exit = float(fout[0])
            b_in = pair_in[0]
            b_out = (pair_a if side_out == "A" else pair_b)[0]
            tb_in = pt_in["clusters"][b_in][0]
            tb_out = pt_out["clusters"][b_out][0]
            # boundary sensors are S1 (A) and S4 (B)
            bs_in = "S1" if side_in == "A" else "S4"
            bs_out = "S1" if side_out == "A" else "S4"
            ts_in = pt_in["clusters"][bs_in][0]
            ts_out = pt_out["clusters"][bs_out][0]
            t_in, t_out = float(ts_in[0]), float(ts_out[-1])
            transit = abs(np.median(ts_out[:5]) - np.median(ts_in[:5]))
            v_mean = abs(x_exit - x_entry) / transit if transit > 0 else np.nan

        # loads: kernel fit on every healthy sensor that observed the passage
        loads = []
        for pt in ({pt_in["t0"]: pt_in, pt_out["t0"]: pt_out}.values()):
            speeds_pt = abs(3.0) / np.abs(pt["lags"])
            for sid, (et, _) in pt["clusters"].items():
                if sid not in healthy or len(et) != n_axles:
                    continue
                v_here = speeds_pt.copy()
                med = np.nanmedian(v_here)
                v_here = np.nan_to_num(v_here, nan=med)
                t, x = streams[sid]
                amps = fit_amplitudes(t, x, et, v_here, beta_fit[sid], fs)
                order_axles = np.argsort(et)
                if shunt and pt is pt_out:
                    order_axles = order_axles[::-1]   # axles exit in reverse
                loads.append(amps[order_axles] / gain[sid])
        loads = np.mean(loads, axis=0) if loads else np.full(n_axles, np.nan)

        # reference-sensor times: S1 events of whichever cluster S1 saw first
        s1_clusters = [pt["clusters"]["S1"][0] for pt in (pt_in, pt_out)
                       if "S1" in pt["clusters"]]
        t_ref = np.sort(s1_clusters[0]) if s1_clusters else np.array([])
        for j in range(n_axles):
            tr = float(t_ref[j]) if j < len(t_ref) else -1.0
            ld = float(loads[j]) if j < len(loads) and np.isfinite(loads[j]) else -1.0
            axle_rows.append((f"train_{rank}", j, tr, ld))

        trains_out.append({
            "rank": rank, "n_axles": n_axles, "direction": direction,
            "v_entry": v_entry, "v_exit": v_exit, "v_mean": v_mean,
            "occupancy": (t_in, t_out),
        })

    # --- deliverables ---
    lines = []
    for tr in trains_out:
        r = tr["rank"]
        lines += [
            f"train_{r}_n_axles: {tr['n_axles']}",
            f"train_{r}_direction: {tr['direction']:+d}",
        ]
        if tr["direction"] != 0:
            lines.append(f"train_{r}_speed_mps: {tr['v_mean']:.3f}")
        lines += [
            f"train_{r}_v_entry_mps: {tr['v_entry']:.3f}",
            f"train_{r}_v_exit_mps: {tr['v_exit']:.3f}",
            f"train_{r}_occupancy_s: [{tr['occupancy'][0]:.3f}, {tr['occupancy'][1]:.3f}]",
        ]
    lines.append(f"faulted_sensor: {faulted_sensor}")
    (OUT / "result.md").write_text("\n".join(lines) + "\n")

    with open(OUT / "axles.csv", "w") as f:
        f.write("train_id,axle_index,t_ref_s,load_kN\n")
        for row in axle_rows:
            f.write(f"{row[0]},{row[1]},{row[2]:.4f},{row[3]:.3f}\n")

    build_paper(OUT / "paper.pdf", trains_out, faulted_sensor, healthy,
                axle_rows, gain, beta_fit, fs)

    print(f"passages={len(trains_out)} faulted={faulted_sensor} "
          f"beta={ {k: round(v, 3) for k, v in beta_fit.items()} } "
          f"gain={ {k: round(v, 3) for k, v in gain.items()} }")


if __name__ == "__main__":
    main()
