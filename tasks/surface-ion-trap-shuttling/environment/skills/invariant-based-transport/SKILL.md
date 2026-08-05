---
name: invariant-based-transport
description: Generate zero-final-excitation harmonic-trap transport trajectories using Lewis-Riesenfeld invariant inverse engineering, including concatenated unequal-distance stages and dwell intervals. Use when a task asks for a trap-center waveform, fast ion shuttling, or a piecewise transport CSV.
---

# Invariant-Based Harmonic Transport

Distinguish the designed classical ion trajectory \(q_c(t)\) from the required
trap-center trajectory \(q_0(t)\). The trap center includes an acceleration
correction and is the waveform normally requested for transport control.

## Single move

1. Determine the duration from distance and speed. Numerically,
   `1 um / (1 m/s) = 1 us`.
2. Evaluate the inverse-engineered trap-center function over the closed interval
   from zero to the move duration.
3. Sample the continuous function directly at the requested number of points.

Evaluate the formula with NumPy on the requested time grid and write the result
with Python's `csv` module or pandas.

## Multi-stage chain move

For each adjacent spacing, reuse the same normalized waveform but scale it by
that stage's distance. Add the cumulative distance from all completed stages.
During a dwell, hold the trap center exactly at the reached position. Preserve
continuity at every move/dwell boundary.

Read [references/trajectory.md](references/trajectory.md) for the equations and
piecewise construction.

## Checks

- Start and end positions equal the requested endpoints.
- Velocity and acceleration vanish at both endpoints.
- The trap-center path may overshoot for fast motion; do not clip it.
- A chain waveform ends at the sum of all adjacent spacings.
- Time and position units in the CSV match the requested units.
