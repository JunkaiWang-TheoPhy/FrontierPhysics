# Task Family: Experimental Systems, Controls, and HPC

Use this family for workflows involving instruments, control stacks, DAQ
configuration, job schedulers, simulation clusters, or laboratory automation.

## Examples

- configure a pulse or transport sequence;
- repair a data-acquisition pipeline;
- diagnose a scheduler or MPI configuration that corrupts a simulation;
- tune a control loop against a frozen plant model;
- produce a reproducible batch configuration for a physics code.

## Environment

Prefer local emulators, recorded telemetry, and containerized services over
live laboratory or cloud resources. Pin controller, driver, scheduler, and
compiler versions.

Never require contributors' production credentials. When hardware cannot be
emulated faithfully, bundle a recorded interface trace and state the boundary
clearly.

## Verifier

Exercise the real configuration or control surface where possible. Check:

- state transitions and safety limits;
- timing, units, and channel mappings;
- deterministic replay of recorded telemetry;
- job completion and scientific output integrity;
- absence of unauthorized network or filesystem side effects.

## Mentor skills (development-time control)

Mentor guidance may contain exact setup and recovery procedures. It may not
contain a precomputed accepted configuration whose only purpose is to be copied
into place.

## Common failure modes

- asynchronous readiness mistaken for failure;
- simulated interfaces that omit the hard part of the real workflow;
- resource pressure becoming the primary difficulty;
- hidden dependence on local hardware, licenses, or credentials;
- configuration tests that pass while the resulting science is invalid.
