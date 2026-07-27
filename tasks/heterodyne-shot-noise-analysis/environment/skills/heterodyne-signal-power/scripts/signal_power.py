"""LO power and signal power helpers. Import and call; nothing here writes a
deliverable."""

from __future__ import annotations

import numpy as np
from scipy.constants import c, h


def lo_power_uw(monitor_v, monitor_scale=100.0):
    """LO power (uW) from one monitor-channel voltage array."""
    return float(np.mean(monitor_v)) * monitor_scale


def vpp_from_displacement(displacement, f_iq=0.5e6):
    """Clean beat Vpp from the phase-corrected IQ centroid magnitude d = A*T/2."""
    return 4.0 * displacement / (1.0 / f_iq)


def signal_power_w(vpp, p_lo1_uw, p_lo2_uw, gain_g=257.988e3):
    """Signal optical power (W) from the beat Vpp and the signal-run LO powers."""
    op_pp = vpp / gain_g
    return (op_pp / 4.0 / (np.sqrt(p_lo1_uw * 1e-6) + np.sqrt(p_lo2_uw * 1e-6))) ** 2 * 2.0


def photon_rate_per_us(p_sig_w, wavelength=795e-9):
    return p_sig_w / (h * (c / wavelength)) * 1e-6
