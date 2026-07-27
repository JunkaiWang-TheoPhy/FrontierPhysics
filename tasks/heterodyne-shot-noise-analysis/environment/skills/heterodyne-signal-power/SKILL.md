---
name: heterodyne-signal-power
description: Extract local-oscillator power from balanced-detector monitor channels and the weak coherent-state signal power (and photon rate) from the balanced-heterodyne beat amplitude. Emphasizes extracting the beat amplitude cleanly, since a windowed FFT loses coherent power to the slow phase drift over a long capture and biases the signal power.
---

# LO power and signal power from heterodyne data

See `references/signal-power.md` for the interferometry and the amplitude
caveat; `scripts/signal_power.py` has the helpers.

## LO power (deliverable 1)

Each monitor channel voltage converts to optical power with the PDB210A monitor
calibration, `P[uW] = 100 * mean(V_monitor)` (recover the 100 uW/V factor from
the monitor transimpedance and responsivity in the manual). Report LO1, LO2 for
both the vacuum and signal acquisitions from `CHAN2` and `CHAN3`.

## Signal power and photon rate (deliverable 2)

The balanced (monitor1 - monitor2) beat has peak-to-peak amplitude

    Vpp = 4 * (sqrt(P_LO1) + sqrt(P_LO2)) * sqrt(P_sig / 2)   /   ... (see reference)

which inverts to

    P_sig = 2 * ( (Vpp / G) / (4 (sqrt(P_LO1) + sqrt(P_LO2))) )**2

with `G = 257.988e3` V/W (given), `P_LO` from the signal acquisition (in watts).
Then photon rate `= P_sig / (h*nu)` (795 nm); report per microsecond.

**Extract Vpp carefully.** The beat is not a pure tone: the detector and scope
are unsynchronized, so its phase drifts across the capture. A single-bin
windowed FFT therefore *underestimates* the amplitude (coherent power spreads
across bins), and `2*sqrt(2)*RMS` *overestimates* it (the shot noise adds to the
RMS). The unbiased amplitude is the phase-corrected IQ-demodulation displacement:
after removing the drift (see the iq-demodulation-and-phase-drift skill), the
signal centroid magnitude `d = |<I+iQ>|` satisfies `d = A*T/2`, so
`Vpp = 2A = 4 d / T`. Using this clean `Vpp` with the true gain gives a signal
power consistent with the shot-noise statistics.
