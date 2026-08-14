# FrontierPhysics Task Ideation Guide

## What Kind of Tasks Are We Looking For?

**FrontierPhysics**: Evaluate agents for end-to-end frontier physics research.

FrontierPhysics is a benchmark evaluating how AI agents do **frontier physics research iteratively**. We evaluate realistic research challenges with iteration loops from **literature deep review** to **research plan implementation**. Tasks come from real research problems that take at least **weeks of effort** for a physics PhD to do deep research and implement, and SOTA LLM agents **struggle** with. The tasks are evaluated with verifiable graders and per-task rubric-based reviewer agents to make sure agents are doing research in ways **aligned with real frontier researchers**. To achieve this, we need contributors from the broad Physics community to add diverse, authetic, challenging, and well-tested task packages.

When doing research, a typical loop is: from **research & planning** -> to **implementation & experiment** -> to **evaluation & feedback**. In this loop, real research is made of many difficult subproblems: running a simulation, analyzing detector data, reproducing a published calculation, designing part of an experiment, testing a hypothesis, or developing a reliable numerical workflow.

A FrontierPhysics task wants to reproduce an entire research project or make an end-to-end scientific discovery. That is the dream but we have to face the reality that when dealing with real world, the **research & planning** -> to **implementation & experiment** -> to **evaluation & feedback** loop can be broken if agent cannot operate real world experiment devices and get feedback signals for its actions. In these cases, especially in experimental physics domains

1. Use digital version of device simulation and mock API to simulate how that device would work: like https://github.com/benchflow-ai/env0 and make sure the device simulation is realistic and obey physics laws.
2. If the whole experiment simulation is too challenging, since the first stage of the task is more about research & planning, we focus on using rubrics (rubric.json) + LLM agent as judge to focus more on evaluation of the experiment planning; device/instrument shopping list planning; etc.

**A project that you have done can be a good FrontierPhysics task if it is a real, challenging, and verifiable end to end physics research.**

The examples below are intentionally **idea-level**. You do not need to define the exact environment, verifier, tolerances, or output schema at this stage. Those details can be worked out later with agents and maintainers.

## Examples by Research Methodology

### 1. Literature, Theory, and Reproduction

Tasks may involve understanding prior work, reproducing a published result (allow agent to access the internet but block the paper access that have the direct answer to this task), extending it to a new regime, or carrying out a theoretical calculation.

**Experimental Physics**

| Domain                | Example task idea                                                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| AMO / Quantum Physics | Review several approaches to increasing remote-entanglement rates and propose a realistic protocol for an existing trapped-ion setup. |
| Detector Physics      | Reproduce a published detector-response study and evaluate whether the method remains valid for a different detector configuration.   |
| Astrophysics          | Reproduce a published observational analysis using public data and test an alternative physical interpretation.                       |

**Theoretical Physics**

| Domain                 | Example task idea                                                                              |
| ---------------------- | ---------------------------------------------------------------------------------------------- |
| Condensed Matter       | Reproduce a published phase diagram or band structure and extend it to a new parameter regime. |
| Gravitational Physics  | Reproduce a published quasinormal-mode calculation for a different coupling or background.     |
| Quantum / Field Theory | Derive an effective model or perturbative result and compare it with known limiting cases.     |

### 2. Simulation and Numerical Computation

A simulation or numerical calculation can itself be the task, even when it is only one component of a larger research project.

**Experimental Physics**

| Domain                | Example task idea                                                                                        |
| --------------------- | -------------------------------------------------------------------------------------------------------- |
| Detector Physics      | Build a Geant4 detector simulation and estimate detection efficiency or background leakage.              |
| AMO / Quantum Physics | Simulate the electric field of a real trap geometry and derive trap frequencies or operating parameters. |
| Accelerator Physics   | Track a particle beam through a lattice and optimize the beam optics under realistic constraints.        |

**Theoretical Physics**

