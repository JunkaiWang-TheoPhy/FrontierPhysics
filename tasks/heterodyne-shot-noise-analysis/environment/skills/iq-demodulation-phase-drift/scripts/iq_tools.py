"""IQ demodulation and phase-drift correction helpers. Import and call."""

from __future__ import annotations

import numpy as np


def demod(v, fs=50e6, f_iq=0.5e6):
    """Return (I, Q) arrays, one point per beat period (units V*s)."""
    m = int(fs / f_iq)
    dt = 1.0 / fs
    n = len(v) // m
    block = v[: n * m].reshape(n, m)
    t = np.arange(m) * dt
    i = (block * np.sin(2 * np.pi * f_iq * t)).sum(1) * dt
    q = (block * np.cos(2 * np.pi * f_iq * t)).sum(1) * dt
    return i, q


def correct_phase_drift(i, q, fs=50e6, f_iq=0.5e6):
    """Remove the linear phase drift from a signal cloud.

    Returns (i_corrected, q_corrected, drift_rate_rad_per_s).
    """
    m = int(fs / f_iq)
    t = np.arange(len(i)) * (m / fs)
    theta = np.unwrap(np.arctan2(q, i))
    slope, intercept = np.polyfit(t, theta, 1)
    ideal = slope * t + intercept
    z = (i + 1j * q) * np.exp(1j * (ideal[0] - ideal))
    return z.real, z.imag, float(slope)
