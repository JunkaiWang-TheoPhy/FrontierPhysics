# Shot-noise standard deviation of the demodulated points

White shot noise at total LO power `P_LO` gives a per-sample optical-power
variance `P_LO * h*nu * fs` (single-sided, to fs/2). The RF voltage is
`v = G * delta_P`, so per-sample voltage variance is `G**2 * P_LO * h*nu * fs`.

One-beat-period IQ integration (M = fs/f_IQ samples, `sum sin^2 = sum cos^2 =
M/2`) turns this into a per-quadrature variance

    Var(I) = G**2 * P_LO * h*nu * fs * dt**2 * (M/2)
           = G**2 * P_LO * h*nu * (T/2),     T = 1/f_IQ

(the sampling rate cancels), so

    sigma_shot = G * sqrt( P_LO * h*nu * (T/2) )

Use `P_LO = P_LO1 + P_LO2` from the vacuum acquisition (watts). The Monte-Carlo
simulation of the same process converges to this.

## Fraction

    shot_noise_fraction = (sigma_shot / sigma_measured)**2

with `sigma_measured` the measured vacuum-cloud std (mean of the two principal
stds). Near 1 => shot-noise limited.
