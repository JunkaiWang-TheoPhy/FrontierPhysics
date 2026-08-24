"""Dual-grating differential FBG transduction, temperature, and noise.

Sensor model per patents CN106476845B / CN206317836U (author's inventions):
two gratings on opposite faces of one bending substrate clamped to the rail
foot; strain moves them oppositely, temperature moves them together.

    wl1 = L1 + Keps * g * eps + KT1 * (T - T_REF) + noise
    wl2 = L2 - Keps * g * eps + KT2 * (T - T_REF) + noise

g is the per-sensor clamp strain-transfer ratio; KT1 != KT2 by a small
mismatch so common-mode rejection is good but imperfect (realism).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

K_EPS_PM_PER_UE = 1.0     # pm/microstrain     [patents]
K_T_PM_PER_C = 10.0       # pm/degC            [patents]
WL1_PM = 1_530_000.0      # pm (1530 nm)       [patents]
WL2_PM = 1_535_000.0      # pm (1535 nm)       [patents]
T_REF_C = 20.0            # installation reference temperature
NOISE_PM_RMS = 3.0        # interrogator wavelength noise (outdoor)
QUANT_PM = 0.1            # interrogator wavelength quantization
SAMPLE_RATE_HZ = 1000.0


@dataclass
class Sensor:
    sensor_id: str
    x_m: float                 # position along the section
    k_foundation: float        # local Winkler modulus (site-dependent)
    transfer: float            # clamp strain-transfer ratio (faulted ~0.5)
    kt_mismatch: float         # fractional KT2/KT1 - 1
    temp_lag_s: float          # solar-transient arrival lag at this sensor
    temp_offset_c: float       # per-sensor static offset (shading)
    is_faulted: bool = False


def rail_temperature_c(t_s: np.ndarray, sensor: Sensor,
                       transient_center_s: float = 1050.0,
                       transient_amp_c: float = 8.0,
                       transient_rise_s: float = 60.0,
                       ramp_c_per_window: float = 2.5,
                       window_s: float = 1500.0) -> np.ndarray:
    """Rail temperature at one sensor: slow ramp + fast solar transient."""
    base = T_REF_C + sensor.temp_offset_c + ramp_c_per_window * (t_s / window_s)
    arg = (t_s - (transient_center_s + sensor.temp_lag_s)) / transient_rise_s
    transient = transient_amp_c / (1.0 + np.exp(-np.clip(arg, -60, 60)))
    return base + transient


def transduce(eps_rail: np.ndarray, temp_c: np.ndarray, sensor: Sensor,
              rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Rail-foot strain + temperature -> two absolute wavelength streams (pm)."""
    eps_ue = eps_rail * 1e6 * sensor.transfer
    dT = temp_c - T_REF_C
    kt1 = K_T_PM_PER_C
    kt2 = K_T_PM_PER_C * (1.0 + sensor.kt_mismatch)
    wl1 = WL1_PM + K_EPS_PM_PER_UE * eps_ue + kt1 * dT
    wl2 = WL2_PM - K_EPS_PM_PER_UE * eps_ue + kt2 * dT
    wl1 = wl1 + rng.normal(0.0, NOISE_PM_RMS, wl1.shape)
    wl2 = wl2 + rng.normal(0.0, NOISE_PM_RMS, wl2.shape)
    wl1 = np.round(wl1 / QUANT_PM) * QUANT_PM
    wl2 = np.round(wl2 / QUANT_PM) * QUANT_PM
    return wl1, wl2


def make_sensors(rng: np.random.Generator) -> list[Sensor]:
    """The four-sensor block-section deployment; S3 has a hidden fault."""
    from rail_model import K_FOUNDATION_NOMINAL

    positions = [("S1", 0.0), ("S2", 3.0), ("S3", 1000.0), ("S4", 1003.0)]
    sensors = []
    for sensor_id, x in positions:
        faulted = sensor_id == "S3"
        # Fault: temperature-compensation failure — the grating pair's KT
        # mismatch is an order of magnitude out of family, so thermal drift
        # leaks into the differential channel. Strain gain stays normal.
        sensors.append(Sensor(
            sensor_id=sensor_id,
            x_m=x,
            k_foundation=K_FOUNDATION_NOMINAL * rng.uniform(0.7, 1.3),
            transfer=rng.uniform(0.85, 1.0),
            kt_mismatch=0.15 * rng.choice([-1, 1]) if faulted
                        else float(np.clip(rng.normal(0.0, 0.015), -0.04, 0.04)),
            temp_lag_s=x / 1003.0 * 25.0 + rng.uniform(0, 5),
            temp_offset_c=rng.uniform(-1.0, 1.0),
            is_faulted=faulted,
        ))
    return sensors
