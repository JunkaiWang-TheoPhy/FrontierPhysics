# Discrimination, std, and theoretical error rate

## Linear threshold error rate

Let the drift-corrected signal centroid be `m = <(I,Q)>` with magnitude
`d = |m|` and unit vector `u = m / d`. Project points onto `u`:

    proj = I*u_x + Q*u_y

Threshold at `d/2`. A signal point with `proj < d/2` is an error; a vacuum point
with `proj > d/2` is an error. `error_rate = (n_sig_err + n_vac_err) / n_total`.

## Standard deviations

Measured vacuum std: eigen-decompose the biased 2x2 covariance of the vacuum
(I, Q); take the mean of the square roots of the two eigenvalues.

Theoretical std from the photon number: in heterodyne, collecting `N` signal
photons places the cloud at displacement `2 sqrt(N)` with per-axis std `sqrt(2)`,
so

    std / displacement = sqrt(2) / (2 sqrt(N)) = 1 / sqrt(2 N)
    theoretical_std     = d / sqrt(2 N)

`measured_std / theoretical_std` is ~1 when shot-noise-limited.

## Theoretical heterodyne error rate

Using normalized quadrature units (per-axis std `sigma = sqrt(2)`, signal mean
`mu = 2 sqrt(N)`, vacuum mean 0, midpoint threshold `x_th = mu/2 = sqrt(N)`):

    P_sig_err = Phi(x_th; mu, sigma)
    P_vac_err = 1 - Phi(x_th; 0, sigma)
    P_err     = 0.5 * (P_sig_err + P_vac_err)

`P_err` is sensitive to `N`, so an inaccurate signal power (photon number) shows
up strongly here even when it barely moves the signal-power estimate itself.
