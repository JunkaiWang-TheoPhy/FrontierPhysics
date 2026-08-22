# Task Family: Computational and Numerical Physics

This is the default FrontierPhysics family: simulation, calculation, fitting,
inference, optimization, or data analysis with a scientifically meaningful
numerical result.

## Environment

- Bundle the geometry, observations, initial conditions, or datasets.
- Pin numerical libraries and thread counts.
- Use CPU unless GPU behavior is itself part of the task.
- Record coordinate systems, units, species, constants, and model assumptions.
- Set explicit seeds for every stochastic component.

## Oracle

Derive the result through the natural scientific workflow. Save diagnostics
such as residuals, convergence curves, null locations, fit covariance, solver
status, and iteration counts.

## Verifier

Use independent recomputation and physical checks. Good anchors include:

- analytic limits;
- published reference values;
- conservation laws;
- symmetry;
- scaling relations;
- mesh, basis, or timestep convergence;
- uncertainty intervals.

Use tolerance bands justified by numerical or experimental variation. A wrong
primary result should fail even if secondary output structure is correct.

## Mentor skills (development-time control)

The control skill may prescribe algorithms, derivations, software setup, and
diagnostics. It may bundle parameterized solver helpers or derived
intermediates, but not accepted final values.

## Common failure modes

- random seeds applied to only one library;
- hidden coordinate or amplitude conventions;
- fitting at a search boundary without diagnosis;
- reporting angular frequency as ordinary frequency;
- treating a discretization result as converged after one resolution;
- verifier and oracle sharing the same solver implementation.
