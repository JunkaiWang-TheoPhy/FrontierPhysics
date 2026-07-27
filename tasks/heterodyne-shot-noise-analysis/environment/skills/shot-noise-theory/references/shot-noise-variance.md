# Theoretical demodulated shot-noise variance

## Per-sample shot noise

For optical power `P` on a shot-noise-limited detector, the fluctuating optical
power sampled at `fs` has per-sample variance

    var(delta_P) = P * h*nu * fs

for white noise up to the sampling bandwidth. The measured signal
`v = G*delta_P` therefore has per-sample variance
`G**2 * P * h*nu * fs`.

## Through the demodulator

For a one-period window of `M` independent samples and an integer-period
reference, `sum sin^2 = sum cos^2 = M/2`:

    Var(I) = var(v) * dt**2 * (M/2)
           = G**2 * P * h*nu * fs * (1/fs**2) * (M/2)
           = G**2 * P * h*nu * (T/2),   T = M*dt

The sampling rate cancels. For an isotropic cloud, the principal-axis statistic
`((sigma_major+sigma_minor)/2)**2` has the same expectation as `Var(I)`.

## Monte Carlo equivalent

Draw `delta_P ~ Normal(0, sqrt(P*h*nu*fs))` of length `M`, set `v = G*delta_P`,
demodulate, repeat for many windows, and compute the same cloud statistic. The
expectation approaches the closed form.

## Units

Use watts for `P`, hertz for `nu`, seconds for `T`, and keep the resulting
variance in the units implied by the chosen IQ normalization.
