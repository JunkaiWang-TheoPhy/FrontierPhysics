"""Discrimination, std, and theoretical error-rate helpers. Import and call."""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def principal_stds(x, y):
    ev = np.sort(np.linalg.eigh(np.cov(np.vstack((x, y)), bias=True))[0])[::-1]
    return np.sqrt(ev[0]), np.sqrt(ev[1])


def linear_threshold_error_rate(sig_i, sig_q, vac_i, vac_q):
    """Return (error_rate, sig_errors, vac_errors, displacement, threshold)."""
    mx, my = np.mean(sig_i), np.mean(sig_q)
    d = np.hypot(mx, my)
    ux, uy = mx / d, my / d
    thr = d / 2.0
    sig_err = int((sig_i * ux + sig_q * uy < thr).sum())
    vac_err = int((vac_i * ux + vac_q * uy > thr).sum())
    total = len(sig_i) + len(vac_i)
    return (sig_err + vac_err) / total, sig_err, vac_err, float(d), float(thr)


def theoretical_std(displacement, photon_number):
    return displacement / np.sqrt(2.0 * photon_number)


def heterodyne_error_rate(photon_number):
    sigma = np.sqrt(2.0)
    mu = 2.0 * np.sqrt(photon_number)
    x_th = mu / 2.0
    return 0.5 * (norm.cdf(x_th, mu, sigma) + (1.0 - norm.cdf(x_th, 0.0, sigma)))
