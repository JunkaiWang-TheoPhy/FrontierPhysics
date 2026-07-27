---
name: state-discrimination-error-rate
description: Discriminate a vacuum state from a weak coherent state on the IQ plane with a linear threshold, compute the measured error rate, the measured vacuum shot-noise standard deviation, the theoretical shot-noise standard deviation from the displacement and photon number, and the theoretical heterodyne discrimination error rate, then compare measured versus theory.
---

# State discrimination and error rate

Use on the phase-corrected signal cloud and the vacuum cloud. See
`references/discrimination.md`; `scripts/discrimination.py` has the helpers.

## Threshold and error rate (deliverable 5)

Project every point onto the unit vector from the origin to the signal centroid,
put the threshold at half the displacement `d/2`, and count errors:

- signal error: projection `< d/2`;
- vacuum error: projection `> d/2`;
- `error_rate = (signal_errors + vacuum_errors) / total_events`.

## Measured vs theoretical std (deliverable 5)

The measured vacuum shot-noise std is the mean of the two principal standard
deviations of the vacuum cloud (square roots of the covariance eigenvalues).
Given the photon number `N` (from the signal power) and the displacement `d`, the
theoretical std is `d / sqrt(2 N)` (heterodyne: displacement `2 sqrt(N)`, per-axis
std `sqrt(2)`, so `std/displacement = 1/sqrt(2N)`). Report their ratio.

## Theoretical error rate (deliverable 5b)

In heterodyne shot-noise units the signal sits at `2 sqrt(N)` and each axis has
std `sqrt(2)`; discriminating against vacuum with the midpoint threshold gives

    P_err = 0.5 * ( Phi(x_th; 2 sqrt(N), sqrt(2)) + (1 - Phi(x_th; 0, sqrt(2))) ),
    x_th  = sqrt(N)

Compare `measured_error_rate / P_err` (near unity for a shot-noise-limited state).
