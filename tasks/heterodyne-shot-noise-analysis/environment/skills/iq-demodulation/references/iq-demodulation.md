# IQ demodulation conventions

## Window

Produce one `(I, Q)` point per integration window. For a sampled reference
frequency `f0` and sampling rate `fs`, use a window containing an integer number
of periods:

    M = integer number of samples in the chosen window
    dt = 1 / fs
    t_k = k * dt, k = 0..M-1

Partition the trace into consecutive non-overlapping windows and drop the final
partial window. Restart `t_k` at zero for every window. If the period is not an
integer number of samples, choose a consistent integer-period window and record
the resulting approximation.

## Demodulation integrals

For an un-normalized convention:

    I = sum_k v_k * sin(2*pi*f0*t_k) * dt
    Q = sum_k v_k * cos(2*pi*f0*t_k) * dt

There is no `2/T` amplitude normalization, so I and Q carry units of
volt-seconds. If a task specifies a different convention, follow that
specification instead.

## Principal standard deviations

Stack the per-window I and Q values and form the biased 2x2 covariance matrix.
Its eigenvalues are the variances along the principal axes; their square roots
are `sigma_major >= sigma_minor`. For isotropic noise the cloud is circular.

For the common isotropic-cloud statistic:

    Variance = ((sigma_major + sigma_minor) / 2) ** 2

## Operating-point calibration

When monitor channels encode an operating point such as optical power, average
each channel over the record and apply the documented instrument calibration.
Keep the calibration units explicit and distinguish summed, differential, and
single-channel quantities.
