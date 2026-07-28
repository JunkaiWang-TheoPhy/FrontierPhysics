#!/usr/bin/env python3
"""Physics core for the YIG magnon dispersion + pumped-magnon-gas task (oracle copy).

Part A -- dipole-exchange spin-wave dispersion of a magnetized YIG film
(Rezende, PRB 79, 174411 (2009)); extract the saturation magnetization 4piM
(Kittel) and the exchange stiffness D (from the spectral minimum f_min), then
predict the surface (Damon-Eshbach) branch and a second film's spectral minimum.

Part B -- thermodynamics of the parametrically pumped magnon gas following
Demokritov et al., Nature 443, 430 (2006): the exchange-dominated 3D bulk
thermal magnon gas (Bloch T^3/2 law), the chemical potential / temperature of
the pumped quasi-equilibrium gas from magnon-number and energy conservation,
the critical pumped density for Bose-Einstein condensation, and the condensed
branch (condensate fraction) of a supercritically pumped gas.
"""

from __future__ import annotations

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq, fsolve

H_PLANCK = 6.62607015e-34  # J s
KB = 1.380649e-23  # J / K
GAMMA = 2.8e-3  # GHz / Gauss  (gyromagnetic ratio for YIG)

# ============================ PART A ============================
# NV3 experimental inputs (film 1)
NV3 = {"H": 330.0, "f_FMR": 2.395, "f_min": 1.913, "d": 0.206e-4}  # d in cm (0.206 um)
D2_FILM = 0.5e-4  # second film thickness (cm), same material, same field H
K_S = 8.0e4  # surface-branch (theta = pi/2) probe wavevector (cm^-1) for film 1


def _F(k, d):
    k = np.asarray(k, float)
    return np.where(k != 0, (1 - np.exp(-k * d)) / (k * d), 1.0)


def film_dispersion_GHz(k, theta, H, fourpiM, D, d):
    """Rezende dipole-exchange film magnon frequency (GHz). k in cm^-1."""
    a = H + D * k**2 + fourpiM * (1 - _F(k, d)) * np.sin(theta) ** 2
    b = H + D * k**2 + fourpiM * _F(k, d)
    return GAMMA * np.sqrt(a * b)


def extract_fourpiM(f_FMR, H):
    """Kittel: f_FMR = gamma sqrt(H (H + 4piM))  ->  4piM."""
    return f_FMR**2 / (GAMMA**2 * H) - H


def film_fmin(H, fourpiM, D, d, n=400000):
    ks = np.linspace(1.0, 3e5, n)
    fk = film_dispersion_GHz(ks, 0.0, H, fourpiM, D, d)
    i = int(np.argmin(fk))
    return float(fk[i]), float(ks[i])


def extract_D(f_min_meas, H, fourpiM, d):
    """Fit D so the backward-volume (theta=0) spectral minimum equals f_min."""
    return brentq(lambda D: film_fmin(H, fourpiM, D, d)[0] - f_min_meas, 1e-10, 3e-8)


def part_A():
    p = NV3
    fourpiM = extract_fourpiM(p["f_FMR"], p["H"])
    D = extract_D(p["f_min"], p["H"], fourpiM, p["d"])
    fmin, kmin = film_fmin(p["H"], fourpiM, D, p["d"])
    # surface (Damon-Eshbach, theta = pi/2) branch of film 1 at K_S
    f_DE = float(film_dispersion_GHz(K_S, np.pi / 2, p["H"], fourpiM, D, p["d"]))
    # second film (same material -> same 4piM, D) spectral minimum at thickness D2_FILM
    fmin2, kmin2 = film_fmin(p["H"], fourpiM, D, D2_FILM)
    return {
        "fourpiM_G": fourpiM,
        "D_Oecm2": D,
        "f_min_GHz": fmin,
        "k_min_percm": kmin,
        "f_DE_GHz": f_DE,
        "fmin2_GHz": fmin2,
        "kmin2_percm": kmin2,
    }


# ============================ PART B ============================
# Config B1: Nature-06 YIG system + sub-critical pumping
NB = {"H": 700.0, "D": 2e-9}  # Gauss, Oe cm^2
T0 = 300.0  # K
NU_P = 4.0e9  # pumped magnon frequency (Hz)
DELTA_N = 5e18  # pumped magnon density (cm^-3)

# Config B2: a second YIG system, supercritically pumped (condenses)
NB2 = {"H": 500.0, "D": 2e-9}
T0_2 = 300.0
NU_P2 = 4.0e9
DELTA_N2 = 1.5e20  # cm^-3 (chosen well above the B2 critical density)

# Config B3: interlocked system that uses the exchange stiffness extracted in Part A
NB3 = {"H": 400.0}  # D supplied from Part A at runtime
T0_3 = 300.0
DELTA_N3 = 2e18  # cm^-3


def _eps(k, H, D):
    """3D bulk exchange magnon energy (J). k in cm^-1."""
    return H_PLANCK * GAMMA * (H + D * k**2) * 1e9


