"""Shot-noise std helper. Import and call."""

from __future__ import annotations

import numpy as np
from scipy.constants import c, h


def shot_noise_std(p_lo_total_w, gain_g=257.988e3, f_iq=0.5e6, wavelength=795e-9):
    """Analytic per-quadrature shot-noise std of the demodulated points."""
    nu = c / wavelength
    return gain_g * np.sqrt(p_lo_total_w * (h * nu) * ((1.0 / f_iq) / 2.0))


def shot_noise_fraction(sigma_shot, sigma_measured):
    return (sigma_shot / sigma_measured) ** 2
