---
name: heterodyne-shot-noise-budget
description: Compute the theoretical (or Monte-Carlo) shot-noise standard deviation of the IQ-demodulated points for a given local-oscillator power, and the fraction of the total measured noise that is shot noise.
---

# Shot-noise budget

See `references/shot-noise.md`; `scripts/shot_noise.py` has the helper.

## Simulated shot-noise std (deliverable 6)

For the vacuum measurement the IQ points scatter by shot noise set by the LO
power. With per-sample optical-power variance `P_LO * h*nu * fs`, scaled by the
RF gain `G` and integrated over one beat period, the demodulated per-quadrature
std is

    sigma_shot = G * sqrt( P_LO * h*nu * (T/2) ),   T = 1/f_IQ

where `P_LO = P_LO1 + P_LO2` is the total LO power (in watts) from the vacuum
acquisition. A Monte-Carlo simulation (draw `delta_P ~ Normal(0, sqrt(P_LO h nu
fs))`, form `v = G delta_P`, demodulate one period, repeat, take the principal
std) reproduces this in expectation.

## Shot-noise fraction

    shot_noise_fraction = (sigma_shot / sigma_measured)**2

using the measured vacuum-cloud std. A value near 1 means the measurement is
shot-noise limited; smaller means extra technical noise is present.
