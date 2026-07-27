---
name: iq-demodulation-phase-drift
description: IQ-demodulate a balanced-heterodyne trace one beat period at a time and remove the slow linear optical-phase drift from the coherent-state cloud so it collapses from a ring to a blob on the IQ plane. Covers the sin/cos integration convention and the unwrap-fit-derotate procedure.
---

# IQ demodulation and phase-drift correction

See `references/demod-and-drift.md`; `scripts/iq_tools.py` has the helpers.

## IQ demodulation (deliverable 3)

Split each trace into consecutive one-beat-period windows of `M = fs / f_IQ`
samples (100 at fs = 50 MHz, f_IQ = 500 kHz). For each window, with the
within-window time restarting at 0,

    I = sum v * sin(2*pi*f_IQ*t) * dt,   Q = sum v * cos(2*pi*f_IQ*t) * dt

(no normalization; units volt-seconds). This gives one (I, Q) point per period
for the vacuum trace and for the signal trace.

## Phase-drift correction (deliverable 4)

The signal cloud is a ring because the beat phase drifts linearly in time. To
collapse it to a blob:

1. `theta = unwrap(arctan2(Q, I))` for the signal points.
2. Fit `theta ~ slope*t + intercept` (the slope is the drift rate in rad/s using
   the real per-window time `t = k * M / fs`).
3. De-rotate every signal point by the negative of the fitted linear phase
   (referenced to the first point): `z_corrected = (I + iQ) * exp(-i*(fit - fit[0]))`.

Apply the de-rotation only to the signal cloud; the vacuum cloud is centered at
the origin and is left as measured. After correction the signal cloud is a
compact blob whose spread is close to the vacuum shot-noise spread.
