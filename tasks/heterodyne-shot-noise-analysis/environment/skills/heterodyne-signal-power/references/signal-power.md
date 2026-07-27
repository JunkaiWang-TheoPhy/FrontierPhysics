# Signal power from the balanced-heterodyne beat

## Interference amplitude

Write the field amplitude as `E = sqrt(P)`. On the balanced detector the two
arms carry the local oscillator (LO1, LO2) and the signal splits equally between
them. The differential (monitor1 - monitor2) oscillation peak-to-peak optical
power is

    OP_pp = 4 * (sqrt(P_LO1) + sqrt(P_LO2)) * sqrt(P_sig / 2)

Inverting for the signal optical power,

    P_sig = 2 * ( OP_pp / (4 (sqrt(P_LO1) + sqrt(P_LO2))) )**2

The measured voltage peak-to-peak relates to the optical peak-to-peak through
the RF conversion gain `G` (V/W): `OP_pp = Vpp / G`. Use `G = 257.988e3`.

## Photon rate

    rate = P_sig / (h * nu),   nu = c / 795 nm     [photons / s]

Report per microsecond, and the mean photons per demodulation window
`N = rate * T` with `T = 1 / f_IQ`.

## Clean amplitude extraction

The beat phase drifts slowly over the capture (unsynchronized clocks). Consider
the amplitude estimators:

- **Windowed FFT peak**: biased *low*, because the drifting tone spreads across
  frequency bins; the longer the capture, the larger the loss.
- **2*sqrt(2)*RMS**: biased *high*, because the RMS includes the shot noise, not
  just the coherent oscillation.
- **Phase-corrected IQ displacement (recommended)**: demodulate per period,
  remove the linear phase drift, and take the signal centroid magnitude
  `d = |<I + iQ>|`. For a tone of amplitude `A`, one-period demodulation gives
  `|I + iQ| = A*T/2`, so `Vpp = 2A = 4 d / T`. The shot noise averages out in the
  centroid, so this is unbiased.

A correct signal power makes the photon number from power agree with the
gain-independent photon number `N = (d / sigma)**2 / 2` (displacement over
vacuum std) and makes the measured statistics match the shot-noise theory.
