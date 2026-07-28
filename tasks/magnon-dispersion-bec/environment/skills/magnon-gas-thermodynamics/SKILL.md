---
name: magnon-gas-thermodynamics
description: Reusable guidance for YIG-film spin-wave calculations and equilibrium or pumped magnon-gas thermodynamics.
---

# YIG spin waves and magnon gases

Use this guide when a problem combines finite-thickness ferromagnetic-film
spectra with a thermal or pumped magnon gas. Keep the field, wavevector,
thickness, frequency, and energy units consistent before doing any fitting or
integration.

## Film spectra

- Use the full finite-thickness dipole-exchange dispersion for an
  in-plane-magnetized film. With `theta` measured from the magnetization,
  `F(x) = (1 - exp(-x))/x` and

  `f(k, theta) = gamma * sqrt((H + D*k^2 + 4piM*(1 - F(k*d))*sin(theta)^2) * (H + D*k^2 + 4piM*F(k*d)))`.

  Take `F(0) = 1`, keep the propagation angle, and use the units supplied by
  the problem. An exchange-only or bulk approximation can give the wrong
  branch and minimum.
- At zero wavevector, use the Kittel relation to infer the saturation
  magnetization when an FMR frequency is supplied.
- Infer exchange stiffness from an observed finite-wavevector minimum by
  minimizing the backward-volume branch while fitting the stiffness. Recompute
  the minimum after changing only the thickness when comparing films of the
  same material.
- Evaluate surface or Damon-Eshbach predictions with the same material
  parameters and full form factor. Use a bounded minimizer and check that the
  result is stable when the wavevector grid or bracket changes.

## Thermal magnons

- Decide whether the thermal cloud is a 3D bulk gas or a lower-dimensional
  film gas from the physical wavelength and geometry. For an exchange-dominated
  3D cloud, use the isotropic dispersion
  `epsilon(k) = h * gamma * (H + D*k^2)`.
- Compute number and energy from the Bose-Einstein occupation with a
  three-dimensional density-of-states factor. Convert frequency to joules with
  `h`, and keep the integration wavevector in the units used by `D`.
- Check the spectral gap at the lowest energy, the density scaling with
  temperature, quadrature convergence, and the high-wavevector cutoff.

## Pumped quasi-equilibrium

- Rapid thermalization with conserved magnon number and energy gives two
  conservation equations for the pumped temperature and chemical potential.
  Include the injected energy at the pump frequency.
- Below condensation, solve for `(T, mu)` while enforcing `mu` below the
  spectral minimum. The critical injected density is the increase needed to
  reach that minimum at the reference temperature.
- Above threshold, pin `mu` at the minimum and solve for the thermal
  temperature plus condensate density. Count condensate magnons at the minimum
  energy when enforcing energy conservation, then divide by total density for
  the condensate fraction.
- If one configuration feeds a fitted material parameter into another, pass
  the computed value through rather than substituting a nominal material value.

## Numerical checks

Use SI constants for energies, document any unit conversions, bracket roots
where possible, and verify both number and energy conservation from the final
state. Keep scripts and intermediate calculations general; do not hardcode
expected outputs or task-specific field names.
