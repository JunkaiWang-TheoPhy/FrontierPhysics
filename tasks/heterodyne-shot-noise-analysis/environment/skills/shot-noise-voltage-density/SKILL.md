---
name: shot-noise-voltage-density
description: Compute a photodetector shot-noise voltage amplitude density from optical power, responsivity, and transimpedance, while keeping density and bandwidth-integrated rms quantities distinct.
---

# Shot-noise voltage density

Use this when a photodetector or spectrum-analyzer task asks for the theoretical
voltage noise density. Read `references/shot-noise-density.md`, identify the
instrument calibration that applies to the spectral measurement, and implement
the calculation directly.

## Workflow

1. Convert the optical power reaching the detector to watts.
2. Use the documented optical responsivity `R` and transimpedance `Z`:

       S_V = 2 * e * Z**2 * R * P   [V**2/Hz]

3. Report the amplitude density:

       sqrt(S_V)  [V/sqrt(Hz)]

Do not multiply by resolution bandwidth when the requested quantity is a
per-root-hertz density. To compare a measured per-bin rms value with it, divide
the rms value by `sqrt(RBW)`.

If the detector has separate optical/DC and RF calibrations, use the optical/DC
values for this density only when the measurement model calls for them; do not
silently substitute a signal-conversion gain.
