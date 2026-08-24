"""Rail mechanics: Euler-Bernoulli beam on a Winkler elastic foundation.

Quasi-static response of a continuously supported rail to moving wheel
loads. Patent references are the task author's own inventions.
"""

from __future__ import annotations

import numpy as np

# --- CN60 rail (60 kg/m), section per GB 2585: Ix = 3217 cm^4, section
# centroid 80.9 mm above the rail base ---
E_RAIL = 215e9          # Pa            [author design records]
I_CN60 = 3.217e-5       # m^4           [GB 2585]
C_FOOT = 0.0809         # m, neutral axis -> rail foot fiber [GB 2585]

# Ballasted-track Winkler foundation modulus, nominal (site-varied by the
# generator). Standard range ~20-100 MN/m^2 (e.g. Esveld, Modern Railway
# Track, 2nd ed. 2001; Hetenyi, Beams on Elastic Foundation, 1946).
K_FOUNDATION_NOMINAL = 68e6  # N/m^2

G_ACCEL = 9.80665       # m/s^2


def beta_of_k(k: float) -> float:
    """Characteristic wavenumber beta = (k / 4EI)^(1/4)  [1/m]."""
    return (k / (4.0 * E_RAIL * I_CN60)) ** 0.25


def foot_strain_kernel(x: np.ndarray, wheel_load_n: float, beta: float) -> np.ndarray:
    """Rail-foot bending strain at longitudinal offset x from one wheel.

    M(x) = (P / 4 beta) * exp(-b|x|) (cos b|x| - sin b|x|); tension positive
    at the foot under the wheel, with the characteristic negative (uplift)
    side lobes beyond b|x| = pi/4.
    """
    bx = beta * np.abs(x)
    moment = (wheel_load_n / (4.0 * beta)) * np.exp(-bx) * (np.cos(bx) - np.sin(bx))
    return moment * C_FOOT / (E_RAIL * I_CN60)


def peak_foot_strain(wheel_load_n: float, beta: float) -> float:
    """Peak strain directly under one wheel: P c / (4 beta E I)."""
    return wheel_load_n * C_FOOT / (4.0 * beta * E_RAIL * I_CN60)
