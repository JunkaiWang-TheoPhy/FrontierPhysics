---
name: shot-noise-theory
description: Predict the variance of an IQ-demodulated shot-noise signal from optical power, photon energy, detector conversion gain, and the integration window.
---

# Shot-noise variance after demodulation

Use this when a task asks for the expected variance of a demodulated optical
shot-noise trace. Read `references/shot-noise-variance.md` for the derivation
and match the model to the measurement's normalization.

## Workflow

1. Express optical power in watts and compute photon frequency
   `nu = c / wavelength`.
2. Use the detector's conversion gain for the measured signal and the same
   integration window as the data analysis.
3. For white shot noise and an un-normalized one-period integral, the expected
   variance is

       Var(P) = G**2 * P * h * nu * (T/2)

   where `T` is the integration-window duration. Derive the corresponding
   expression again if the IQ normalization or noise bandwidth differs.
4. Evaluate the requested power grid. A Monte Carlo check is useful, but should
   converge to the same expectation and should not replace a clear unit check.

The curve should be nonnegative, vanish at zero power, and be linear in power
under the white-shot-noise model. Preserve the requested output units.
