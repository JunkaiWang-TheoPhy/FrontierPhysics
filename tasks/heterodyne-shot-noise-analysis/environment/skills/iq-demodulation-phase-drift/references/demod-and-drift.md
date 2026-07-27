# Demodulation and phase-drift conventions

## Per-period demodulation

    M  = fs / f_IQ            # samples per beat period (integer)
    dt = 1 / fs
    t_k = k*dt, k = 0..M-1    # within-window time, restarts each window

    I = sum_k v_k sin(2*pi*f_IQ*t_k) dt
    Q = sum_k v_k cos(2*pi*f_IQ*t_k) dt

For a tone `v = A sin(2*pi*f_IQ*t + phi)`, one-period integration gives
`I = (A T/2) cos(phi)`, `Q = (A T/2) sin(phi)`, so the point sits at radius
`A T/2` and angle `phi`. Noise adds an isotropic scatter of order the shot-noise
std.

## Why the signal is a ring

`phi` drifts linearly with time (unsynchronized clocks): `phi(t) = omega t + phi0`.
Over the capture the points sweep an annulus (ring) of radius `A T/2`.

## Collapsing the ring

Unwrap the measured phase, fit the linear trend, and de-rotate:

    theta        = unwrap(arctan2(Q, I))
    slope, b     = polyfit(t_window, theta, 1)     # slope = omega [rad/s]
    ideal        = slope*t_window + b
    z_corrected  = (I + iQ) * exp(-i*(ideal - ideal[0]))

The `- ideal[0]` keeps the cloud on its original axis. The de-rotation is
invariant to the absolute time scale, but the reported drift rate `omega`
requires the real per-window time `t_window = k * M / fs`.

The vacuum cloud is not de-rotated. After correction the signal centroid
`d = |<I+iQ>|` is the clean coherent amplitude and the residual spread is the
shot noise.