def bulk_density(T, mu, H, D):
    """3D bulk thermal magnon density (cm^-3): n = (1/2pi^2) int k^2 nBE dk."""
    val, _ = quad(lambda k: k**2 / np.expm1((_eps(k, H, D) - mu) / (KB * T)), 0, 3e8, limit=600)
    return val / (2 * np.pi**2)


def bulk_energy(T, mu, H, D):
    val, _ = quad(lambda k: k**2 * _eps(k, H, D) / np.expm1((_eps(k, H, D) - mu) / (KB * T)), 0, 3e8, limit=600)
    return val / (2 * np.pi**2)


def _subcritical_solve(H, D, T0_cfg, nu_p, delta_n, n0, e0):
    """Pumped sub-critical quasi-equilibrium: conserve number and energy -> (T, mu)."""
    nT = n0 + delta_n
    eT = e0 + H_PLANCK * nu_p * delta_n
    eps_min = _eps(0.0, H, D)
    sol = fsolve(
        lambda v: [(bulk_density(v[0], v[1], H, D) - nT) / nT, (bulk_energy(v[0], v[1], H, D) - eT) / eT],
        [T0_cfg, eps_min * 0.3],
        full_output=True,
    )
    (T_p, mu_p), ier = sol[0], sol[2]
    return T_p, mu_p, bool(ier == 1)


def _condensed_solve(H, D, T0_cfg, nu_p, delta_n, n0, e0):
    """Pumped supercritical branch: mu pinned at eps_min, conserve number+energy
    for (T, condensate density n_c). Returns (T_p, condensate_fraction)."""
    eps_min = _eps(0.0, H, D)
    mu_pin = eps_min * (1 - 1e-12)
    n_tot = n0 + delta_n
    e_tot = e0 + H_PLANCK * nu_p * delta_n

    def f_T(T):
        n_th = bulk_density(T, mu_pin, H, D)
        return bulk_energy(T, mu_pin, H, D) + (n_tot - n_th) * eps_min - e_tot

    T_p = brentq(f_T, 20.0, 3.0 * T0_cfg)
    n_c = n_tot - bulk_density(T_p, mu_pin, H, D)
    return T_p, n_c / n_tot


def part_B(D_from_A=None):
    # ---- Config B1 (sub-critical) ----
    H, D = NB["H"], NB["D"]
    eps_min = _eps(0.0, H, D)  # k=0 gap = h gamma H
    n0 = bulk_density(T0, 0.0, H, D)
    e0 = bulk_energy(T0, 0.0, H, D)
    n_crit = bulk_density(T0, eps_min * (1 - 1e-9), H, D)  # density at mu -> eps_min
    dN_c = n_crit - n0
    T_p, mu_p, conv1 = _subcritical_solve(H, D, T0, NU_P, DELTA_N, n0, e0)
    # Bloch exponent of the gapless 3D gas: n0(T) ~ T^p near T0
    p_bloch = float(np.log(bulk_density(2 * T0, 0.0, H, D) / n0) / np.log(2.0))

    # ---- Config B2 (supercritical -> condensate) ----
    H2, D2 = NB2["H"], NB2["D"]
    eps_min2 = _eps(0.0, H2, D2)
    n0_2 = bulk_density(T0_2, 0.0, H2, D2)
    e0_2 = bulk_energy(T0_2, 0.0, H2, D2)
    dN_c2 = bulk_density(T0_2, eps_min2 * (1 - 1e-9), H2, D2) - n0_2
    bec2 = bool(DELTA_N2 > dN_c2)
    T_p2, ncfrac2 = _condensed_solve(H2, D2, T0_2, NU_P2, DELTA_N2, n0_2, e0_2)

    # ---- Config B3 (A->B interlock: uses D extracted in Part A) ----
    D3 = D_from_A if D_from_A is not None else part_A()["D_Oecm2"]
    H3 = NB3["H"]
    eps_min3 = _eps(0.0, H3, D3)
    n0_3 = bulk_density(T0_3, 0.0, H3, D3)
    dN_c3 = bulk_density(T0_3, eps_min3 * (1 - 1e-9), H3, D3) - n0_3
    bec3 = bool(DELTA_N3 > dN_c3)

    return {
        # config B1
        "eps_min_mK": eps_min / KB * 1e3,
        "n0_percm3": n0,
        "e0_Jpercm3": e0,
        "p_bloch": p_bloch,
        "dN_c_percm3": dN_c,
        "mu_p_mK": mu_p / KB * 1e3,
        "T_p_K": T_p,
        "bec": bool(DELTA_N > dN_c),
        "converged": conv1,
        # config B2 (supercritical)
        "eps_min2_mK": eps_min2 / KB * 1e3,
        "dN_c2_percm3": dN_c2,
        "bec2": bec2,
        "ncfrac2": ncfrac2,
        "T_p2_K": T_p2,
        # config B3 (interlock)
        "n0_3_percm3": n0_3,
        "dN_c3_percm3": dN_c3,
        "bec3": bec3,
    }


if __name__ == "__main__":
    import json

    A = part_A()
    B = part_B(D_from_A=A["D_Oecm2"])
    print(json.dumps({"A": A, "B": B}, indent=2))
