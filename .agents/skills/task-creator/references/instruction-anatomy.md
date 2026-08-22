# Anatomy of a FrontierPhysics Prompt

A task prompt is a research brief for a capable colleague. Preserve the
scientific objective while removing lab-notebook fragments, solution hints,
grader details, and implementation-specific commentary.

A FrontierPhysics `task.md` body has two stages — Research & Plan, then
Experiment & Implementation — ending with the deliverables list (canonical
example: `tasks/multiplexing-ion-chain-qnet/task.md`). Deliverables are only
paper-submission or presentable artifacts (`paper.pdf`, `report.pptx`, result
data) — never process files like `PLAN.md`. The research stage is a concise
brief graded by `verifier/rubric.json`; the anatomy below applies to the
implementation stage.

## Required anatomy

1. **Context:** the physical system or research question.
2. **Inputs:** absolute paths, file formats, provenance, and coordinate or unit
   conventions.
3. **Assumptions:** boundary conditions, approximations, species, geometry,
   reference frames, or model regime.
4. **Outputs:** exact paths and artifact schemas.
5. **Acceptance-relevant constraints:** precision, sample count, time window,
   reproducibility, or required diagnostics.

## Prompt versus development-time mentor skill

The prompt defines the problem. A mentor skill — an optional development-time
control, never shipped in the final package — explains a reliable way to solve
it. In the final experiment the agent gets only the prompt, so everything in
the skill column is exactly what the task measures.

Keep these in the prompt:

- what physical quantity or artifact is required;
- units and coordinate conventions;
- model assumptions needed to make the problem well-defined;
- output paths and schemas.

Keep these out of the prompt (in a development-time skill, if you use one):

- recommended algorithms and software;
- derivations and implementation recipes;
- fragile setup steps;
- convergence and debugging guidance.

## Example

Raw research note:

> Use the two middle rails as RF, probably around 80 V at 39 MHz. Find the
> radial frequency, then use alpha for axial confinement and make the transport
> waveform like the paper.

Task prompt:

> Using `/root/surface_trap.stl`, calculate the in-plane radial secular
> frequency of a singly charged `40Ca+` ion for an 80 V RF amplitude at
> 39.15 MHz. Treat the two central rails as the RF electrode and the remaining
> electrodes as ground. Report frequencies in MHz. Use
> \(\alpha=(f_z/f_r)^2=0.00174\) for the axial frequency and write the requested
> transport waveforms to the specified CSV paths.

The rewrite makes the physical model and outputs explicit without prescribing
the BEM implementation or inverse-engineering derivation.

## Source text that may remain verbatim

Equations, constants, instrument readings, table values, and quoted paper
passages may remain verbatim when they are task inputs. The surrounding
instruction should still be concise, human-authored, and free of solution
leakage.