| Domain                | Example task idea                                                                                    |
| --------------------- | ---------------------------------------------------------------------------------------------------- |
| Condensed Matter      | Compute a phase boundary using a lattice, spin, or many-body simulation.                             |
| Gravitational Physics | Compute a quasinormal-mode spectrum while controlling numerical artifacts and convergence.           |
| Plasma Physics        | Numerically solve an instability problem and map the transition between stable and unstable regimes. |

### 3. Data Analysis, Calibration, and Inference

A meaningful stage of experimental, observational, or computational analysis is fully in scope. The task does not need to start from completely raw data.

**Experimental Physics**

| Domain                | Example task idea                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------------ |
| Detector Physics      | Calibrate PMT or SiPM response from raw DAQ waveforms using an appropriate response model.                   |
| Particle Physics      | Construct a signal/background analysis and infer a physics parameter or limit with systematic uncertainties. |
| AMO / Quantum Physics | Analyze spectroscopy data to determine a transition frequency, coherence time, or heating rate.              |
| Astrophysics          | Fit spectra or light curves and infer physical parameters with uncertainties.                                |

**Theoretical Physics**

| Domain                | Example task idea                                                                                     |
| --------------------- | ----------------------------------------------------------------------------------------------------- |
| Computational Physics | Extract scaling parameters or critical behavior from a large set of simulation outputs.               |
| Cosmology             | Infer model parameters from supplied observables, likelihoods, or simulated datasets.                 |
| Gravitational Physics | Track numerical mode families across a parameter scan and identify physically meaningful transitions. |

### 4. Experiment, Hardware, and Control Design

A task may focus on designing or optimizing one scientifically meaningful component of a research workflow. The hardware does not need to be physically built during evaluation.

**Experimental Physics**

| Domain                | Example task idea                                                                                              |
| --------------------- | -------------------------------------------------------------------------------------------------------------- |
| Detector Physics      | Design a low-noise front-end circuit or PCB for a detector with specified signal and noise requirements.       |
| AMO / Quantum Physics | Design an optical setup or ion-shuttling waveform satisfying realistic experimental constraints.               |
| Nuclear Physics       | Design a detector arrangement that optimizes acceptance and coincidence efficiency for a proposed measurement. |
| Accelerator Physics   | Design or optimize a beamline configuration under magnet, aperture, and emittance constraints.                 |

**Theoretical Physics**

| Domain                | Example task idea                                                                                                      |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Quantum Control       | Design a pulse sequence that maximizes theoretical gate fidelity under amplitude, duration, and bandwidth constraints. |
| Computational Physics | Design an adaptive numerical strategy that reaches a required precision under a fixed computational budget.            |
| Plasma Physics        | Design a control strategy predicted by a physical model to suppress a specified instability.                           |

### 5. Hypothesis Testing and Method Validation

Sometimes the research task is to determine whether a claim, approximation, numerical method, or physical interpretation can actually be trusted.

**Experimental Physics**

| Domain                | Example task idea                                                                                                            |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Particle Physics      | Test whether a background model calibrated in one control region extrapolates correctly to another.                          |
| AMO / Quantum Physics | Test whether a simplified heating or decoherence model explains measurements across several experimental settings.           |
| Condensed Matter      | Determine whether an observed feature survives different fitting choices, preprocessing methods, or experimental conditions. |

**Theoretical Physics**

| Domain                | Example task idea                                                                              |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| Gravitational Physics | Test whether an apparent change in a numerical spectrum is physical or a solver artifact.      |
| Condensed Matter      | Test whether a proposed scaling law survives larger system sizes or a wider parameter range.   |
| Plasma Physics        | Test whether an analytic instability threshold agrees with numerical simulations.              |
| Computational Physics | Compare multiple numerical methods and determine which remains reliable in a difficult regime. |

## A Simple Rule of Thumb

A promising task is:

* **Real** — it comes from something a physicist would genuinely need to do in research.
* **Challenging** — it requires meaningful physics reasoning, iteration, or methodological choices.
* **Verifiable** — there is a credible way to determine whether the result is scientifically correct.

A detector simulation, a calibration analysis, a PCB needed for an experiment, a theoretical calculation, or a reproduction of a published result can all be excellent FrontierPhysics tasks ideas.
