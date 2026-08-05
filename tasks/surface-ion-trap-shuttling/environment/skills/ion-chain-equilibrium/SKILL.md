---
name: ion-chain-equilibrium
description: Compute equilibrium positions and adjacent spacings of a one-dimensional Coulomb crystal in a harmonic axial trap. Use when a task specifies ion count, charge, mass, and axial secular frequency and asks for ion-chain positions or spacings.
---

# Ion-Chain Equilibrium

Solve the coupled force-balance equations; do not divide the total chain length
into equal intervals.

## Workflow

1. Convert the axial secular frequency from MHz to angular frequency in rad/s.
2. Solve the dimensionless equilibrium equations for ordered positions.
3. Scale the dimensionless positions by the Coulomb/harmonic length scale.
4. Sort positions and take adjacent differences.

Use a nonlinear root solver such as `scipy.optimize.root` or
`scipy.optimize.least_squares`. Keep the positions ordered and solve at full
precision before converting to micrometers.

## Checks

- A symmetric odd-ion chain has one ion at the origin.
- Adjacent spacings are positive and mirror-symmetric.
- The smallest spacings occur near the center.
- Lower axial frequency increases every spacing with
  \(\omega_z^{-2/3}\) scaling.

Read [references/equilibrium.md](references/equilibrium.md) for the equations
and length scale.
